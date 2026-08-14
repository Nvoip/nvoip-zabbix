import json
import pathlib
import re
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
TEMPLATE_PATH = ROOT / "templates" / "template-nvoip-mysql-1267-log.json"


class Mysql1267LogTemplateTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.document = json.loads(TEMPLATE_PATH.read_text(encoding="utf-8"))
        cls.export = cls.document["zabbix_export"]
        cls.template = cls.export["templates"][0]
        cls.item = cls.template["items"][0]
        cls.trigger = cls.item["triggers"][0]

    def test_targets_zabbix_7_with_unique_valid_uuids(self):
        self.assertEqual("7.0", self.export["version"])
        uuids = [
            self.export["template_groups"][0]["uuid"],
            self.template["uuid"],
            self.item["uuid"],
            self.trigger["uuid"],
        ]
        self.assertEqual(len(uuids), len(set(uuids)))
        for value in uuids:
            self.assertRegex(value, r"^[0-9a-f]{32}$")

    def test_collects_only_collation_error_lines_with_active_agent(self):
        self.assertEqual("ZABBIX_ACTIVE", self.item["type"])
        self.assertEqual("LOG", self.item["value_type"])
        self.assertIn("{$NVOIP.MYSQL1267.LOG_PATH}", self.item["key"])
        self.assertRegex(self.item["key"], r"1267\|Illegal mix of collations")
        self.assertNotRegex(
            self.item["key"],
            re.compile(r"\b(ALTER|UPDATE|INSERT|DELETE|KILL)\b", re.IGNORECASE),
        )

    def test_one_match_in_five_minutes_opens_high_manual_event(self):
        self.assertIn(",5m)>0", self.trigger["expression"])
        self.assertEqual("HIGH", self.trigger["priority"])
        self.assertEqual("YES", self.trigger["manual_close"])
        self.assertIn("protected table collations", self.trigger["description"])

    def test_path_is_a_host_macro_and_history_is_short(self):
        macros = {entry["macro"]: entry["value"] for entry in self.template["macros"]}
        self.assertIn("{$NVOIP.MYSQL1267.LOG_PATH}", macros)
        self.assertEqual("7d", self.item["history"])
        self.assertEqual("0", self.item["trends"])


if __name__ == "__main__":
    unittest.main()
