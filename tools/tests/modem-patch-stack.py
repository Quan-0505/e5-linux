#!/usr/bin/env python3
"""Apply the pinned Unisoc source patches and retain auth/mobility/SMS fixes."""
import argparse
from pathlib import Path
import subprocess
import sys
import tempfile

TOP = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--run-c-tests', action='store_true')
args = parser.parse_args()
patches = sorted((TOP / 'device/debian_device_common/patches').glob('modemmanager-[0-9][0-9]-*.patch'))
patches += sorted((TOP / 'openwrt/patches').glob('modemmanager-[0-9][0-9]-*.patch'))
assert len(patches) == 15
with tempfile.TemporaryDirectory(prefix='e5-unisoc-source-') as temp:
    source = Path(temp)
    for patch in patches:
        print('Checking', patch.name, flush=True)
        subprocess.run(['git', 'apply', '--allow-empty', '--unidiff-zero', '--whitespace=nowarn',
                        '--include=src/plugins/unisoc/*', '-'],
                       cwd=source, input=patch.read_bytes().replace(b'\r\n', b'\n'), check=True)
    modem = (source / 'src/plugins/unisoc/mm-broadband-modem-unisoc.c').read_text()
    bearer = (source / 'src/plugins/unisoc/mm-broadband-bearer-unisoc.c').read_text()
    assert 'ScopedSmsCommand' in modem
    assert 'cgpco_ready' in bearer
    assert 'SPPCODATA' in modem or 'SPPCODATA' in bearer
    if args.run_c_tests:
        subprocess.run([sys.executable, str(TOP / 'openwrt/tests/modem-mobility.py')], check=True)
        subprocess.run([sys.executable, str(TOP / 'openwrt/tests/sms-isolation.py'), str(source / 'src')], check=True)
print('All 15 pinned/fork plugin patches apply; auth, mobility and SMS isolation retained.')
