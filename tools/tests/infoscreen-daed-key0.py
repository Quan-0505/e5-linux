#!/usr/bin/env python3
"""Test the configurable E5 keypad shortcut overlay against pinned upstream."""

from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

TOP = Path(__file__).resolve().parents[2]
SCREEN = TOP / "ci/infoscreen"
PATCHER = TOP / "tools/patch-e5-daed-shortcut.py"
FILES = (
    "root/usr/share/e5-infoscreen/www/app.js",
    "root/usr/share/e5-infoscreen/www/mobile.js",
    "root/usr/share/e5-infoscreen/settings.uc",
    "root/usr/share/e5-infoscreen/api.uc",
)

with tempfile.TemporaryDirectory(prefix="e5-shortcuts-") as temp:
    root = Path(temp)
    for source_name in FILES:
        data = subprocess.run(
            ["git", "-C", str(SCREEN), "show", f"HEAD:{source_name}"],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        ).stdout
        path = root / source_name.removeprefix("root/usr/share/e5-infoscreen/")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(data, encoding="utf-8")

    subprocess.run([sys.executable, str(PATCHER), str(root)], check=True)
    patched = {name: (root / name).read_text(encoding="utf-8") for name in ("www/app.js", "www/mobile.js", "settings.uc", "api.uc")}
    js = patched["www/app.js"]
    settings = patched["settings.uc"]
    api = patched["api.uc"]
    mobile = patched["www/mobile.js"]

    assert "return 'shortcut' + k" in js and "Numpad" in js
    assert "async function runScreenShortcut(digit)" in js
    assert "target == 'default'" in js and "target == 'off'" in js
    assert "target.startsWith('page:')" in js and "^app:([a-z0-9][a-z0-9_-]*)$" in js
    assert "if (keyLock(kind == 'power'" in js
    assert js.index("if (blank) {", js.index("if (keyLock(kind == 'power'")) < js.index("kind?.startsWith('shortcut')")
    assert "const digitKind = keyKind(m)" in js and "!T551MCalls.active()" in js
    assert "['ui', 'navigation', 'shortcuts'].includes(v.cat.id)" in js
    assert settings.count("id:`shortcut_${digit}`") == 1
    assert "uci_category('shortcuts', L('快捷按钮','Shortcut buttons')" in settings
    for target in ("default", "off", "app:daed", "app:phone", "page:${p[0]}"):
        assert target in settings
    screen_config = api.split("function screen_config() {", 1)[1].split("\n}\n", 1)[0]
    for digit in range(10):
        assert f"shortcut_{digit}: c.get('e5-infoscreen', 'main', 'shortcut_{digit}') ?? 'default'" in screen_config
    assert "shortcuts:'keyboard'" in mobile and "/^shortcut_[0-9]$/" in mobile

    node = shutil.which("node")
    if node:
        subprocess.run([node, "--check", str(root / "www/app.js")], check=True)
        subprocess.run([node, "--check", str(root / "www/mobile.js")], check=True)

    subprocess.run([sys.executable, str(PATCHER), str(root)], check=True)
    for name, content in patched.items():
        assert (root / name).read_text(encoding="utf-8") == content

builder = (TOP / "openwrt/build-rootfs.sh").read_text(encoding="utf-8")
patch_call = 'tools/patch-e5-daed-shortcut.py "$R/usr/share/e5-infoscreen"'
assert patch_call in builder
assert builder.index('python3 /in/feature-source/device/openwrt_device_common/shared/ui.py --root $R --profile e5') < builder.index(patch_call)
assert builder.index('python3 /in/feature-source/device/openwrt_device_e5/stage.py --root $R') < builder.index(patch_call)
# The screen was already hotpatched with the earlier fixed 0 -> DAED mapping
# on the E5. Keep support for that live state so the settings can be tested
# without first restoring the older app.js.
with tempfile.TemporaryDirectory(prefix="e5-shortcuts-hotpatch-") as temp:
    root = Path(temp)
    for source_name in FILES:
        path = root / source_name.removeprefix("root/usr/share/e5-infoscreen/")
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(SCREEN / source_name, path)
    subprocess.run([sys.executable, str(PATCHER), str(root)], check=True)
    js = (root / "www/app.js").read_text(encoding="utf-8")
    assert "openDaedShortcut" not in js
    assert "void runScreenShortcut(kind.slice(8))" in js
print("E5 keypad shortcuts: 0-9 UI, UCI persistence, page/app targets, guard order and idempotency passed")
