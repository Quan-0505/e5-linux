#!/usr/bin/env python3
"""Exercise standard and E5-WPS add-on staging without external artifacts."""
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import struct
import tarfile
import tempfile
from unittest.mock import patch

TOP = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('addons_variants', TOP / 'tools/stage-network-addons.py')
addons = importlib.util.module_from_spec(spec)
spec.loader.exec_module(addons)
update = __import__('runpy').run_path(str(TOP / 'tools/e5-update.py'))
update['validate_variant_layout']('wps', 'part')
update['validate_variant_layout']('standard', 'sd')
for layout in ('sd', 'image'):
    try:
        update['validate_variant_layout']('wps', layout)
        raise AssertionError('WPS update accepted non-e5root layout: ' + layout)
    except ValueError as error:
        assert 'existing internal e5root partition' in str(error)
stage_script = (TOP / 'openwrt/device-stage-part-update.sh').read_text()
assert 'E5-WPS updates require the existing internal e5root partition' in stage_script

def digest(data):
    return hashlib.sha256(data).hexdigest()

with tempfile.TemporaryDirectory() as temp:
    temp = Path(temp)
    source = temp / 'source'
    work = temp / 'work'
    (source / 'upstream/out-release').mkdir(parents=True)
    options = ['NETKIT', 'VETH', 'BPF_SYSCALL', 'BPF_JIT', 'DEBUG_INFO_BTF', 'NET_CLS_ACT',
               'NET_CLS_BPF', 'NET_SCH_INGRESS', 'NET_ACT_BPF', 'TUN']
    (source / 'upstream/out-release/config').write_text(
        ''.join(f'CONFIG_{option}=y\n' for option in options))
    work.mkdir()

    archive_bytes = io.BytesIO()
    with tarfile.open(fileobj=archive_bytes, mode='w:gz') as archive:
        for name, data, mode in (
                ('owjdxb/start.sh', b'    export SPECIAL_IFACE_NAME=lo\n', 0o755),
                ('owjdxb/bin/owjdxb', b'nodebaby fixture\n', 0o755)):
            info = tarfile.TarInfo(name); info.size = len(data); info.mode = mode
            archive.addfile(info, io.BytesIO(data))
    nodebaby = archive_bytes.getvalue()
    lock = dict(addons.LOCK, nodebaby_sha256=digest(nodebaby))
    addons.LOCK, addons.TOP, addons.WORK = lock, source, work
    (work / 'nodebaby.tgz').write_bytes(nodebaby)

    daemon = bytearray(64)
    daemon[:4] = b'\x7fELF'; daemon[4] = 2
    struct.pack_into('<H', daemon, 18, 183)
    daemon += b'version=v' + lock['rust_daed_version'].encode()
    daemon = bytes(daemon)
    (work / 'daed').write_bytes(daemon)
    (work / 'web').mkdir()
    (work / 'web/index.html').write_text('<!doctype html><title>fixture</title>')
    for name in ('geoip.dat', 'geosite.dat'):
        (work / name).write_bytes((name.encode() + b'\0') * 50001)

    software_paths = [name for name, _, _ in addons.nodebaby_files()]
    software_paths += ['etc/init.d/owjdxb', 'etc/config/nodebaby',
                       'usr/libexec/e5-nodebaby-guard',
                       'usr/share/luci/menu.d/luci-app-nodebaby.json',
                       'www/luci-static/resources/view/network-addons/nodebaby.js',
                       'etc/init.d/daed']

    def set_metadata(variant):
        metadata = {**lock, 'variant': variant, 'nodebaby_enabled': variant == 'standard',
                    'rust_daed_binary_sha256': digest(daemon),
                    'geo_sha256': {name: digest((work / name).read_bytes())
                                   for name in ('geoip.dat', 'geosite.dat')},
                    'nodebaby_software_files': [name for name, _, _ in addons.nodebaby_files()]}
        (work / 'build.json').write_text(json.dumps(metadata, indent=2) + '\n')
        (work / 'software.list').write_text('\n'.join(software_paths) + '\n')

    def root_fixture(label):
        root = temp / label
        for name in ('sbin/init', 'sbin/ip', 'sbin/tc', 'etc/openwrt_release'):
            path = root / name; path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('fixture\n')
        return root

    def pack(root, output, variant):
        links = {'etc/rc.d/S95daed': '../init.d/daed',
                 'etc/rc.d/S97owjdxb': '../init.d/owjdxb'}
        modes = {name: mode for name, _, mode in addons.payload(variant)}
        with tarfile.open(output, 'w') as archive:
            for path in sorted(root.rglob('*')):
                if path.is_dir():
                    continue
                name = path.relative_to(root).as_posix()
                if name in links:
                    link = tarfile.TarInfo(name)
                    link.type = tarfile.SYMTYPE; link.linkname = links[name]
                    archive.addfile(link)
                else:
                    data = path.read_bytes()
                    item = tarfile.TarInfo(name); item.size = len(data)
                    item.mode = modes.get(name, 0o644)
                    archive.addfile(item, io.BytesIO(data))

    def fixture_symlink(path, target, target_is_directory=False):
        # Windows runners may lack symlink privilege. The archive builder above
        # emits the exact POSIX links that the production Linux image needs.
        path.write_text('symlink fixture: ' + target)

    # Standard E5 keeps NodeBaby and does not carry the WPS variant marker.
    set_metadata('standard')
    standard = root_fixture('standard')
    with patch.object(Path, 'symlink_to', fixture_symlink):
        addons.stage(standard, 'standard')
    assert (standard / 'usr/local/owjdxb/bin/owjdxb').is_file()
    assert not (standard / 'etc/e5/device-variant').exists()
    pack(standard, temp / 'standard-root.tar', 'standard')
    addons.verify(temp / 'standard-root.tar', 'standard')

    # A WPS update from an older standard image removes stale NodeBaby files.
    set_metadata('wps')
    wps = root_fixture('wps')
    stale = ('etc/init.d/owjdxb', 'etc/config/nodebaby', 'usr/libexec/e5-nodebaby-guard',
             'usr/share/luci/menu.d/luci-app-nodebaby.json',
             'www/luci-static/resources/view/network-addons/nodebaby.js',
             'usr/local/owjdxb/bin/owjdxb')
    for name in stale:
        path = wps / name; path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('stale fixture\n')
    rc = wps / 'etc/rc.d/S97owjdxb'; rc.parent.mkdir(parents=True, exist_ok=True)
    rc.write_text('stale symlink fixture\n')
    with patch.object(Path, 'symlink_to', fixture_symlink):
        addons.stage(wps, 'wps')
    assert (wps / 'etc/e5/device-variant').read_text().strip() == 'e5wps'
    assert not (wps / 'usr/local/owjdxb/bin/owjdxb').exists()
    for name in stale[:-1]:
        assert not (wps / name).exists(), f'stale WPS NodeBaby entry remains: {name}'
    assert not rc.exists()
    exclusions = set((work / 'software.list').read_text().splitlines())
    assert set(software_paths).issubset(exclusions)

    packed = temp / 'wps-root.tar'
    pack(wps, packed, 'wps')
    addons.verify(packed, 'wps')

    try:
        list(addons.payload('standard'))
        raise AssertionError('WPS metadata was accepted as standard E5')
    except AssertionError as error:
        assert 'variant mismatch' in str(error)

print('PASS: standard E5 retains NodeBaby; WPS removes stale NodeBaby, sets marker and passes rootfs verification')
