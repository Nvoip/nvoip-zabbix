#!/bin/sh
set -eu

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
. "$SCRIPT_DIR/nvoip_zabbix_common.sh"

if [ -z "${NVOIP_CALLER:-}" ]; then
  printf 'Missing required variable: NVOIP_CALLER\n' >&2
  exit 1
fi

ACCESS_TOKEN="$(nvoip_get_access_token)"

curl -sS \
  --request POST \
  --header "Authorization: Bearer $ACCESS_TOKEN" \
  --header "Content-Type: application/json" \
  --data-binary "{
    \"caller\": \"$(nvoip_json_escape "$NVOIP_CALLER")\",
    \"called\": \"$(nvoip_json_escape "$1")\",
    \"audios\": [
      {
        \"audio\": \"$(nvoip_json_escape "$2")\",
        \"positionAudio\": 1
      }
    ],
    \"dtmfs\": []
  }" \
  "$NVOIP_BASE_URL/torpedo/voice"
