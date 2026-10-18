#!/usr/bin/env python3
"""Check the strict OpenWrt 25.12.6 Unisoc SAE patch anchor and idempotence."""
import importlib.util
from pathlib import Path
import tempfile

SCRIPT = Path(__file__).resolve().parents[1] / 'patch-hostapd-sae.py'
spec = importlib.util.spec_from_file_location('patch_hostapd_sae', SCRIPT)
patcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(patcher)

with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp) / 'wifi-scripts'
    files = root / 'files'
    shell = files / 'lib/netifd'
    ucode = root / 'files-ucode/usr/share/ucode/wifi'
    shell.mkdir(parents=True)
    ucode.mkdir(parents=True)
    (shell / 'hostapd.sh').write_text(
        'hostapd_set_bss_options() {\n'
        '\t[ -n "$spp_amsdu" ] && append bss_conf "spp_amsdu=$spp_amsdu" "$N"\n',
        encoding='utf-8')
    ap = ucode / 'ap.uc'
    ap.write_text(
        "import * as iface from 'wifi.iface';\n"
        'function generate(interface, data, config) {\n'
        '\tiface_auth_type(config, data.config.band);\n'
        '}\n', encoding='utf-8')

    patcher.patch_wifi(files)
    patcher.patch_wifi(files)
    text = ap.read_text(encoding='utf-8')
    assert text.count("import { configure as unisoc_sae_config } from 'wifi.unisoc-sae';") == 1
    assert text.count('unisoc_sae_config(config, fs.realpath(') == 1
    assert "iface_auth_type(config, data.config.band);" in text
    assert text.index('unisoc_sae_config(config,') < text.index('iface_auth_type(config,')
print('OpenWrt 25.12.6 Unisoc SAE patch anchor and idempotence: PASS')
