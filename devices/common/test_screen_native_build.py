"""Native-screen cache must survive disposal of the build volume safely."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('screen_native', Path(__file__).with_name('build-screen-native.py'))
native = importlib.util.module_from_spec(spec)
spec.loader.exec_module(native)


class NativeCache(unittest.TestCase):
    def test_verified_cache_needs_no_docker_but_tampering_rebuilds(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = root/'layout.json'
            config.write_text(json.dumps({'native_screen': {'toolchain': 'fixture', 'volume': 'fixture', 'image': 'fixture'}}))
            elf = bytearray(64)
            elf[:6] = b'\x7fELF\x02\x01'
            elf[18:20] = (183).to_bytes(2, 'little')

            def compile_fixture(command, **kwargs):
                (root/'t551m-sim-status.tmp').write_bytes(elf)

            with patch.object(native, 'OUT', root), patch.object(native, 'linux', side_effect=str), \
                    patch.object(native.subprocess, 'run', side_effect=compile_fixture) as compiler:
                output = native.build(['t551m-sim-status'], config)['t551m-sim-status']
                self.assertEqual(compiler.call_count, 1)
                self.assertIn('/build/openwrt/staging_dir/target-aarch64_generic_musl/usr/include/gio-unix-2.0',
                              [arg[2:] for arg in compiler.call_args.args[0] if arg.startswith('-I')])
                # CI removes the toolchain volume here. A matching fingerprint
                # and binary hash must permit staging without invoking Docker.
                compiler.side_effect = AssertionError('toolchain volume is gone')
                self.assertEqual(native.build(['t551m-sim-status'], config)['t551m-sim-status'], output)
                self.assertEqual(compiler.call_count, 1)
                output.write_bytes(b'corrupt')
                compiler.side_effect = compile_fixture
                native.build(['t551m-sim-status'], config)
                self.assertEqual(compiler.call_count, 2)
                self.assertEqual(output.read_bytes(), elf)
                config.write_text(json.dumps({'native_screen': {'toolchain': 'changed', 'volume': 'fixture', 'image': 'fixture'}}))
                native.build(['t551m-sim-status'], config)
                self.assertEqual(compiler.call_count, 3)


if __name__ == '__main__':
    unittest.main()
