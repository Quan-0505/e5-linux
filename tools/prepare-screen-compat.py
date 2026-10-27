#!/usr/bin/env python3
"""Apply a checked fix to the pinned infoscreen USB settings dispatcher."""
import hashlib
from pathlib import Path

top = Path(__file__).resolve().parents[1]
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
    # Newer pinned infoscreen revisions carry the same guard as two lines.
    # Accept only the exact setting allowlist and require it before hardware I/O.
    guard = b"if (index(['usb_role','usb_host_boot','usb_lan_auto','usb_net_mode','usb_net_scope','usb_net_auto'], id) < 0)"
    no_such = b"return 'no such setting';"
    hardware = b"let s = ctx.sh_json('/usr/libexec/unisoc-modem/device-usb get');"
    guard_at = normalized_source.find(guard)
    return_at = normalized_source.find(no_such, guard_at + len(guard)) if guard_at >= 0 else -1
    hardware_at = normalized_source.find(hardware)
    if not (guard_at >= 0 and return_at > guard_at and hardware_at > return_at):
        assert source_hash in original, 'Unknown infoscreen source; review USB compatibility fix'
        normalized_before = before.replace('\r\n', '\n').encode()
        assert normalized_source.count(normalized_before) == 1
        patched = normalized_source.replace(normalized_before, after.replace('\r\n', '\n').encode())
        path.write_bytes(patched)
print('USB unknown-setting rejection applied before hardware status probing')

# Older pinned network harnesses predate the shared hotspot module. Keep the
# wireless-state unit dependency explicit and mount the real module for API tests.
path = top / 'ci/infoscreen/tests/network-checks.sh'
source = path.read_bytes()
before = b"source = (top / 'root/usr/share/e5-infoscreen/api.uc').read_text()"
after = b"shutil.copytree(top.parent.parent / 'device/openwrt_device_common/luci-app-t551m/root/usr/libexec/unisoc-modem', temp / 'unisoc-modem')\n" + before
if after not in source:
    normalized = source.replace(b'\r\n', b'\n')
    # The newer pinned harness gets the same real hotspot module through
    # E5_DEVICE_COMMON and mounts its own isolated control stubs.
    current_harness = (b'DEVICE_COMMON=${E5_DEVICE_COMMON:-' in normalized and
                       b'HOTSPOT="$DEVICE_COMMON/luci-app-t551m/root/usr/libexec/unisoc-modem/hotspot.uc"' in normalized and
                       b'-v "$HOTSPOT":/usr/libexec/unisoc-modem/hotspot.uc:ro' in normalized and
                       b"(temp / 'controls').mkdir()" in normalized)
    if not current_harness:
        assert hashlib.sha256(normalized).hexdigest() == '63bb2b4577bd2dc8b590144d6efc2add7112113be42279e163554ad71537790d'
        normalized = normalized.replace(before, after)
        normalized = normalized.replace(b'const cursor=ctx.cursor,', b'const hotspot={config:ctx.hotspot_config}; const cursor=ctx.cursor,')
        normalized = normalized.replace(b'    -v "$T/helpers":/helpers:ro', b'    -v "$T/unisoc-modem":/usr/libexec/unisoc-modem:ro \\\n    -v "$T/helpers":/helpers:ro')
        path.write_bytes(normalized)
path = top / 'ci/infoscreen/tests/wifi-status.uc'
source = path.read_bytes()
before = b'const ctx={\n'
after = before + b" hotspot_config:()=>({radio:'radio0',enabled,qr_revision:1}),\n"
if after not in source:
    normalized = source.replace(b'\r\n', b'\n')
    # Newer upstream fixtures model the real wireless config and QR revision.
    current_fixture = (b'foreach:(config,kind,visit)=>visit(' in normalized and
                       b'initial=status();' in normalized and
                       b'qr_revision' in normalized)
    if not current_fixture:
        assert hashlib.sha256(normalized).hexdigest() == '07036507fc3d5d093f265e5f232f615faed862e3ebde908dd56ad974fd7530fd'
        assert normalized.count(before) == 1
        path.write_bytes(normalized.replace(before, after))
print('Network harness verified: explicit hotspot dependency and isolated API fixtures')
