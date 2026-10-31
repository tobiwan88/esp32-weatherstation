#!/usr/bin/env bash
# Hardware gate for weatherstation-v1: profile files parse, BOM check, power/charger check, critical blocks once a routed board exists.
# Options are passed to the BOM check: --strict (order time: MISSING fails), --stock [--qty N] (live JLCPCB stock, needs network).
set -euo pipefail
cd "$(dirname "$0")/.."
B=hardware/weatherstation-v1
PY=${PYTHON:-python3}
rc=0
$PY - <<PYEOF || rc=1
import sys, yaml, pathlib
b = pathlib.Path("$B")
for f in ["board.yaml", "critical.yaml", *sorted(str(p.relative_to(b)) for p in (b / "parts").glob("*.yaml"))]:
    try:
        yaml.safe_load((b / f).read_text())
    except Exception as e:
        print("FAIL profile file", f, e); sys.exit(1)
print("profile files: OK")
PYEOF
$PY hardware/calc/bom_check.py $B "$@" || rc=1
$PY hardware/calc/power_budget.py $B || rc=1
if [ -f $B/weatherstation-v1.kicad_pcb ]; then
    $PY hardware/calc/critical.py $B || rc=1
else
    echo "SKIP: no routed board yet, critical.py not run (ERC/DRC need KiCad and a board)" >&2
fi
[ $rc -eq 0 ] && echo "hardware checks: OK" || echo "hardware checks: FAILED"
exit $rc
