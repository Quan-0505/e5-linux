"""Stage event-driven low-battery shutdown into existing offline board roots."""
from pathlib import Path
import os
import runpy

TOP = Path(__file__).resolve().parents[1]
source_bytes = runpy.run_path(str(TOP/'devices/staging.py'))['source_bytes']


def stage(root):
    root = Path(root).resolve()
    if root == Path('/'):
        raise ValueError('Expected an offline root')
    entries = ['etc/init.d/unisoc-battery', 'etc/hotplug.d/power_supply/80-unisoc-battery']
    entries += [p.relative_to(TOP/'openwrt/overlay').as_posix()
                for p in (TOP/'openwrt/overlay/usr/libexec/unisoc-battery').glob('*.uc')]
    links = {'S86unisoc-battery': '../init.d/unisoc-battery',
             'K08unisoc-battery': '../init.d/unisoc-battery'}
    for name, target in links.items():
        path = root/'etc/rc.d'/name
        if path.is_symlink():
            if os.readlink(path) != target:
                raise ValueError('Foreign battery service link: '+str(path))
        elif path.exists():
            raise ValueError('Battery service link occupied: '+str(path))
    for name in entries:
        path = root/name
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.is_symlink():
            raise ValueError('Battery service destination is a symlink: '+str(path))
        path.write_bytes(source_bytes(TOP/'openwrt/overlay'/name))
        path.chmod(0o755 if name.startswith(('etc/init.d/', 'etc/hotplug.d/')) else 0o644)
    for name, target in links.items():
        path = root/'etc/rc.d'/name
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.is_symlink():
            path.symlink_to(target)
