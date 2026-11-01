#!/usr/bin/env python3
"""NN-6660: aggregate recent Flow failures and local Redis health.

Run as root on the URA host. Output contains counters only, without call data.
"""

import subprocess
import sys
import time


def command(args):
    return subprocess.run(
        args, check=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        timeout=12, universal_newlines=True,
    ).stdout


def journal_command(args):
    result = subprocess.run(
        args, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        timeout=12, universal_newlines=True,
    )
    # journalctl --grep returns 1 when no line matches.
    if result.returncode not in (0, 1) or result.stderr:
        raise ValueError("journal query failed")
    return result.stdout


def main():
    patterns = {
        "fallback_failed_10m": "FLOW_QUEUE_FAILURE_FALLBACK_FAILED",
        "trigger_not_found_10m": "TRIGGER_NOT_FOUND",
        "asset_unavailable_10m": "ASSET_SOURCE_UNAVAILABLE",
        "snapshot_missing_10m": "snapshot_missing",
    }
    journal = journal_command([
        "journalctl", "-u", "freeswitch", "--since", "-10 min",
        "--grep", "|".join(patterns.values()), "-o", "cat", "--no-pager",
    ])
    stats = command(["redis-cli", "--raw", "INFO", "stats"])
    ping = command(["redis-cli", "--raw", "PING"]).strip()
    parsed = {}
    for line in stats.splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            parsed[key] = value.strip()
    if ping != "PONG":
        raise ValueError("Redis ping failed")
    values = {key: journal.count(pattern) for key, pattern in patterns.items()}
    for key in ("evicted_keys", "rejected_connections"):
        values[key] = int(parsed[key])
    values["redis_ping"] = 1
    values["updated_epoch"] = int(time.time())
    for key, value in values.items():
        print("{}={}".format(key, value))


if __name__ == "__main__":
    try:
        main()
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired,
            KeyError, ValueError):
        sys.stderr.write("ura_voicebot_metrics: collection failed\n")
        sys.exit(1)
