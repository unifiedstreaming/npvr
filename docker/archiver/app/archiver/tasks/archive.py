"""
Archive validation and cleanup tasks
"""
from archiver import celery, state
from datetime import datetime
import isodate
from archiver.utils.archive import Archive
from celery.utils.log import get_task_logger


logger = get_task_logger(__name__)

EPOCH = datetime(1970, 1, 1, tzinfo=isodate.tzinfo.UTC)


@celery.task
def verify_archive(channel_name):
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

        logger.info(f"verifying archive for channel: {channel_name}")

        now = datetime.now(isodate.UTC)
        start = now - isodate.parse_duration(channel["archive_length"])

        interval = isodate.parse_duration(channel["chunk_duration"])

        start_interval = (start - EPOCH) // interval
        end_interval = (now - EPOCH) // interval

        archive_chunks = channel_archive.list_chunks_between(start, now)

        for i in range(start_interval, end_interval):
            chunk_start = EPOCH + (i * interval)
            chunk_end = EPOCH + ((i + 1) * interval)
            chunk = "{0}/{1}/{2}--{3}.ismv".format(
                channel_name,
                chunk_start.strftime("%Y-%m-%d"),
                chunk_start.isoformat().replace("+00:00", "Z"),
                chunk_end.isoformat().replace("+00:00", "Z"),
            )

            logger.info(f"checking chunk: {chunk}")

            chunk_in_archive = chunk in archive_chunks

            logger.info(f"in archive: {chunk_in_archive}")
            if chunk_in_archive:
                # mark complete
                state.mark_chunk_complete(
                    channel_name, chunk_start.timestamp(), chunk
                )
            else:
                # mark missing
                state.mark_chunk_missing(channel_name, chunk)

        return "verified channel {0} archive".format(channel_name)


@celery.task
def cleanup_archive(channel_name):
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

        # get all chunks older than the channel archive_length
        chunks_to_delete = state.get_complete_chunks(
            "scte35",
            0,
            (
                datetime.now()
                - isodate.parse_duration(channel["archive_length"])
            ).timestamp(),
        )

        for chunk in chunks_to_delete:
            logger.info(f"deleting chunk: {chunk}")
            channel_archive.delete_chunk(chunk)
            state.mark_chunk_missing(channel_name, chunk)
            logger.info(f"deleted chunk: {chunk}")

        return "cleaned channel {0} archive, deleting {1} chunks".format(
            channel_name, len(chunks_to_delete)
        )
