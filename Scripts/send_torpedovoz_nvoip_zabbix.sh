#!/bin/sh
set -eu
SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
. "$SCRIPT_DIR/nvoip_zabbix_common.sh"
nvoip_require_command python3
exec python3 "$SCRIPT_DIR/nvoip_api.py" voice "$@"
