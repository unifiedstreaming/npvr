# Remix nPVR archiver
POC for nPVR Archiver.

Can manage archives for multiple channels, initiating Unified Capture jobs to
make a permanent archive from a live channel.

This is provided as-is, it is not supported or designed for running in a
production setup.




## Supported features

* configure channels using REST API
* scaleable workers for Capture jobs
* upload to S3 or compatible object store
* view status of jobs through web UI or REST API
* view channel archive status through API

## Not yet implemented

* gap/discontinuity handling
* proper checking of all streams on channel, currently just checks video
* DRM

## Usage

The full stack can be run using Docker Compose to launch all components.

This requires setting a license key to the ``UspLicenseKey`` environment
variable, and then can be run with ``docker-compose up``.

The Origin and demo frontend will then be available at ``http://<address>``,
and the management API will be at ``http://<address>/api/``.

API docs can be viewed at ``http://<address>/api/apidocs``.

### Configure channels

Channels can be configured using the REST API. The API specification can be
seen at `http://<address>/api/apidocs/`

Channels are created or updated by PUTting a JSON configuration, for example:

```json
{
    "channel_url": "https://demo.unified-streaming.com/k8s/live/scte35.isml",
    "chunk_duration": "PT5M",
    "s3_endpoint": "minio:9000",
    "s3_access_key": "minioadmin",
    "s3_secret_key": "minioadmin",
    "s3_bucket": "npvr-demo",
    "s3_region": "default",
    "archive_length": "P7D",
    "secure": false
}
```

An example, if this is running locally and accessed on localhost port 80, which
will set up archiving of our SCTE 35 demo livestream:

```bash
# PUT new channel configuration
$ curl \
    -X PUT \
    -H 'Content-Type: application/json' \
    -d '{"channel_url": "https://demo.unified-streaming.com/k8s/live/scte35.isml", "chunk_duration": "PT5M", "s3_endpoint": "minio:9000", "s3_access_key": "minioadmin", "s3_secret_key": "minioadmin", "s3_bucket": "npvr-demo", "s3_region": "default", "archive_length": "P7D", "secure": false}' \
    http://localhost/api/channel/scte35
```

The Archiver should start creating jobs to archive the new channel.

Note: it is also possible to use another S3 compatible storage system, but then
the Origin and Remix configurations in the Docker Compose file will need to be
updated with the access key details.


### Check jobs

Job states can be viewed at `http://<address>/api/job/`

In progress jobs will be grey, successful green and failed red.

![](archiver_jobs.png)

Click to expand the job details, and also show a link from which the output log
of Unified Capture can be viewed.

## How it works

The POC has the following components:

