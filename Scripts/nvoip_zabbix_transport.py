#!/usr/bin/env python3
"""Nvoip API transport for the supported Zabbix script entry points."""
import base64
import http.client
import json
import os
import re
import sys
from urllib.parse import urlencode, urlsplit


PASSWORD_GRANT = "password"


class TransportError(Exception):
    pass


def required(config, key):
    value = config.get(key, '').strip()
    if not value:
        raise TransportError('Missing required variable: ' + key)
    return value


def url(value, base=False):
    parsed = urlsplit(value.rstrip('/'))
    if (parsed.scheme != 'https' or not parsed.hostname or parsed.username
            or parsed.password or parsed.query or parsed.fragment):
        raise TransportError('Nvoip URLs must use HTTPS without userinfo, query or fragment')
    if base and parsed.path not in ('/v3', '/v2'):
        raise TransportError('NVOIP_BASE_URL must end in /v3 or /v2; integrations endpoints are retired')
    return parsed


def bounded(config, key, default, maximum):
    try:
        value = int(config.get(key, str(default)))
    except (ValueError, TypeError):
        raise TransportError('Invalid integer configuration: ' + key) from None
    if not 1 <= value <= maximum:
        raise TransportError('Configuration outside supported range: ' + key)
    return value


def classified(status, phase):
    retryable = status in (0, 408, 425, 429) or status >= 500
    kind = 'NVOIP_RETRYABLE' if retryable else 'NVOIP_PERMANENT'
    return TransportError('{} {} failed with HTTP {}'.format(kind, phase, status))


def post(address, body, headers, config, phase, connection_factory=http.client.HTTPSConnection):
    parsed = url(address)
    connection = connection_factory(parsed.hostname, parsed.port or 443,
        timeout=bounded(config, 'NVOIP_HTTP_TIMEOUT', 10, 15))
    try:
        connection.request('POST', parsed.path or '/', body=body, headers=headers)
        response = connection.getresponse()
        data = response.read(65537)
        if not 200 <= response.status < 300:
            raise classified(response.status, phase)
        if len(data) > 65536:
            raise TransportError('NVOIP_PERMANENT ' + phase + ' response is too large')
        try:
            result = json.loads(data)
        except (ValueError, UnicodeError):
            raise TransportError('NVOIP_PERMANENT ' + phase + ' returned invalid JSON') from None
        if not isinstance(result, dict):
            raise TransportError('NVOIP_PERMANENT ' + phase + ' returned invalid JSON object')
        return response.status, result
    except TransportError:
        raise
    except Exception:
        raise TransportError('NVOIP_RETRYABLE ' + phase + ' transport failed; delivery unknown') from None
    finally:
        connection.close()


def get_bearer(config, channel, connection_factory=http.client.HTTPSConnection):
    mode = config.get('NVOIP_AUTH_MODE', 'client_credentials')
    if mode == 'bearer':
        return required(config, 'NVOIP_ACCESS_TOKEN')
    base = config.get('NVOIP_BASE_URL', 'https://api.nvoip.com.br/v3').rstrip('/')
    version = url(base, base=True).path
    client_id = required(config, 'NVOIP_OAUTH_CLIENT_ID')
    credential = required(config, 'NVOIP_OAUTH_CLIENT_SECRET')
    if mode == 'client_credentials':
        auth_url = config.get('NVOIP_AUTH_URL', 'https://api.nvoip.com.br/auth/oauth2/token')
        fields = {'grant_type': mode, 'client_id': client_id}
        scopes = config.get('NVOIP_OAUTH_SCOPES', 'call:make' if channel == 'voice' else 'sms:send')
        if scopes.strip():
            fields['scope'] = scopes
    elif mode == PASSWORD_GRANT and version == '/v2':
        auth_url = config.get('NVOIP_AUTH_URL', base + '/oauth/token')
        fields = {'grant_type': mode, 'username': required(config, 'NVOIP_NUMBERSIP'),
            'password':
                required(config, 'NVOIP_USER_TOKEN')}
    else:
        raise TransportError('NVOIP_AUTH_MODE must be client_credentials or bearer; password requires explicit /v2')
    basic = base64.b64encode((client_id + ':' + credential).encode()).decode('ascii')
    _, result = post(auth_url, urlencode(fields).encode(),
        {'Authorization': 'Basic ' + basic, 'Content-Type': 'application/x-www-form-urlencoded'},
        config, 'oauth', connection_factory)
    token = result.get(
        'access_token'
    )
    if not isinstance(token, str) or not token.strip():
        raise TransportError('NVOIP_PERMANENT oauth response did not include access_token')
    return token


