#!/usr/bin/env python3
"""Apply a checked fix to the pinned infoscreen USB settings dispatcher."""
import hashlib
from pathlib import Path
import re

top = Path(__file__).resolve().parents[1]
metadata = top / 'ci/infoscreen/.version'
version_file = top / 'ci/infoscreen/root/usr/share/e5-infoscreen/VERSION'
version_match = re.search(r'^version=(\d+\.\d+\.\d+)$', metadata.read_text(), re.M)
assert version_match, 'Invalid or missing infoscreen release version'
version = version_match.group(1)
version_file.write_text(version + '\n')
print(f'Info-screen package version synchronized to {version}')

path = top / 'ci/infoscreen/root/usr/share/e5-infoscreen/settings.uc'
original = {
    'dc46dbca8cdda89da1eb85a696ae7415da2cd637a109795a0e7930763f59e271',
    '00685898b60d4c95f8f8bbc7893c48a82054a71815157388efcc5cbd544b74b2',
    # Reviewed 3dd1de3 adds SIM-radio and charger power controls only.
    'e90c4e6b2a9981385d7e058f7f25825a4f4ada5005cdcfd6d2f8b58ec5d63f27',
}
before = "\t\tif (id == 'check') return ctx.network_check();\n"
after = before + "\t\tif (index(['usb_role','usb_host_boot','usb_lan_auto','usb_net_mode','usb_net_scope','usb_net_auto'], id) < 0) return 'no such setting';\n"
source = path.read_bytes()
normalized_source = source.replace(b'\r\n', b'\n')
source_hash = hashlib.sha256(normalized_source).hexdigest()
if after.encode() not in source:
    assert source_hash in original, 'Unknown infoscreen source; review USB compatibility fix'
    normalized_before = before.replace('\r\n', '\n').encode()
    assert normalized_source.count(normalized_before) == 1
    patched = normalized_source.replace(normalized_before, after.replace('\r\n', '\n').encode())
    path.write_bytes(patched)
print('USB unknown-setting rejection applied before hardware status probing')

# The pinned network harness predates the shared hotspot module. Keep the
# wireless-state unit dependency explicit and mount the real module for API tests.
path = top / 'ci/infoscreen/tests/network-checks.sh'
source = path.read_bytes()
before = b"source = (top / 'root/usr/share/e5-infoscreen/api.uc').read_text()"
after = b"shutil.copytree(top.parent.parent / 'device/openwrt_device_common/luci-app-t551m/root/usr/libexec/unisoc-modem', temp / 'unisoc-modem')\n" + before
if after not in source:
    assert hashlib.sha256(source.replace(b'\r\n', b'\n')).hexdigest() == '63bb2b4577bd2dc8b590144d6efc2add7112113be42279e163554ad71537790d'
    source = source.replace(before, after)
    source = source.replace(b'const cursor=ctx.cursor,', b'const hotspot={config:ctx.hotspot_config}; const cursor=ctx.cursor,')
    source = source.replace(b'    -v "$T/helpers":/helpers:ro', b'    -v "$T/unisoc-modem":/usr/libexec/unisoc-modem:ro \\\n    -v "$T/helpers":/helpers:ro')
    path.write_bytes(source)
path = top / 'ci/infoscreen/tests/wifi-status.uc'
source = path.read_bytes()
before = b'const ctx={\n'
after = before + b" hotspot_config:()=>({radio:'radio0',enabled,qr_revision:1}),\n"
if after not in source:
    assert hashlib.sha256(source.replace(b'\r\n', b'\n')).hexdigest() == '07036507fc3d5d093f265e5f232f615faed862e3ebde908dd56ad974fd7530fd'
    normalized = source.replace(b'\r\n', b'\n')
    assert normalized.count(before) == 1
    path.write_bytes(normalized.replace(before, after))
print('Network harness restored: explicit unit dependency and real shared module for API tests')
