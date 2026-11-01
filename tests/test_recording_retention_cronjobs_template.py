import json
import pathlib
import re
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
TEMPLATE_PATH = ROOT / "templates" / "template-nvoip-recording-retention-cronjobs.json"


class RecordingRetentionCronJobsTemplateTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.export = json.loads(TEMPLATE_PATH.read_text(encoding="utf-8"))["zabbix_export"]
        cls.template = cls.export["templates"][0]
        cls.items = {item["name"]: item for item in cls.template["items"]}

    def test_collects_only_aggregate_log_lines(self):
        summary = self.items["Recording retention CronJobs: aggregate cycle summary"]
        pattern = re.compile(summary["key"].split('"', 2)[1])
        safe = (
            "Sun Nov  1 11:55:00 2026 account_recording_retention selected=1302 "
            "held=0 warned=5 completed=0 empty=0 deferred=1297 deletion_blocked=0 "
            "delivery_blocked=0 failed=0 deletion_enabled=false dry_run=false"
        )
        self.assertIsNotNone(pattern.fullmatch(safe))
        self.assertIsNone(pattern.fullmatch("Sun Nov  1 11:55:00 2026 account=123 recording_retention=failed"))
        self.assertIsNone(pattern.fullmatch(safe + " recipient=someone@example.com"))
        self.assertEqual("ZABBIX_ACTIVE", summary["type"])
        self.assertTrue(summary["key"].endswith(",,,skip]"))

    def test_log_items_are_active_and_numeric_items_are_passive(self):
        log_items = [item for item in self.template["items"] if item["key"].startswith("log[")]
        numeric_items = [item for item in self.template["items"] if not item["key"].startswith("log[")]
        self.assertEqual(2, len(log_items))
        self.assertEqual(3, len(numeric_items))
        for item in log_items:
            self.assertEqual("ZABBIX_ACTIVE", item["type"])
        for item in numeric_items:
            self.assertEqual("ZABBIX_PASSIVE", item["type"])

    def test_checks_isolation_runtime_and_process_safety(self):
        keys = {item["key"] for item in self.template["items"]}
        self.assertIn("vfs.file.time[{$NVOIP.RETENTION.LOG},modify]", keys)
        self.assertIn("vfs.file.cksum[{$NVOIP.RETENTION.SCRIPT}]", keys)
        self.assertIn(
            "proc.num[lua,root,,s3_delete_recordings-v3.lua --retention-only]", keys
        )
        isolation = self.items["Recording retention CronJobs: retention-only marker"]
        self.assertIn("s3_lgpd skipped reason=retention_only", isolation["key"])
        self.assertTrue(isolation["key"].endswith(",,,skip]"))

    def test_has_critical_trigger_for_legacy_flag_and_duplicate_worker(self):
        triggers = [
            trigger
            for item in self.template["items"]
            for trigger in item.get("triggers", [])
        ]
        critical = {trigger["name"]: trigger for trigger in triggers if trigger["priority"] == "DISASTER"}
        self.assertIn("CRITICAL: legacy cancelled-recording deletion flag is enabled", critical)
        self.assertIn("Recording retention has duplicate worker processes", critical)
        self.assertIn("deletion_enabled=true", critical["CRITICAL: legacy cancelled-recording deletion flag is enabled"]["expression"])

    def test_crc_macro_matches_the_current_legacy_agent_contract(self):
        macros = {entry["macro"]: entry["value"] for entry in self.template["macros"]}
        self.assertEqual("2220100890", macros["{$NVOIP.RETENTION.SCRIPT.CRC32}"])
        self.assertEqual(
            "/etc/nvoip/maintenance/s3_delete_recordings-v3.lua",
            macros["{$NVOIP.RETENTION.SCRIPT}"],
        )

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
