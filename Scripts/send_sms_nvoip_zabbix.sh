#!/bin/sh
set -eu

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
. "$SCRIPT_DIR/nvoip_zabbix_common.sh"

nvoip_require_command cut || exit 1

if [ "$#" -lt 3 ]; then
  printf 'Usage: %s <destination> <subject> <message> [host]\n' "$0" >&2
  exit 2
fi

DESTINATION="$1"
SUBJECT="$2"
ALERT_MESSAGE="$3"
HOST_NAME="${4:-}"
MESSAGE="$SUBJECT - $ALERT_MESSAGE"
if [ -n "$HOST_NAME" ]; then
  MESSAGE="$MESSAGE ($HOST_NAME)"
fi

# API v2 rejects SMS content above 160 chars.
SMS_MAX_CHARS="${NVOIP_SMS_MAX_CHARS:-160}"
MESSAGE="$(printf '%s' "$MESSAGE" | cut -c "1-$SMS_MAX_CHARS")"

ACCESS_TOKEN="$(nvoip_get_access_token)"

curl -sS \
  --request POST \
  --header "Authorization: Bearer $ACCESS_TOKEN" \
  --header "Content-Type: application/json" \
  --data-binary "{
    \"numberPhone\": \"$(nvoip_json_escape "$DESTINATION")\",
    \"message\": \"$(nvoip_json_escape "$MESSAGE")\",
    \"flashSms\": false
  }" \
  "$NVOIP_BASE_URL/sms"
