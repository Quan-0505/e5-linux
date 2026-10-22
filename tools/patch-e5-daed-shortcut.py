#!/usr/bin/env python3
"""Add persistent, configurable E5 info-screen keypad shortcuts."""

from __future__ import annotations

import sys
from pathlib import Path


def patch_file(path: Path, before: str, after: str, marker: str) -> None:
    source = path.read_text(encoding="utf-8")
    if marker in source:
        return
    count = source.count(before)
    if count != 1:
        raise SystemExit(f"{path}: expected one patch anchor, found {count}: {before[:72]!r}")
    path.write_text(source.replace(before, after, 1), encoding="utf-8", newline="\n")


def patch_any(path: Path, alternatives: tuple[tuple[str, str], ...], marker: str) -> None:
    source = path.read_text(encoding="utf-8")
    if marker in source:
        return
    matches = [(before, after) for before, after in alternatives if source.count(before) == 1]
    if len(matches) != 1:
        raise SystemExit(f"{path}: expected one supported patch anchor, found {len(matches)}")
    before, after = matches[0]
    path.write_text(source.replace(before, after, 1), encoding="utf-8", newline="\n")


def main() -> int:
    if len(sys.argv) != 2:
        print(f"usage: {Path(sys.argv[0]).name} INFOSCREEN_ROOT", file=sys.stderr)
        return 2
    root = Path(sys.argv[1])
    app = root / "www/app.js"
    settings = root / "settings.uc"
    api = root / "api.uc"
    mobile = root / "www/mobile.js"

    dynamic_key_mapping = (
        "\tif (k == 'Power' || k == 'PowerOff' || k == 'Standby' || k == 'Sleep') return 'power';\n"
        "\tif (k >= '0' && k <= '9' && k.length == 1) return 'shortcut' + k;\n"
        "\tif (/^(Digit|Numpad)[0-9]$/.test(e.code ?? '')) return 'shortcut' + e.code.slice(-1);\n"
        "\tif (c >= 48 && c <= 57) return 'shortcut' + String.fromCharCode(c);\n"
        "\tif (c >= 96 && c <= 105) return 'shortcut' + (c - 96);\n"
    )
    patch_any(
        app,
        (
            (
                "\tif (k == 'Power' || k == 'PowerOff' || k == 'Standby' || k == 'Sleep') return 'power';\n"
                "\tif (k >= '1' && k <= '9' && k.length == 1) return 'page' + k;\n",
                dynamic_key_mapping,
            ),
            (
                "\tif (k == 'Power' || k == 'PowerOff' || k == 'Standby' || k == 'Sleep') return 'power';\n"
                "\tif (k == '0' || e.code == 'Digit0' || e.code == 'Numpad0' || c == 48 || c == 96) return 'daed';\n"
                "\tif (k >= '1' && k <= '9' && k.length == 1) return 'page' + k;\n",
                dynamic_key_mapping,
            ),
        ),
        "return 'shortcut' + e.code.slice(-1)",
    )
    shortcut_functions = (
        "function screenShortcutTarget(digit) {\n"
        "\treturn last?.screen?.['shortcut_' + digit] ?? 'default';\n"
        "}\n\n"
        "async function runScreenShortcut(digit) {\n"
        "\tlet target = screenShortcutTarget(digit);\n"
        "\tif (target == 'default') target = digit == '0' ? 'app:daed' : `page:${+digit - 1}`;\n"
        "\tif (target == 'off') return;\n"
        "\tif (target.startsWith('page:')) {\n"
        "\t\tconst n = Number(target.slice(5));\n"
        "\t\tif (!Number.isInteger(n) || n < 0 || n >= pages.length) return;\n"
        "\t\tif (appOpen) closeApp();\n"
        "\t\tshowPage(n);\n"
        "\t\treturn;\n"
        "\t}\n"
        "\tconst match = /^app:([a-z0-9][a-z0-9_-]*)$/.exec(target);\n"
        "\tif (!match) return;\n"
        "\tif (appOpen?.id == match[1]) return;\n"
        "\tif (!apps?.some((item) => item.id == match[1])) await loadApps();\n"
        "\tconst app = apps?.find((item) => item.id == match[1]);\n"
        "\tif (!app) { toast(lang == 'zh' ? '快捷按钮对应的应用未安装' : 'Shortcut app is not installed'); return; }\n"
        "\tif (appOpen) closeApp();\n"
        "\topenApp(app);\n"
        "}\n\n"
    )
    old_open_daed = (
        "async function openDaedShortcut() {\n"
        "\tif (appOpen?.id == 'daed') return;\n"
        "\tif (!apps?.some((app) => app.id == 'daed')) await loadApps();\n"
        "\tconst app = apps?.find((item) => item.id == 'daed');\n"
        "\tif (!app) { toast(lang == 'zh' ? 'DAED 应用未安装' : 'DAED app is not installed'); return; }\n"
        "\tif (appOpen) closeApp();\n"
        "\topenApp(app);\n"
        "}\n"
    )
    patch_any(
        app,
        (
            (
                "\treturn null;\n}\n\n// the keypad's back key reports KEY_BACK and BackSpace (kernel 0004) in one\n",
                "\treturn null;\n}\n\n" + shortcut_functions + "// the keypad's back key reports KEY_BACK and BackSpace (kernel 0004) in one\n",
            ),
            (old_open_daed, shortcut_functions),
        ),
        "async function runScreenShortcut(digit)",
    )
    shortcut_dispatch = (
        "\tif (kind?.startsWith('shortcut')) {\n"
        "\t\tif (!e.repeat) void runScreenShortcut(kind.slice(8));\n"
        "\t\treturn;\n"
        "\t}\n"
    )
    old_daed_dispatch = (
        "\tif (kind == 'daed') {\n"
        "\t\tif (!e.repeat) void openDaedShortcut();\n"
        "\t\treturn;\n"
        "\t}\n"
    )
    if old_daed_dispatch in app.read_text(encoding="utf-8"):
        patch_file(app, old_daed_dispatch, shortcut_dispatch, "void runScreenShortcut(kind.slice(8))")
    else:
        patch_file(
            app,
            "\tif (kind == 'menu') {\n"
            "\t\tif (!e.repeat) { if (appOpen) closeApp(); showPage(P.apps); }\n"
            "\t\treturn;\n"
            "\t}\n",
            "\tif (kind == 'menu') {\n"
            "\t\tif (!e.repeat) { if (appOpen) closeApp(); showPage(P.apps); }\n"
            "\t\treturn;\n"
            "\t}\n" + shortcut_dispatch,
            "void runScreenShortcut(kind.slice(8))",
        )
    digit_bridge = (
        "\t\tif (fromApp && !T551MCalls.active() && !m.repeat) {\n"
        "\t\t\tconst digitKind = keyKind(m);\n"
        "\t\t\tif (digitKind?.startsWith('shortcut')) {\n"
        "\t\t\t\tconst digit = digitKind.slice(8), target = screenShortcutTarget(digit);\n"
        "\t\t\t\tif (digit == '0' || (target != 'default' && target != 'off')) {\n"
        "\t\t\t\t\tvoid runScreenShortcut(digit);\n"
        "\t\t\t\t\treturn;\n"
        "\t\t\t\t}\n"
        "\t\t\t}\n"
        "\t\t}\n"
    )
    old_digit_bridge = (
        "\t\tif (fromApp && !T551MCalls.active() && !m.repeat && (m.key == '0' || m.code == 'Digit0' || m.code == 'Numpad0' || m.keyCode == 48 || m.keyCode == 96)) {\n"
        "\t\t\tvoid openDaedShortcut();\n"
        "\t\t\treturn;\n"
        "\t\t}\n"
    )
    if old_digit_bridge in app.read_text(encoding="utf-8"):
        patch_file(app, old_digit_bridge, digit_bridge, "const digitKind = keyKind(m)")
    else:
        patch_file(
            app,
            "\t\tif (m.kind == 'menu' && !m.repeat) { if (fromIme) closeInputMethod(); else { closeApp(); showPage(P.apps); } return; }\n",
            "\t\tif (m.kind == 'menu' && !m.repeat) { if (fromIme) closeInputMethod(); else { closeApp(); showPage(P.apps); } return; }\n" + digit_bridge,
            "const digitKind = keyKind(m)",
        )
    patch_file(
        app,
        "\tif (r?.ok && ['ui', 'navigation'].includes(v.cat.id)) {\n",
        "\tif (r?.ok && ['ui', 'navigation', 'shortcuts'].includes(v.cat.id)) {\n",
        "['ui', 'navigation', 'shortcuts'].includes(v.cat.id)",
    )

    # Expose the saved values to the renderer immediately after a setting is changed.
    api_anchor = "\t\tnav_slot5: c.get('e5-infoscreen', 'main', 'nav_slot5') ?? '7',\n"
    api_fields = "".join(
        f"\t\tshortcut_{digit}: c.get('e5-infoscreen', 'main', 'shortcut_{digit}') ?? 'default',\n"
        for digit in range(10)
    )
    patch_file(api, api_anchor, api_anchor + api_fields, "shortcut_9: c.get('e5-infoscreen'")

    settings_anchor = "const mobile_navigation = uci_category('navigation', L('底部导航', 'Bottom navigation'), nav_defs);\n"
    shortcut_category = (
        "\nconst shortcut_targets = [\n"
        "\t{value:'default',label:L('默认操作','Default action')},\n"
        "\t{value:'off',label:L('关闭','Disabled')},\n"
        "\t{value:'app:daed',label:'DAED'},\n"
        "\t{value:'app:phone',label:L('电话','Phone')},\n"
        "\t...map([[0,L('概览','Overview')],[1,L('信号','Signal')],[2,L('流量','Usage')],[3,L('短信','Messages')],[4,L('热点','Hotspot')],[5,L('设备','Device')],[6,L('详细信息','Details')],[7,L('设置','Settings')],[8,L('应用列表','App list')]], p=>({value:`page:${p[0]}`,label:p[1]}))\n"
        "];\n"
        "const shortcut_buttons = uci_category('shortcuts', L('快捷按钮','Shortcut buttons'), map([0,1,2,3,4,5,6,7,8,9], digit => ({\n"
        "\tid:`shortcut_${digit}`, type:'choice', uci:`e5-infoscreen.main.shortcut_${digit}`, default:'default',\n"
        "\tlabel:L(`数字 ${digit}`,`Number ${digit}`), options:shortcut_targets,\n"
        "\tnote:L('默认操作：0 打开 DAED，1–9 切换原页面','Default: 0 opens DAED; 1–9 keep their original page actions')\n"
        "})));\n"
    )
    patch_file(settings, settings_anchor, settings_anchor + shortcut_category, "const shortcut_buttons = uci_category('shortcuts'")
    return_anchor = "charge, notify, ...(has_sound ? [ sound ] : []), screen, mobile_ui, mobile_navigation, usb_cat"
    patch_file(
        settings,
        return_anchor,
        "charge, notify, ...(has_sound ? [ sound ] : []), screen, mobile_ui, mobile_navigation, shortcut_buttons, usb_cat",
        "mobile_navigation, shortcut_buttons, usb_cat",
    )

    mobile_anchor = "settings:'M4 6h16M4 18h16M8 3v6m8 6v6M4 12h16m-4-3v6',\n"
    mobile_icon = "keyboard:'M3 5h18v14H3zM7 9h1m3 0h1m3 0h1m3 0h.01M7 12h1m3 0h1m3 0h1m-11 3h12',\n"
    patch_file(mobile, mobile_anchor, mobile_anchor + "        " + mobile_icon, "keyboard:'M3 5h18v14H3z")
    mobile_names_anchor = "network:'signal',at:'terminal',devices:'device',appmgr:'apps',bluetooth:'bluetooth',\n"
    patch_file(
        mobile,
        mobile_names_anchor,
        mobile_names_anchor + "            shortcuts:'keyboard',\n",
        "shortcuts:'keyboard'",
    )
    item_icon_anchor = "            else if (kind === 'item') icon = /^nav_slot[1-5]$/.test(id)\n"
    patch_file(
        mobile,
        item_icon_anchor,
        "            else if (kind === 'item') icon = /^shortcut_[0-9]$/.test(id) ? 'keyboard' : /^nav_slot[1-5]$/.test(id)\n",
        "/^shortcut_[0-9]$/",
    )
    print("applied configurable E5 info-screen shortcuts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
