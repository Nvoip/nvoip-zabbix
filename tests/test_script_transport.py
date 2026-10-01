import importlib.util
import json
import os
import subprocess
import unittest
from pathlib import Path
from urllib.parse import parse_qs

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('transport', ROOT / 'Scripts/nvoip_zabbix_transport.py')
transport = importlib.util.module_from_spec(spec)
spec.loader.exec_module(transport)


class FakeNetwork:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = []
        self.closed = 0

    def connect(self, host, port, timeout):
        owner = self

        class Connection:
            def request(self, method, path, body, headers):
                owner.calls.append({'host': host, 'path': path, 'body': body, 'headers': headers})

            def getresponse(self):
                item = owner.responses.pop(0)
                if isinstance(item, Exception):
                    raise item

                class Response:
                    status = item[0]

                    def read(self, limit):
                        body = item[1]
                        return body if isinstance(body, bytes) else json.dumps(body).encode()
                return Response()

            def close(self):
                owner.closed += 1
        return Connection()


OAUTH_BODY = {
    'access_token': 'dummy',
}
ACCEPTED = (200, {'status': '200 - SMS Enviado com Sucesso', 'mensagem': 'not-to-be-logged'})
ARGS = ['+5511999999999', 'High: teste', 'Aspas "á" e barra \\ \t' + '🙂' * 200]
BEARER = {'NVOIP_AUTH_MODE': 'bearer', 'NVOIP_ACCESS_TOKEN': 'dummy'}


class ScriptTransportTest(unittest.TestCase):
    def test_default_v3_oauth_grant_and_json_payload(self):
        network = FakeNetwork((200, OAUTH_BODY), ACCEPTED)
        result = transport.run('sms', ARGS,
            {'NVOIP_OAUTH_CLIENT_ID': 'dummy-client', 'NVOIP_OAUTH_CLIENT_SECRET': 'dummy-credential'},
            network.connect)
        self.assertEqual(network.calls[0]['path'], '/auth/oauth2/token')
        fields = parse_qs(network.calls[0]['body'].decode())
        self.assertEqual(fields['grant_type'], ['client_credentials'])
        self.assertEqual(fields['scope'], ['sms:send'])
        self.assertNotIn('password', fields)
        self.assertEqual(network.calls[1]['path'], '/v3/sms')
        sent = json.loads(network.calls[1]['body'])
        self.assertIn('Aspas "á" e barra \\', sent['message'])
        self.assertLessEqual(len(sent['message'].encode('utf-16-le')) // 2, 160)
        self.assertEqual(sent['numberPhone'], '5511999999999')
        self.assertEqual(result['status'], 'accepted')
        self.assertFalse(result['delivery_confirmed'])
        self.assertNotIn('dummy', json.dumps(result))
        self.assertNotIn('not-to-be-logged', json.dumps(result))
        self.assertEqual(network.closed, 2)

    def test_http_and_business_rejections_fail_without_retry_or_body(self):
        for response in (
            (403, b'<html>Just a moment... private-body</html>'),
            (429, {'detail': 'private-body'}),
            (503, {'detail': 'private-body'}),
            (200, {'status': '400 - Saldo Insuficiente', 'mensagem': 'private-body'}),
            (200, {'status': '500 - Erro ao enviar SMS', 'mensagem': 'private-body'}),
            (200, {}), (200, []), (200, b'private-body'),
        ):
            with self.subTest(response=response):
                network = FakeNetwork(response)
                with self.assertRaises(transport.TransportError) as error:
                    transport.run('sms', ARGS, BEARER, network.connect)
                self.assertNotIn('private-body', str(error.exception))
                self.assertEqual(len(network.calls), 1)
                self.assertEqual(network.closed, 1)

    def test_missing_credentials_and_oauth_error_do_not_send_sms(self):
        network = FakeNetwork()
        with self.assertRaisesRegex(transport.TransportError, 'NVOIP_OAUTH_CLIENT_ID'):
            transport.run('sms', ARGS, {}, network.connect)
        self.assertEqual(network.calls, [])
        network = FakeNetwork((401, {'detail': 'private-credential'}))
        with self.assertRaisesRegex(transport.TransportError, 'oauth failed with HTTP 401'):
            transport.run('sms', ARGS, {'NVOIP_OAUTH_CLIENT_ID': 'dummy', 'NVOIP_OAUTH_CLIENT_SECRET': 'dummy'}, network.connect)
        self.assertEqual(len(network.calls), 1)

    def test_timeout_error_is_sanitized_and_not_retried(self):
        network = FakeNetwork(TimeoutError('private-credential private-body'))
        with self.assertRaises(transport.TransportError) as error:
            transport.run('sms', ARGS, BEARER, network.connect)
        self.assertIn('delivery unknown', str(error.exception))
        self.assertNotIn('private-', str(error.exception))
        self.assertEqual(len(network.calls), 1)

    def test_retired_endpoint_invalid_limit_and_destination_fail_before_network(self):
        for config, args in (
            ({**BEARER, 'NVOIP_BASE_URL': 'https://api.nvoip.test/integrations/nvoip'}, ARGS),
            ({**BEARER, 'NVOIP_SMS_MAX_CHARS': '161'}, ARGS),
            (BEARER, ['invalid', 'subject', 'body']),
        ):
            network = FakeNetwork()
            with self.assertRaises(transport.TransportError):
                transport.run('sms', args, config, network.connect)
            self.assertEqual(network.calls, [])

    def test_explicit_v2_password_compatibility_does_not_silently_migrate(self):
        config = {'NVOIP_BASE_URL': 'https://api.nvoip.test/v2', 'NVOIP_AUTH_MODE': transport.PASSWORD_GRANT,
            'NVOIP_NUMBERSIP': '119999001', 'NVOIP_USER_TOKEN': 'dummy',
            'NVOIP_OAUTH_CLIENT_ID': 'dummy', 'NVOIP_OAUTH_CLIENT_SECRET': 'dummy'}
        network = FakeNetwork((200, OAUTH_BODY), ACCEPTED)
        transport.run('sms', ARGS, config, network.connect)
        self.assertEqual(network.calls[0]['path'], '/v2/oauth/token')
        self.assertEqual(network.calls[1]['path'], '/v2/sms')
        config['NVOIP_BASE_URL'] = 'https://api.nvoip.test/v3'
        network = FakeNetwork()
        with self.assertRaises(transport.TransportError):
            transport.run('sms', ARGS, config, network.connect)
        self.assertEqual(network.calls, [])

    def test_voice_entrypoint_uses_current_route_and_payload(self):
        network = FakeNetwork((200, {'uuid': 'dummy'}))
        transport.run('voice', ARGS[:3], {**BEARER, 'NVOIP_CALLER': '1049'}, network.connect)
        self.assertEqual(network.calls[0]['path'], '/v3/torpedo/voice')
        self.assertEqual(json.loads(network.calls[0]['body'])['caller'], '1049')

    def test_shell_entrypoint_returns_failure_when_configuration_missing(self):
        env = {k: v for k, v in os.environ.items() if not k.startswith('NVOIP_')}
        result = subprocess.run(['sh', str(ROOT / 'Scripts/send_sms_nvoip_zabbix.sh'), *ARGS],
            env=env, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Missing required variable', result.stderr)
        self.assertEqual(result.stdout, '')


if __name__ == '__main__':
    unittest.main()
