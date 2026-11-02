#!/usr/bin/env python3
"""Stage current generated screen sources for device-free browser regression."""
from pathlib import Path
import runpy
import subprocess
import sys

top = Path(__file__).resolve().parents[1]
root = Path(sys.argv[1]).resolve()
for name, content in runpy.run_path(str(top / 'devices/common/infoscreen/stage.py'))['sources']().items():
    target = root / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding='utf-8', newline='\n')
subprocess.run([sys.executable, str(top / 'tools/patch-e5-daed-shortcut.py'), str(root)], check=True)
