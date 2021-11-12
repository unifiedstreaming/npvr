"""
SMIL generation endpoint
TODO:
* multiple ranges in single clip
"""
from datetime import datetime
from archiver import archiver_api, state
from archiver.utils.smil import SMIL, SMILItem
from flask import make_response
from isodate import parse_datetime, parse_duration, tzinfo


EPOCH = datetime(1970, 1, 1, tzinfo=tzinfo.UTC)


@archiver_api.route("/smil/")
def smil_alive():
    return make_response("alive")


@archiver_api.route("/smil/<channel>/<start>--<end>")
@archiver_api.route("/smil/<channel>/<start>--<end>.smil")
def timerange_smil(channel, start, end):
    """
    SMIL endpoint
    Request with start and end parameters formatted as ISO 8601 interval,
    e.g. 2019-03-21T12:03:00Z--2019-03-21T13:04:00Z
    ---
    parameters:
        - name: channel
          in: path
          description: channel name
          type: string
          required: true
        - name: start
          in: path
          description: start datetime (iso 8601)
          type: string
          required: true
        - name: end
          in: path
          description: start datetime (iso 8601)
          type: string
          required: true
    definitions:
        smil:
            type: string
    responses:
        200:
            description: smil
            content:
                application/xml:
                    schema:
                        $ref: '#/definitions/smil'
    """
    start = parse_datetime(start)
    end = parse_datetime(end)

    return smil(channel, start, end)


@archiver_api.route("/smil/<channel>/fixed.smil")
def fixed_smil(channel):
    now = datetime.now(tz=tzinfo.UTC)
    start = now - parse_duration("PT1H")
    end = now - parse_duration("PT55M")

    return smil(channel, start, end)


def smil(channel, start, end):
    channel_config = state.get_channel(channel)

    if not channel_config:
        return make_response("invalid channel", 404)

    interval = parse_duration(channel_config["chunk_duration"])

    smil = SMIL()

    start_interval = (start - EPOCH) // interval
    end_interval = (end - EPOCH) // interval

    # if start of first clip aligns exactly with expected boundary include
    # previous clip
    if start == (EPOCH + (start_interval * interval)):
        start_interval = start_interval - 1

    chunks = state.get_complete_chunks(
        channel,
        int((EPOCH + (start_interval * interval)).timestamp()),
        int((EPOCH + (end_interval * interval)).timestamp()),
    )

    for chunk in chunks:
        c = SMILItem(
            src=(
                f"http://{channel_config['s3_endpoint']}/"
                f"{channel_config['s3_bucket']}/"
                f"{chunk}"
            )
        )

        smil.append(c)

    if len(chunks) > 0:
        # set clipBegin and clipEnd for first and last items
        smil[0].begin = start
        smil[-1].end = end

    response = make_response(str(smil))
    response.headers["Content-Type"] = "application/xml"

    return response
