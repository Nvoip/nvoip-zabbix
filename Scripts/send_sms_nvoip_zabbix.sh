#!/bin/sh
set -eu

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
. "$SCRIPT_DIR/nvoip_zabbix_common.sh"

ACCESS_TOKEN="$(nvoip_get_access_token)"
MESSAGE="$2 $3 $4"

curl -sS \
  --request POST \
  --header "Authorization: Bearer $ACCESS_TOKEN" \
  --header "Content-Type: application/json" \
  --data-binary "{
    \"numberPhone\": \"$(nvoip_json_escape "$1")\",
    \"message\": \"$(nvoip_json_escape "$MESSAGE")\",
    \"flashSms\": false
  }" \
  "$NVOIP_BASE_URL/sms"
