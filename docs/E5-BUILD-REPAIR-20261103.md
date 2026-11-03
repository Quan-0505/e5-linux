# E5 build repair — 2026-11-03

The previous build stopped in the Windows installer gate. This update pins the current shared installer plus narrow Windows fixture corrections: canonical temporary paths and an explicit OpenWrt release in the release-identity regression. Boot device alias boundaries and recovery checks remain enforced. Windows CI enables Python UTF-8 for subprocesses.

Local Windows installer suite: 625 tests, 520 passed, 105 platform-dependent skips, no failures. These are offline tests, not device acceptance.

Rust DAED is pinned to source 34c3962ba80672b68b39746ae076d65c538cb478, including upstream UI 76ad4577501b and core d0c477e62617. Its Debian build has passed separate live validation; E5 ARM64 acceptance remains pending. The eBPF compiler is pinned to the matching nightly-2026-05-29.

The next standard E5 CI run must pass installer builds, firmware assembly and all artifact/source checks. It uses publish=false. No device flash is performed by CI.

Run 41632391841 passed Windows/macOS/Linux installer gates and the Rust,
Wi-Fi and block builds. Firmware checks then exposed a missing dependency:
screen staging now builds shared ARM64 daemons, but ran before the registered
OpenWrt toolchain existed. CI now builds json-c alongside ModemManager, builds
the native screen binaries before disposing of that runner's toolchain volume,
and caches binaries plus their source/toolchain fingerprints and hashes. APN
staging tests run after that preparation, including on cache hits. The compiler
also receives GLib's separate gio-unix header directory. No staging test or
artifact validation was removed. Local cache regression uses temporary synthetic
ELF fixtures only; actual ARM64 compilation and acceptance remain CI gates.

Run 41643494197 passed all six prerequisite jobs. The early firmware test
then rejected a stale literal driver-list assertion: boot/init also prepares
firmware for axs15205. The test now executes the actual shell dispatch for
ST7123, AXS15205 and WCN, checks that preparation precedes insmod, and confirms
unrelated modules do not trigger it. The existing read-only fake-card tests
remain. Independent logic suites now run through tools/ci-logic-checks.sh,
which preserves every suite and reports all failures before failing the job;
bootstrap checksum failures still stop immediately. Linux-specific filesystem
and device tests require the CI runtime; Windows checks are not substitutes.
