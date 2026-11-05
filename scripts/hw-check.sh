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
$PY hardware/calc/track_width.py $B || rc=1
# routed = the board carries router copper; the generator's hand-drawn copper (charger power stage) is always locked
routed() { python3 -c 'import re, sys
blocks = re.findall(r"\(segment\b.*?\(uuid", open(sys.argv[1]).read(), re.S)
sys.exit(0 if any("(locked yes)" not in b for b in blocks) else 1)' "$1"; }
if [ -f $B/weatherstation-v1.kicad_pcb ] && routed $B/weatherstation-v1.kicad_pcb; then
    $PY hardware/calc/critical.py $B || rc=1
else
    echo "SKIP: no routed board yet (placement only), critical.py not run (ERC/DRC need KiCad and a board)" >&2
fi
# footprint fit against the fab's own footprints (cached; fill the cache with one fab_package.py run without --offline)
[ -f scripts/kicad-env.sh ] && . scripts/kicad-env.sh >/dev/null 2>&1
if [ -n "$KICAD_PYTHON" ] && "$KICAD_PYTHON" -c "import pcbnew" >/dev/null 2>&1; then
    for pcb in $B/weatherstation-v1.kicad_pcb hardware/*-board/*-board.kicad_pcb; do
        [ -f "$pcb" ] || continue
        fit=$(python3 -I hardware/tools/fab_package.py --fit-only --offline "$pcb" 2>&1) || rc=1
        printf '%s\n' "$fit" | grep -v "^LAND"
    done
else
    echo "SKIP: placement fit (needs KiCad's pcbnew: source scripts/kicad-env.sh)" >&2
fi
[ $rc -eq 0 ] && echo "hardware checks: OK" || echo "hardware checks: FAILED"
exit $rc
