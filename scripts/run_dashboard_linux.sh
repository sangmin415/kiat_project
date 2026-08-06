#!/usr/bin/env bash
# Usage: bash scripts/run_dashboard_linux.sh /dev/ttyUSB1
set -euo pipefail
PORT="${1:-/dev/ttyUSB0}"
BAUD="${2:-115200}"
exec python3 pc/bno085_rvc_dashboard.py --port "$PORT" --baud "$BAUD"
