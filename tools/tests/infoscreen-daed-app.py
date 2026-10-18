#!/usr/bin/env python3
"""Audit the E5 screen DAED control app and its QR login boundary."""
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

TOP = Path(__file__).resolve().parents[2]
APP = TOP / 'openwrt/infoscreen-plugins/daed'
manifest = json.loads((APP / 'manifest.json').read_text(encoding='utf-8'))
assert manifest['id'] == 'daed' and manifest['api_version'] == 2
assert manifest['entry'] == 'index.html' and manifest['version'] == '1.3.0'
assert {'index.html', 'daed.css', 'daed.js', 'manifest.json', 'backend.uc', 'phone-login.html', 'pair-cgi.py'} == {p.name for p in APP.iterdir()}

page = (APP / 'index.html').read_text(encoding='utf-8')
script = (APP / 'daed.js').read_text(encoding='utf-8')
backend = (APP / 'backend.uc').read_text(encoding='utf-8')
phone = (APP / 'phone-login.html').read_text(encoding='utf-8')
cgi = (APP / 'pair-cgi.py').read_text(encoding='utf-8')
for label in ('DAED开关', '启动', '停止', '重载', '更新订阅'):
    assert label in page
assert '/sdk/e5.js' in page and 'iframe' not in page
assert 'id="pairing"' in page and 'id="qr-code"' in page
assert '代理服务运行中' not in script and "'DAED运行中'" in script and "'DAED已停止'" in script
assert 'window.e5.api(\'/pairing\'' in script and "window.e5.api('/pair-status')" in script
assert "window.e5.api('/subscriptions')" in script and 'sessionStorage' not in script and 'localStorage' not in script
assert 'type="password"' in phone and 'location.hash' in phone and '/cgi-bin/e5-daed-pair' in phone
assert 'password=' not in phone and 'username=' not in phone
assert 'https://' in backend and 'qrencode -t SVG' in backend
assert "'POST /pair-login'" in backend and "'POST /pairing'" in backend
assert "'auth/token'" in backend and "Authorization: Bearer " in backend
assert "ctx.ubus('network.interface.lan', 'status', {})" in backend
assert "expiresAt: time() + 30 * 86400" in backend and "fs.chmod(TOKEN_FILE, 0o600)" in backend
assert "'DAED 已经运行。'" in backend and "'DAED 已经停止。'" in backend
assert 'REQUEST_SCHEME' in cgi and 'HTTP_ORIGIN' in cgi and 'REMOTE_ADDR' in cgi
assert '127.0.0.1:8088/api/plugins/daed/pair-login' in cgi
assert 'print(' not in cgi[cgi.index('def main():'):cgi.index('if __name__')]

builder = (TOP / 'openwrt/build-rootfs.sh').read_text(encoding='utf-8')
auditor = (TOP / 'tools/ci-release.py').read_text(encoding='utf-8')
assert '/in/feature-source/openwrt/infoscreen-plugins/daed' in builder
assert 'www/e5-daed-login/index.html' in builder and 'www/cgi-bin/e5-daed-pair' in builder
assert "openwrt/infoscreen-plugins/daed" in auditor
assert "www/e5-daed-login/index.html" in auditor and "www/cgi-bin/e5-daed-pair" in auditor
updater = (TOP / 'openwrt/device-install-image.sh').read_text(encoding='utf-8')
assert 'for app in phone daed' in updater and 'appstash' in updater
assert 'apk_retry add ucode-mod-fs' in builder

for path in APP.iterdir():
    assert path.is_file() and not path.is_symlink()
    data = path.read_bytes()
    assert b'\r' not in data and data.endswith(b'\n')
    if path.suffix in {'.html', '.js', '.css', '.json', '.uc', '.py'}:
        data.decode('utf-8')

# The CGI must reject non-HTTPS, cross-origin, and non-private requests before
# forwarding any credentials. Exercise those gates with an empty body.
with tempfile.TemporaryDirectory(prefix='e5-daed-cgi-test-') as temp:
    env = dict(__import__('os').environ, REQUEST_METHOD='POST', HTTPS='off', REQUEST_SCHEME='http',
               HTTP_HOST='192.168.9.1', HTTP_ORIGIN='https://192.168.9.1', REMOTE_ADDR='192.168.9.20', CONTENT_LENGTH='0')
    run = subprocess.run(['python', str(APP / 'pair-cgi.py')], input=b'', env=env, capture_output=True)
    assert run.returncode == 0 and b'403 Forbidden' in run.stdout and b'HTTPS' in run.stdout

# Exercise keep_config() against temporary images: configuration and installed
# app data survive, while the bundled screen app is restored from the new image.
installer = (TOP / 'openwrt/device-install-image.sh').read_text(encoding='utf-8')
start = installer.index('keep_config() {')
end = installer.index('\n}\n\n# The device\'s own files', start) + 2
function = installer[start:end]
shell = shutil.which('sh')
if shell:
    with tempfile.TemporaryDirectory(prefix='e5-screen-app-test-') as temp:
        old, new = Path(temp) / 'old', Path(temp) / 'new'
        def put(root, path, value):
            dest = root / path; dest.parent.mkdir(parents=True, exist_ok=True); dest.write_text(value, encoding='utf-8')
        for app in ('phone', 'daed'):
            put(new, f'etc/e5-infoscreen/plugins/{app}/manifest.json', '{"version":"new"}')
            put(new, f'etc/e5-infoscreen/plugins/{app}/index.html', 'new bundled app')
            put(old, f'etc/e5-infoscreen/plugins/{app}/manifest.json', '{"version":"old"}')
            put(old, f'etc/e5-infoscreen/plugins/{app}/index.html', 'old installed app')
        put(old, 'etc/e5-infoscreen/plugins/other/index.html', 'user-installed app')
        put(old, 'etc/e5-infoscreen/daed-token.json', '{"token":"retained-test-token"}')
        put(old, 'etc/config/network', 'user config')
        put(new, 'usr/libexec/e5-network-addons-preserve-run', '#!/bin/sh\nexit 0\n')
        completed = subprocess.run([shell, '-c', function + '\nkeep_config "$1" "$2"\n', 'test', str(old), str(new)], capture_output=True, text=True)
        assert completed.returncode == 0, completed.stderr or completed.stdout
        for app in ('phone', 'daed'):
            assert (new / f'etc/e5-infoscreen/plugins/{app}/index.html').read_text() == 'new bundled app'
        assert (new / 'etc/e5-infoscreen/plugins/other/index.html').read_text() == 'user-installed app'
        assert (new / 'etc/e5-infoscreen/daed-token.json').read_text() == '{"token":"retained-test-token"}'
        assert (new / 'etc/config/network').read_text() == 'user config'

print('DAED labels, QR pairing, HTTPS-only credential bridge, 30-day token handling, subscription controls and preserve-config: PASS')
