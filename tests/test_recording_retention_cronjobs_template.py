import json
import pathlib
import re
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
TEMPLATE_PATH = ROOT / "templates" / "template-nvoip-recording-retention-cronjobs.json"

# Formato das linhas de maintenance/s3_delete_recordings-v3.lua --lgpd-only
# (Nvoip/api-cronjobs, NN-6673), com dados sintéticos.
LGPD_SUMMARY = (
    "Sun Nov  1 22:45:00 2026 s3_lgpd selected=3 held=1 completed=1 failed=0 prefix_pages=1 "
    "prefix_objects=2 legacy_objects=3 ura_objects=1 dry_run=false pending_ambiguous=1 deferred=0 "
    "attempted=2 elapsed_s=12 budget_s=5400 max_accounts=200 stop=none rechecked=0 "
    "recheck_deferred=0 shared_checked=0 shared_released=0 shared_objects=0 recheck_days=30"
)
LGPD_ONLY_LOG = (
    "Sun Nov  1 22:30:01 2026 s3_lgpd state accounts=2 scanning=0 pending=2 rechecking=0 recheck_days=30",
    "Sun Nov  1 22:30:02 2026 account=123 skipped=legal_hold",
    "Sun Nov  1 22:30:03 2026 account=123 legacy_recording_retention blocked_ambiguous=4",
    "Sun Nov  1 22:45:00 2026 account=123 s3_cleanup=complete prefix_pages=1 prefix_objects=2 "
    "legacy_objects=3 ura_objects=1 dry_run=false shared_checked=0 shared_released=0 "
    "shared_objects=0 mode=full",
    "Sun Nov  1 22:45:00 2026 s3_lgpd budget_exhausted reason=time_budget deferred_accounts=1",
    LGPD_SUMMARY,
    "Sun Nov  1 22:45:00 2026 account_recording_retention skipped reason=lgpd_only",
)


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
        self.assertEqual(3, len(log_items))
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

    def _log_pattern(self, name):
        return re.compile(self.items[name]["key"].split('"', 2)[1])

    def test_lgpd_only_lines_stay_out_of_the_retention_items(self):
        summary = self._log_pattern("Recording retention CronJobs: aggregate cycle summary")
        marker = self._log_pattern("Recording retention CronJobs: retention-only marker")
        for line in LGPD_ONLY_LOG:
            self.assertIsNone(summary.fullmatch(line), line)
            self.assertIsNone(marker.fullmatch(line), line)

    def test_lgpd_only_process_stays_out_of_the_retention_worker_count(self):
        item = self.items["Recording retention CronJobs: running Lua processes"]
        name, user, _state, cmdline = item["key"][len("proc.num["):-1].split(",")
        self.assertEqual(("lua", "root"), (name, user))
        pattern = re.compile(cmdline)
        self.assertIsNotNone(pattern.search(
            "lua /etc/nvoip/maintenance/s3_delete_recordings-v3.lua --retention-only"))
        self.assertIsNone(pattern.search(
            "lua /etc/nvoip/maintenance/s3_delete_recordings-v3.lua --lgpd-only"))
        self.assertIsNone(pattern.search(
            "lua /etc/nvoip/maintenance/s3_delete_recordings-v3.lua --lgpd-only --dry-run"))

    def test_lgpd_summary_collects_only_the_real_aggregate_line(self):
        item = self.items["Recording retention CronJobs: LGPD cleanup cycle summary"]
        pattern = self._log_pattern("Recording retention CronJobs: LGPD cleanup cycle summary")
        self.assertIsNotNone(pattern.fullmatch(LGPD_SUMMARY))
        self.assertEqual(
            [LGPD_SUMMARY], [line for line in LGPD_ONLY_LOG if pattern.fullmatch(line)])
        self.assertIsNone(pattern.fullmatch(LGPD_SUMMARY.replace("dry_run=false", "dry_run=true")))
        self.assertIsNone(pattern.fullmatch(LGPD_SUMMARY + " recipient=someone@example.com"))
        self.assertEqual("ZABBIX_ACTIVE", item["type"])
        self.assertTrue(item["key"].endswith(",,,skip]"))

    def test_lgpd_summary_alerts_on_missing_cycle_and_failures(self):
        item = self.items["Recording retention CronJobs: LGPD cleanup cycle summary"]
        triggers = {trigger["name"]: trigger for trigger in item["triggers"]}
        missing = triggers["LGPD recording cleanup has no real cycle summary"]
        self.assertEqual("HIGH", missing["priority"])
        self.assertIn(",26h)=1", missing["expression"])
        failed = triggers["LGPD recording cleanup cycle reported failures"]
        self.assertEqual("HIGH", failed["priority"])
        self.assertIn('" failed=[1-9][0-9]* "', failed["expression"])
        self.assertEqual("YES", failed["manual_close"])

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
        self.assertEqual("3046723097", macros["{$NVOIP.RETENTION.SCRIPT.CRC32}"])
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
