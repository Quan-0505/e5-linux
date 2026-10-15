#!/usr/bin/env python3
"""Retain the reviewed MMC/EIC/thermal fixes before pinned E5 adaptation."""
import argparse
from pathlib import Path
import runpy
import subprocess

TOP = Path(__file__).resolve().parents[1]


def apply(kernel):
    kernel = Path(kernel).resolve()
    source = runpy.run_path(str(TOP / 'device/linux_device_e5/prepare-kernel.py'))
    commit = subprocess.check_output(['git', '-C', str(kernel), 'rev-parse', 'HEAD'], text=True).strip()
    if not commit.startswith(source['COMMIT']):
        raise ValueError('Unexpected E5 kernel revision: ' + commit)
    for name in ('emmc', 'eic', 'thermal'):
        runpy.run_path(str(TOP / 'devices/common' / (name + '.py')))['apply'](kernel)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('kernel', type=Path)
    apply(parser.parse_args().kernel)
