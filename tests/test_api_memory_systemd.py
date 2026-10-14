import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SERVICE = ROOT / "systemd" / "nvoip-api-memory-collector.service"
TIMER = ROOT / "systemd" / "nvoip-api-memory-collector.timer"


class ApiMemorySystemdTest(unittest.TestCase):
    def test_service_is_bounded_and_does_not_restart_tomcats(self):
        service = SERVICE.read_text(encoding="utf-8")
        self.assertIn("Type=oneshot", service)
        self.assertIn("User=root", service)
        self.assertIn("ProtectSystem=strict", service)
        self.assertIn("ReadWritePaths=/run/nvoip-api-memory /tmp", service)
        self.assertNotIn("ExecStop", service)
        self.assertNotIn("systemctl restart", service)
        self.assertNotIn("jcmd", service)

    def test_timer_collects_once_per_minute(self):
        timer = TIMER.read_text(encoding="utf-8")
        self.assertIn("OnUnitActiveSec=60s", timer)
        self.assertIn("Persistent=true", timer)
        self.assertIn("WantedBy=timers.target", timer)


if __name__ == "__main__":
    unittest.main()
