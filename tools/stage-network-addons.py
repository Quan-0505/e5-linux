#!/usr/bin/env python3
"""Stage only reproducible public software, then verify the generated E5 rootfs."""
import argparse
import hashlib
import json
import struct
import tarfile
import time
import urllib.error
import urllib.request
from pathlib import Path

TOP = Path(__file__).resolve().parents[1]
BASE = TOP / 'openwrt/network-addons'
WORK = TOP / 'work/network-addons'
LOCK = json.loads((BASE / 'lock.json').read_text())

def sha(data):
    return hashlib.sha256(data).hexdigest()

def download_with_retry(urls, timeout=60, retries=3):
    if isinstance(urls, str):
        urls = [urls]
    headers = {'User-Agent': 'Mozilla/5.0 (compatible; E5-Build/1.0)'}
    last_err = None
    for url in urls:
        req = urllib.request.Request(url, headers=headers)
        for attempt in range(1, retries + 1):
            try:
                with urllib.request.urlopen(req, timeout=timeout) as response:
                    return response.read()
            except (urllib.error.URLError, TimeoutError, OSError) as err:
                last_err = err
                print(f'Attempt {attempt}/{retries} failed for {url}: {err}', flush=True)
                if attempt < retries:
                    time.sleep(attempt * 2)
    raise last_err

def fetch():
    WORK.mkdir(parents=True, exist_ok=True)
    archive = WORK / 'nodebaby.tgz'
    if not archive.exists() or sha(archive.read_bytes()) != LOCK['nodebaby_sha256']:
        # No authorization is needed for this public software download.
        urls = [
            'https://github.com/Quan-0505/e5-linux/releases/download/build-inputs/owjdxb_openwrt_arm64_4.3.5-734.tgz',
            LOCK['nodebaby_url'],
        ]
        archive.write_bytes(download_with_retry(urls))
    assert sha(archive.read_bytes()) == LOCK['nodebaby_sha256'], 'NodeBaby checksum mismatch'
    binary = (WORK / 'daed').read_bytes()
    assert binary[:4] == b'\x7fELF' and binary[4] == 2 and struct.unpack('<H', binary[18:20])[0] == 183, 'Rust daed must be ARM64 ELF'
    assert f"version=v{LOCK['rust_daed_version']}".encode() in binary, 'Wrong Rust daed version'
    metadata = {**LOCK, 'rust_daed_binary_sha256': sha(binary), 'geo_sha256': {}}
    for name in ['geoip.dat', 'geosite.dat']:
        data = (WORK / name).read_bytes()
        assert len(data) > 100000 and not data.lstrip().startswith(b'<'), 'Invalid bundled public geodata'
        metadata['geo_sha256'][name] = sha(data)
    assert (WORK / 'web/index.html').is_file(), 'Rust DaedNext web UI missing'
    metadata['nodebaby_software_files'] = [name for name, _, _ in nodebaby_files()]
    # The internal updater snapshots selected settings from the running image.
    # Preserve NodeBaby identity/state, but never restore the old Go daemon's
    # init script over the Rust service shipped in the new root filesystem.
    snapshot_excludes = metadata['nodebaby_software_files'] + ['etc/init.d/daed']
    (WORK / 'software.list').write_text('\n'.join(snapshot_excludes) + '\n')
    (WORK / 'build.json').write_text(json.dumps(metadata, indent=2) + '\n')

def nodebaby_files():
    archive = WORK / 'nodebaby.tgz'
    assert sha(archive.read_bytes()) == LOCK['nodebaby_sha256']
    with tarfile.open(archive) as tar:
        for item in tar.getmembers():
            path = Path(item.name)
            assert path.parts and path.parts[0] == 'owjdxb' and not path.is_absolute() and '..' not in path.parts
            assert item.isdir() or item.isfile(), 'Unexpected link or special file in NodeBaby'
            if item.isfile():
                assert path.name not in {'.dmac', '.dmacv1', 'wing.db', 'daed.db'}, 'Device state in public payload'
                data = tar.extractfile(item).read()
                if path.as_posix() == 'owjdxb/start.sh':
                    assert data.count(b'    export SPECIAL_IFACE_NAME=lo') == 1
                    data = data.replace(b'    export SPECIAL_IFACE_NAME=lo\n', b'')
                mode = 0o755 if item.mode & 0o111 or path.suffix == '.sh' or path.name in {'owjdxb', 'NodeBabyLinkService', 'ownbsvman', 'owjdgjman'} else 0o644
                yield 'usr/local/' + path.as_posix(), data, mode

