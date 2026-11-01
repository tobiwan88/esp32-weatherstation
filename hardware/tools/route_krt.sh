#!/bin/sh
# Route a placed weatherstation-v1 board with KiCadRoutingTools: GND planes on In1 and In2, then every other net on
# F.Cu/B.Cu only, so both planes stay solid (REQUIREMENTS E2). Fab floors pinned (rules/krt-fab.txt).
# Usage: route_krt.sh placed.kicad_pcb routed.kicad_pcb
# Stage boards live in a temp dir (no stray KiCad projects in the repo); logs go to hardware/out/route/.
set -e
# Pin Python's hash order (KRT_SEED, default 1); the result also depends on the object ids of the input board.
export PYTHONHASHSEED="${KRT_SEED:-1}"
here="$(cd "$(dirname "$0")/.." && pwd)"
K="$here/.tools/KiCadRoutingTools"; P="$K/.venv/bin/python"; F="$here/rules/krt-fab.txt"
[ -x "$P" ] || { echo "KiCadRoutingTools missing: run hardware/tools/setup_tools.sh" >&2; exit 1; }
in="$(cd "$(dirname "$1")" && pwd)/$(basename "$1")"; out="$2"
work="$(mktemp -d)"; logs="$here/out/route"
trap 'mkdir -p "$logs"; cp "$work"/*.log "$work"/route.json "$logs"/ 2>/dev/null; rm -rf "$work"' EXIT
cd "$work"
pro="${in%.kicad_pcb}.kicad_pro"
cp "$in" placed.kicad_pcb
for f in placed poured; do cp "$pro" "$f.kicad_pro"; cp "${in%.kicad_pcb}.kicad_dru" "$f.kicad_dru"; done
common="--fab-overrides $F --no-fix-drc-settings --same-net-pad-clearance 0.15"
$P "$K/py_router/route_planes.py" placed.kicad_pcb poured.kicad_pcb --nets GND GND \
    --plane-layers In1.Cu In2.Cu --clearance 0.15 $common > planes.log 2>&1
# Widths = board.yaml net classes (calc/track_width.py): Charge 0.65 mm, Power 0.4 mm
CHARGE="USB_VBUS VBUS PMID SYS BAT_PACK /Battery/BAT_CON /Battery/BAT_N /Battery/PB_MID /Charger/SW1 /Charger/SW2 /Charger/PV_IN /Input/PV_RAW /Input/PV_N_RAW /Input/ACF1_MID /Input/ACF2_MID"
POWER="+3V3 3V3_SW 5V_SW /Rails/BUCK_L1 /Rails/BUCK_L2 /Rails/GAS_SW"
widths=""; for n in $CHARGE; do widths="$widths 0.65"; done; for n in $POWER; do widths="$widths 0.4"; done
$P "$K/py_router/route.py" poured.kicad_pcb routed.kicad_pcb --nets "*" --layers F.Cu B.Cu --ordering inside_out \
    --power-nets $CHARGE $POWER GND --power-nets-widths $widths 0.3 --track-width 0.2 \
    --clearance 0.15 --json-out route.json --keep-input-copper $common > route.log 2>&1 || true
grep -h "JSON_SUMMARY_MIN" route.log | cut -c1-600
cd - >/dev/null
cp "$work/routed.kicad_pcb" "$out"
