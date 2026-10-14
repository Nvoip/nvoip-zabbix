import importlib.util
import json
import pathlib
import stat
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "Scripts" / "nvoip_api_memory_collector.py"
SPEC = importlib.util.spec_from_file_location("nvoip_api_memory_collector", MODULE_PATH)
collector = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(collector)


GC_OUTPUT = """S0C S1C S0U S1U EC EU OC OU MC MU CCSC CCSU YGC YGCT FGC FGCT CGC CGCT GCT
10 20 1 2 30 3 400 200 600 500 70 60 8 1.25 4 9.5 - - 10.75
"""
CLASS_OUTPUT = """Loaded Bytes Unloaded Bytes Time
120000 1000.0 17000 200.0 3.5
"""


class ApiMemoryCollectorTest(unittest.TestCase):
    def make_proc(self, root: pathlib.Path):
        (root / "meminfo").write_text(
            "MemTotal: 4096000 kB\n"
            "MemAvailable: 900000 kB\n"
            "SwapTotal: 4194304 kB\n"
            "SwapFree: 3145728 kB\n",
            encoding="utf-8",
        )
        for pid, base, rss in (
            (101, "/opt/tomcat9", 123456),
            (102, "/opt/tomcat10", 654321),
        ):
            process = root / str(pid)
            process.mkdir()
            (process / "cmdline").write_bytes(
                f"java\0-Dcatalina.base={base}\0Bootstrap\0".encode("utf-8")
            )
            (process / "status").write_text(
                f"Name:\tjava\nVmRSS:\t{rss} kB\n", encoding="utf-8"
            )

    def make_jstat(self, root: pathlib.Path) -> pathlib.Path:
        executable = root / "jstat"
        executable.write_text(
            "#!/bin/sh\n"
            "case \"$1\" in\n"
            f"  -gc) cat <<'EOF'\n{GC_OUTPUT}EOF\n"
            "  ;;\n"
            f"  -class) cat <<'EOF'\n{CLASS_OUTPUT}EOF\n"
            "  ;;\n"
            "  *) exit 2;;\n"
            "esac\n",
            encoding="utf-8",
        )
        executable.chmod(0o755)
        return executable

    def test_collects_only_aggregate_host_and_jvm_metrics(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            proc_root = root / "proc"
            proc_root.mkdir()
            self.make_proc(proc_root)
            payload = collector.collect(proc_root, str(self.make_jstat(root)), 1234)

        self.assertEqual(1, payload["schema_version"])
        self.assertEqual(1234, payload["collected_at_epoch"])
        self.assertEqual(900000 * 1024, payload["host"]["memory_available_bytes"])
        self.assertEqual(1048576 * 1024, payload["host"]["swap_used_bytes"])
        self.assertEqual({"tomcat9", "tomcat10"}, set(payload["jvms"]))

        tomcat9 = payload["jvms"]["tomcat9"]
        self.assertEqual(101, tomcat9["pid"])
        self.assertEqual(123456 * 1024, tomcat9["rss_bytes"])
        self.assertEqual(500 * 1024, tomcat9["metaspace_used_bytes"])
        self.assertEqual(600 * 1024, tomcat9["metaspace_committed_bytes"])
        self.assertEqual(50.0, tomcat9["old_gen_used_percent"])
        self.assertEqual(4, tomcat9["full_gc_count"])
        self.assertEqual(9.5, tomcat9["full_gc_seconds"])
        self.assertEqual(120000, tomcat9["classes_loaded"])
        self.assertEqual(17000, tomcat9["classes_unloaded"])

        serialized = json.dumps(payload)
        for forbidden in ("cmdline", "environment", "request", "token", "secret"):
            self.assertNotIn(forbidden, serialized.lower())

    def test_rejects_ambiguous_tomcat_processes(self):
        with tempfile.TemporaryDirectory() as directory:
            proc_root = pathlib.Path(directory)
            self.make_proc(proc_root)
            duplicate = proc_root / "103"
            duplicate.mkdir()
            (duplicate / "cmdline").write_bytes(
                b"java\0-Dcatalina.base=/opt/tomcat9\0Bootstrap\0"
            )
            (duplicate / "status").write_text("VmRSS:\t1 kB\n", encoding="utf-8")
            with self.assertRaisesRegex(collector.CollectionError, "exactly one JVM"):
                collector.discover_jvm_pids(proc_root)

    def test_atomic_output_is_world_readable_but_not_writable(self):
        with tempfile.TemporaryDirectory() as directory:
            output = pathlib.Path(directory) / "runtime" / "metrics.json"
            collector.atomic_write_json(output, {"schema_version": 1})
            self.assertEqual({"schema_version": 1}, json.loads(output.read_text()))
            self.assertEqual(
                stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH,
                stat.S_IMODE(output.stat().st_mode),
            )


if __name__ == "__main__":
    unittest.main()
