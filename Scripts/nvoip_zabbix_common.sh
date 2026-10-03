#!/bin/sh
# NN-5546: authentication and JSON transport live in nvoip_api.py.
nvoip_require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    printf 'Missing required command: %s\n' "$1" >&2
    return 1
  fi
}
