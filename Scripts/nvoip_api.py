"""NN-5546: legacy Zabbix script entrypoints using scoped OAuth and API v3."""
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

API_URL = "https://api.nvoip.com.br/v3"
TOKEN_URL = "https://api.nvoip.com.br/auth/oauth2/token"

class ApiError(Exception):
    pass

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def required(env, key):
    value = env.get(key, "").strip()
    if not value:
        raise ApiError("Missing required variable: " + key)
    return value


def request_json(url, payload, headers, transport=None):
    request = urllib.request.Request(url, data=payload, headers=headers, method="POST")
    opener = transport or urllib.request.build_opener(NoRedirect()).open
    try:
        with opener(request, timeout=20) as response:
            if not 200 <= response.status < 300:
                raise ApiError("Nvoip request failed with HTTP " + str(response.status))
            return json.load(response)
    except urllib.error.HTTPError as error:
        raise ApiError("Nvoip request failed with HTTP " + str(error.code)) from None
    except (urllib.error.URLError, TimeoutError, OSError):
        raise ApiError("Nvoip transport failed; delivery unknown") from None
    except (ValueError, TypeError):
        raise ApiError("Nvoip returned invalid JSON") from None


def access_token(env, transport=None):
    # No password grant, numbersip/usertoken, or fallback to legacy credentials.
    body = urllib.parse.urlencode({
        "grant_type": "client_credentials",
        "client_id": required(env, "NVOIP_OAUTH_CLIENT_ID"),
        "client_secret": required(env, "NVOIP_OAUTH_CLIENT_SECRET"),
    }).encode()
    result = request_json(TOKEN_URL, body, {"Content-Type": "application/x-www-form-urlencoded"}, transport)
    token = result.get("access_token") if isinstance(result, dict) else None
    if not isinstance(token, str) or not token or any(c.isspace() for c in token):
        raise ApiError("OAuth response did not include a valid access_token")
    return token


def send(mode, args, env, transport=None):
    if env.get("NVOIP_BASE_URL", API_URL).rstrip("/") != API_URL:
        raise ApiError("NVOIP_BASE_URL must use the API v3 canonical URL")
    payload = None
    if mode in ("sms", "voice"):
        minimum = 3 if mode == "sms" else 2
        if len(args) < minimum or not re.fullmatch(r"[0-9]{8,15}", args[0]):
            raise ApiError("Expected international destination, subject and message (message optional for voice)")
        if mode == "sms":
            template = required(env, "NVOIP_SMS_TEMPLATE_ID")
            if not template.isdecimal() or not 0 < int(template) <= 2147483647:
                raise ApiError("NVOIP_SMS_TEMPLATE_ID must be a positive template ID")
            variables = [args[1], args[2], args[3] if len(args) > 3 else ""]
            if env.get("NVOIP_SMS_TEMPLATE_LAYOUT") == "zabbix":
                if len(args) != 4 or len(args[3].split("\t")) != 9:
                    raise ApiError("Expected the nine Zabbix event metadata fields")
                name, host, severity, event_id, when, value, updated, recovered_when, updated_when = args[3].split("\t")
                mode = "update" if updated == "1" else ("recovery" if value == "0" else "problem")
                template = required(env, "NVOIP_SMS_" + mode.upper() + "_TEMPLATE_ID")
                if not template.isdecimal() or not 0 < int(template) <= 2147483647:
                    raise ApiError("Invalid approved Zabbix template ID")
                when = updated_when if mode == "update" else recovered_when if mode == "recovery" else when
                if not re.fullmatch(r"[0-9]{4}\.[0-9]{2}\.[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}", when):
                    raise ApiError("Invalid Zabbix event date/time")
                fields = [name, host, severity, event_id]
                if any(not field.strip() or re.search(r"\{(?:EVENT|HOST)\.", field) for field in fields):
                    raise ApiError("Unresolved Zabbix event metadata")
                variables = [" ".join(field.split())[:limit] for field, limit in zip(fields, [40, 20, 12, 20])]
                variables.append(when.replace(".", "-"))
            payload = {"templateId": int(template), "phoneNumber": args[0], "variables": variables}
            path = "/sms/sendTemplate"
        else:
            caller = required(env, "NVOIP_CALLER")
            if not re.fullmatch(r"[0-9]{8,15}", caller):
                raise ApiError("NVOIP_CALLER must be an authorized caller number")
            message = "Alerta Zabbix. " + args[1] + (". " + args[2] if len(args) > 2 else "")
            payload = {"caller": caller, "called": args[0],
                       "audios": [{"audio": message, "positionAudio": 1}], "dtmfs": []}
            path = "/torpedo/voice"
    elif mode != "check":
        raise ApiError("Unsupported operation")
    token = access_token(env, transport)
    if payload is None:
        return "Nvoip OAuth configuration OK."
    result = request_json(API_URL + path, json.dumps(payload, ensure_ascii=False).encode(),
                          {"Authorization": "Bearer " + token, "Content-Type": "application/json; charset=utf-8",
                           "X-Nvoip-Integration": "zabbix"}, transport)
    if mode == "sms" and (not isinstance(result, dict) or result.get("accepted") is not True
                           or result.get("smsStatus") != "200 - SMS Enviado com Sucesso"):
        raise ApiError("SMS API acceptance was not confirmed (HTTP 2xx)")
    if mode == "voice" and (not isinstance(result, dict) or result.get("error")
                            or result.get("status") not in {"queued", "success"}):
        raise ApiError("Voice API acceptance was not confirmed (HTTP 2xx)")
    return "Nvoip API accepted the request; recipient delivery is not confirmed."


if __name__ == "__main__":
    try:
        print(send(sys.argv[1] if len(sys.argv) > 1 else "", sys.argv[2:], os.environ))
    except ApiError as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
