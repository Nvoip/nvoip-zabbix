#!/bin/sh
set -eu

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
. "$SCRIPT_DIR/nvoip_zabbix_common.sh"

ACCESS_TOKEN="$(nvoip_get_access_token)"
if [ -n "$ACCESS_TOKEN" ]; then
  printf 'Nvoip OAuth configuration OK.\n'
fi
