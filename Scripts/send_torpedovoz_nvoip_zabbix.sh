#!/bin/sh
set -eu

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
. "$SCRIPT_DIR/nvoip_zabbix_common.sh"

if [ "$#" -lt 2 ]; then
  printf 'Usage: %s <destination> <subject> [message]\n' "$0" >&2
  exit 2
fi

if [ -z "${NVOIP_CALLER:-}" ]; then
  printf 'Missing required variable: NVOIP_CALLER\n' >&2
  exit 1
fi

DESTINATION="$1"
SUBJECT="$2"
ALERT_MESSAGE="${3:-}"
VOICE_MESSAGE="Alerta Zabbix. $SUBJECT"
if [ -n "$ALERT_MESSAGE" ]; then
  VOICE_MESSAGE="$VOICE_MESSAGE. $ALERT_MESSAGE"
fi

ACCESS_TOKEN="$(nvoip_get_access_token)"

curl -sS \
  --request POST \
  --header "Authorization: Bearer $ACCESS_TOKEN" \
  --header "Content-Type: application/json" \
  --data-binary "{
    \"caller\": \"$(nvoip_json_escape "$NVOIP_CALLER")\",
    \"called\": \"$(nvoip_json_escape "$DESTINATION")\",
    \"audios\": [
      {
        \"audio\": \"$(nvoip_json_escape "$VOICE_MESSAGE")\",
        \"positionAudio\": 1
      }
    ],
    \"dtmfs\": []
  }" \
  "$NVOIP_BASE_URL/torpedo/voice"
