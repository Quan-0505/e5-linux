#!/usr/bin/env python3
"""Reject legacy APKs, source drift and changed binaries before image assembly."""
import importlib.util
import contextlib
import json
import os
import runpy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

TOP = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('package_state', TOP / 'tools/openwrt-package-state.py')
package = importlib.util.module_from_spec(spec)
spec.loader.exec_module(package)


class PackageState(unittest.TestCase):
    def test_real_shared_stager_and_helpers_are_fingerprinted(self):
        inputs = package.sources('25.12.6')['files']
        common = TOP / 'device/openwrt_device_common'
        stager = common / 'shared/network-startup.py'
        self.assertIn(stager.relative_to(TOP).as_posix(), inputs)
        stage = runpy.run_path(str(stager))['patch_root']
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            # Windows may lack symlink privilege; Linux CI exercises real links.
            links = patch.object(Path, 'symlink_to') if os.name == 'nt' else contextlib.nullcontext()
            with links:
                stage(root, 'e5')
            for asset in ('usr/libexec/e5-mm-report-ports',
                          'etc/hotplug.d/wwan/26-e5-sipa-eth',
                          'usr/libexec/e5-network-recovery',
                          'etc/init.d/e5-network-recovery'):
                source = common / 'overlay' / asset
                self.assertIn(source.relative_to(TOP).as_posix(), inputs)
                self.assertEqual((root / asset).read_bytes(),
                                 source.read_bytes().replace(b'\r\n', b'\n'))

    def test_apk_and_source_changes_make_the_record_different(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory)
            daemon = out / 'modemmanager-1.24.0-r914.apk'; daemon.write_bytes(b'daemon build A')
            rpc = out / 'modemmanager-rpcd-1.24.0-r914.apk'; rpc.write_bytes(b'RPC build A')
            with patch.object(package, 'OUT', out), patch.object(package, 'sources', return_value={'patch': 'A'}):
                saved = package.inspect('25.12.6')
                daemon.write_bytes(b'old daemon copied into new build')
                self.assertNotEqual(package.inspect('25.12.6'), saved)
                daemon.write_bytes(b'daemon build A')
                self.assertEqual(package.inspect('25.12.6'), saved)
            with patch.object(package, 'OUT', out), patch.object(package, 'sources', return_value={'patch': 'B'}):
                self.assertNotEqual(package.inspect('25.12.6'), saved)

    def test_missing_required_package_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory)
            (out / 'modemmanager-rpcd-1.24.0-r914.apk').write_bytes(b'RPC only')
            with patch.object(package, 'OUT', out), self.assertRaises(ValueError):
                package.inspect('25.12.6')


if __name__ == '__main__':
    unittest.main()
