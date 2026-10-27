#!/bin/sh
# Prepare only: the mounted root is never overwritten from the running system.
set -eu
stage=${1:?upload directory}
stage_parent=${stage%/*}
stage_name=${stage##*/}
case "$stage_parent" in /tmp|/root) ;; *) exit 1 ;; esac
case "$stage_name" in e5-update-*) ;; *) exit 1 ;; esac
stage_token=${stage_name#e5-update-}
case "$stage_token" in *[!0-9a-f]*|'') exit 1 ;; esac
[ "${#stage_token}" = 32 ] && [ -d "$stage" ] && [ ! -L "$stage" ] || exit 1
[ "$(cat /etc/e5/device-profile)" = "${E5_UPDATE_PROFILE:?}" ]
expected_variant=${E5_UPDATE_VARIANT:?}
case "$expected_variant" in
    standard|wps) ;;
    *) echo 'unsupported update variant' >&2; exit 1 ;;
esac
actual_variant=standard
if [ -f /etc/e5/device-variant ]; then
    case "$(cat /etc/e5/device-variant)" in
        standard) actual_variant=standard ;;
        wps|e5wps) actual_variant=wps ;;
        *) echo 'unknown installed firmware variant' >&2; exit 1 ;;
    esac
elif grep -q e5wps /etc/e5/image-version 2>/dev/null; then
    actual_variant=wps
fi
[ "$actual_variant" = "$expected_variant" ] || {
    echo 'firmware variant does not match this device' >&2; exit 1;
}
if [ "$expected_variant" = wps ]; then
    [ -f /etc/e5/part-root ] && [ ! -f /etc/e5/sd-root ] || {
        echo 'E5-WPS updates require the existing internal e5root partition' >&2; exit 1;
    }
fi
if [ ! -f /etc/e5/part-root ] && [ ! -f /etc/e5/sd-root ]; then
    E5_IMAGE_SIZE=${E5_IMAGE_SIZE:?} sh "$stage/device-install-image.sh" "$stage/openwrt.ext4.gz"
    exit
fi
exec 9>/run/e5-part-update.lock
flock -n 9 || { echo 'another partition update is running' >&2; exit 1; }
[ ! -e /.e5-update/request ] || { echo 'an update is already pending' >&2; exit 1; }
[ ! -L /.e5-update ] || { echo 'unsafe update staging directory' >&2; exit 1; }
kind=part
[ ! -f /etc/e5/sd-root ] || kind=sd
dev=$(cat "/run/e5linux/$kind-root-dev")
node=${dev##*/}; disk=${node%p*}
[ -b "$dev" ]
if [ "$kind" = part ]; then
    grep -qx PARTNAME=e5root "/sys/class/block/$node/uevent"
else
    [ "$(cat /sys/class/block/$disk/device/type)" = SD ]
fi
[ "$(awk '$2=="/" {print $1}' /proc/mounts | tail -1)" = "$dev" ]
bytes=$(( $(cat "/sys/class/block/$node/size") * 512 ))
[ "${E5_IMAGE_SIZE:?}" -le "$bytes" ]
case "${E5_IMAGE_SHA256:?}" in *[!0-9a-f]*|'') exit 1 ;; esac
[ "${#E5_IMAGE_SHA256}" = 64 ]
gzip -t "$stage/openwrt.ext4.gz"
# Persistent staging lives on the selected root; Android userdata is untouched.
mkdir -p /.e5-update
chmod 700 /.e5-update
cp "$stage/openwrt.ext4.gz" "$stage/ext4-tools.tar" /.e5-update/
view=$(mktemp -d /tmp/e5-update-view.XXXXXX)
trap 'umount "$view" 2>/dev/null || :; rmdir "$view" 2>/dev/null || :' EXIT
mount --bind / "$view"
# Plain bind excludes the vendor chroot's live proc/sys/dev bind mounts.
cd "$view"
firmware=
for name in lib/firmware/wcnmodem.bin lib/firmware/gnssmodem.bin lib/firmware/wifi_board_config*.ini \
    lib/firmware/tsx_data lib/firmware/l_agdsp_a.img lib/firmware/audio_structure lib/firmware/dsp_vbc \
    lib/firmware/codec.xml \
    lib/firmware/cvs lib/firmware/aw87xxx_acf.bin lib/firmware/sprd \
    lib/firmware/aw883xx_acf.bin lib/firmware/awinic_params.bin \
    lib/firmware/sitronix_firmware_huaying.dump lib/firmware/sitronix \
    lib/firmware/yuanhang41s-HiFi.conf lib/firmware/yuanhang41s-media-max \
    lib/firmware/android-firmware-slot opt/e5/android; do
    [ ! -e "$name" ] || firmware="$firmware $name"
done
[ -s lib/firmware/wcnmodem.bin ] && [ -x opt/e5/android/vendor/bin/modem_control ]
tar -cf /.e5-update/firmware.tar $firmware
settings=
for name in etc/config etc/shadow etc/passwd etc/group etc/dropbear etc/e5 etc/e5linux \
    etc/uhttpd.crt etc/uhttpd.key etc/vnstat etc/e5-infoscreen etc/e5-sms etc/unisoc-modem \
    etc/e5-sounds etc/e5-cpu-voltage.json etc/bluetooth etc/daed etc/daed-kdae \
    etc/init.d/daed etc/init.d/owjdxb usr/local/owjdxb usr/libexec/e5-nodebaby-guard \
    etc/init.d/daed-dns usr/libexec/e5-daed-dns etc/rc.d/S96daed-dns etc/rc.d/K9daed-dns; do
    [ ! -e "$name" ] || settings="$settings $name"
done
sh "$stage/e5-network-addons-snapshot" "$view" /.e5-update/settings.tar \
    "$stage/network-addons-software.list" $settings
cd /
umount "$view"; rmdir "$view"; trap - EXIT
cd /.e5-update
tar -tf settings.tar >/dev/null; tar -tf firmware.tar >/dev/null; tar -tf ext4-tools.tar >/dev/null
sha256sum openwrt.ext4.gz firmware.tar settings.tar ext4-tools.tar > SHA256SUMS
sha256sum -c SHA256SUMS
payload=$(du -k openwrt.ext4.gz firmware.tar settings.tar ext4-tools.tar | awk '{s+=$1} END {print s}')
[ "$(awk '/MemAvailable:/ {print $2}' /proc/meminfo)" -gt "$((payload + 262144))" ] || {
    echo 'not enough memory for offline update; request not armed' >&2; exit 1;
}
cid=$(cat "/sys/class/block/$disk/device/cid")
{
    echo VERSION=1; echo KIND="$kind"; echo CID="$cid"; echo ROOT_BYTES="$bytes"
    echo RAW_BYTES="$E5_IMAGE_SIZE"; echo RAW_SHA256="$E5_IMAGE_SHA256"
    echo PROFILE="$E5_UPDATE_PROFILE"; echo VARIANT="$E5_UPDATE_VARIANT"
} > request.ready
sync
echo '== staged offline root update (no partition changes); settings and firmware saved'
