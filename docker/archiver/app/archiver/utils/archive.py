from minio import Minio
from minio.error import S3Error
import isodate
import datetime


class Archive(object):
    def __init__(
        self,
        channel_name,
        s3_endpoint,
        s3_access_key,
        s3_secret_key,
        s3_bucket,
        secure=True,
    ):
        self.minio_client = Minio(
            s3_endpoint,
            access_key=s3_access_key,
            secret_key=s3_secret_key,
            secure=secure,
        )
        self.bucket = s3_bucket
        if not self.minio_client.bucket_exists(self.bucket):
            self.minio_client.make_bucket(self.bucket)
        self.channel_name = channel_name

    def check_chunk_in_archive(self, start, end):
        """
        check if given chunk is already in archive
        """
        # convert string input to datetime
        if isinstance(start, str):
            start = datetime.fromisoformat(start)
        if isinstance(end, str):
            end = datetime.fromisoformat(end)

        date = start.strftime("%Y-%m-%d")
        start_str = start.isoformat().replace("+00:00", "Z")
        end_str = end.isoformat().replace("+00:00", "Z")

        chunk = "{0}/{1}/{2}--{3}.ismv".format(
            self.channel_name, date, start_str, end_str
        )

        # TODO: actual error handling
        try:
            ob = self.minio_client.stat_object(self.bucket, chunk)
            if ob.object_name == chunk:
                return True
        except S3Error:
            return False

    def put_chunk(self, chunk, data, length):
        """
        Put chunk in archive
        """
        # TODO: actual error handling
        put = self.minio_client.put_object(self.bucket, chunk, data, length)
        if put:
            return put

    def list_chunks(self, date=""):
        """
        list all chunks in archive, optionally restrict to single date
        """
        if isinstance(date, datetime.date):
            date = date.strftime("%Y-%m-%d")

        chunks = self.minio_client.list_objects(
            self.bucket, prefix=f"{self.channel_name}/{date}", recursive=True
        )
        return [c.object_name for c in chunks]

    def list_chunks_between(self, start, end):
        """
        list all chunks between (inclusive) two dates
        """
        # type checking/forcing
        if isinstance(start, datetime.datetime):
            start = start.date()
        if isinstance(end, datetime.datetime):
            end = end.date()
        if not isinstance(start, datetime.date) or not isinstance(
            end, datetime.date
        ):
            raise TypeError("start and end must be dates")

        dates = [
            start + datetime.timedelta(days=x)
            for x in range((end - start).days + 1)
        ]

        chunks = [
            chunk
            for date_chunks in [self.list_chunks(date) for date in dates]
            for chunk in date_chunks
        ]

        return chunks

    def delete_chunk(self, chunk):
        """
        delete a chunk from the archive
        """
        # TODO: error handling
        # TODO: verify object exists before delete and is gone after
        self.minio_client.remove_object(self.bucket, chunk)

        return True
