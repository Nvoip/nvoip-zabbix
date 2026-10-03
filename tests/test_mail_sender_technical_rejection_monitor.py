from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
SERIES_SQL = (ROOT / "docs/grafana/mail-sender-technical-rejection-series.sql").read_text()
ALERT_SQL = (ROOT / "docs/grafana/mail-sender-technical-rejection-alerts.sql").read_text()
GUIDE = (ROOT / "docs/grafana/mail-sender-technical-rejection-monitor.md").read_text()


class MailSenderTechnicalRejectionMonitorTest(unittest.TestCase):
    def test_technical_rejection_contract_and_window(self):
        for sql in (SERIES_SQL, ALERT_SQL):
            self.assertIn("FROM desenvolvimento.mail_sender FORCE INDEX (idx_date_created)", sql)
            self.assertIn("date_created >= NOW() - INTERVAL 1 DAY", sql)
            self.assertIn("sent = -1", sql)
            self.assertIn("status_bounce LIKE 'invalid:%'", sql)
            self.assertIn("status_bounce LIKE 'lim:%'", sql)
            self.assertIn("status_bounce = 'processing_failed'", sql)

    def test_series_is_grouped_by_template_and_status_without_recipient_data(self):
        self.assertIn("GROUP BY time, id_template, sent, status_bounce", SERIES_SQL)
        self.assertIn("messages_with_status_24h", SERIES_SQL)
        for forbidden in ("toemail", "id_astpp", "id_user", "subject", "body"):
            self.assertNotIn(forbidden, SERIES_SQL.lower())

    def test_alert_values_cover_rate_count_and_full_rejection(self):
        self.assertIn("technical_rejections_24h", ALERT_SQL)
        self.assertIn("technical_rejection_pct_24h", ALERT_SQL)
        self.assertIn("GROUP BY id_template", ALERT_SQL)
        self.assertIn("technical_rejection_pct_24h > 1", GUIDE)
        self.assertIn("technical_rejections_24h > 20", GUIDE)
        self.assertIn("technical_rejection_pct_24h = 100", GUIDE)

    def test_queries_are_read_only(self):
        for sql in (SERIES_SQL, ALERT_SQL):
            normalized = re.sub(r"/\\*.*?\\*/", "", sql, flags=re.DOTALL).upper()
            for statement in ("INSERT ", "UPDATE ", "DELETE ", "REPLACE ", "ALTER ", "DROP "):
                self.assertNotIn(statement, normalized)


if __name__ == "__main__":
    unittest.main()
