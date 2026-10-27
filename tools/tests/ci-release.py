#!/usr/bin/env python3
"""CI input/release gates, without a device, uploads or production credentials."""
import importlib.util
import io
import json
import runpy
from pathlib import Path
import subprocess
import struct
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch
import zlib

TOP = Path(__file__).resolve().parents[2]


def module(name):
    spec = importlib.util.spec_from_file_location(name.replace('-', '_'), TOP / 'tools' / (name + '.py'))
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


inputs = module('ci-inputs')
release = module('ci-release')


class Bootstrap(unittest.TestCase):
    def test_boot_strips_payload_and_preserves_avb(self):
        data = bytearray(64 << 20)
        data[:8] = b'ANDROID!'
        struct.pack_into('<I', data, 40, 4)
        data[4096:4120] = b'stock kernel to remove!!'
        data[8192:8448] = b'AVB0' + b'v' * 252
        data[-64:-60] = b'AVBf'
        struct.pack_into('>QQQ', data, len(data) - 52, 8192, 8192, 256)
        result = inputs.boot_template(bytes(data))
        self.assertNotIn(b'stock kernel', result)
        self.assertEqual(result[4096:4352], b'AVB0' + b'v' * 252)
        self.assertEqual(inputs.boot_template(result), result)

    def test_misc_strips_everything_outside_control(self):
        data = bytearray(b'x' * 4096)
        bc = bytearray(32)
        bc[4:8] = b'BCAB'
        struct.pack_into('<I', bc, 28, zlib.crc32(bc[:28]))
        data[0x800:0x820] = bc
        result = inputs.misc_template(data)
        self.assertEqual(result[0x800:0x820], bc)
        self.assertEqual(result[:0x800], bytes(0x800))

    def test_unsafe_archive_path_rejected_before_write(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'bad.tar.gz'
            with tarfile.open(path, 'w:gz') as archive:
                entry = tarfile.TarInfo('../outside'); entry.size = 1
                archive.addfile(entry, io.BytesIO(b'x'))
            with self.assertRaisesRegex(ValueError, 'path'):
                inputs.inspect(path)
            self.assertFalse((Path(temp).parent / 'outside').exists())

    def test_hash_checked_before_extracting(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'bad.tar.gz'; path.write_bytes(b'not an archive')
            args = type('Args', (), {'archive': path, 'sha256': '0' * 64, 'destination': Path(temp) / 'restore'})()
            with self.assertRaisesRegex(ValueError, 'SHA-256'):
                inputs.restore(args)
            self.assertFalse(args.destination.exists())

    def test_extra_package_rejected(self):
        with self.assertRaisesRegex(ValueError, 'exactly'):
            inputs.package_paths('P:cog\n\nP:libcogcore\n\nP:libwpewebkit\n\nP:vendor-firmware\n')


class RootAudit(unittest.TestCase):
    def audit(self, files, staged_vendor=None, kernel_out=None, nonexec=(), variant='standard'):
        with tempfile.TemporaryDirectory() as temp:
            top = Path(temp)
            (top / 'work/openwrt').mkdir(parents=True)
            (top / 'upstream/out-release').mkdir(parents=True)
            (top / 'upstream/out-release/kernel.release').write_text('6.18-e5\n')
            (top / 'device/linux_device_common/overlay/opt/e5').mkdir(parents=True)
            for name in release.BLOCK_SOURCES + (
                    'build-hostapd.sh', 'build-hostapd-inner.sh', 'hostapd.Dockerfile',
                    'patch-hostapd-sae.py', 'hostapd-unisoc-sae.h',
                    'wifi-sae-state.py', 'hostapd-unisoc.sh', 'hostapd-unisoc.uc'):
                target = top / 'openwrt' / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes((TOP / 'openwrt' / name).read_bytes())
            wifi_id = runpy.run_path(str(TOP / 'openwrt/wifi-sae-state.py'))['build_id']()
            files['etc/e5/wifi-sae.build-id'] = (wifi_id + '\n').encode()
            files['lib/netifd/hostapd-unisoc.sh'] = (TOP / 'openwrt/hostapd-unisoc.sh').read_bytes()
            files['usr/share/ucode/wifi/unisoc-sae.uc'] = (TOP / 'openwrt/hostapd-unisoc.uc').read_bytes()
            for name in ('vendor-start.sh', 'e5-modem-coldboot'):
                (top / 'device/linux_device_common/overlay/opt/e5' / name).write_bytes(b'startup fixture')
                files = {**files, 'opt/e5/' + name: b'startup fixture'}
            screen_source = TOP / 'ci/infoscreen/root/usr/share/e5-infoscreen'
            for name in ('settings.uc', 'api.uc', 'www/app.js', 'www/mobile.js'):
                target = top / 'ci/infoscreen/root/usr/share/e5-infoscreen' / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes((screen_source / name).read_bytes())
            if staged_vendor is not None:
                files.update({'etc/e5/feature-port.json': b'{"profile":"e5"}',
                              'opt/e5/vendor-start.sh': staged_vendor})
            if kernel_out:
                (top / kernel_out).mkdir(parents=True)
                (top / kernel_out / 'kernel.release').write_text('6.18-e5\n')
                (top / 'upstream/out-release/kernel.release').write_text('wrong-default\n')
            path = top / 'work/openwrt/e5-openwrt-25.12.6-generic-rootfs.tar.gz'
            with tarfile.open(path, 'w:gz') as archive:
                for name, data in files.items():
                    entry = tarfile.TarInfo(name); entry.size = len(data)
                    if name in ('etc/init.d/e5-boot-ok', 'etc/init.d/e5-infoscreen', 'usr/libexec/e5-infoscreen/session',
                                'usr/libexec/e5-infoscreen/plugin', 'usr/libexec/e5-infoscreen/update') and name not in nonexec:
                        entry.mode = 0o755
                    archive.addfile(entry, io.BytesIO(data))
            info = {'openwrt_version': '25.12.6', 'build_epoch': 123, 'variant': variant}
            def stage_nv(root):
                (root / 'opt/e5/vendor-start.sh').write_bytes(b'isolated NV fixture')
            env = {'E5_UPSTREAM_OUT': str(top / kernel_out)} if kernel_out else {}
            with patch.object(release, 'TOP', top), patch.object(release.subprocess, 'check_output', return_value=''), \
                 patch.object(release.runpy, 'run_path', return_value={'stage_nv': stage_nv, 'build_id': lambda: wifi_id}), \
                 patch.dict(release.os.environ, env):
                release.audit_root(info)
            return info

    def files(self):
        files = {'etc/e5/block-mount.build-id': b'fixture-block-build\n',
                'sbin/block': b'block fixture', 'lib/libblkid-tiny.so': b'probe fixture',
                'etc/init.d/fstab': b'fstab fixture',
                'etc/init.d/e5-boot-ok': b'#!/bin/sh\n',
                'etc/init.d/e5-infoscreen': b'#!/bin/sh\n',
                'usr/libexec/e5-infoscreen/session': b'#!/bin/sh\n',
                'usr/libexec/e5-infoscreen/plugin': b'#!/bin/sh\n',
                'usr/libexec/e5-infoscreen/update': b'#!/bin/sh\n',
                'usr/bin/openssl': b'OpenSSL fixture', 'usr/share/e5-infoscreen/VERSION': b'1.6.3',
                'etc/e5-infoscreen/plugins/phone/manifest.json': json.dumps({'version': '1.4'}).encode(),
                'etc/e5-infoscreen/plugins/daed/manifest.json': json.dumps({'version': '1.0.0'}).encode(),
                'etc/e5/block-mount.build-id': (release.block_build_id() + '\n').encode(),
                'sbin/block': b'block', 'lib/libblkid-tiny.so': b'library', 'etc/init.d/fstab': b'init',
                'etc/e5/build-time': b'123', 'lib/modules/6.18-e5/modem/sipc_wwan.ko': b'module'}
        source = TOP / 'ci/infoscreen/root/usr/share/e5-infoscreen'
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for name in ('settings.uc', 'api.uc', 'www/app.js', 'www/mobile.js'):
                target = root / name; target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes((source / name).read_bytes())
            subprocess.run([sys.executable, str(TOP / 'tools/patch-e5-daed-shortcut.py'), str(root)], check=True)
            for name in ('settings.uc', 'api.uc', 'www/app.js', 'www/mobile.js'):
                files['usr/share/e5-infoscreen/' + name] = (root / name).read_bytes()
        return files

    def test_same_release_and_epoch_pass(self):
        info = self.audit(self.files())
        self.assertEqual(info['phone_version'], '1.4')
        self.assertEqual(info['daed_screen_app_version'], '1.0.0')

    def test_wps_variant_marker_passes(self):
        files = self.files()
        files['etc/e5/device-variant'] = b'e5wps\n'
        self.audit(files, variant='wps')

    def test_wps_variant_marker_required(self):
        with self.assertRaisesRegex(ValueError, 'WPS root filesystem variant marker'):
            self.audit(self.files(), variant='wps')

    def test_standard_root_rejects_wps_marker(self):
        files = self.files()
        files['etc/e5/device-variant'] = b'e5wps\n'
        with self.assertRaisesRegex(ValueError, 'standard E5 root filesystem carries a WPS marker'):
            self.audit(files)

    def test_expected_e5_shortcut_overlay_passes(self):
        self.audit(self.files())

    def test_unexpected_e5_shortcut_change_rejected(self):
        files = self.files()
        files['usr/share/e5-infoscreen/settings.uc'] += b'\n// unexpected change\n'
        with self.assertRaisesRegex(ValueError, 'root source mismatch.*settings.uc'):
            self.audit(files)

    def test_nonexecutable_screen_start_rejected(self):
        with self.assertRaisesRegex(ValueError, 'not executable.*e5-infoscreen'):
            self.audit(self.files(), nonexec=('etc/init.d/e5-infoscreen',))

    def test_nonexecutable_boot_confirmation_rejected(self):
        with self.assertRaisesRegex(ValueError, 'not executable.*e5-boot-ok'):
            self.audit(self.files(), nonexec=('etc/init.d/e5-boot-ok',))

    def test_nonexecutable_plugin_manager_rejected(self):
        with self.assertRaisesRegex(ValueError, 'not executable.*plugin'):
            self.audit(self.files(), nonexec=('usr/libexec/e5-infoscreen/plugin',))

    def test_stale_block_mount_build_rejected(self):
        files = self.files(); files['etc/e5/block-mount.build-id'] = b'stale\n'
        with self.assertRaisesRegex(ValueError, 'block-mount'):
            self.audit(files)

    def test_missing_block_mount_payload_rejected(self):
        for name in ('sbin/block', 'lib/libblkid-tiny.so', 'etc/init.d/fstab'):
            files = self.files(); files.pop(name)
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, 'block-mount'):
                self.audit(files)

    def test_selected_kernel_output_pass(self):
        self.assertEqual(self.audit(self.files(), kernel_out='out/e5/kernel')['kernel_release'], '6.18-e5')

    def test_exact_nv_transformation_pass(self):
        self.audit(self.files(), staged_vendor=b'isolated NV fixture')

    def test_unexpected_nv_transformation_rejected(self):
        with self.assertRaisesRegex(ValueError, 'vendor-start'):
            self.audit(self.files(), staged_vendor=b'unexpected vendor fixture')

    def test_missing_openssl_rejected(self):
        files = self.files(); files.pop('usr/bin/openssl')
        with self.assertRaisesRegex(ValueError, 'openssl-util'):
            self.audit(files)

    def test_wrong_kernel_modules_rejected(self):
        files = self.files(); files['lib/modules/5.15/audio/card.ko'] = b'wrong kernel'
        with self.assertRaisesRegex(ValueError, 'modules'):
            self.audit(files)

    def test_wrong_build_time_rejected(self):
        files = self.files(); files['etc/e5/build-time'] = b'456'
        with self.assertRaisesRegex(ValueError, 'build time'):
            self.audit(files)

    def test_device_firmware_rejected(self):
        files = self.files(); files['lib/firmware/wcnmodem.bin'] = b'device firmware'
        with self.assertRaisesRegex(ValueError, 'device-specific'):
            self.audit(files)


    def test_unguarded_mount_package_rejected(self):
        files = self.files()
        files['etc/e5/block-mount.build-id'] = b'old-package\n'
        with self.assertRaisesRegex(ValueError, 'source mismatch'):
            self.audit(files)

    def test_missing_mount_package_payload_rejected(self):
        files = self.files()
        del files['sbin/block']
        with self.assertRaisesRegex(ValueError, 'block-mount payload missing'):
            self.audit(files)


class InternalUpdatePackage(unittest.TestCase):
    def fixture(self):
        members = {name: release.file_digest(path) for name, path in release.internal_update_sources().items()}
        members['files/network-addons-software.list'] = 'a' * 64
        boot = {'part_update': {'version': 1, 'script_sha256': release.file_digest(TOP / 'boot/part-update.sh')}}
        return members, boot

    def test_complete_update_chain_passes(self):
        release.verify_internal_update(*self.fixture())

    def test_missing_upload_tool_rejected(self):
        members, boot = self.fixture()
        del members['scripts/tools/e5-update.py']
        with self.assertRaisesRegex(ValueError, 'helper missing'):
            release.verify_internal_update(members, boot)

    def test_stale_boot_updater_rejected(self):
        members, boot = self.fixture()
        boot['part_update']['script_sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'boot updater'):
            release.verify_internal_update(members, boot)

    def test_missing_software_exclusions_rejected(self):
        members, boot = self.fixture()
        del members['files/network-addons-software.list']
        with self.assertRaisesRegex(ValueError, 'exclusion list'):
            release.verify_internal_update(members, boot)




class MagiskModuleSources(unittest.TestCase):
    def test_sd_registry_uses_shared_linux_overlay(self):
        sources = release.magisk_module_sources()
        self.assertEqual(
            sources['sd-registry.sh'],
            TOP / 'device/linux_device_common/overlay/opt/e5/e5-sd-registry')
        self.assertTrue(sources['sd-registry.sh'].is_file())


if __name__ == '__main__':
    unittest.main()
