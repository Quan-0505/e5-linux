# E5 build repair — 2026-11-03

The previous build stopped in the Windows installer gate. This update pins the current shared installer plus narrow Windows fixture corrections: canonical temporary paths and an explicit OpenWrt release in the release-identity regression. Boot device alias boundaries and recovery checks remain enforced. Windows CI enables Python UTF-8 for subprocesses.

Local Windows installer suite: 625 tests, 520 passed, 105 platform-dependent skips, no failures. These are offline tests, not device acceptance.

Rust DAED is pinned to source 34c3962ba80672b68b39746ae076d65c538cb478, including upstream UI 76ad4577501b and core d0c477e62617. Its Debian build has passed separate live validation; E5 ARM64 acceptance remains pending. The eBPF compiler is pinned to the matching nightly-2026-05-29.

The next standard E5 CI run must pass installer builds, firmware assembly and all artifact/source checks. It uses publish=false. No device flash is performed by CI.
