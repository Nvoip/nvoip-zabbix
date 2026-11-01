import json
import pathlib
import re
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
TEMPLATE_PATH = ROOT / "templates" / "template-nvoip-recording-retention-database.json"
SQL_PATH = ROOT / "docs" / "sql" / "nn2350-recording-retention-health.sql"
MASTER_KEY = "db.odbc.get[nvoip.recording.retention.health,{$NVOIP.RETENTION.DB.DSN}]"


class RecordingRetentionDatabaseTemplateTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.export = json.loads(TEMPLATE_PATH.read_text(encoding="utf-8"))["zabbix_export"]
        cls.template = cls.export["templates"][0]
        cls.items = {item["key"]: item for item in cls.template["items"]}
        cls.master = cls.items[MASTER_KEY]

    def test_targets_zabbix_7_and_uses_one_read_only_master(self):
        self.assertEqual("7.0", self.export["version"])
        self.assertEqual("ODBC", self.master["type"])
        query = " ".join(self.master["params"].split())
        self.assertTrue(query.upper().startswith("SELECT "))
        self.assertIsNone(
            re.search(
                r"\b(ALTER|CALL|CREATE|DELETE|DROP|GRANT|INSERT|KILL|RENAME|REVOKE|TRUNCATE|UPDATE)\b",
                query,
                re.IGNORECASE,
            )
        )
        for item in self.template["items"]:
            if item["type"] == "DEPENDENT":
                self.assertEqual(MASTER_KEY, item["master_item"]["key"])

    def test_documented_sql_and_template_query_are_the_same_statement(self):
        documented = SQL_PATH.read_text(encoding="utf-8").strip().rstrip(";")
        embedded = self.master["params"]
        normalize = lambda value: re.sub(r"\s+", "", value).lower()
        self.assertEqual(normalize(documented), normalize(embedded))

    def test_query_returns_only_aggregate_health_fields(self):
        query = self.master["params"]
        expected = {
            "approval_active",
            "approval_seconds_left",
            "pending_intent_count",
            "oldest_pending_seconds",
            "deleted_5m",
            "audited_deleted_5m",
            "due_candidate_count",
            "active_legal_hold_count",
            "deleted_without_gone_count",
            "gone_without_deleted_count",
            "warning_pending_over_30m",
            "warning_failed_1h",
        }
        selected = query.split("FROM", 1)[0].split("SELECT", 1)[1]
        self.assertEqual(expected, {column.strip() for column in selected.split(",")})
        self.assertNotRegex(query, r"\b(account_id|owner_user_id|object_key|version_id|toemail)\b", re.I)

    def test_destructive_and_delivery_failure_modes_have_triggers(self):
        trigger_names = {
            trigger["name"]
            for item in self.template["items"]
            for trigger in item.get("triggers", [])
        }
        required = (
            "approval is absent or expired",
            "stuck or uncertain delete intent",
            "batch-1 envelope",
            "not being drained",
            "ledger disagrees",
            "gone without a DELETED intent",
            "pending for more than 30 minutes",
            "failure or bounce",
        )
        for fragment in required:
            self.assertTrue(any(fragment in name for name in trigger_names), fragment)

    def test_uuid_values_are_unique_and_well_formed(self):
        values = [group["uuid"] for group in self.export["template_groups"]]
        values.append(self.template["uuid"])
        values.extend(item["uuid"] for item in self.template["items"])
        values.extend(
            trigger["uuid"]
            for item in self.template["items"]
            for trigger in item.get("triggers", [])
        )
        self.assertEqual(len(values), len(set(values)))
        for value in values:
            self.assertRegex(value, r"^[0-9a-f]{32}$")


if __name__ == "__main__":
    unittest.main()
