from flask import jsonify, make_response, render_template, request
from archiver import archiver_api, state
from archiver.utils.flask_request_helpers import request_wants_json


@archiver_api.route("/job/")
def get_all_jobs():
    """
    List all jobs
    ---
    definitions:
        job:
            type: object
            properties:
                id:
                    type: string
                channel_name:
                    type: string
                channel_url:
                    type: string
                start:
                    type: string
                end:
                    type: string
                s3_access_key:
                    type: string
                s3_bucket:
                    type: string
                s3_endpoint:
                    type: string
                s3_secret_key:
                    type: string
                stages:
                    type: object
                start_time:
                    type: string
                start_timestamp:
                    type: number
                chunk:
                    type: string
                capture_command:
                    type: array
                    items:
                        type: string
                capture_returncode:
                    type: integer
                capture_log:
                    type: string
                capture_file_path:
                    type: string
                complete_time:
                    type: string
                complete_timestamp:
                    type: number
        job_list:
            type: object
            properties:
                id:
                    type: array
                    items:
                        $ref: '#/definitions/job'
    responses:
        200:
            description: List of jobs
            schema:
                $ref: '#/definitions/job_list'
    """
    jobs = state.get_all_job_states()

    for name, job in jobs.items():
        if "s3_secret_key" in job:
            job["s3_secret_key"] = "<REDACTED>"
        if "s3_access_key" in job:
            job["s3_access_key"] = "<REDACTED>"
        if "capture_command" in job:
            job["capture_command"] = [
                x for x in job["capture_command"] if "license" not in x
            ]

    if request_wants_json(request):
        response = make_response(jsonify(jobs))
    else:
        response = make_response(render_template("jobs.html", jobs=jobs))
    return response, 200


@archiver_api.route("/job/<job_id>")
def get_job(job_id):
    """
    Get job state
    ---
    parameters:
        - name: job_id
          in: path
          description: job ID
          type: string
          required: true
    responses:
        200:
            description: job
            schema:
                $ref: '#/definitions/job'
        404:
            description: job not found
    """
    job = state.get_job_state(job_id)

    if job is not None:
        if "s3_secret_key" in job:
            job["s3_secret_key"] = "<REDACTED>"
        if "s3_access_key" in job:
            job["s3_access_key"] = "<REDACTED>"
        if "capture_command" in job:
            job["capture_command"] = [
                x for x in job["capture_command"] if "license" not in x
            ]

        return make_response(jsonify(job))
    else:
        return make_response(jsonify({"error": "job not found"}), 404)


@archiver_api.route("/job/<job_id>/capture_log")
def get_job_capture_log(job_id):
    """
    get capture log from a job
    ---
    parameters:
        - name: job_id
          in: path
          description: job ID
          type: string
          required: true
    definitions:
        capture_log:
            type: object
            properties:
                stderr:
                    type: string
    responses:
        200:
            description: capture_log
            schema:
                $ref: '#/definitions/capture_log'
        404:
            description: job not found, or incomplete and no capture log
    """
    job = state.get_job_state(job_id)

    if job is not None:
        if "capture_log" in job:
            capture_log = state.get_capture_log(job["capture_log"])

            if request_wants_json(request):
                return make_response(jsonify(capture_log), 200)
            else:
                return make_response(
                    render_template("capture_log.html", capture=capture_log),
                    200,
                )
        else:
            return make_response(jsonify({"error": "no capture logs"}), 404)
    else:
        return make_response(jsonify({"error": "job not found"}), 404)
