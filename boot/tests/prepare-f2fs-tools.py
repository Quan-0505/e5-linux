#!/usr/bin/env python3
"""Check output-path resolution both in the repository and the build mount."""
import importlib.util
from pathlib import Path
import unittest

BOOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('prepare_f2fs_tools', BOOT/'prepare-f2fs-tools.py')
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class OutputPath(unittest.TestCase):
    def test_repository_script_uses_repository_output_directory(self):
        self.assertEqual(MODULE.default_output_path(), BOOT.parent/'out/boot/f2fs-tools')

    def test_root_mounted_script_has_valid_default(self):
        self.assertEqual(MODULE.default_output_path(Path('/prepare-f2fs-tools.py')),
                         Path('/').resolve()/'out/boot/f2fs-tools')


if __name__ == '__main__':
    unittest.main()
