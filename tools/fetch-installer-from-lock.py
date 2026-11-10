#!/usr/bin/env python3
"""Restore a reviewed desktop-installer archive pinned by tools/installer-inputs.lock.json.

The E5 firmware bundle embeds the Windows and macOS installers as opaque inputs.  The
input lock pins both the installer submodule commit and one published archive per
platform (URL + SHA-256), so a rebuild never has to re-create PyInstaller/Electron
artifacts for a commit that already shipped them.  When the platform job does produce
a fresh artifact this script is not used; it is the fallback for hosted-runner
failures that have nothing to do with the firmware (macOS runner quota, UI-only
regression drift).
"""
import hashlib
import json
import pathlib
import sys
import tarfile
import tempfile
import urllib.request

PLATFORMS = {
    'windows-x64': ('installer_windows', 'windows'),
    'macos-arm64': ('installer_macos', 'macos-arm64'),
    'android-aarch64': ('installer_android', 'android'),
}


def load_lock(top):
    data = json.loads((top / 'tools/installer-inputs.lock.json').read_text(encoding='utf-8'))
    if data.get('format') != 1:
        raise SystemExit('Unsupported installer input lock format')
    return data


def main(argv):
    if len(argv) != 3:
        raise SystemExit('usage: fetch-installer-from-lock.py <platform> <destination>')
    platform, destination = argv[1], pathlib.Path(argv[2]).resolve()
    if platform not in PLATFORMS:
        raise SystemExit('Unknown platform: ' + platform)
    key, _directory = PLATFORMS[platform]

    top = pathlib.Path(__file__).resolve().parent.parent
    lock = load_lock(top)
    pin = lock['installer_commit'][:7]
    record = lock['assets'][key]
    url, expected = record['url'], record['sha256']
    if '/build-tools-' + pin + '/' not in url or not url.endswith('/installer-' + platform + '-' + pin + '.tar.gz'):
        raise SystemExit('Locked archive does not belong to the pinned installer commit: ' + key)

    with tempfile.TemporaryDirectory(prefix='installer-lock-') as temporary:
        archive = pathlib.Path(temporary) / 'installer.tar.gz'
        digest = hashlib.sha256()
        print('fetch', url, flush=True)
        with urllib.request.urlopen(url, timeout=120) as response, archive.open('wb') as sink:
            while chunk := response.read(1 << 20):
                digest.update(chunk)
                sink.write(chunk)
        actual = digest.hexdigest()
        if actual != expected:
            raise SystemExit('Locked installer archive checksum mismatch: ' + key + ' ' + actual)

        destination.mkdir(parents=True, exist_ok=True)
        with tarfile.open(archive, 'r:gz') as bundle:
            for member in bundle.getmembers():
                target = (destination / member.name).resolve()
                if not target.is_relative_to(destination):
                    raise SystemExit('Unsafe installer archive path: ' + member.name)
                if member.issym() or member.islnk():
                    link = (target.parent / member.linkname).resolve()
                    if not link.is_relative_to(destination):
                        raise SystemExit('Unsafe installer archive link: ' + member.name)
            bundle.extractall(destination, filter='data')

    build = destination / 'build.json'
    if not build.is_file():
        raise SystemExit('Restored installer archive lacks build.json: ' + str(destination))
    print('restored', platform, 'from', pin, 'into', destination, flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
