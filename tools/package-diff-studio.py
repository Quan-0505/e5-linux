#!/usr/bin/env python3
"""E5 firmware entry into the shared Diff Studio packager, without Android APK."""
import argparse
from pathlib import Path
import runpy
import sys

_SHARED = Path(__file__).resolve().parents[1] / 'installer'
_SOURCE = _SHARED / 'package_diff.py'
if not _SOURCE.is_file():
    raise RuntimeError('Initialize the installer submodule / 请先执行 git submodule update --init --recursive')
sys.path.insert(0,str(_SHARED))
_exports = runpy.run_path(str(_SOURCE),run_name='openwrt_tools_entry')


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--package',type=Path)
    parser.add_argument('--prepare',action='store_true')
    parser.add_argument('--from-release',type=Path)
    parser.add_argument('--output-zip',type=Path)
    args=parser.parse_args(argv)
    if args.from_release or args.output_zip:
        if not args.from_release or not args.output_zip or args.package or args.prepare:
            parser.error('Use --from-release and --output-zip together without --package/--prepare')
        _exports['export_standalone'](args.from_release,args.output_zip)
        return
    if not args.package:
        parser.error('Supply --package or --from-release/--output-zip')
    args.package.mkdir(parents=True,exist_ok=True)
    if args.prepare:
        runpy.run_path(str(_SHARED/'package_gui.py'))['attach'](args.package)
    attach(args.package)


globals().update({key:value for key,value in _exports.items() if not key.startswith('__')})
# The parent repository's compatibility entry is E5-specific, so preserve the
# shared packager default while exposing this narrow firmware-bundle behavior.
def attach(package):
    """Attach desktop tools to an E5 firmware bundle; Android APK is omitted."""
    return _exports['attach'](package,include_android=False)


globals()['attach']=attach

if __name__=='__main__':
    main()
