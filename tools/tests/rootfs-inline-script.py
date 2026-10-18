from pathlib import Path


root = Path(__file__).resolve().parents[2]
source = (root / "openwrt/build-rootfs.sh").read_text(encoding="utf-8")
start_marker = "/bin/sh -euc '\n"
end_marker = "\n'\n"
start = source.index(start_marker) + len(start_marker)
end = source.index(end_marker, start)
script = source[start:end]

if "'" in script:
    raise SystemExit("the single-quoted inline container script contains an apostrophe")
if "tar -czf /out/$NAME ." not in script:
    raise SystemExit("the rootfs archive creation step is missing")

print("OpenWrt rootfs inline-script quoting: OK")
