#!/usr/bin/env python3
"""Verify ext4 helper lock-addon generation and mainline build wiring."""
import hashlib
from pathlib import Path
import runpy
import tarfile
import tempfile
import unittest
from unittest.mock import patch

TOP = Path(__file__).resolve().parents[2]
TOOLS = runpy.run_path(str(TOP / 'openwrt/prepare-ext4-tools.py'))


def arm64_elf():
    data = bytearray(64)
    data[:6] = b'\x7fELF\x02\x01'
    data[18:20] = (183).to_bytes(2, 'little')
    return bytes(data)


class Ext4Tools(unittest.TestCase):
    def test_lock_addon_contains_only_flock_and_its_checksum(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'root'
            baseline = Path(directory) / 'ext4-tools.tar'
            addon = Path(directory) / 'install-lock-tools.tar'
            for name in ('usr/sbin/e2fsck', 'usr/sbin/resize2fs',
                         'lib/ld-musl-aarch64.so.1', 'usr/bin/flock'):
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(arm64_elf())

            with patch.object(TOOLS['subprocess'], 'check_output', return_value=''):
                TOOLS['build'](root, baseline)
                TOOLS['build_lock'](root, baseline, addon)

            with tarfile.open(addon) as archive:
                self.assertEqual(set(archive.getnames()), {
                    'usr/bin/flock', 'INSTALL-LOCK-SHA256SUMS',
                })
                self.assertEqual(archive.extractfile('usr/bin/flock').read(), arm64_elf())
                checksum = archive.extractfile('INSTALL-LOCK-SHA256SUMS').read().decode()
                self.assertEqual(checksum, hashlib.sha256(arm64_elf()).hexdigest() + '  usr/bin/flock\n')

    def test_mainline_rootfs_generates_the_addon_before_packaging(self):
        source = (TOP / 'openwrt/build-rootfs.sh').read_text(encoding='utf-8')
        baseline = 'python3 /prepare-ext4-tools.py --root /tmp/r --out /out/ext4-tools.tar'
        addon = ('python3 /prepare-ext4-tools.py --root /tmp/r --lock-addon-from '
                 '/out/ext4-tools.tar --out /out/install-lock-tools.tar')
        self.assertIn(baseline, source)
        self.assertIn(addon, source)
        self.assertLess(source.index(baseline), source.index(addon))
        self.assertLess(source.index(addon), source.index('mke2fs -q -t ext4'))


if __name__ == '__main__':
    unittest.main()
