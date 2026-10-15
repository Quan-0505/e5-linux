#!/usr/bin/env python3
"""Stage pinned upstream E5 features while retaining the internal-install fixes.

Keep the device repositories clean. Supply fork startup sources before their
upstream NV transformation, then install the internal GPT/boot-ok interfaces.
"""
import argparse
from pathlib import Path
import runpy
import shutil

TOP = Path(__file__).resolve().parents[1]
OVERLAY = TOP / 'openwrt/fork-compat/overlay'


def stage(root):
    root = Path(root).resolve()
    module = runpy.run_path(str(TOP / 'device/openwrt_device_e5/stage.py'))
    upstream = module['stage']
    original_copy = upstream.__globals__['copy']

    def copy(target_root, source, target, mode=0o755, preserve=False):
        alternate = OVERLAY / target
        if target in ('opt/e5/e5-next-boot', 'opt/e5/vendor-start.sh'):
            source = alternate
        return original_copy(target_root, source, target, mode, preserve)

    upstream.__globals__['copy'] = copy
    try:
        upstream(root)
    finally:
        upstream.__globals__['copy'] = original_copy
    for name in ('etc/init.d/e5-boot-ok', 'usr/libexec/e5-gpt', 'opt/e5/android-import-perms.sh'):
        target = root / name
        if target.is_symlink():
            raise ValueError('Refusing to follow fork runtime symlink: ' + name)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(OVERLAY / name, target)
        target.chmod(0o755)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True, type=Path)
    stage(parser.parse_args().root)
