#!/usr/bin/env bash
# Single local gate: hardware checks, unit tests (when the project has any), privacy scan, kit drift (when hw-kit/ is present).
set -euo pipefail
cd "$(dirname "$0")/.."
scripts/hw-check.sh
if [ -f pytest.ini ] || grep -qs pytest pyproject.toml; then
    python3 -m pytest -q 2>/dev/null || uv run pytest -q
fi
scripts/privacy-check.sh
[ -x hw-kit/install.sh ] && hw-kit/install.sh . --check
echo "check OK"