def payload():
    metadata = json.loads((WORK / 'build.json').read_text())
    assert all(metadata[key] == value for key, value in LOCK.items()), 'Build metadata does not match source lock'
    binary = (WORK / 'daed').read_bytes()
    assert sha(binary) == metadata['rust_daed_binary_sha256'], 'Rust daed changed after provenance recording'
    yield 'usr/bin/daed', binary, 0o755
    # Public data, never a user's config directory.
    for name in ['geoip.dat', 'geosite.dat']:
        data = (WORK / name).read_bytes()
        assert len(data) > 100000, 'Missing public geo data'
        assert sha(data) == metadata['geo_sha256'][name], 'Geo data changed after download'
        yield 'usr/share/daed/' + name, data, 0o644
    web = WORK / 'web'
    for path in sorted(web.rglob('*')):
        if path.is_file():
            yield 'usr/share/daed/web/' + path.relative_to(web).as_posix(), path.read_bytes(), 0o644
    yield from nodebaby_files()
    for path in sorted((BASE / 'overlay').rglob('*')):
        if path.is_file():
            name = path.relative_to(BASE / 'overlay').as_posix()
            mode = 0o755 if name.startswith(('etc/init.d/', 'usr/libexec/')) else 0o644
            yield name, path.read_bytes(), mode
    yield 'etc/e5/network-addons.json', (WORK / 'build.json').read_bytes(), 0o644

def stage(root):
    assert (root / 'sbin/init').exists(), 'Not an assembled OpenWrt root'
    for name, data, mode in payload():
        dest = root / name
        assert not dest.is_symlink(), 'Refusing to follow rootfs symlink: ' + name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        dest.chmod(mode)
    for service, start in [('daed', 95), ('owjdxb', 97)]:
        link = root / f'etc/rc.d/S{start}{service}'
        link.parent.mkdir(parents=True, exist_ok=True)
        link.unlink(missing_ok=True)
        link.symlink_to('../init.d/' + service)
    for name in ['etc/daed-kdae', 'etc/daed']:
        path = root / name
        if path.exists():
            assert not any(path.iterdir()), 'Personal controller state must not be bundled'

def verify(archive):
    with tarfile.open(archive) as tar:
        members = {item.name.removeprefix('./'): item for item in tar.getmembers()}
        assert 'sbin/init' in members and 'etc/openwrt_release' in members, 'Rootfs positive control missing'
        for name, data, mode in payload():
            item = members[name]
            assert item.isfile() and sha(tar.extractfile(item).read()) == sha(data), 'Installed payload differs: ' + name
            assert item.mode & 0o777 == mode, 'Bad permissions: ' + name
        for service, start in [('daed', 95), ('owjdxb', 97)]:
            item = members[f'etc/rc.d/S{start}{service}']
            assert item.issym() and item.linkname == '../init.d/' + service
        for name in members:
            assert not name.startswith(('etc/daed/', 'etc/daed-kdae/')), 'Controller state found'
            assert Path(name).name not in {'wing.db', 'daed.db', '.dmac', '.dmacv1', 'id_rsa', 'id_ed25519'}, 'Private state found: ' + name
        for program in ['tc', 'ip']:
            assert any(prefix + program in members for prefix in ['usr/sbin/', 'sbin/', 'usr/bin/', 'bin/']), 'Missing networking dependency: ' + program
        assert 'usr/share/daed/web/index.html' in members, 'Missing Rust DaedNext UI'
    cfg = (TOP / 'upstream/out-release/config').read_text()
    for option in ['NETKIT', 'VETH', 'BPF_SYSCALL', 'BPF_JIT', 'DEBUG_INFO_BTF', 'NET_CLS_ACT', 'NET_CLS_BPF', 'NET_SCH_INGRESS', 'NET_ACT_BPF', 'TUN']:
        assert f'CONFIG_{option}=y' in cfg.splitlines(), 'Required kernel capability dropped: ' + option
    print('Verified actual rootfs: Rust ARM64 daed, DaedNext UI, NodeBaby, services, LuCI entries, dependencies, privacy, kernel capabilities')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fetch', action='store_true')
    parser.add_argument('--root', type=Path)
    parser.add_argument('--verify-archive', type=Path)
    args = parser.parse_args()
    if args.fetch:
        fetch()
    if args.root:
        stage(args.root)
    if args.verify_archive:
        verify(args.verify_archive)
