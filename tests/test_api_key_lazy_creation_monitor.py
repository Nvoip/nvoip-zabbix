from pathlib import Path
import re
import unittest


MONITOR_SQL = (
    Path("docs/grafana") / "api-key-lazy-creation-monitor.sql"
).read_text()


class ApiKeyLazyCreationMonitorTest(unittest.TestCase):
    def test_monitor_checks_unresolved_lazy_creation_requests_only(self):
        self.assertIn("api_key_lazy_creation_requested", MONITOR_SQL)
        self.assertIn("INTERVAL 5 MINUTE", MONITOR_SQL)
        self.assertIn("api_key_row.id IS NULL", MONITOR_SQL)
        self.assertIn("user_account.id_profile = 1", MONITOR_SQL)
        self.assertIn("protected_user.id_profile IN (11, 12)", MONITOR_SQL)
        self.assertIn("COALESCE(account.reseller_id, 0) = 0", MONITOR_SQL)
        self.assertNotIn("action_outcome", MONITOR_SQL)

    def test_monitor_is_aggregate_only_and_never_projects_credentials(self):
        select_clause = re.search(
            r"\)\s*SELECT\s+(.*?)\s+FROM creation_requests",
            MONITOR_SQL,
            re.IGNORECASE | re.DOTALL,
        ).group(1)
        self.assertIn("COUNT(*)", select_clause)
        self.assertNotIn("apikey", select_clause.lower())
        self.assertNotIn("id_user", select_clause.lower())
        self.assertNotIn("id_astpp", select_clause.lower())
        self.assertNotIn("fingerprint", MONITOR_SQL.lower())

    def test_monitor_contains_no_mutating_statement(self):
        normalized = re.sub(r"/\*.*?\*/", "", MONITOR_SQL, flags=re.DOTALL).upper()
        for statement in ("INSERT ", "UPDATE ", "DELETE ", "REPLACE ", "ALTER ", "DROP "):
            self.assertNotIn(statement, normalized)


if __name__ == "__main__":
    unittest.main()
