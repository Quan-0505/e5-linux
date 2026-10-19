#!/usr/bin/env python3
"""Verify the E5 DAED shortcut overlay applies cleanly to pinned upstream."""

from pathlib import Path
import subprocess
import sys
import tempfile

TOP = Path(__file__).resolve().parents[2]
SCREEN = TOP / "ci/infoscreen"
SOURCE = "root/usr/share/e5-infoscreen/www/app.js"
PATCHER = TOP / "tools/patch-e5-daed-shortcut.py"

base = subprocess.run(
    ["git", "-C", str(SCREEN), "show", f"HEAD:{SOURCE}"],
    check=True,
    capture_output=True,
    text=True,
    encoding="utf-8",
).stdout

with tempfile.TemporaryDirectory(prefix="e5-daed-key0-") as temp:
    app = Path(temp) / "app.js"
    app.write_text(base, encoding="utf-8")
    subprocess.run([sys.executable, str(PATCHER), str(app)], check=True)
    patched = app.read_text(encoding="utf-8")
    subprocess.run(["node", "--check", str(app)], check=True)
    assert patched.count("async function openDaedShortcut()") == 1
    assert "e.preventDefault();\n\t// the volume works" in patched
    key_handler = patched.index("if (keyLock(kind == 'power'")
    shortcut = patched.index("if (kind == 'daed')", key_handler)
    assert key_handler < patched.index("if (blank) {", key_handler) < shortcut
    assert "if (!e.repeat) void openDaedShortcut();" in patched
    assert "fromApp && !T551MCalls.active() && !m.repeat" in patched

    # Applying the overlay a second time must be harmless for local rebuilds.
    subprocess.run([sys.executable, str(PATCHER), str(app)], check=True)
    assert app.read_text(encoding="utf-8") == patched

builder = (TOP / "openwrt/build-rootfs.sh").read_text(encoding="utf-8")
assert "tools/patch-e5-daed-shortcut.py" in builder
assert builder.index("cp -a /in/infoscreen/root/. $R/") < builder.index("tools/patch-e5-daed-shortcut.py")
print("E5 DAED keypad-0 overlay: source, guard order, syntax, and idempotency passed")
