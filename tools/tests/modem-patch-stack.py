#!/usr/bin/env python3
"""Apply the pinned Unisoc source patches and retain auth/mobility/SMS fixes."""
import argparse
import hashlib
import urllib.request
from pathlib import Path
import subprocess
import sys
import tempfile

TOP = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--run-c-tests', action='store_true')
parser.add_argument('--real-source', action='store_true', help='Verify the full patches against checksum-pinned ModemManager 1.24.0')
args = parser.parse_args()
patches = sorted((TOP / 'device/debian_device_common/patches').glob('modemmanager-[0-9][0-9]-*.patch'))
patches += sorted((TOP / 'openwrt/patches').glob('modemmanager-[0-9][0-9]-*.patch'))
assert len(patches) == 15
with tempfile.TemporaryDirectory(prefix='e5-unisoc-source-') as temp:
    source = Path(temp)
    if args.real_source:
        blob = urllib.request.urlopen('https://sources.openwrt.org/modemmanager-1.24.0.tar.zst', timeout=60).read()
        assert hashlib.sha256(blob).hexdigest() == 'b81e0fc5a112fa52dd7ec72cdb684e10b04755a3492ea392cf6cde5688bb0e03'
        archive = source / 'source.tar.zst'
        archive.write_bytes(blob)
        subprocess.run(['tar', '--zstd', '-xf', str(archive), '-C', str(source)], check=True)
        source = source / 'modemmanager-1.24.0'
        assert (source / 'src/mm-base-bearer.c').is_file()
    for patch in patches:
        print('Checking', patch.name, flush=True)
        if args.real_source:
            subprocess.run(['git', 'apply', '--unidiff-zero', '--whitespace=nowarn', '-'], cwd=source, input=patch.read_bytes().replace(b'\r\n', b'\n'), check=True)
            continue
        subprocess.run(['git', 'apply', '--allow-empty', '--unidiff-zero', '--whitespace=nowarn',
                        '--include=src/plugins/unisoc/*', '-'],
                       cwd=source, input=patch.read_bytes().replace(b'\r\n', b'\n'), check=True)
    modem = (source / 'src/plugins/unisoc/mm-broadband-modem-unisoc.c').read_text()
    bearer = (source / 'src/plugins/unisoc/mm-broadband-bearer-unisoc.c').read_text()
    assert 'ScopedSmsCommand' in modem
    assert 'cgpco_ready' in bearer
    assert 'SPPCODATA' in modem or 'SPPCODATA' in bearer
    if args.run_c_tests:
        subprocess.run([sys.executable, str(TOP / 'openwrt/tests/modem-mobility.py')] + ([str(source / 'src')] if args.real_source else []), check=True)
        subprocess.run([sys.executable, str(TOP / 'openwrt/tests/sms-isolation.py'), str(source / 'src')], check=True)
print('All 15 pinned/fork plugin patches apply; auth, mobility and SMS isolation retained.')
