#!/bin/sh

NVOIP_BASE_URL="${NVOIP_BASE_URL:-https://api.nvoip.com.br/v2}"

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

nvoip_resolve_basic_auth() {
  if [ -n "${NVOIP_OAUTH_BASIC_AUTH:-}" ]; then
    printf '%s\n' "$NVOIP_OAUTH_BASIC_AUTH"
    return 0
  fi

  if [ -z "${NVOIP_OAUTH_CLIENT_ID:-}" ] || [ -z "${NVOIP_OAUTH_CLIENT_SECRET:-}" ]; then
    printf 'Missing required OAuth configuration. Use NVOIP_OAUTH_CLIENT_ID + NVOIP_OAUTH_CLIENT_SECRET or NVOIP_OAUTH_BASIC_AUTH.\n' >&2
    return 1
  fi

  printf '%s' "$NVOIP_OAUTH_CLIENT_ID:$NVOIP_OAUTH_CLIENT_SECRET" | base64 | tr -d '\n'
}

nvoip_get_access_token() {
  nvoip_require_zabbix_config || return 1
  basic_auth="$(nvoip_resolve_basic_auth)" || return 1

  response="$(curl -sS \
    --request POST \
    --header "Authorization: Basic $basic_auth" \
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
