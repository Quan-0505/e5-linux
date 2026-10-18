#!/usr/bin/env python3
"""Audit the E5 screen's small, allowlisted daed control panel."""
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

TOP = Path(__file__).resolve().parents[2]
APP = TOP / 'openwrt/infoscreen-plugins/daed'
manifest = json.loads((APP / 'manifest.json').read_text(encoding='utf-8'))
assert manifest['id'] == 'daed' and manifest['api_version'] == 2
assert manifest['entry'] == 'index.html' and manifest['version'] == '1.1.0'
assert {'index.html', 'daed.css', 'daed.js', 'manifest.json', 'backend.uc'} == {p.name for p in APP.iterdir()}

page = (APP / 'index.html').read_text(encoding='utf-8')
script = (APP / 'daed.js').read_text(encoding='utf-8')
backend = (APP / 'backend.uc').read_text(encoding='utf-8')
for label in ('启动', '停止', '重载', '更新订阅'):
    assert label in page
assert '/sdk/e5.js' in page and 'iframe' not in page
assert '2023' not in script and 'window.e5?.exit()' in script
assert "window.e5?.onBack(() => false)" in script
assert "window.e5?.onKey" in script and "window.e5?.press" in script
assert "window.e5.api('/status')" in script and "window.e5.api('/action'" in script
assert "订阅更新需要 daed 账号验证" in script
assert "订阅更新需要 daed 账号验证" in backend
assert "ctx.sh_json('/usr/bin/daed wait-ready --timeout 1s --json 2>/dev/null')" in backend
assert "'/etc/init.d/daed start'" in backend
assert "'/etc/init.d/daed stop'" in backend
assert "'/usr/bin/daed reload --timeout 20s --json >/dev/null 2>&1'" in backend
assert "req.body?.action" in backend and "index([ 'start', 'stop', 'reload' ], action)" in backend
assert "req.body" in backend and "ctx.run(req" not in backend
assert "password" not in backend.lower() and "token" not in backend.lower()

builder = (TOP / 'openwrt/build-rootfs.sh').read_text(encoding='utf-8')
auditor = (TOP / 'tools/ci-release.py').read_text(encoding='utf-8')
assert '/in/feature-source/openwrt/infoscreen-plugins/daed' in builder
assert "openwrt/infoscreen-plugins/daed" in auditor
assert "etc/e5-infoscreen/plugins/daed/manifest.json" in auditor
updater = (TOP / 'openwrt/device-install-image.sh').read_text(encoding='utf-8')
assert 'for app in phone daed' in updater
assert 'appstash' in updater

for path in APP.iterdir():
    assert path.is_file() and not path.is_symlink()
    data = path.read_bytes()
    assert b'\r' not in data and data.endswith(b'\n')
    if path.suffix in {'.html', '.js', '.css', '.json', '.uc'}:
        data.decode('utf-8')

# Exercise keep_config() against temporary images. It must ship the new built-in
# control panel while retaining unrelated installed apps and device settings.
installer = (TOP / 'openwrt/device-install-image.sh').read_text(encoding='utf-8')
start = installer.index('keep_config() {')
end = installer.index('\n}\n\n# The device\'s own files', start) + 2
function = installer[start:end]
shell = shutil.which('sh')
if shell:
    with tempfile.TemporaryDirectory(prefix='e5-screen-app-test-') as temp:
        old, new = Path(temp) / 'old', Path(temp) / 'new'
        def put(root, path, value):
            dest = root / path
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(value, encoding='utf-8')
        for app in ('phone', 'daed'):
            put(new, f'etc/e5-infoscreen/plugins/{app}/manifest.json', '{"version":"new"}')
            put(new, f'etc/e5-infoscreen/plugins/{app}/index.html', 'new bundled app')
            put(old, f'etc/e5-infoscreen/plugins/{app}/manifest.json', '{"version":"old"}')
            put(old, f'etc/e5-infoscreen/plugins/{app}/index.html', 'old installed app')
        put(old, 'etc/e5-infoscreen/plugins/other/index.html', 'user-installed app')
        put(old, 'etc/config/network', 'user config')
        put(new, 'usr/libexec/e5-network-addons-preserve-run', '#!/bin/sh\nexit 0\n')
        completed = subprocess.run([shell, '-c', function + '\nkeep_config "$1" "$2"\n',
                                    'test', str(old), str(new)], capture_output=True, text=True)
        assert completed.returncode == 0, completed.stderr or completed.stdout
        for app in ('phone', 'daed'):
            assert (new / f'etc/e5-infoscreen/plugins/{app}/index.html').read_text() == 'new bundled app'
        assert (new / 'etc/e5-infoscreen/plugins/other/index.html').read_text() == 'user-installed app'
        assert (new / 'etc/config/network').read_text() == 'user config'

print('daed info-screen controls: allowlisted local actions, SDK navigation, auth boundary, package staging and preserve-config contract: PASS')
