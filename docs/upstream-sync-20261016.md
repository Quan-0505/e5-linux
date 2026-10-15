# E5 upstream synchronization — 2026-10-16

Merged sprd-linux-devs/e5-linux main at 569f13d4ce15585f70817c2a1e03bb574a84720b
(16 upstream commits since the shared ancestor e4cfda0).

The upstream device split is now represented by ten pinned device submodules,
plus the pinned screen and screen-plugin repositories. Clone with
`git clone --recurse-submodules`, or run `git submodule update --init --recursive`.

The custom build branch retains the existing internal e5root installer and
preserve-data update path, transactional boot selection, MMC/EIC/thermal fixes,
Unisoc authentication/mobility/SMS isolation patches, and network-addon staging.
Fork runtime changes live in `openwrt/fork-compat/`; pinned upstream repositories
remain clean. The E5 stager injects startup fixes before the isolated-NV transform.
Package fingerprints include both upstream and fork modem patches.

Validation is split between portable Windows checks and the Ubuntu source-check
workflow. A source-check success is not a firmware build, release or device test.
No device, partition table, Android data, credentials or subscriptions are changed
by this synchronization. The existing 7046071 share package remains the previously
verified firmware, rather than silently claiming these source changes.

Thanks to sprd-linux-devs, Enceka, the OpenWrt and Linux communities, and all
contributors to the pinned device repositories.
