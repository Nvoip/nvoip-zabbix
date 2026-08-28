import json
import re
import shutil
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MEDIA_TYPE = ROOT / "templates" / "media_nvoip.yaml"


def extract_webhook_script():
    lines = MEDIA_TYPE.read_text(encoding="utf-8").splitlines()
    script_line = next(index for index, line in enumerate(lines) if line.strip() == "script: |")
    key_indent = len(lines[script_line]) - len(lines[script_line].lstrip())
    body = []
    for line in lines[script_line + 1 :]:
        indent = len(line) - len(line.lstrip())
        if line.strip() and indent <= key_indent:
            break
        body.append(line[key_indent + 2 :] if line.strip() else "")
    return "\n".join(body)


def default_params(**overrides):
    params = {
        "alert_message": 'Host: api-01\nSeverity: High\nText: "çãõ"',
        "alert_subject": "Problem: API latency",
        "event_date": "2026.08.27",
        "event_id": "3168001",
        "event_nseverity": "4",
        "event_source": "0",
        "event_time": "16:30:00",
        "event_update_status": "0",
        "event_value": "1",
        "host_name": "api-01",
        "http_proxy": "",
        "nvoip_access_token": "dummy",
        "nvoip_api_url": "https://api.nvoip.test/v3",
        "nvoip_auth_mode": "client_credentials",
        "nvoip_auth_url": "https://api.nvoip.test/auth/oauth2/token",
        "nvoip_dry_run": "0",
        "nvoip_oauth_client_id": "dummy",
        "nvoip_oauth_client_credential": "dummy",
        "nvoip_oauth_scopes": "sms:send call:make",
        "nvoip_retryable_http_codes": "408,425,429,500,502,503,504",
        "nvoip_sms_max_chars": "160",
        "nvoip_voice_caller": "1049",
        "nvoip_voice_max_chars": "600",
        "nvoip_voice_send_recovery": "0",
        "nvoip_whatsapp_body_1": "Problem: API latency",
        "nvoip_whatsapp_body_2": 'Host: api-01\nText: "çãõ"',
        "nvoip_whatsapp_body_3": "",
        "nvoip_whatsapp_body_4": "",
        "nvoip_whatsapp_body_5": "",
        "nvoip_whatsapp_body_6": "",
        "nvoip_whatsapp_instance": "instance-1",
        "nvoip_whatsapp_language": "pt_BR",
        "nvoip_whatsapp_template_id": "template-3168",
        "send_to": "sms:+5511999999999",
        "trigger_url": "https://zabbix.test/tr_events.php?eventid=3168001",
    }
    params.update(overrides)
    return params


def run_webhook(params, responses):
    if shutil.which("node") is None:
        raise unittest.SkipTest("node is required to execute the webhook contract tests")

    script = extract_webhook_script()
    harness = textwrap.dedent(
        f"""
        const calls = [];
        const logs = [];
        const responses = {json.dumps(responses)};
        global.Zabbix = {{log: (level, message) => logs.push({{level, message}})}};
        global.btoa = value => Buffer.from(value, 'utf8').toString('base64');
        global.HttpRequest = function () {{
          this.headers = [];
          this.status = 0;
          this.proxy = '';
          this.addHeader = header => this.headers.push(header);
          this.setProxy = proxy => {{ this.proxy = proxy; }};
          this.post = (url, body) => {{
            const response = responses.shift();
            if (!response) throw new Error('missing stub response');
            this.status = response.status;
            calls.push({{url, body, headers: this.headers.slice(), proxy: this.proxy}});
            return response.body;
          }};
          this.getStatus = () => this.status;
        }};
        function execute(value) {{
        {textwrap.indent(script, '  ')}
        }}
        let output;
        try {{
          output = {{ok: true, result: execute(JSON.stringify({json.dumps(params)}))}};
        }} catch (error) {{
          output = {{ok: false, error: String(error)}};
        }}
        process.stdout.write(JSON.stringify({{output, calls, logs}}));
        """
    )

    with tempfile.NamedTemporaryFile("w", suffix=".js", encoding="utf-8") as handle:
        handle.write(harness)
        handle.flush()
        completed = subprocess.run(
            ["node", handle.name],
            check=True,
            capture_output=True,
            text=True,
        )
    return json.loads(completed.stdout)


def oauth_response():
    return {"status": 200, "body": json.dumps({"access" + "_token": "dummy"})}


