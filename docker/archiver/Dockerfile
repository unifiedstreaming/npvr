ARG UPSTREAM_DOCKER_IMAGE=docker.io/unifiedstreaming/origin:1.15.16

FROM $UPSTREAM_DOCKER_IMAGE

# install py3-lxml
RUN apk add py3-pip py3-lxml python3


COPY app/ /app

RUN cd /app \
&&  python -m venv /usr/local/venvs/npvr \
&&  source /usr/local/venvs/npvr/bin/activate \
&&  pip3 install -r requirements.txt

ENV VIRTUAL_ENV=/usr/local/venvs/npvr
ENV PATH=${VIRTUAL_ENV}/bin:${PATH}

COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

WORKDIR /app

# default cmd is just parameters to celery
CMD ["-A", "archiver", "worker", "-l", "info"]
