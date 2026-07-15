#!/bin/sh
# =====================================================================
# Container entrypoint.
# Bind-mounted host directories (e.g. ./logs) are created by Docker as
# root, which overrides any `chown` done at image-build time. This
# script runs once as root on every container start, fixes ownership
# of the writable directories, then drops privileges to the
# unprivileged `botuser` for the actual application process.
# =====================================================================
set -e

mkdir -p /app/logs /app/temp
chown -R botuser:botuser /app/logs /app/temp

exec gosu botuser "$@"
