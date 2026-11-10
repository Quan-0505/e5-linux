#!/usr/bin/env python3
"""E5 firmware entry into the shared Diff Studio packager, without Android APK."""
import argparse
import inspect
from pathlib import Path
import runpy
import sys

_SHARED = Path(__file__).resolve().parents[1] / 'installer'
_SOURCE = _SHARED / 'package_diff.py'
if not _SOURCE.is_file():
    raise RuntimeError('Initialize the installer submodule / 请先执行 git submodule update --init --recursive')
sys.path.insert(0,str(_SHARED))
_exports = runpy.run_path(str(_SOURCE),run_name='openwrt_tools_entry')

# Files the shared packager attaches for the Android control app. E5 firmware
# bundles must never carry them: tools/ci-release.py::verify_archive rejects them.
_ANDROID_ATTACHMENTS = ('OpenWrt-Tools.apk','docs/GUI-BUILD-android.json','docs/ANDROID-INSTALLER.md')


def _drop_android_attachments(package):
    """Remove the Android control app that the reviewed packager attaches by default.

    The reviewed installer pin (tools/installer-inputs.lock.json) attaches the Android
    app from package_android as a self-contained extra set of files; the first-class
    ``include_android`` switch only exists on a later, unpublished branch of the
    shared repository. Dropping the attachment afterwards leaves the Diff Studio
    manifest (diff-tool.json) untouched, because that manifest lists only the files
    the Diff Studio packager itself owns.
    """
    package=Path(package)
    for name in _ANDROID_ATTACHMENTS:
        target=package/name
        if target.is_symlink() or target.is_file():
            target.unlink()
    guide=package/'START-HERE.md'
    if guide.is_file():
        kept=[line for line in guide.read_text(encoding='utf-8').splitlines(True)
              if 'OpenWrt-Tools.apk' not in line and 'ANDROID-INSTALLER.md' not in line]
        guide.write_text(''.join(kept),encoding='utf-8',newline='\n')


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
def attach(package, *, include_android=False):
    """Attach desktop tools to an E5 firmware bundle; Android APK is omitted by default."""
    shared=_exports['attach']
    try:
        accepts='include_android' in inspect.signature(shared).parameters
    except (TypeError,ValueError):
        accepts=False
    if accepts:
        return shared(package,include_android=include_android)
    manifest=shared(package)
    if not include_android:
        _drop_android_attachments(package)
    return manifest


globals()['attach']=attach

if __name__=='__main__':
    main()
