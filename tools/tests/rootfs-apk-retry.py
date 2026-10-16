#!/usr/bin/env python3
"""Exercise the retry function in the standalone image container's own shell."""
from pathlib import Path
import subprocess
import unittest

TOP = Path(__file__).resolve().parents[2]


class StandaloneApkRetry(unittest.TestCase):
    def run_retry(self, succeeds_on):
        source = (TOP / "openwrt/build-rootfs.sh").read_text()
        container = source.split("alpine:3.22 sh -euc '\n", 1)[1]
        function = container.split("\napk_retry add -q", 1)[0]
        script = """set -eu
calls=0
apk() { calls=$((calls + 1)); [ "$calls" -ge "$SUCCEEDS_ON" ]; }
sleep() { :; }
""" + function + """
result=0
apk_retry add -q e2fsprogs python3 binutils || result=$?
printf '%s %s' "$result" "$calls"
"""
        import os
        result = subprocess.run(["sh", "-c", script], env={**os.environ, "SUCCEEDS_ON": str(succeeds_on)}, capture_output=True, text=True, check=True)
        return result.stdout

    def test_transient_failure_recovers(self):
        self.assertEqual(self.run_retry(3), "0 3")

    def test_permanent_failure_is_bounded_and_propagated(self):
        self.assertEqual(self.run_retry(99), "1 4")


if __name__ == "__main__":
    unittest.main()
