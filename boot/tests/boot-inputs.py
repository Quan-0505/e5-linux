#!/usr/bin/env python3
"""Verify source files required to assemble the early E5 boot image."""
import importlib.util
from pathlib import Path
import unittest

REPO = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('build_boot_image', REPO/'boot/build-boot-image.py')
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class BootInputs(unittest.TestCase):
    def test_sd_registry_comes_from_shared_linux_overlay(self):
        expected = REPO/'device/linux_device_common/overlay/opt/e5/e5-sd-registry'
        source = MODULE.sd_registry_source()
        self.assertEqual(source, expected)
        self.assertTrue(source.is_file(), f'missing required boot input: {source}')
        self.assertGreater(source.stat().st_size, 0)


if __name__ == '__main__':
    unittest.main()
