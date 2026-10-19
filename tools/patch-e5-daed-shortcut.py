#!/usr/bin/env python3
"""Apply the E5 DAED keypad-0 shortcut to the pinned info-screen app.js."""

from __future__ import annotations

import sys
from pathlib import Path


REPLACEMENTS = (
    (
        "\tif (k == 'Power' || k == 'PowerOff' || k == 'Standby' || k == 'Sleep') return 'power';\n",
        "\tif (k == 'Power' || k == 'PowerOff' || k == 'Standby' || k == 'Sleep') return 'power';\n"
        "\tif (k == '0' || e.code == 'Digit0' || e.code == 'Numpad0' || c == 48 || c == 96) return 'daed';\n",
    ),
    (
        "\treturn null;\n}\n\n// the keypad's back key reports KEY_BACK and BackSpace (kernel 0004) in one\n",
        "\treturn null;\n}\n\n"
        "async function openDaedShortcut() {\n"
        "\tif (appOpen?.id == 'daed') return;\n"
        "\tif (!apps?.some((app) => app.id == 'daed')) await loadApps();\n"
        "\tconst app = apps?.find((item) => item.id == 'daed');\n"
        "\tif (!app) { toast(lang == 'zh' ? 'DAED 应用未安装' : 'DAED app is not installed'); return; }\n"
        "\tif (appOpen) closeApp();\n"
        "\topenApp(app);\n"
        "}\n\n"
        "// the keypad's back key reports KEY_BACK and BackSpace (kernel 0004) in one\n",
    ),
    (
        "\tif (kind == 'menu') {\n"
        "\t\tif (!e.repeat) { if (appOpen) closeApp(); showPage(P.apps); }\n"
        "\t\treturn;\n"
        "\t}\n",
        "\tif (kind == 'menu') {\n"
        "\t\tif (!e.repeat) { if (appOpen) closeApp(); showPage(P.apps); }\n"
        "\t\treturn;\n"
        "\t}\n"
        "\tif (kind == 'daed') {\n"
        "\t\tif (!e.repeat) void openDaedShortcut();\n"
        "\t\treturn;\n"
        "\t}\n",
    ),
    (
        "\t\tif (m.kind == 'menu' && !m.repeat) { if (fromIme) closeInputMethod(); else { closeApp(); showPage(P.apps); } return; }\n",
        "\t\tif (m.kind == 'menu' && !m.repeat) { if (fromIme) closeInputMethod(); else { closeApp(); showPage(P.apps); } return; }\n"
        "\t\tif (fromApp && !T551MCalls.active() && !m.repeat && (m.key == '0' || m.code == 'Digit0' || m.code == 'Numpad0' || m.keyCode == 48 || m.keyCode == 96)) {\n"
        "\t\t\tvoid openDaedShortcut();\n"
        "\t\t\treturn;\n"
        "\t\t}\n",
    ),
)


def main() -> int:
    if len(sys.argv) != 2:
        print(f"usage: {Path(sys.argv[0]).name} APP_JS", file=sys.stderr)
        return 2
    path = Path(sys.argv[1])
    source = path.read_text(encoding="utf-8")
    if "async function openDaedShortcut()" in source:
        if source.count("async function openDaedShortcut()") != 1:
            raise SystemExit("DAED shortcut appears more than once")
        print("E5 DAED keypad shortcut already applied")
        return 0
    for before, _after in REPLACEMENTS:
        count = source.count(before)
        if count != 1:
            raise SystemExit(f"expected exactly one info-screen patch anchor, found {count}: {before[:72]!r}")
    for before, after in REPLACEMENTS:
        source = source.replace(before, after, 1)
    path.write_text(source, encoding="utf-8", newline="\n")
    print("applied E5 DAED keypad-0 shortcut")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
