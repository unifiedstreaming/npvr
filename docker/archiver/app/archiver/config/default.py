# default config can be overriden by OS env vars
import os

# celery config stuff

if "CELERY_BROKER_URL" in os.environ:
    broker_url = os.environ["CELERY_BROKER_URL"]
else:
    broker_url = "pyamqp://guest@rabbitmq"

if "CELERY_RESULT_BACKEND" in os.environ:
    result_backend = os.environ["CELERY_RESULT_BACKEND"]
else:
    result_backend = "redis://redis"

# json serializer is more secure than the default pickle
task_serializer = "json"
accept_content = ["json"]
result_serializer = "json"

# Use UTC instead of localtime
enable_utc = True

# celery periodic tasks
beat_schedule = {
    "master-every-min": {
        "task": "archiver.tasks.scheduler.master_scheduler",
        "schedule": 60,
        "options": {"expires": 5},
    },
    "archive-maintenance-daily": {
        "task": "archiver.tasks.scheduler.archive_maintenance",
        "schedule": 86400,
    },
}

# flask and general app config

# Unified Capture log level
if "CAPTURE_LOGLEVEL" in os.environ:
    CAPTURE_LOGLEVEL = os.environ["CAPTURE_LOGLEVEL"]
else:
    CAPTURE_LOGLEVEL = "3"

# Capture timeout in seconds, kill any captures taking longer than this
if "CAPTURE_TIMEOUT" in os.environ:
    CAPTURE_TIMEOUT = int(os.environ["CAPTURE_TIMEOUT"])
else:
    CAPTURE_TIMEOUT = 300

if "REMIX_URL" in os.environ:
    REMIX_URL = os.environ["REMIX_URL"]
else:
    REMIX_URL = "http://remix-proxy"
