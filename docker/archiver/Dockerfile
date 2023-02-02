ARG UPSTREAM_DOCKER_IMAGE=docker.io/unifiedstreaming/origin:1.12.1

FROM $UPSTREAM_DOCKER_IMAGE

# Remove Origin and other things we don't want
RUN apk add py3-pip \
&&  apk del \
    apache2 \
    apache2-proxy \
    mod_smooth_streaming \
    mod_unified_s3_auth \
    manifest-edit

# install python and libxml stuff
RUN apk --update add --virtual .build-deps \
        gcc \
        musl-dev \
        python3-dev \
&&  apk add \
        libxml2-dev \
        libxslt-dev \
&&  pip3 install lxml \
&&  apk del .build-deps \
&&  rm -f /var/cache/apk/*

COPY app/ /app

RUN cd /app \
&&  pip3 install -r requirements.txt


COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

WORKDIR /app

# default cmd is just parameters to celery
CMD ["-A", "archiver", "worker", "-l", "info"]
