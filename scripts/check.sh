#!/usr/bin/env bash
# Single local gate: hardware checks, unit tests, privacy scan.
set -euo pipefail
cd "$(dirname "$0")/.."
scripts/hw-check.sh
python3 -m pytest -q 2>/dev/null || uv run pytest -q
scripts/privacy-check.sh
echo "check OK"
