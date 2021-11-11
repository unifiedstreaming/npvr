from flask import jsonify, make_response, render_template, request
from datetime import datetime
import isodate
from archiver import archiver_api, state
from archiver.tasks.archive import cleanup_archive, verify_archive
from archiver.utils.archive import Archive
from archiver.utils.flask_request_helpers import request_wants_json


EPOCH = datetime(1970, 1, 1, tzinfo=isodate.tzinfo.UTC)


@archiver_api.route("/channel/")
def get_all_channels():
    """
    List all channels
    ---
    definitions:
        channel:
            type: object
            properties:
                archive_length:
                    type: string
                channel_url:
                    type: string
                chunk_duration:
                    type: string
                s3_access_key:
                    type: string
                s3_bucket:
                    type: string
                s3_endpoint:
                    type: string
                s3_secret_key:
                    type: string
        channel_list:
            type: object
            properties:
                channel_name:
                    type: array
                    items:
                        $ref: '#/definitions/channel'
    responses:
        200:
            description: List of channels
            schema:
                $ref: '#/definitions/channel_list'
    """
    channels = state.get_all_channels()

    for name, channel in channels.items():
        if "s3_secret_key" in channel:
            channel["s3_secret_key"] = "<REDACTED>"
        if "s3_access_key" in channel:
            channel["s3_access_key"] = "<REDACTED>"

    if request_wants_json(request):
        response = make_response(jsonify(channels))
    else:
        response = make_response(
            render_template("channel.html", channels=channels)
        )
    return response, 200


@archiver_api.route("/channel/<channel_name>")
def get_channel(channel_name):
    """
    Get channel config
    ---
    parameters:
        - name: channel_name
          in: path
          description: channel name
          type: string
          required: true
    responses:
        200:
            description: channel config
            schema:
                $ref: '#/definitions/channel'
        404:
            description: channel not found
            schema:
                type: object
                properties:
                    error:
                        type: string
                        default: channel not found
    """
    channel = state.get_channel(channel_name)

    if channel is not None:
        if "s3_secret_key" in channel:
            channel["s3_secret_key"] = "<REDACTED>"
        if "s3_access_key" in channel:
            channel["s3_access_key"] = "<REDACTED>"
        return make_response(jsonify(channel))
    else:
        return make_response(jsonify({"error": "channel not found"}), 404)


@archiver_api.route("/channel/<channel_name>", methods=["PUT"])
def put_channel(channel_name):
    """
    Create/update channel config
    ---
    parameters:
        - name: channel_name
          in: path
          description: channel name
          type: string
          required: true
        - name: body
          in: body
          required: true
          schema:
            $ref: '#/definitions/channel'
    responses:
        200:
            description: updated channel
            schema:
                type: object
                properties:
                    success:
                        type: string
                        default: updated channel
        201:
            description: created channel
            schema:
                type: object
                properties:
                    success:
                        type: string
                        default: created new channel
        415:
            description: wrong content type
            schema:
                type: object
                properties:
                    error:
                        type: string
                        default: invalid data format, expect application/json
        500:
            description: unknown error
            schema:
                type: object
                properties:
                    error:
                        type: string
                        default: something went wrong
    """
    request_json = request.get_json(silent=True)

    if request_json:
        # check all required fields
        missing_fields = []

        for field in [
            "channel_url",
            "chunk_duration",
            "archive_length",
            "s3_endpoint",
            "s3_bucket",
            "s3_access_key",
            "s3_secret_key",
            "s3_region",
            "secure"
        ]:
            if field not in request_json:
                missing_fields.append(field)

        if len(missing_fields) > 0:
            return make_response(
                jsonify(
                    {
                        "error": "missing required fields: {fields}".format(
                            fields=missing_fields
                        )
                    }
                ),
                400,
            )

        channel_config = {
            x: request_json[x]
            for x in [
                "channel_url",
                "chunk_duration",
                "archive_length",
                "s3_endpoint",
                "s3_bucket",
                "s3_access_key",
                "s3_secret_key",
                "s3_region",
                "secure"
            ]
        }

        set_channel = state.set_channel(channel_name, channel_config)

        if set_channel == 1:
            return make_response(
                jsonify({"success": "created new channel"}), 201
            )
        elif set_channel == 0:
            return make_response(jsonify({"success": "updated channel"}), 200)
        else:
            return make_response(
                jsonify({"error": "something went wrong"}), 500
            )

    return make_response(
        jsonify({"error": "invalid data format, expect application/json"}), 415
    )


