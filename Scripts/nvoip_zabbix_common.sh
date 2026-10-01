#!/bin/sh

nvoip_transport() {
  if ! command -v python3 >/dev/null 2>&1; then
    printf 'Missing required command: python3\n' >&2
    return 1
  fi
  exec python3 "$SCRIPT_DIR/nvoip_zabbix_transport.py" "$@"
}
