"""
Functionality to parse publishing point archive
"""
import requests
from lxml import etree
import isodate
from datetime import datetime


EPOCH = datetime(1970, 1, 1, tzinfo=isodate.tzinfo.UTC)


class PubPoint(object):
    def __init__(self, url):
        self.url = url
        # TODO: proper error handling on get + parse
        response = requests.get("{url}/archive".format(url=url))
        if response.status_code == 200:
            self.archive = etree.fromstring(response.content)
        else:
            raise Exception("failed to get or parse pub point archive")

    def get_video_ranges(self):
        """
        return a list of all video ranges in archive
        """
        video_ranges = []
        for c in self.archive.findall(".//{*}video/{*}c"):
            video_ranges.append(
                {
                    "start": isodate.parse_datetime(c.attrib["start"]),
                    "end": isodate.parse_datetime(c.attrib["end"]),
                }
            )
        return video_ranges

    def get_video_chunks(self, chunk_duration):
        """
        return a list of complete chunks
        """
        interval = isodate.parse_duration(chunk_duration)

        video_ranges = self.get_video_ranges()

        complete_chunks = []

        for r in video_ranges:
            start_interval = (r["start"] - EPOCH) // interval
            end_interval = (r["end"] - EPOCH) // interval

            for i in range(start_interval, end_interval):
                complete_chunks.append(
                    {
                        "start": EPOCH + (i * interval),
                        "end": EPOCH + ((i + 1) * interval),
                    }
                )

        return complete_chunks
