#!/usr/bin/env python3
"""Keep the static daed info-screen launcher packaged and state-free."""
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

TOP = Path(__file__).resolve().parents[2]
APP = TOP / 'openwrt/infoscreen-plugins/daed'
manifest = json.loads((APP / 'manifest.json').read_text(encoding='utf-8'))
assert manifest['id'] == 'daed' and manifest['api_version'] == 2
assert manifest['entry'] == 'index.html' and manifest['version']
assert {'index.html', 'daed.css', 'daed.js', 'manifest.json'} == {p.name for p in APP.iterdir()}
assert not (APP / 'backend.uc').exists(), 'launcher must not add a root backend'

page = (APP / 'index.html').read_text(encoding='utf-8')
script = (APP / 'daed.js').read_text(encoding='utf-8')
assert '/sdk/e5.js' in page and 'iframe' in page
assert 'http://${host}:2023/' in script, 'management UI must resolve to this device only'
assert "window.e5?.exit()" in script and 'onBack(() => false)' in script
assert 'fetch(' not in script and 'backend.uc' not in script

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
    if path.suffix in {'.html', '.js', '.css', '.json'}:
        data.decode('utf-8')

# Exercise the actual keep_config() function against temporary old/new images.
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

print('daed info-screen app: local UI route, SDK return handling, rootfs staging, CI audit, and state-free payload: PASS')