* [redis](https://redis.io/): data store for job states, results, etc.
* [rabbitmq](https://www.rabbitmq.com): message broker for task queues
* worker: archiver application running a Celery worker
* beat: triggers scheduled Celery tasks
* api: Flask based API & web UI
* origin: Unified Origin for just-in-time packaging
* remix: Remix origin for playlist processing
* remix-proxy: nginx caching proxy for Remix outputs
* minio: S3 compatible storage server to store archive

The `worker`, `beat` and `api` Docker containers are all based on the Archiver
application, but run in different ways to cover their desired purposes.

Every minute the `beat` container triggers a new `master_scheduler` task. This
task iterates over all configured channels and initiates a 
`check_channel_archive` task for each one.

The `check_channel_archive` task will query the `/archive` from the channel URL
and look for complete chunks which should be available for capturing. It checks
if each chunk has already been successfully captured to the permanent archive,
and if not initiates a new `capture` task. It also checks that there are no
other `capture` tasks already in progress for the same chunk to avoid duplicate
jobs.

The `capture` task marks the chunk as being in progress, runs Unified Capture
to capture the chunk to a local temporary file inside the container, then
uploads this file to the channel's configured S3 storage location and deletes
the temp file.

Chunks are stored inside the S3 bucket sorted by channel name and date, e.g.
`scte35/2018-12-06/2018-12-06T12:55:00Z--2018-12-06T13:00:00Z.ismv`

### Task queues

Jobs are managed using [Celery](http://www.celeryproject.org/) task queues,
this allows for easy scaling and management of workflows.

RabbitMQ is used as a message broker, Redis is used for persistent storage of
task results, job status, Unified Capture logs and more.

The Celery task queues can be monitored using Flower, which is available on
`http://<HOST>:5555/`.


## Playback

The API has a SMIL generation endpoint which creates playlists based on a time
range in the request URL.

This is available at `http://<HOST>:81/smil/<CHANNEL>/<START>--<END>.smil`

For example:
```bash
$ curl http://192.168.1.114:81/smil/scte35/2019-07-08T06:00:00Z--2019-07-08T06:04:30Z.smil
```

```xml
<?xml version='1.0' encoding='UTF-8'?>
<smil xmlns="http://www.w3.org/2001/SMIL20/Language">
  <head/>
  <body>
    <seq>
      <video src="http://s3.eu-central-1.amazonaws.com/npvr-archiver-test/scte35/2019-07-08/2019-07-08T05:55:00Z--2019-07-08T06:00:00Z.ismv" clipBegin="wallclock(2019-07-08T06:00:00Z)"/>
      <video src="http://s3.eu-central-1.amazonaws.com/npvr-archiver-test/scte35/2019-07-08/2019-07-08T06:00:00Z--2019-07-08T06:05:00Z.ismv" clipEnd="wallclock(2019-07-08T06:04:30Z)"/>
    </seq>
  </body>
</smil>
```

This SMIL gets used by Remix to create a reference MP4 based on the media
included in the playlist. The Remix reference MP4 is then used like any other
VOD input to Origin, which plays out all the different formats as usual.

This is done through a chain of proxies:

```
client -> origin -> remix-proxy -> remix -> smil api
```

An nginx caching proxy is used between Origin and Remix to avoid processing
each playlist multiple times, which is a relatively intensive process taking
approximately 1 second per hour of content in the playlist, depending on 
the exact content and network and storage I/O.

Origin playback URLs are like so:
* HLS: `http://<HOST>/<CHANNEL>/<START>--<END>.ism/.m3u8`
* DASH: `http://<HOST>/<CHANNEL>/<START>--<END>.ism/.mpd`

For example:

```bash
$ curl http://192.168.1.114/scte35/2019-07-08T06:00:00Z--2019-07-08T06:04:30Z.ism/.m3u8
```
```
#EXTM3U
#EXT-X-VERSION:4
## Created with Unified Streaming Platform (version=1.10.10-18292)

# AUDIO groups
#EXT-X-MEDIA:TYPE=AUDIO,GROUP-ID="audio-aacl-69",NAME="audio",DEFAULT=YES,AUTOSELECT=YES,CHANNELS="1",URI="./2019-07-08T06:00:00Z--2019-07-08T06:04:30Z-audio=69000.m3u8"

# variants
#EXT-X-STREAM-INF:BANDWIDTH=176000,CODECS="mp4a.40.2,avc1.64001F",RESOLUTION=1280x720,FRAME-RATE=25,AUDIO="audio-aacl-69",CLOSED-CAPTIONS=NONE
./2019-07-08T06:00:00Z--2019-07-08T06:04:30Z-video=100000.m3u8

# keyframes
#EXT-X-I-FRAME-STREAM-INF:BANDWIDTH=14000,CODECS="avc1.64001F",RESOLUTION=1280x720,URI="keyframes/2019-07-08T06:00:00Z--2019-07-08T06:04:30Z-video=100000.m3u8"
```

## DRM

Client manifests (.ism) are generated by the `/ism/` endpoint of the API
server.

This is currently hardcoded to generate an .ism with only one option:
`--hls.client_manifest_version 4`.

Logic for setting additional options such as DRM can be implemented in
`archiver/app/archiver/views/ism.py`.