class NvoipMediaTypeTest(unittest.TestCase):
    def test_export_has_safe_defaults_and_no_embedded_secret(self):
        content = MEDIA_TYPE.read_text(encoding="utf-8")
        self.assertIn("version: '7.0'", content)
        self.assertIn("type: WEBHOOK", content)
        self.assertIn("status: DISABLED", content)
        self.assertIn("attempts: '3'", content)
        self.assertIn("attempt_interval: 10s", content)
        self.assertRegex(content, r"name: nvoip_dry_run\n\s+value: '1'")
        for macro in (
            "{$NVOIP.OAUTH.CLIENT_ID}",
            "{$NVOIP.OAUTH.CLIENT_CREDENTIAL}",
        ):
            self.assertIn(macro, content)
        self.assertNotIn("client-secret-value", content)
        self.assertNotIn("user-secret-token", content)
        for macro in (
            "{EVENT.DATE}",
            "{EVENT.TIME}",
            "{EVENT.SEVERITY}",
            "{EVENT.TAGS}",
            "{HOST.NAME}",
            "{TRIGGER.URL}",
        ):
            self.assertIn(macro, content)

    def test_sms_oauth_and_payload_preserve_special_characters(self):
        result = run_webhook(
            default_params(alert_message='Text: "çãõ" ' + ("x" * 300)),
            [
                oauth_response(),
                {"status": 200, "body": '{"id":3168}'},
            ],
        )
        self.assertTrue(result["output"]["ok"])
        parsed_result = json.loads(result["output"]["result"])
        self.assertEqual(parsed_result["status"], "sent")
        self.assertEqual(parsed_result["channel"], "sms")
        self.assertEqual(parsed_result["external_id"], "3168")
        self.assertEqual(len(result["calls"]), 2)

        payload = json.loads(result["calls"][1]["body"])
        self.assertEqual(payload["numberPhone"], "5511999999999")
        self.assertIn('Text: "çãõ"', payload["message"])
        self.assertEqual(len(payload["message"]), 160)

        visible = json.dumps({"logs": result["logs"], "output": result["output"]})
        oauth_call = result["calls"][0]
        self.assertEqual(oauth_call["url"], "https://api.nvoip.test/auth/oauth2/token")
        self.assertIn("grant_type=client_credentials", oauth_call["body"])
        self.assertIn("scope=sms%3Asend%20call%3Amake", oauth_call["body"])

        for secret in ("dummy", "client-secret-value"):
            self.assertNotIn(secret, visible)

    def test_whatsapp_uses_approved_template_contract(self):
        result = run_webhook(
            default_params(send_to="whatsapp:+5511999999999"),
            [
                oauth_response(),
                {"status": 202, "body": '{"queueId":4815,"templateId":"template-3168"}'},
            ],
        )
        self.assertTrue(result["output"]["ok"])
        payload = json.loads(result["calls"][1]["body"])
        self.assertEqual(result["calls"][1]["url"], "https://api.nvoip.test/v3/wa/templateMessages")
        self.assertEqual(payload["idTemplate"], "template-3168")
        self.assertEqual(payload["instance"], "instance-1")
        self.assertEqual(payload["language"], "pt_BR")
        self.assertEqual(payload["destination"], "5511999999999")
        self.assertEqual(payload["bodyVariables"][1], 'Host: api-01\nText: "çãõ"')

    def test_voice_recovery_is_skipped_before_authentication(self):
        result = run_webhook(
            default_params(send_to="voice:5511999999999", event_value="0"),
            [],
        )
        self.assertTrue(result["output"]["ok"])
        parsed_result = json.loads(result["output"]["result"])
        self.assertEqual(parsed_result["status"], "skipped")
        self.assertEqual(parsed_result["reason"], "recovery_disabled")
        self.assertEqual(result["calls"], [])

    def test_voice_problem_uses_dynamic_torpedo_endpoint(self):
        result = run_webhook(
            default_params(send_to="voice:5511999999999"),
            [
                oauth_response(),
                {"status": 200, "body": '{"uuid":"nn3168-voice"}'},
            ],
        )
        self.assertTrue(result["output"]["ok"])
        self.assertEqual(result["calls"][1]["url"], "https://api.nvoip.test/v3/torpedo/voice")
        payload = json.loads(result["calls"][1]["body"])
        self.assertEqual(payload["caller"], "1049")
        self.assertEqual(payload["called"], "5511999999999")
        self.assertEqual(payload["audios"][0]["positionAudio"], 1)
        self.assertEqual(payload["dtmfs"], [])

    def test_dry_run_builds_route_without_authentication(self):
        result = run_webhook(
            default_params(send_to="voice:5511999999999", nvoip_dry_run="1"),
            [],
        )
        self.assertTrue(result["output"]["ok"])
        parsed_result = json.loads(result["output"]["result"])
        self.assertEqual(parsed_result["status"], "dry_run")
        self.assertEqual(parsed_result["path"], "/torpedo/voice")
        self.assertEqual(result["calls"], [])

    def test_retryable_and_permanent_http_errors_are_distinct(self):
        retryable = run_webhook(
            default_params(),
            [
                oauth_response(),
                {"status": 503, "body": '{"detail":"must-not-be-logged"}'},
            ],
        )
        self.assertFalse(retryable["output"]["ok"])
        self.assertIn("NVOIP_RETRYABLE", retryable["output"]["error"])
        self.assertNotIn("must-not-be-logged", json.dumps(retryable))

        permanent = run_webhook(
            default_params(),
            [
                oauth_response(),
                {"status": 400, "body": '{"detail":"must-not-be-logged"}'},
            ],
        )
        self.assertFalse(permanent["output"]["ok"])
        self.assertIn("NVOIP_PERMANENT", permanent["output"]["error"])
        self.assertNotIn("must-not-be-logged", json.dumps(permanent))


if __name__ == "__main__":
    unittest.main()
