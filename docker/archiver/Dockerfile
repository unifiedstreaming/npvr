ARG UPSTREAM_DOCKER_IMAGE=docker.io/unifiedstreaming/origin:1.11.9

FROM $UPSTREAM_DOCKER_IMAGE

# install python and libxml stuff
RUN apk --update add --virtual .build-deps \
        gcc \
        musl-dev \
        python3-dev \
 && apk add \
        libxml2-dev \
        libxslt-dev \
        python3 \
 && pip3 install lxml \
 && apk del .build-deps \
 && rm -f /var/cache/apk/*

# Remove Origin and other things we don't want
RUN apk del \
       apache2 \
       apache2-proxy \
       mod_smooth_streaming \
       mod_unified_s3_auth \
       manifest-edit

COPY app/ /app

RUN cd /app \
 && pip3 install -r requirements.txt


COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

WORKDIR /app

# default cmd is just parameters to celery
CMD ["-A", "archiver", "worker", "-l", "info"]
