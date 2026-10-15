#!/usr/bin/env python3
"""Regress fork startup staging through upstream's real isolated-NV transform."""
from pathlib import Path
import runpy
import tempfile
from unittest.mock import patch

TOP = Path(__file__).resolve().parents[2]
stage = runpy.run_path(str(TOP / 'tools/stage-e5-compat.py'))['stage']
original = runpy.run_path

def load(path, *args, **kwargs):
    # UI packages are independent network downloads; this test covers boot/NV.
    if Path(path).resolve() == TOP / 'device/openwrt_device_common/shared/ui.py':
        return {'stage': lambda root, **kw: None}
    return original(path, *args, **kwargs)

with tempfile.TemporaryDirectory() as temp:
    root = Path(temp)
    for name in ('etc/init.d/e5-vendor', 'etc/init.d/e5-sipc-wwan',
                 'usr/libexec/e5-infoscreen/session', 'usr/share/rpcd/ucode/e5-infoscreen.uc'):
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text('fixture')
    (root / 'usr/share/e5-infoscreen').mkdir(parents=True)
    with patch.object(runpy, 'run_path', load):
        for _ in range(2):
            stage(root)
            vendor = (root / 'opt/e5/vendor-start.sh').read_text()
            assert vendor.count('nr_fixnv*|nr_runtimenv*|nr_deltanv*|calinv') == 1
            assert 'mount --bind /run/e5-bootconfig.android' in vendor
            assert 'for p in nr_modem nr_phy;' in vendor
            for name in ('etc/init.d/e5-boot-ok', 'usr/libexec/e5-gpt', 'opt/e5/e5-next-boot'):
                assert (root / name).read_bytes() == (TOP / 'openwrt/fork-compat/overlay' / name).read_bytes()
                assert (root / name).stat().st_mode & 0o111
    (root / 'etc/e5/device-profile').write_text('m8\n')
    try:
        stage(root)
    except ValueError:
        pass
    else:
        raise AssertionError('Foreign board accepted')
print('PASS: repeat staging retains internal boot/GPT and isolated NV; foreign board refused')
