#!/usr/bin/env python3
"""Apply a checked fix to the pinned infoscreen USB settings dispatcher."""
import hashlib
from pathlib import Path

top = Path(__file__).resolve().parents[1]
path = top / 'ci/infoscreen/root/usr/share/e5-infoscreen/settings.uc'
original = 'dc46dbca8cdda89da1eb85a696ae7415da2cd637a109795a0e7930763f59e271'
before = "\t\tif (id == 'check') return ctx.network_check();\n"
after = before + "\t\tif (index(['usb_role','usb_host_boot','usb_lan_auto','usb_net_mode','usb_net_scope','usb_net_auto'], id) < 0) return 'no such setting';\n"
source = path.read_bytes()
if after.encode() not in source:
    assert hashlib.sha256(source).hexdigest() == original, 'Unknown infoscreen source; review USB compatibility fix'
    assert source.count(before.encode()) == 1
    path.write_bytes(source.replace(before.encode(), after.encode()))
print('USB unknown-setting rejection applied before hardware status probing')
