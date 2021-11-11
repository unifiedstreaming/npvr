"""
Master scheduler task
"""
from archiver import celery, state
from archiver.utils.pub_point import PubPoint
from archiver.utils.archive import Archive
from . import capture, archive
from uuid import uuid4
from celery.utils.log import get_task_logger


logger = get_task_logger(__name__)


@celery.task
def master_scheduler():
    """
    Fires off archive comparison tasks for each channel
    """
    channels = state.get_all_channels()

    if not channels:
        logger.info("No channels configured, nothing to do")
        return

    for channel, config in channels.items():
        check_channel_archive.s(channel, config).apply_async()


@celery.task
def check_channel_archive(channel, config):
    """
    Checks channel by comparing the /archive to what is already archived
    If there are any new chunks available that aren't stored then trigger new
    capture task
    """
    pp = PubPoint(config["channel_url"])
    archive = Archive(
        channel,
        config["s3_endpoint"],
        config["s3_access_key"],
        config["s3_secret_key"],
        config["s3_bucket"],
        config["secure"],
    )

    chunks = pp.get_video_chunks(config["chunk_duration"])

    capture_tasks = []

    for chunk in chunks:
        if not archive.check_chunk_in_archive(chunk["start"], chunk["end"]):
            chunk_name = "{0}/{1}/{2}--{3}.ismv".format(
                channel,
                chunk["start"].strftime("%Y-%m-%d"),
                chunk["start"].isoformat().replace("+00:00", "Z"),
                chunk["end"].isoformat().replace("+00:00", "Z"),
            )
            chunk_in_progress = state.check_chunk_in_progress(chunk_name)
            logger.info(
                "{0} in_progress: {1}".format(chunk_name, chunk_in_progress)
            )
            if not chunk_in_progress:
                job = {
                    "id": uuid4(),
                    "channel_name": channel,
                    "channel_url": config["channel_url"],
                    "start": chunk["start"],
                    "end": chunk["end"],
                    "s3_endpoint": config["s3_endpoint"],
                    "s3_access_key": config["s3_access_key"],
                    "s3_secret_key": config["s3_secret_key"],
                    "s3_bucket": config["s3_bucket"],
                    "secure": config["secure"],
                    "stages": {},
                }

                capture_task = capture.capture.s(job).apply_async()

                capture_tasks.append(repr(capture_task))

    if len(capture_tasks) == 0:
        logger.info("No gaps in archive which can be filled.")

    return capture_tasks


@celery.task
def archive_maintenance():
    """
    Triggers archive verification and cleanup for each channel
    """
    channels = state.get_all_channels()

    if not channels:
        logger.info("No channels configured, nothing to do")
        return

    for channel, config in channels.items():
        archive.verify_archive.s(channel).apply_async()
        archive.cleanup_archive.s(channel).apply_async()
