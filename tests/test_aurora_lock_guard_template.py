import json
import pathlib
import re
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
TEMPLATE_PATH = ROOT / "templates" / "template-nvoip-aurora-lock-guard.json"
MASTER_KEY = "db.odbc.get[nvoip.db.guard,{$NVOIP.DB.DSN}]"


class AuroraLockGuardTemplateTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.document = json.loads(TEMPLATE_PATH.read_text(encoding="utf-8"))
        cls.export = cls.document["zabbix_export"]
        cls.template = cls.export["templates"][0]
        cls.items = {item["key"]: item for item in cls.template["items"]}

    def test_targets_zabbix_7_and_has_expected_template(self):
        self.assertEqual("7.0", self.export["version"])
        self.assertEqual(
            "Template Nvoip Aurora Lock Guard", self.template["template"]
        )

        uuids = []
        uuids.extend(group["uuid"] for group in self.export["template_groups"])
        uuids.append(self.template["uuid"])
        uuids.extend(item["uuid"] for item in self.template["items"])
        uuids.extend(
            trigger["uuid"]
            for item in self.template["items"]
            for trigger in item.get("triggers", [])
        )
        self.assertEqual(len(uuids), len(set(uuids)))
        for uuid in uuids:
            self.assertRegex(uuid, r"^[0-9a-f]{32}$")

    def test_master_query_is_aggregate_and_read_only(self):
        master = self.items[MASTER_KEY]
        self.assertEqual("ODBC", master["type"])
        self.assertEqual("TEXT", master["value_type"])
        self.assertEqual("0", master["trends"])
        query = " ".join(master["params"].split())
        self.assertTrue(query.upper().startswith("SELECT "))
        self.assertIn("information_schema.PROCESSLIST", query)
        for alias in (
            "visible_session_count",
            "metadata_wait_count",
            "metadata_wait_max_seconds",
            "long_query_count",
            "longest_query_seconds",
        ):
            self.assertRegex(query, rf"\b{alias}\b")

        self.assertNotRegex(query.upper(), r"\b(INFO|PROCESSLIST_INFO)\b")
        self.assertIsNone(
            re.search(
                r"\b(ALTER|CREATE|DELETE|DROP|GRANT|INSERT|KILL|RENAME|REVOKE|TRUNCATE|UPDATE)\b",
                query,
                flags=re.IGNORECASE,
            )
        )

    def test_all_dependent_items_use_the_single_master_query(self):
        dependents = [
            item for item in self.template["items"] if item["type"] == "DEPENDENT"
        ]
        self.assertEqual(5, len(dependents))
        for item in dependents:
            self.assertEqual(MASTER_KEY, item["master_item"]["key"])
            self.assertEqual("JSONPATH", item["preprocessing"][0]["type"])
            self.assertRegex(
                item["preprocessing"][0]["parameters"][0],
                r"^\$\[0\]\.[a-z_]+$",
            )

    def test_guard_covers_detection_and_collector_health(self):
        trigger_names = {
            trigger["name"]
            for item in self.template["items"]
            for trigger in item.get("triggers", [])
        }
        expected_fragments = (
            "no fresh sample",
            "cannot see other sessions",
            "sustained metadata-lock queue",
            "threatening availability",
            "running longer than",
        )
        for fragment in expected_fragments:
            self.assertTrue(
                any(fragment in name for name in trigger_names),
                msg=f"missing trigger containing {fragment!r}",
            )

    def test_threshold_macros_are_declared(self):
        macros = {entry["macro"]: entry["value"] for entry in self.template["macros"]}
        self.assertEqual("nvoip", macros["{$NVOIP.DB.DSN}"])
        self.assertEqual("300", macros["{$NVOIP.DB.LONG_QUERY.WARN}"])
        self.assertEqual("900", macros["{$NVOIP.DB.LONG_QUERY.HIGH}"])
        self.assertEqual("3", macros["{$NVOIP.DB.MDL.WAIT.COUNT.WARN}"])
        self.assertEqual("20", macros["{$NVOIP.DB.MDL.WAIT.COUNT.HIGH}"])
        self.assertEqual("30", macros["{$NVOIP.DB.MDL.WAIT.AGE.WARN}"])
        self.assertEqual("120", macros["{$NVOIP.DB.MDL.WAIT.AGE.HIGH}"])


if __name__ == "__main__":
    unittest.main()
