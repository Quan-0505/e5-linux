#!/usr/bin/env python3
"""Run the image updater's config migration against disposable directories."""
from pathlib import Path
import subprocess
import tarfile
import tempfile

top = Path(__file__).resolve().parents[2]
sources = [
    ('device-install-image.sh', '/tmp/e5-img.'),
    ('device-install-part.sh', '/tmp/e5-part.'),
]
with tempfile.TemporaryDirectory() as directory:
    base = Path(directory)
    def shell_path(path):
        if path.drive:
            return '/' + path.drive[0].lower() + path.as_posix()[2:]
        return str(path)

    def put(root, name, text):
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    for filename, temp_prefix in sources:
        source = (top / 'openwrt' / filename).read_text()
        start = source.index('keep_config() {')
        function = source[start:source.index('\n}\n', start) + 3]
        for bundled in (True, False):
            old = base / f'old-{filename}-{bundled}'
            new = base / f'new-{filename}-{bundled}'
            phone = 'etc/e5-infoscreen/plugins/phone/'
            for name, text in {
                'etc/config/network': 'user network', 'etc/shadow': 'user password',
                'etc/e5/contacts.json': 'user contacts', 'etc/e5/image-version': 'old',
                'etc/e5/build.json': 'stale old build metadata',
                'etc/e5/sim-radio': '0 1\n', 'etc/e5/release.json': 'old release',
                'etc/e5-infoscreen/plugins/other/user.json': 'other app data',
                phone + 'phone.js': 'old phone', phone + 'manifest.json': 'old manifest',
                'etc/e5-sounds/notification.wav': 'own ringtone bytes',
                'etc/e5-cpu-voltage.json': '{"offset":3125}',
                'etc/bluetooth/main.conf': '[General]\nName=User Bluetooth\n',
                'etc/unisoc-modem/apn-profiles.json': 'own per-SIM APN profiles',
            }.items():
                put(old, name, text)
            for name in ('image-version', 'image-form', 'build-time', 'release.json'):
                put(new, 'etc/e5/' + name, 'new ' + name)
            if bundled:
                put(new, 'etc/e5/build.json', 'new build metadata')
                put(new, phone + 'phone.js', 'new phone')
                put(new, phone + 'manifest.json', 'new manifest')
            if filename == 'device-install-image.sh':
                put(new, 'usr/libexec/e5-network-addons-preserve-run', '#!/bin/sh\nexit 0\n')
            script = function.replace(temp_prefix, shell_path(base / (filename + '.tmp.')))
            subprocess.run(['sh', '-ec', script + '\nkeep_config "$1" "$2"',
                            'test', shell_path(old), shell_path(new)], check=True)
            assert (new / (phone + 'phone.js')).read_text() == ('new phone' if bundled else 'old phone')
            assert (new / 'etc/e5/contacts.json').read_text() == 'user contacts'
            assert (new / 'etc/e5/sim-radio').read_text() == '0 1\n'
            assert (new / 'etc/config/network').read_text() == 'user network'
            assert (new / 'etc/shadow').read_text() == 'user password'
            assert (new / 'etc/e5/image-version').read_text() == 'new image-version'
            assert (new / 'etc/e5/release.json').read_text() == 'new release.json'
            build_meta = new / 'etc/e5/build.json'
            if bundled:
                assert build_meta.read_text() == 'new build metadata'
            else:
                assert not build_meta.exists(), 'stale build metadata survived the upgrade'
            if filename == 'device-install-image.sh':
                assert (new / 'etc/e5-infoscreen/plugins/other/user.json').read_text() == 'other app data'
                assert (new / 'etc/e5-sounds/notification.wav').read_text() == 'own ringtone bytes'
                assert (new / 'etc/e5-cpu-voltage.json').read_text() == '{"offset":3125}'
                assert (new / 'etc/bluetooth/main.conf').read_text() == '[General]\nName=User Bluetooth\n'
                assert (new / 'etc/unisoc-modem/apn-profiles.json').read_text() == 'own per-SIM APN profiles'
                assert not list(base.glob('device-install-image.sh.tmp.*phone.*'))

    source = (top / 'openwrt/device-install.sh').read_text()
    start = source.index("    # the new image's version and build metadata")
    end = source.index('\nfi\n', start)
    restore = source[start:end]
    for bundled in (True, False):
        old, payload, new = (base / f'debian-{name}-{bundled}' for name in ('old', 'payload', 'new'))
        put(old, 'etc/e5/build.json', 'stale old build metadata')
        for name in ('image-version', 'build-time', 'release.json'):
            put(payload, 'etc/e5/' + name, 'new ' + name)
        if bundled:
            put(payload, 'etc/e5/build.json', 'new build metadata')
        archive = base / f'debian-payload-{bundled}.tar.gz'
        with tarfile.open(archive, 'w:gz') as bundle:
            bundle.add(payload, arcname='.')
        script = 'NEW="$1"; T="$2"\n' + restore
        subprocess.run(['sh', '-ec', script, 'test', shell_path(old), shell_path(archive)], check=True)
        metadata = old / 'etc/e5/build.json'
        if bundled:
            assert metadata.read_text() == 'new build metadata'
        else:
            assert not metadata.exists(), 'Debian install retained stale build metadata'
print('PASS: upgrades keep user configuration but do not retain stale build metadata')