@archiver_api.route("/channel/<channel_name>", methods=["DELETE"])
def delete_channel(channel_name):
    """
    Delete a channel
    ---
    parameters:
        - name: channel_name
          in: path
          description: Name of channel
          type: string
          required: true
    responses:
        200:
            description: channel deleted
            schema:
                type: object
                properties:
                    success:
                        type: string
                        default: channel delerted
        404:
            description: channel does not exist
            schema:
                type: object
                properties:
                    error:
                        type: string
                        default: channel does not exist
    """
    deleted = state.delete_channel(channel_name)

    if deleted == 1:
        return make_response(jsonify({"success": "channel deleted"}), 200)
    elif deleted == 0:
        return make_response(jsonify({"error": "channel does not exist"}), 404)


@archiver_api.route("/channel/<channel_name>/archive")
def get_channel_archive(channel_name):
    """
    Get channel archive
    ---
    parameters:
        - name: channel_name
          in: path
          description: channel name
          type: string
          required: true
    definitions:
        archive:
            type: array
            items:
                type: string
    responses:
        200:
            description: Channel archive
            schema:
                $ref: '#/definitions/archive'
    """
    channel = state.get_channel(channel_name)

    if channel is not None:
        channel_archive = Archive(
            channel_name,
            channel["s3_endpoint"],
            channel["s3_access_key"],
            channel["s3_secret_key"],
            channel["s3_bucket"],
            channel["secure"],
        )

        chunks = channel_archive.list_chunks()

        if request_wants_json(request):
            response = make_response(jsonify(chunks))
        else:
            response = make_response(
                render_template(
                    "archive.html", channel=channel_name, chunks=chunks
                )
            )
        return response

    else:
        return make_response(jsonify({"error": "channel not found"}), 404)


@archiver_api.route("/channel/<channel_name>/archive/gaps")
def get_channel_archive_gaps(channel_name):
    """
    Get channel archive gaps
    ---
    parameters:
        - name: channel_name
          in: path
          description: channel name
          type: string
          required: true
    definitions:
        archive:
            type: array
            items:
                type: string
    responses:
        200:
            description: Channel archive
            schema:
                $ref: '#/definitions/archive'
    """
    channel = state.get_channel(channel_name)

    if channel is not None:
        channel_archive = Archive(
            channel_name,
            channel["s3_endpoint"],
            channel["s3_access_key"],
            channel["s3_secret_key"],
            channel["s3_bucket"],
            channel["secure"],
        )

        chunks = channel_archive.list_chunks()

        gaps = []

        now = datetime.now(isodate.UTC)
        start = now - isodate.parse_duration(channel["archive_length"])

        interval = isodate.parse_duration(channel["chunk_duration"])

        start_interval = (start - EPOCH) // interval
        end_interval = (now - EPOCH) // interval

        for i in range(start_interval, end_interval):
            chunk_start = EPOCH + (i * interval)
            chunk_end = EPOCH + ((i + 1) * interval)
            chunk = "{0}/{1}/{2}--{3}.ismv".format(
                channel_name,
                chunk_start.strftime("%Y-%m-%d"),
                chunk_start.isoformat().replace("+00:00", "Z"),
                chunk_end.isoformat().replace("+00:00", "Z"),
            )

            if chunk not in chunks:
                gaps.append(chunk)

        if request_wants_json(request):
            response = make_response(jsonify(gaps))
        else:
            response = make_response(
                render_template(
                    "archive.html", channel=channel_name, chunks=gaps
                )
            )
        return response

    else:
        return make_response(jsonify({"error": "channel not found"}), 404)


@archiver_api.route("/channel/<channel_name>/archive/verify", methods=["POST"])
def verify_channel_archive(channel_name):
    """
    Trigger verification job for channel's archive
    ---
    parameters:
        - name: channel_name
          in: path
          description: channel name
          type: string
          required: true
    responses:
        200:
            description: success
        404:
            description: channel not found
    """
    channel = state.get_channel(channel_name)

    if channel is not None:
        verify_task = verify_archive.s(channel_name).apply_async()
        return make_response(jsonify({"verify_task_id": verify_task.id}), 404)
    else:
        return make_response(jsonify({"error": "channel not found"}), 404)


@archiver_api.route(
    "/channel/<channel_name>/archive/cleanup", methods=["POST"]
)
def cleanup_channel_archive(channel_name):
    """
    Trigger cleanup job for channel's archive
    ---
    parameters:
        - name: channel_name
          in: path
          description: channel name
          type: string
          required: true
    responses:
        200:
            description: success
        404:
            description: channel not found
    """
    channel = state.get_channel(channel_name)

    if channel is not None:
        cleanup_task = cleanup_archive.s(channel_name).apply_async()
        return make_response(
            jsonify({"cleanup_task_id": cleanup_task.id}), 404
        )
    else:
        return make_response(jsonify({"error": "channel not found"}), 404)
