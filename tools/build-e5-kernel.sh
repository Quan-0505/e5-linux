#!/bin/bash
set -euo pipefail
TOP=$(cd "$(dirname "$0")/.." && pwd)
python3 "$TOP/tools/prepare-e5-kernel-compat.py" "${E5_KERNEL_TREE:?Set E5_KERNEL_TREE}"
exec bash "$TOP/device/linux_device_e5/build-kernel.sh" "$@"
