#!/bin/sh
set -e


# validate required variables are set
if [ -z "$UspLicenseKey" ]
  then
  echo >&2 "Error: UspLicenseKey environment variable is required but not set."
  exit 1
fi

# first arg is `-f` or `--some-option`
if [ "${1#-}" != "$1" ] || [ $# -eq 0 ]; then
  set -- celery "$@"
fi

exec "$@"
