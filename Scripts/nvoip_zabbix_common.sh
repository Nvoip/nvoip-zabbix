#!/bin/sh
# NN-5546: authentication and JSON transport live in nvoip_api.py.
nvoip_require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    printf 'Missing required command: %s\n' "$1" >&2
    return 1
  fi
}

# Administrators can install this root-controlled file outside the web root.
NVOIP_OAUTH_ENV_FILE="${NVOIP_OAUTH_ENV_FILE:-/etc/zabbix/nvoip-oauth.env}"
if [ -r "$NVOIP_OAUTH_ENV_FILE" ]; then
  set -a
  . "$NVOIP_OAUTH_ENV_FILE"
  set +a
fi