def destination(value, channel):
    if not re.fullmatch(r'\+?[0-9]+', value):
        raise TransportError('Destination must contain digits and an optional leading +')
    value = value.lstrip('+')
    minimum, maximum = (11, 16) if channel == 'sms' else (8, 13)
    if not minimum <= len(value) <= maximum:
        raise TransportError('Invalid destination length')
    return value


def truncate(value, limit):
    # Match the Java/JavaScript length limit without cutting a surrogate pair.
    return value.encode('utf-16-le')[:limit * 2].decode('utf-16-le', errors='ignore')


def payload(channel, args, config):
    if len(args) < (3 if channel == 'sms' else 2):
        raise TransportError('Usage: destination subject message [host]')
    number = destination(args[0], channel)
    subject, message = args[1], args[2] if len(args) > 2 else ''
    if channel == 'sms':
        text = subject + ' - ' + message
        if len(args) > 3 and args[3]:
            text += ' (' + args[3] + ')'
        if not (subject.strip() or message.strip()):
            raise TransportError('Empty SMS')
        return '/sms', {'numberPhone': number, 'message': truncate(' '.join(text.split()),
            bounded(config, 'NVOIP_SMS_MAX_CHARS', 160, 160)), 'flashSms': False}
    caller = required(config, 'NVOIP_CALLER')
    if not re.fullmatch(r'[0-9]{3,13}', caller):
        raise TransportError('NVOIP_CALLER must contain 3 to 13 digits')
    text = 'Alerta Zabbix. ' + subject + ('. ' + message if message else '')
    return '/torpedo/voice', {'caller': caller, 'called': number,
        'audios': [{'audio': truncate(text, bounded(config, 'NVOIP_VOICE_MAX_CHARS', 600, 1000)),
            'positionAudio': 1}], 'dtmfs': []}


def validate_sms(result):
    if result.get('status') != '200 - SMS Enviado com Sucesso':
        # V2/V3 can return provider rejection inside an HTTP 200 JSON body.
        match = re.match(r'^(\d{3})(?:\s|$)', str(result.get('status', '')))
        kind = 'NVOIP_RETRYABLE' if match and int(match[1]) >= 500 else 'NVOIP_PERMANENT'
        raise TransportError(kind + ' sms API acceptance was not confirmed (HTTP 2xx)')


def run(channel, args, config, connection_factory=http.client.HTTPSConnection):
    base = config.get('NVOIP_BASE_URL', 'https://api.nvoip.com.br/v3').rstrip('/')
    url(base, base=True)
    request_path, request_payload = payload(channel, args, config)
    token = get_bearer(config, channel, connection_factory)
    status, result = post(base + request_path, json.dumps(request_payload, ensure_ascii=True).encode(),
        {'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json',
            'X-Nvoip-Integration': 'zabbix'}, config, channel, connection_factory)
    if channel == 'sms':
        validate_sms(result)
    return {'status': 'accepted', 'channel': channel, 'http_status': status,
        'delivery_confirmed': False}


def main(argv=None, config=None):
    argv = sys.argv[1:] if argv is None else argv
    config = os.environ if config is None else config
    try:
        if not argv or argv[0] not in ('sms', 'voice', 'config'):
            raise TransportError('Expected sms, voice or config command')
        if argv[0] == 'config':
            url(config.get('NVOIP_BASE_URL', 'https://api.nvoip.com.br/v3'), base=True)
            get_bearer(config, 'sms')
            print('Nvoip OAuth configuration OK; no notification sent.')
        else:
            print(json.dumps(run(argv[0], argv[1:], config)))
        return 0
    except TransportError as error:
        print(str(error), file=sys.stderr)
    except Exception:
        print('NVOIP_PERMANENT invalid configuration or payload', file=sys.stderr)
    return 1


if __name__ == '__main__':
    sys.exit(main())
