#!/bin/sh
# Both E5 variants expose two SIM slots through the native SIPC adapter.
# Older retained configurations omit this capability and policy defaults to one.
[ "$(cat /etc/e5/device-profile 2>/dev/null)" = e5 ] || exit 0
[ -e /sys/module/sipc_wwan/parameters/card ] || exit 0
uci -q get unisoc_modem.main >/dev/null || exit 1
uci set unisoc_modem.main.sim_slots=2
uci commit unisoc_modem
exit 0
