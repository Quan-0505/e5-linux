#!/usr/bin/env bash
# Run independent, device-free checks and report every failing suite at once.
# Bootstrap/rootfs validation remains fail-fast in the caller.
set -euo pipefail
failures=()
check() {
    if "$@"; then
        return 0
    else
        status=$?
        failures+=("$* (exit $status)")
        printf '::error::Logic check failed: %s (exit %s)\n' "$*" "$status"
    fi
}
check python3 upstream/tests/test_kernel_source.py
check python3 upstream/tests/test_e5_mainline_config.py
check python3 upstream/test_usb_ncm.py linux-lts-e5
check python3 tools/tests/android-bootchain.py
check python3 openwrt/tests/block-probe.py
check python3 openwrt/tests/userdata-size.py
check python3 openwrt/tests/flash-diagnostics.py
check python3 openwrt/tests/install-entrypoints.py
check python3 openwrt/tests/image-keep-config.py
E5_TEST_IMAGE="e5-openwrt-base:$E5_WRT_VER" check python3 openwrt/tests/gpt-plan.py
check python3 openwrt/tests/voice-audio.py
check python3 openwrt/tests/dual-sms.py
check python3 openwrt/tests/sms-multipart.py
check python3 openwrt/tests/power-events.py
check python3 devices/t551m/test_apn.py
check python3 devices/common/test_screen_native_build.py
check python3 openwrt/tests/modem-port-discovery.py
check python3 openwrt/tests/screen-session-startup.py
check node devices/t551m/test_calls_transport.cjs
check python3 openwrt/tests/dual-sms-send.py
check python3 openwrt/tests/sim-probe.py
E5_TEST_IMAGE="e5-openwrt-base:$E5_WRT_VER" check python3 openwrt/tests/sim-lock.py
check node openwrt/tests/luci-sim-slots.cjs
check python3 magisk/tests.py
check python3 rootfs/tests/sd-registry.py
check python3 rootfs/tests/early-sd-firmware.py
E5_TEST_IMAGE="e5-openwrt-base:$E5_WRT_VER" check python3 rootfs/tests/sd-write.py
check python3 rootfs/tests/voice-state.py
check python3 rootfs/tests/modem-coldboot.py
check python3 tools/tests/ci-release.py
check python3 tools/tests/infoscreen-daed-app.py
check python3 tools/tests/infoscreen-daed-key0.py
check python3 tools/tests/openwrt-package-state.py
check python3 tools/tests/rootfs-inline-script.py
check python3 tools/tests/rootfs-apk-retry.py
check python3 openwrt/tests/part-root-boot.py
check python3 openwrt/tests/patch-hostapd-sae.py
check python3 boot/tests/boot-inputs.py
check python3 boot/tests/prepare-f2fs-tools.py
check python3 boot/tests/part-install.py
check python3 boot/tests/part-update.py
check python3 tools/tests/network-addons-snapshot.py
check python3 ci/infoscreen-plugins/tools/check.py
if [ -f ci/infoscreen/tests/network-checks.sh ]; then
  E5_DEVICE_COMMON="$PWD/openwrt" E5_TEST_IMAGE="e5-openwrt-base:$E5_WRT_VER" check bash ci/infoscreen/tests/network-checks.sh
  check python3 ci/infoscreen/tests/usb-reset.py
fi
if [ "${#failures[@]}" -ne 0 ]; then
    printf 'Failed logic suite: %s\n' "${failures[@]}" >&2
    exit 1
fi
