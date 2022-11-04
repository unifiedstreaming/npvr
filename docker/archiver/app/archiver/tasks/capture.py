from __future__ import absolute_import, unicode_literals
from archiver import app, celery, state
import subprocess
import tempfile
import os
import isodate
from archiver.utils.archive import Archive
from datetime import datetime
from celery.utils.log import get_task_logger


logger = get_task_logger(__name__)

CAPTURE_LOGLEVEL = app.config["CAPTURE_LOGLEVEL"]
CAPTURE_TIMEOUT = app.config["CAPTURE_TIMEOUT"]


@celery.task
def capture(job):
    # mark chunk as in progress
    job_start_time = datetime.utcnow()
    job["start_time"] = job_start_time.isoformat()
    job["start_timestamp"] = job_start_time.timestamp()

    job["stages"]["mark_chunk_in_progress"] = "starting"
    state.set_job_state(job)

    date = isodate.parse_datetime(job["start"]).strftime("%Y-%m-%d")
    chunk = "{0}/{1}/{2}--{3}.ismv".format(
        job["channel_name"], date, job["start"], job["end"]
    )
    job["chunk"] = chunk

    chunk_in_progress = state.check_chunk_in_progress(chunk)

    logger.info("{0} in_progress: {1}".format(chunk, chunk_in_progress))

    if chunk_in_progress:
        job["stages"]["mark_chunk_in_progress"] = "rejected"
        state.set_job_state(job)
        raise Exception("chunk already in progress")

    state.mark_chunk_in_progress(chunk)

    job["stages"]["mark_chunk_in_progress"] = "done"

    # start capture
    job["stages"]["capture"] = "starting"
    state.set_job_state(job)

    meta_filter = 'filter=(type!="meta")'
    capture_url = "{0}/.mpd?vbegin={1}&vend={2}&{3}".format(
        job["channel_url"], job["start"], job["end"], meta_filter
    )

    capture_path = tempfile.mkdtemp()
    file_name = "{0}--{1}.ismv".format(job["start"], job["end"])

    capture_file_path = os.path.join(capture_path, file_name)

    capture_cmd = [
        "/usr/bin/unified_capture",
        "--remix",
        "-v",
        CAPTURE_LOGLEVEL,
        "-o",
        capture_file_path,
        capture_url,
    ]
    job["capture_command"] = capture_cmd
    x = subprocess.run(
        capture_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=CAPTURE_TIMEOUT,
    )
    job["capture_returncode"] = x.returncode
    job["capture_log"] = state.set_capture_log(x.stderr)

    # if capture succeeded then do s3 upload
    if x.returncode == 0:
        job["capture_file_path"] = capture_file_path
        job["stages"]["capture"] = "done"
        job["stages"]["s3_put"] = "starting"
        state.set_job_state(job)

        archive = Archive(
            job["channel_name"],
            job["s3_endpoint"],
            job["s3_access_key"],
            job["s3_secret_key"],
            job["s3_bucket"],
            job["secure"],
        )

        file_stat = os.stat(capture_file_path)

        with open(capture_file_path, "rb") as file_data:
            archive.put_chunk(job["chunk"], file_data, file_stat.st_size)

        if os.path.exists(job["capture_file_path"]):
            os.remove(job["capture_file_path"])
        if os.path.exists(os.path.dirname(job["capture_file_path"])):
            os.rmdir(os.path.dirname(job["capture_file_path"]))
        job["stages"]["s3_put"] = "done"

        state.mark_chunk_complete(
            job["channel_name"],
            isodate.parse_datetime(job["start"]).timestamp(),
            job["chunk"],
        )
    else:
        job["stages"]["capture"] = "failed"
        if os.path.exists(job["capture_file_path"]):
            os.remove(job["capture_file_path"])
        if os.path.exists(os.path.dirname(job["capture_file_path"])):
            os.rmdir(os.path.dirname(job["capture_file_path"]))

    # mark chunk as available
    job["stages"]["mark_chunk_not_in_progress"] = "starting"
    state.set_job_state(job)
    state.mark_chunk_not_in_progress(job["chunk"])
    job["stages"]["mark_chunk_not_in_progress"] = "done"

    job_complete_time = datetime.utcnow()
    job["complete_time"] = job_complete_time.isoformat()
    job["complete_timestamp"] = job_complete_time.timestamp()

    state.set_job_state(job)

    return job
