#!/usr/bin/env bash
# Hardware gate for any number of boards. A board is every hardware/<name>/ that holds a board.yaml
# (override: HW_BOARDS="hardware/a hardware/b" scripts/hw-check.sh).
# Per board: profile files parse; BOM check; power budget; track widths; I2C bus; rail switch; critical blocks (placement mode
# until the board carries router copper, full check after); footprint fit against the fab's own footprints (needs KiCad's pcbnew).
# Checks between boards (split proof, stack/header fit) are project specific: put them in scripts/hw-check.d/*.sh. Each hook is
# run from the repo root with the same options, PYTHON exported, and must exit non-zero on failure.
# Options are passed to the BOM check: --strict (order time: MISSING fails), --stock [--qty N] (live fab stock, needs network).
set -euo pipefail
cd "$(dirname "$0")/.."
PY=${PYTHON:-python3}
export PYTHON="$PY"
if [ -n "${HW_BOARDS:-}" ]; then BOARDS="$HW_BOARDS"; else
    BOARDS=$(for f in hardware/*/board.yaml; do [ -f "$f" ] && dirname "$f"; done | sort | tr '\n' ' ')
fi
[ -n "${BOARDS// /}" ] || { echo "no board found (hardware/<name>/board.yaml); see the hw-base skill, bootstrap" >&2; exit 2; }
rc=0
# routed = the board carries router copper (locked tracks are generator copper)
routed() { "$PY" -c 'import re, sys
blocks = re.findall(r"\(segment\b.*?\(uuid", open(sys.argv[1]).read(), re.S)
sys.exit(0 if any("(locked yes)" not in b for b in blocks) else 1)' "$1"; }

for D in $BOARDS; do
    n=$(basename "$D")
    echo "== $D"
    "$PY" - <<PYEOF || rc=1
import sys, yaml, pathlib
b = pathlib.Path("$D")
for f in ["board.yaml", *(["critical.yaml"] if (b / "critical.yaml").exists() else []),
          *(["emi.yaml"] if (b / "emi.yaml").exists() else []),
          *sorted(str(p.relative_to(b)) for p in (b / "parts").glob("*.yaml"))]:
    try:
        yaml.safe_load((b / f).read_text())
    except Exception as e:
        print("FAIL profile file", f, e); sys.exit(1)
print("profile files: OK")
PYEOF
    "$PY" hardware/calc/bom_check.py "$D" "$@" || rc=1
    "$PY" hardware/calc/power_budget.py "$D" || rc=1
    "$PY" hardware/calc/track_width.py "$D" || rc=1
    "$PY" hardware/calc/i2c_bus.py "$D" >/dev/null && echo "i2c_bus: OK" || { "$PY" hardware/calc/i2c_bus.py "$D"; rc=1; }
    "$PY" hardware/calc/rail_switch.py "$D" >/dev/null && echo "rail_switch: OK" || { "$PY" hardware/calc/rail_switch.py "$D"; rc=1; }
    if [ -f "$D/$n.kicad_pcb" ] && [ -f "$D/critical.yaml" ]; then
        if routed "$D/$n.kicad_pcb"; then mode=""; else mode="--placement"; fi
        "$PY" hardware/calc/critical.py "$D" $mode | tail -1 | sed "s|^|$n |"; [ "${PIPESTATUS[0]}" -eq 0 ] || rc=1
    else
        echo "SKIP: critical.py ($n has no board file or critical.yaml yet)" >&2
    fi
done

echo "== calc selftests"
for c in power_budget i2c_bus rail_switch; do "$PY" hardware/calc/$c.py --selftest || rc=1; done

# project hooks: checks between boards (split proof, stack, header) and anything else the project needs
if [ -d scripts/hw-check.d ]; then
    for h in scripts/hw-check.d/*.sh; do
        [ -f "$h" ] || continue
        echo "== hook $(basename "$h")"
        bash "$h" "$@" || rc=1
    done
fi

# footprint fit against the fab's own footprints (cached; fill the cache with one fab_package.py run without --offline)
[ -f scripts/kicad-env.sh ] && . scripts/kicad-env.sh >/dev/null 2>&1 || true
if [ -n "${KICAD_PYTHON:-}" ] && "$KICAD_PYTHON" -c "import pcbnew" >/dev/null 2>&1; then
    for D in $BOARDS; do
        pcb="$D/$(basename "$D").kicad_pcb"
        [ -f "$pcb" ] || continue
        fit=$("$PY" -I hardware/tools/fab_package.py --fit-only --offline "$pcb" 2>&1) || rc=1
        printf '%s\n' "$fit" | grep -v "^LAND" || true
    done
else
    echo "SKIP: placement fit (needs KiCad's pcbnew: source scripts/kicad-env.sh)" >&2
fi
[ $rc -eq 0 ] && echo "hardware checks: OK" || echo "hardware checks: FAILED"
exit $rc
