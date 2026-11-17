#!/bin/sh
set -eu
export FORCE_UNSAFE_CONFIGURE=1
cd /build
exec 9>/build/unisoc-hostapd.lock
flock 9
[ -d openwrt/.git ] || git clone -q --depth 1 --branch "v$VER" https://git.openwrt.org/openwrt/openwrt.git openwrt
cd openwrt
[ "$(git rev-parse HEAD)" = "$(git rev-parse "v$VER^{commit}")" ]
P=package/network/utils/iwinfo
grep -q 'PKG_SOURCE_VERSION:=66bdd1a071895d91babc9b9228bb84626bbce226' "$P/Makefile"
grep -q 'PKG_MIRROR_HASH:=e58dab2e33c52b0c217134e81b3ba5376b7a3b57dc1885edf62826573d9f6292' "$P/Makefile"
sed -i 's/^PKG_RELEASE:=.*/PKG_RELEASE:=1001/' "$P/Makefile"
if [ ! -s .config ]; then
    printf '%s\n' 'CONFIG_TARGET_armsr=y' 'CONFIG_TARGET_armsr_armv8=y' 'CONFIG_TARGET_armsr_armv8_DEVICE_generic=y' 'CONFIG_ALL_KMODS=n' 'CONFIG_ALL_NONSHARED=n' > .config
fi
grep -q '^CONFIG_PACKAGE_libiwinfo=m$' .config || printf '\nCONFIG_PACKAGE_libiwinfo=m\n' >> .config
make defconfig
ls staging_dir/host/bin/openssl >/dev/null 2>&1 || make -j"$JOBS" tools/install
ls staging_dir/toolchain-*/bin/*-gcc >/dev/null 2>&1 || make -j"$JOBS" toolchain/install
make "$P/prepare" V=s
source_dir=$(find build_dir/target-* -mindepth 1 -maxdepth 1 -type d -name 'libiwinfo-2026.05.26~66bdd1a0')
[ -n "$source_dir" ] && [ "$(printf '%s\n' "$source_dir" | wc -l)" = 1 ]
python3 /src/patch-iwinfo-ap-scan.py "$source_dir"
# A new backend revision edits the prepared C file. Invalidate the package's
# build dependency through its own prepare stamp, retaining source/tool caches.
for stamp in "$source_dir"/.prepared_*; do
    [ -f "$stamp" ] && touch "$stamp"
done
make -j"$JOBS" "$P/compile" V=s
apk=$(find bin -type f -name 'libiwinfo20230701-2026.05.26~66bdd1a0-r1001.apk')
[ -n "$apk" ] && [ "$(printf '%s\n' "$apk" | wc -l)" = 1 ]
cp "$apk" /out/
(cd /out && sha256sum libiwinfo20230701-2026.05.26~66bdd1a0-r1001.apk > SHA256SUMS)
printf '%s\n' "$BUILD_ID" > /out/build-id
