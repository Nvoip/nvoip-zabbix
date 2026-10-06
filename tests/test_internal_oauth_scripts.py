import importlib.util
import io
import json
import unittest
from pathlib import Path
from urllib.parse import parse_qs

spec = importlib.util.spec_from_file_location("nvoip_api", Path(__file__).parents[1] / "Scripts/nvoip_api.py")
api = importlib.util.module_from_spec(spec)
spec.loader.exec_module(api)

class Response(io.BytesIO):
    status = 200

class OAuthScriptsTest(unittest.TestCase):
    def setUp(self):
        self.env = {"NVOIP_OAUTH_CLIENT_ID": "synthetic-id", "NVOIP_OAUTH_CLIENT_SECRET": "synthetic-secret",
                    "NVOIP_SMS_TEMPLATE_ID": "123", "NVOIP_CALLER": "112544001"}
        self.requests = []
        self.result = {"accepted": True, "smsStatus": "200 - SMS Enviado com Sucesso"}

    def transport(self, request, timeout):
        self.requests.append(request)
        result = {"access_token": "fake-scoped"} if request.full_url == api.TOKEN_URL else self.result
        return Response(json.dumps(result).encode())

    def test_sms_oauth_then_approved_template_without_secret_in_urls(self):
        api.send("sms", ["5511999999999", "Alerta", "Problema", "servidor"], self.env, self.transport)
        self.assertEqual(len(self.requests), 2)
        auth, send = self.requests
        self.assertEqual(parse_qs(auth.data.decode())["grant_type"], ["client_credentials"])
        self.assertEqual(parse_qs(auth.data.decode())["scope"], ["sms:send"])
        self.assertEqual(send.full_url, api.API_URL + "/sms/sendTemplate")
        self.assertEqual(send.get_header("Authorization"), "Bearer fake-scoped")
        self.assertEqual(json.loads(send.data), {"templateId":123, "phoneNumber":"5511999999999",
                                               "variables":["Alerta", "Problema", "servidor"]})
        for req in self.requests:
            self.assertNotIn("synthetic-secret", req.full_url)
            self.assertNotIn("napikey", req.full_url)
            self.assertNotIn("/v2", req.full_url)

    def test_native_five_variables_select_recovery_and_update_without_message_leaks(self):
        env = dict(self.env, NVOIP_SMS_TEMPLATE_LAYOUT="zabbix", NVOIP_SMS_PROBLEM_TEMPLATE_ID="2988",
                   NVOIP_SMS_RECOVERY_TEMPLATE_ID="2989", NVOIP_SMS_UPDATE_TEMPLATE_ID="2990")
        for value, updated, expected in [("1", "0", 2988), ("0", "0", 2989), ("1", "1", 2990)]:
            self.requests.clear()
            fields = ["Very long event " * 5, "server", "High", "77", "2026.10.03 12:00:00",
                      value, updated, "2026.10.03 13:00:00", "2026.10.03 14:00:00"]
            api.send("sms", ["5511999999999", "subject", "private-message", "\t".join(fields)], env, self.transport)
            payload = json.loads(self.requests[-1].data)
            self.assertEqual(payload["templateId"], expected)
            self.assertEqual(len(payload["variables"]), 5)
            self.assertEqual(len(payload["variables"][0]), 40)
            self.assertNotIn("private-message", str(payload))
            self.assertEqual(payload["variables"][-1], "2026-10-03 " + ("14" if updated == "1" else "13" if value == "0" else "12") + ":00:00")

    def test_missing_event_macros_block_before_token_and_send(self):
        env = dict(self.env, NVOIP_SMS_TEMPLATE_LAYOUT="zabbix", NVOIP_SMS_PROBLEM_TEMPLATE_ID="2988")
        with self.assertRaises(api.ApiError):
            api.send("sms", ["5511999999999", "subject", "message", "{HOST.NAME1}"], env, self.transport)
        self.assertEqual(self.requests, [])

    def test_password_only_credentials_block_before_http(self):
        with self.assertRaises(api.ApiError):
            api.send("check", [], {"NVOIP_NUMBERSIP":"112544001", "NVOIP_USER_TOKEN":"legacy"}, self.transport)
        self.assertEqual(self.requests, [])

    def test_bad_configuration_blocks_before_oauth_and_send(self):
        for extra in [{"NVOIP_BASE_URL":"https://api.nvoip.com.br/v2"}, {"NVOIP_SMS_TEMPLATE_ID":"0"}]:
            with self.assertRaises(api.ApiError):
                api.send("sms", ["5511999999999", "Alerta", "Problema"], dict(self.env, **extra), self.transport)
        self.assertEqual(self.requests, [])

    def test_http_200_rejection_is_not_sms_success(self):
        self.result = {"accepted":False, "smsStatus":"403 - synthetic-sensitive-body"}
        with self.assertRaisesRegex(api.ApiError, "acceptance was not confirmed") as caught:
            api.send("sms", ["5511999999999", "Alerta", "Problema"], self.env, self.transport)
        self.assertNotIn("sensitive", str(caught.exception))

    def test_voice_uses_oauth_caller_and_v3_contract(self):
        self.result = {"status": "queued", "uuid": "synthetic-queue"}
        api.send("voice", ["5511999999999", "Alerta", "Falha"], self.env, self.transport)
        self.assertEqual(parse_qs(self.requests[0].data.decode())["scope"], ["call:make"])
        self.assertEqual(self.requests[1].full_url, api.API_URL + "/torpedo/voice")
        self.assertEqual(json.loads(self.requests[1].data)["caller"], "112544001")

    def test_voice_http_success_requires_queue_acceptance(self):
        self.result = {"status": "error"}
        with self.assertRaisesRegex(api.ApiError, "Voice API acceptance was not confirmed"):
            api.send("voice", ["5511999999999", "Alerta", "Falha"], self.env, self.transport)

    def test_zabbix_event_rejection_is_not_success_for_any_sms_template(self):
        env = dict(self.env, NVOIP_SMS_TEMPLATE_LAYOUT="zabbix", NVOIP_SMS_PROBLEM_TEMPLATE_ID="2988",
                   NVOIP_SMS_RECOVERY_TEMPLATE_ID="2989", NVOIP_SMS_UPDATE_TEMPLATE_ID="2990")
        self.result = {"accepted": False, "smsStatus": "403 - synthetic-sensitive-body"}
        for value, updated in [("1", "0"), ("0", "0"), ("1", "1")]:
            self.requests.clear()
            metadata = "\t".join(["event", "host", "High", "77", "2026.10.06 12:00:00",
                                  value, updated, "2026.10.06 13:00:00", "2026.10.06 14:00:00"])
            with self.assertRaisesRegex(api.ApiError, "acceptance was not confirmed") as caught:
                api.send("sms", ["5511999999999", "subject", "private-message", metadata], env, self.transport)
            self.assertEqual(parse_qs(self.requests[0].data.decode())["scope"], ["sms:send"])
            self.assertNotIn("sensitive", str(caught.exception))

    def test_configuration_check_requests_both_supported_script_scopes_without_sending(self):
        api.send("check", [], self.env, self.transport)
        self.assertEqual(len(self.requests), 1)
        self.assertEqual(parse_qs(self.requests[0].data.decode())["scope"], ["sms:send call:make"])

    def test_redirect_is_not_followed_with_a_credential(self):
        self.assertIsNone(api.NoRedirect().redirect_request(None, None, 302, "", {}, "https://other.test"))

if __name__ == "__main__":
    unittest.main()
