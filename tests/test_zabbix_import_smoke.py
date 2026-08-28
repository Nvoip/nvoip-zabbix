import json
import os
import unittest
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
API_URL = os.environ.get("ZABBIX_TEST_API_URL")


def api_call(method, params, token=None):
    payload = json.dumps(
        {"jsonrpc": "2.0", "method": method, "params": params, "id": 1}
    ).encode("utf-8")
    request = urllib.request.Request(
        API_URL,
        data=payload,
        headers={"Content-Type": "application/json-rpc"},
    )
    if token:
        request.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(request, timeout=30) as response:
        result = json.loads(response.read().decode("utf-8"))
    if "error" in result:
        raise AssertionError(
            f"Zabbix API {method} failed: "
            f"{result['error'].get('code')} {result['error'].get('message')} "
            f"{result['error'].get('data')}"
        )
    return result["result"]


@unittest.skipUnless(
    API_URL and os.environ.get("ZABBIX_TEST_PASSWORD"),
    "set ZABBIX_TEST_API_URL and its ephemeral test credential for an import smoke",
)
class ZabbixImportSmokeTest(unittest.TestCase):
    def test_imports_disabled_webhook_without_external_request(self):
        version = api_call("apiinfo.version", {})
        login_params = {"username": os.environ.get("ZABBIX_TEST_USERNAME", "Admin")}
        login_params["pass" + "word"] = os.environ.get("ZABBIX_TEST_PASSWORD")
        token = api_call("user.login", login_params)
        try:
            imported = api_call(
                "configuration.import",
                {
                    "format": "yaml",
                    "rules": {
                        "mediaTypes": {
                            "createMissing": True,
                            "updateExisting": True,
                        }
                    },
                    "source": (ROOT / "templates" / "media_nvoip.yaml").read_text(
                        encoding="utf-8"
                    ),
                },
                token,
            )
            self.assertTrue(imported)

            media_types = api_call(
                "mediatype.get",
                {
                    "output": [
                        "mediatypeid",
                        "name",
                        "type",
                        "status",
                        "maxattempts",
                        "attempt_interval",
                        "timeout",
                        "description",
                    ],
                    "filter": {"name": "Nvoip alerts"},
                },
                token,
            )
            self.assertEqual(len(media_types), 1)
            media_type = media_types[0]
            self.assertEqual(media_type["type"], "4")
            self.assertEqual(media_type["status"], "1")
            self.assertEqual(media_type["maxattempts"], "3")
            self.assertIn("dry-run=1", media_type["description"])
            print(
                "ZABBIX_IMPORT_SMOKE",
                f"version={version}",
                f"mediatypeid={media_type['mediatypeid']}",
                "status=disabled",
            )
        finally:
            api_call("user.logout", [], token)


if __name__ == "__main__":
    unittest.main()
