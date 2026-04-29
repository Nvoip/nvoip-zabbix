#!/bin/sh

NVOIP_BASE_URL="${NVOIP_BASE_URL:-https://api.nvoip.com.br/v2}"
NVOIP_BASIC_AUTH="TnZvaXBBcGlWMjpUblp2YVhCQmNHbFdNakl3TWpFPQ=="

nvoip_json_escape() {
  printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g' | tr '\n' ' '
}

nvoip_extract_json_string() {
  printf '%s' "$1" | tr -d '\n' | sed -nE "s/.*\"$2\"[[:space:]]*:[[:space:]]*\"([^\"]+)\".*/\1/p"
}

nvoip_require_zabbix_config() {
  for var_name in NVOIP_NUMBERSIP NVOIP_USER_TOKEN; do
    eval "var_value=\${$var_name:-}"
    if [ -z "$var_value" ]; then
      printf 'Missing required variable: %s\n' "$var_name" >&2
      return 1
    fi
  done
}

nvoip_get_access_token() {
  nvoip_require_zabbix_config || return 1

  response="$(curl -sS \
    --request POST \
    --header "Authorization: Basic $NVOIP_BASIC_AUTH" \
    --header "Content-Type: application/x-www-form-urlencoded" \
    --data "username=$NVOIP_NUMBERSIP&password=$NVOIP_USER_TOKEN&grant_type=password" \
    "$NVOIP_BASE_URL/oauth/token")" || return 1

  token="$(nvoip_extract_json_string "$response" access_token)"
  if [ -z "$token" ]; then
    printf '%s\n' "$response" >&2
    return 1
  fi

  printf '%s\n' "$token"
}
