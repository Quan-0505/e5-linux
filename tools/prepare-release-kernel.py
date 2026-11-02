#!/usr/bin/env python3
"""Apply upstream E5 policies to a clean kernel and record their exact source."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import runpy
import subprocess
import sys

TOP = Path(__file__).resolve().parents[1]
POLICIES = (
    'devices/common/display.py', 'devices/e5/panel-dither.py',
    'devices/common/power.py', 'devices/common/charger-capabilities.py',
    'devices/common/emmc.py', 'devices/common/sd-power.py',
    'devices/common/eic.py', 'devices/common/thermal.py',
    'devices/common/sipa.py', 'devices/common/wifi-tx.py',
    'devices/common/fuel-gauge.py', 'devices/common/wifi-sae.py',
    'devices/common/wifi-stations.py', 'devices/common/wcn-firmware.py',
)


def prepare(kernel):
    kernel = kernel.resolve()
    check = runpy.run_path(str(TOP / 'upstream/check-kernel-source.py'))['check']
    baseline = check(kernel)
    def git(*args):
        return subprocess.check_output(['git', '-C', str(kernel), *args])
    for policy in POLICIES:
        subprocess.run([sys.executable, str(TOP / policy), str(kernel)], check=True)
    # Include newly added headers in the readable policy diff, then require
    # every policy to be idempotent before accepting that diff as an input.
    subprocess.run(['git', '-C', str(kernel), 'add', '--all'], check=True)
    patch = git('diff', '--cached', '--binary', 'HEAD')
    for policy in POLICIES:
        subprocess.run([sys.executable, str(TOP / policy), str(kernel)], check=True)
    if git('diff', '--binary') or git('ls-files', '--others', '--exclude-standard'):
        raise ValueError('Kernel policies are not idempotent; refusing to compile')
    if patch:
        env = dict(os.environ)
        # A real local build commit keeps the existing clean-tree gates intact.
        # It is never pushed to the upstream kernel repository.
        subprocess.run(['git', '-C', str(kernel), '-c', 'user.name=E5 release builder',
                        '-c', 'user.email=build@users.noreply.github.com', 'commit',
                        '-m', 'Apply tracked E5 release policies'], check=True, env=env)
    prepared = check(kernel)
    directory = TOP / 'out/release'
    directory.mkdir(parents=True, exist_ok=True)
    (directory / 'kernel-policy.patch').write_bytes(patch)
    record = {'baseline_revision': baseline, 'prepared_revision': prepared,
              'patch_sha256': hashlib.sha256(patch).hexdigest(),
              'e5_source_revision': subprocess.check_output(
                  ['git', '-C', str(TOP), 'rev-parse', 'HEAD'], text=True).strip(),
              'policies': {p: hashlib.sha256((TOP / p).read_bytes()).hexdigest()
                           for p in POLICIES}}
    (directory / 'kernel-policy.json').write_text(json.dumps(record, indent=2) + '\n')
    print('Verified clean E5 policy kernel:', prepared)


def verify(kernel):
    record = json.loads((TOP / 'out/release/kernel-policy.json').read_text())
    check = runpy.run_path(str(TOP / 'upstream/check-kernel-source.py'))['check']
    if check(kernel) != record['prepared_revision']:
        raise ValueError('Kernel differs from the verified policy source')
    patch = subprocess.check_output(['git', '-C', str(kernel), 'diff', '--binary',
                                     record['baseline_revision'], record['prepared_revision']])
    if hashlib.sha256(patch).hexdigest() != record['patch_sha256']:
        raise ValueError('Kernel policy diff changed')
    for path, expected in record['policies'].items():
        if hashlib.sha256((TOP / path).read_bytes()).hexdigest() != expected:
            raise ValueError('Kernel policy input changed: ' + path)
    print('Kernel policy source and patch hashes verified')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('kernel', type=Path)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    (verify if args.check else prepare)(args.kernel)
