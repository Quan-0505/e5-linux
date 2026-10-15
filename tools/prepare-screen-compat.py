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

# The pinned network harness predates the shared hotspot module. Keep the
# wireless-state unit dependency explicit and mount the real module for API tests.
path = top / 'ci/infoscreen/tests/network-checks.sh'
source = path.read_bytes()
before = b"source = (top / 'root/usr/share/e5-infoscreen/api.uc').read_text()"
after = b"shutil.copytree(top.parent.parent / 'device/openwrt_device_common/luci-app-t551m/root/usr/libexec/unisoc-modem', temp / 'unisoc-modem')\n" + before
if after not in source:
    assert hashlib.sha256(source).hexdigest() == '63bb2b4577bd2dc8b590144d6efc2add7112113be42279e163554ad71537790d'
    source = source.replace(before, after)
    source = source.replace(b'const cursor=ctx.cursor,', b'const hotspot={config:ctx.hotspot_config}; const cursor=ctx.cursor,')
    source = source.replace(b'    -v "$T/helpers":/helpers:ro', b'    -v "$T/unisoc-modem":/usr/libexec/unisoc-modem:ro \\\n    -v "$T/helpers":/helpers:ro')
    path.write_bytes(source)
path = top / 'ci/infoscreen/tests/wifi-status.uc'
source = path.read_bytes()
before = b'const ctx={\n'
after = before + b" hotspot_config:()=>({radio:'radio0',enabled,qr_revision:1}),\n"
if after not in source:
    assert hashlib.sha256(source).hexdigest() == '07036507fc3d5d093f265e5f232f615faed862e3ebde908dd56ad974fd7530fd'
    assert source.count(before) == 1
    path.write_bytes(source.replace(before, after))
print('Network harness restored: explicit unit dependency and real shared module for API tests')
