from archiver import archiver_api, app, state
from flask import make_response
import subprocess
import tempfile
import os


REMIX_URL = app.config["REMIX_URL"]
ISM_OPTIONS = "--hls.client_manifest_version=4"


@archiver_api.route("/ism/<channel>/<remix>.ism")
def get_ism(channel, remix):
    """
    unoptimised way to get ism from remote Remix mp4
    """
    remix_url = f"{REMIX_URL}/{channel}/{remix}.mp4"

    ism_path = tempfile.mkdtemp()
    file_name = f"{remix}.ism"

    ism_file_path = os.path.join(ism_path, file_name)

    # need to get S3 auth options from the channel config
    channel_config = state.get_channel(channel)

    mp4split_cmd = [
        "/usr/bin/mp4split",
        ISM_OPTIONS,
        "--s3_access_key",
        channel_config["s3_access_key"],
        "--s3_secret_key",
        channel_config["s3_secret_key"],
        "--s3_region",
        channel_config["s3_region"],
        "-o",
        ism_file_path,
        remix_url
    ]

    x = subprocess.run(
        mp4split_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
    )

    if x.returncode == 0:
        with open(ism_file_path, "r") as f:
            ism = f.read()

        response = make_response(ism)

    else:
        response = make_response(x.stderr, 500)

    if os.path.exists(ism_file_path):
        os.remove(ism_file_path)
    if os.path.exists(os.path.dirname(ism_file_path)):
        os.rmdir(os.path.dirname(ism_file_path))

    return response
