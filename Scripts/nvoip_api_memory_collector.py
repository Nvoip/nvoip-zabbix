#!/usr/bin/env python3
"""Collect bounded host and Tomcat JVM memory metrics for Zabbix.

The collector is intended to run as a root-owned systemd oneshot because the
production Tomcats currently run as root and HotSpot attach is restricted to
the process owner. It writes only aggregate runtime counters; no application
arguments, environment variables, request data or customer data are emitted.
"""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import tempfile
import time
from typing import Dict, Iterable, Mapping


JVM_BASES = {
    "tomcat9": "/opt/tomcat9",
    "tomcat10": "/opt/tomcat10",
}
JSTAT_PATH = "/usr/bin/jstat"
OUTPUT_PATH = pathlib.Path("/run/nvoip-api-memory/metrics.json")
PROC_ROOT = pathlib.Path("/proc")


class CollectionError(RuntimeError):
    """Raised when a complete and trustworthy sample cannot be collected."""


def read_text(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8", errors="strict")


def parse_meminfo(content: str) -> Dict[str, int]:
    values: Dict[str, int] = {}
    for line in content.splitlines():
        name, separator, raw_value = line.partition(":")
        if not separator:
            continue
        parts = raw_value.split()
        if not parts:
            continue
        multiplier = 1024 if len(parts) > 1 and parts[1] == "kB" else 1
        values[name] = int(parts[0]) * multiplier

    required = ("MemAvailable", "SwapTotal", "SwapFree")
    missing = [name for name in required if name not in values]
    if missing:
        raise CollectionError("missing /proc/meminfo fields: " + ", ".join(missing))
    return values


def parse_status_rss(content: str) -> int:
    for line in content.splitlines():
        if line.startswith("VmRSS:"):
            parts = line.split()
            if len(parts) >= 2:
                return int(parts[1]) * 1024
    raise CollectionError("VmRSS is missing from process status")


def discover_jvm_pids(proc_root: pathlib.Path) -> Dict[str, int]:
    matches: Dict[str, list[int]] = {name: [] for name in JVM_BASES}
    for entry in proc_root.iterdir():
        if not entry.name.isdigit():
            continue
        try:
            cmdline = (entry / "cmdline").read_bytes().replace(b"\0", b" ").decode(
                "utf-8", errors="replace"
            )
        except (FileNotFoundError, PermissionError, ProcessLookupError):
            continue
        for name, base in JVM_BASES.items():
            if f"-Dcatalina.base={base}" in cmdline:
                matches[name].append(int(entry.name))

    invalid = {name: pids for name, pids in matches.items() if len(pids) != 1}
    if invalid:
        detail = ", ".join(f"{name}={pids}" for name, pids in invalid.items())
        raise CollectionError("expected exactly one JVM per Tomcat: " + detail)
    return {name: pids[0] for name, pids in matches.items()}


def parse_jstat_table(output: str) -> Dict[str, float]:
    lines = [line.split() for line in output.splitlines() if line.strip()]
    if len(lines) != 2 or len(lines[0]) != len(lines[1]):
        raise CollectionError("unexpected jstat table shape")
    try:
        return {
            name: (float("nan") if value == "-" else float(value))
            for name, value in zip(lines[0], lines[1])
        }
    except ValueError as exc:
        raise CollectionError("jstat returned a non-numeric value") from exc


def run_jstat(mode: str, pid: int) -> Dict[str, float]:
    if mode not in {"-gc", "-class"} or not isinstance(pid, int) or pid <= 0:
        raise CollectionError("invalid jstat request")
    # The executable is fixed, the mode is allow-listed and the PID is a positive int
    # discovered under /proc; shell expansion is never used.
    completed = subprocess.run(  # nosemgrep: python.lang.security.audit.dangerous-subprocess-use-audit.dangerous-subprocess-use-audit
        [JSTAT_PATH, mode, str(pid)],
        check=False,
        capture_output=True,
        text=True,
        timeout=20,
    )
    if completed.returncode != 0:
        error = completed.stderr.strip() or f"exit {completed.returncode}"
        raise CollectionError(f"jstat {mode} failed for pid {pid}: {error}")
    return parse_jstat_table(completed.stdout)


def kibibytes(value: float) -> int:
    return int(round(value * 1024))


def require_fields(values: Mapping[str, float], names: Iterable[str], mode: str) -> None:
    missing = [name for name in names if name not in values]
    if missing:
        raise CollectionError(f"jstat {mode} missing fields: {', '.join(missing)}")


def collect_jvm(proc_root: pathlib.Path, pid: int) -> Dict[str, object]:
    gc = run_jstat("-gc", pid)
    classes = run_jstat("-class", pid)
    require_fields(gc, ("OC", "OU", "MC", "MU", "FGC", "FGCT"), "-gc")
    require_fields(classes, ("Loaded", "Unloaded"), "-class")

    old_capacity = kibibytes(gc["OC"])
    old_used = kibibytes(gc["OU"])
    return {
        "pid": pid,
        "rss_bytes": parse_status_rss(read_text(proc_root / str(pid) / "status")),
        "metaspace_committed_bytes": kibibytes(gc["MC"]),
        "metaspace_used_bytes": kibibytes(gc["MU"]),
        "old_gen_capacity_bytes": old_capacity,
        "old_gen_used_bytes": old_used,
        "old_gen_used_percent": round(
            (old_used * 100.0 / old_capacity) if old_capacity else 0.0, 3
        ),
        "full_gc_count": int(gc["FGC"]),
        "full_gc_seconds": round(gc["FGCT"], 3),
        "classes_loaded": int(classes["Loaded"]),
        "classes_unloaded": int(classes["Unloaded"]),
    }


def collect(proc_root: pathlib.Path, now_epoch: int) -> Dict[str, object]:
    meminfo = parse_meminfo(read_text(proc_root / "meminfo"))
    pids = discover_jvm_pids(proc_root)
    return {
        "schema_version": 1,
        "collected_at_epoch": now_epoch,
        "host": {
            "memory_available_bytes": meminfo["MemAvailable"],
            "swap_used_bytes": meminfo["SwapTotal"] - meminfo["SwapFree"],
        },
        "jvms": {
            name: collect_jvm(proc_root, pid) for name, pid in pids.items()
        },
    }


def atomic_write_json(output: pathlib.Path, payload: Mapping[str, object]) -> None:
    output.parent.mkdir(mode=0o755, parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=output.parent,
        prefix=output.name + ".",
        suffix=".tmp",
        delete=False,
    ) as handle:
        temporary = pathlib.Path(handle.name)
        json.dump(payload, handle, ensure_ascii=True, separators=(",", ":"))
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    try:
        temporary.chmod(0o644)
        os.replace(temporary, output)
    finally:
        temporary.unlink(missing_ok=True)


def main() -> int:
    payload = collect(PROC_ROOT, int(time.time()))
    atomic_write_json(OUTPUT_PATH, payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
