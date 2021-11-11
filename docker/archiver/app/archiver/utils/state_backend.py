from kombu.serialization import dumps, loads
from uuid import uuid4


CHANNEL_CONFIG_HASH = "channels"
IN_PROGRESS_SET = "archiver_in_progress"
CAPTURE_LOG_PREFIX = "capture_log"
JOB_STATE_PREFIX = "archiver_job"
JOB_STATE_TTL = 86400
ARCHIVE_STATE_PREFIX = "archive"

# re-use the existing Celery backend


class StateBackend(object):
    def __init__(self, app):
        self.app = app

    # channel config
    def set_channel(self, channel_name, channel_config):
        _, _, encoded_channel_config = dumps(
            channel_config, serializer=self.app.backend.serializer
        )

        return self.app.backend.client.hset(
            CHANNEL_CONFIG_HASH, channel_name, encoded_channel_config
        )

    def get_channel(self, channel_name):
        channel_config = self.app.backend.client.hget(
            CHANNEL_CONFIG_HASH, channel_name
        )

        decoded_channel_config = loads(
            channel_config,
            content_type=self.app.backend.content_type,
            content_encoding=self.app.backend.content_encoding,
            accept=self.app.backend.accept,
        )

        return decoded_channel_config

    def delete_channel(self, channel_name):
        return self.app.backend.client.hdel(CHANNEL_CONFIG_HASH, channel_name)

    def get_all_channels(self):
        all_channels = self.app.backend.client.hgetall(CHANNEL_CONFIG_HASH)

        decoded_channels = {}

        for channel_name, channel_config in all_channels.items():
            decoded_channel_config = loads(
                channel_config,
                content_type=self.app.backend.content_type,
                content_encoding=self.app.backend.content_encoding,
                accept=self.app.backend.accept,
            )
            decoded_channel_name = str(
                channel_name, self.app.backend.content_encoding
            )
            decoded_channels[decoded_channel_name] = decoded_channel_config

        return decoded_channels

    # in progress archive task management
    def mark_chunk_in_progress(self, chunk):
        return self.app.backend.client.sadd(IN_PROGRESS_SET, chunk)

    def check_chunk_in_progress(self, chunk):
        return self.app.backend.client.sismember(IN_PROGRESS_SET, chunk)

    def mark_chunk_not_in_progress(self, chunk):
        return self.app.backend.client.srem(IN_PROGRESS_SET, chunk)

    # job state
    def set_job_state(self, job):
        """
        set job status, if job_id not specified will create one
        """
        job_key = "{0}_{1}".format(JOB_STATE_PREFIX, job["id"])

        _, _, encoded_job = dumps(job, serializer=self.app.backend.serializer)

        return self.app.backend.client.setex(
            job_key, JOB_STATE_TTL, encoded_job
        )

    def get_job_state(self, id):
        """
        get job state
        """
        job_key = "{0}_{1}".format(JOB_STATE_PREFIX, id)

        job_state = self.app.backend.client.get(job_key)

        decoded_job_state = loads(
            job_state,
            content_type=self.app.backend.content_type,
            content_encoding=self.app.backend.content_encoding,
            accept=self.app.backend.accept,
        )

        return decoded_job_state

    def get_all_jobs(self):
        """
        return a list of all job keys
        """
        return self.app.backend.client.scan_iter(
            match="{0}_*".format(JOB_STATE_PREFIX)
        )

    def get_all_job_states(self):
        job_states = {}

        job_state_keys = self.app.backend.client.scan_iter(
            match="{0}_*".format(JOB_STATE_PREFIX)
        )

        for key in job_state_keys:
            key = str(key, self.app.backend.content_encoding).replace(
                "{0}_".format(JOB_STATE_PREFIX), "", 1
            )
            job_states[key] = self.get_job_state(key)

        return job_states

    # job logs
    def set_capture_log(self, stderr):
        """
        store stderr for capture command
        """
        log_key = "{0}_{1}".format(CAPTURE_LOG_PREFIX, uuid4())

        self.app.backend.client.hset(log_key, "stderr", stderr)

        # set expiry same as job state
        self.app.backend.client.expire(log_key, JOB_STATE_TTL)

        return log_key

    def get_capture_log(self, log_key):

        return {
            "stderr": str(
                self.app.backend.client.hget(log_key, "stderr"),
                self.app.backend.content_encoding,
            )
        }

    def mark_chunk_complete(self, channel, timestamp, chunk):
        return self.app.backend.client.zadd(
            "{0}-{1}".format(ARCHIVE_STATE_PREFIX, channel), {chunk: timestamp}
        )

    def mark_chunk_missing(self, channel, chunk):
        """
        actually just removes the chunk from the list
        """
        return self.app.backend.client.zrem(
            "{0}-{1}".format(ARCHIVE_STATE_PREFIX, channel), chunk
        )

    def get_complete_chunks(self, channel, start, end):
        """
        get complete chunks within given time range
        """
        chunks = self.app.backend.client.zrangebyscore(
            "{0}-{1}".format(ARCHIVE_STATE_PREFIX, channel), start, end
        )
        chunks = [
            str(chunk, self.app.backend.content_encoding) for chunk in chunks
        ]

        return chunks
