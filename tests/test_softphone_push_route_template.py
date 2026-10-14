import json
import pathlib
import re
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
TEMPLATE = json.loads(
    (ROOT / "templates" / "template-nvoip-softphone-push-routes.json").read_text(
        encoding="utf-8"
    )
)["zabbix_export"]


class SoftphonePushRouteTemplateTest(unittest.TestCase):
    def test_two_routes_have_distinct_items_and_valid_triggers(self):
        self.assertEqual("7.0", TEMPLATE["version"])
        template = TEMPLATE["templates"][0]
        self.assertEqual(2, len(template["items"]))
        uuids = [template["uuid"]]
        for item in template["items"]:
            self.assertEqual("ZABBIX_ACTIVE", item["type"])
            self.assertEqual("LOG", item["value_type"])
            self.assertEqual(2, len(item["triggers"]))
            uuids.append(item["uuid"])
            for trigger in item["triggers"]:
                uuids.append(trigger["uuid"])
                self.assertEqual("HIGH", trigger["priority"])
        self.assertEqual(len(uuids), len(set(uuids)))
        for value in uuids:
            self.assertRegex(value, r"^[0-9a-f]{32}$")

    def test_log_filters_separate_routes_and_skip_payloads(self):
        items = TEMPLATE["templates"][0]["items"]
        samples = [
            "1791980000.123 /nvoip-softphone/push/chat-message 403 1",
            "1791980001.123 /nvoip-softphone/push/incoming-call 503 1",
        ]
        for index, item in enumerate(items):
            pattern = re.compile(item["key"].split('"', 2)[1])
            self.assertIsNotNone(pattern.fullmatch(samples[index]))
            self.assertIsNone(pattern.fullmatch(samples[1 - index]))
            self.assertIsNone(pattern.fullmatch(samples[index] + " token=secret"))

    def test_triggers_cover_internal_4xx_and_route_failures(self):
        for item in TEMPLATE["templates"][0]["items"]:
            expressions = [trigger["expression"] for trigger in item["triggers"]]
            self.assertTrue(any('" 4[0-9][0-9] 1$"' in expression and "15m" in expression for expression in expressions))
            self.assertTrue(any('" 499 1$"' in expression and '" 5[0-9][0-9] [01]$"' in expression for expression in expressions))


if __name__ == "__main__":
    unittest.main()
