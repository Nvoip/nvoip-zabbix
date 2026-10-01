#!/bin/sh
set -eu
SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
. "$SCRIPT_DIR/nvoip_zabbix_common.sh"
nvoip_transport voice "$@"
