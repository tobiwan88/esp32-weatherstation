#!/bin/sh
# Route the power board end to end (board-local copy of the weatherstation-v1 pipeline, tools/route_v1.sh):
#   placed board with the locked hand copper of gen/power_copper.py (tools/build_board.sh power-board)
#   -> KRT GND planes on In1/In2 (pad vias only, both planes stay solid)
#   -> KRT every open net on F.Cu/B.Cu (inside-out, pinned seed, soft keep-away of signals from SW1/SW2)
#   -> rip-up finishing pass -> tools/finish_v1.py (via nudge off same-net pads, dangling cleanup, zone refill)
#   -> tools/silk_fix.py -> kicad-cli DRC summary (all severities).
# Charge-class nets left to the router are sense and pull-up branches (power paths are hand copper): routed at
# 0.3 mm, the "charge path neck" floor of rules/power-board.kicad_dru.
# Usage: hardware/tools/route_power.sh [out.kicad_pcb]   (default: the board in place, hardware/power-board/)
# Env: KRT_SEED (default 1), KRT_ARGS (extra route.py options), KRT_LOGS (default hardware/out/route-power).
set -e
cd "$(dirname "$0")/../.."
. scripts/kicad-env.sh >/dev/null 2>&1
here="$(pwd)/hardware"
P=$here/power-board/power-board
out="${1:-$P.kicad_pcb}"
K="$here/.tools/KiCadRoutingTools"; PY="$K/.venv/bin/python"; F="$here/rules/krt-fab.txt"
[ -x "$PY" ] || { echo "KiCadRoutingTools missing: run hardware/tools/setup_tools.sh" >&2; exit 1; }
export PYTHONHASHSEED="${KRT_SEED:-1}"
work="$(mktemp -d)"; logs="${KRT_LOGS:-$here/out/route-power}"
trap 'mkdir -p "$logs"; cp "$work"/*.log "$logs"/ 2>/dev/null; rm -rf "$work"' EXIT
for f in placed poured routed finished; do cp $P.kicad_pro "$work/$f.kicad_pro"; cp $P.kicad_dru "$work/$f.kicad_dru"; done
cp $P.kicad_pcb "$work/placed.kicad_pcb"
cd "$work"
common="--fab-overrides $F --no-fix-drc-settings --same-net-pad-clearance 0.15"
$PY "$K/py_router/route_planes.py" placed.kicad_pcb poured.kicad_pcb --nets GND GND --plane-layers In1.Cu In2.Cu \
    --clearance 0.15 $common > planes.log 2>&1
# Charge class (board.yaml net_classes) as power nets at the 0.3 mm neck floor; GND taps 0.3 mm
CHARGE="USB_VBUS VBUS PMID SYS BAT_PACK /Battery/BAT_CON /Battery/BAT_N /Battery/PB_MID /Charger/SW1 /Charger/SW2 /Charger/PV_IN /Inputs/PV_RAW /Inputs/PV_N_RAW /Inputs/ACF1_MID /Inputs/ACF2_MID"
widths=""; for n in $CHARGE; do widths="$widths 0.3"; done
pw="--power-nets $CHARGE GND --power-nets-widths $widths 0.3 --no-power-tap-neckdown --track-width 0.2 --clearance 0.15"
# switch nodes are noisy aggressors, the BC1.2 pair a victim: other nets 0.6 mm away where they can (soft cost)
ka="--keep-away /Charger/SW1,/Charger/SW2:*:0.6 /Charger/USB_DP,/Charger/USB_DN:*:0.65 --keep-away-cost 2"
$PY "$K/py_router/route.py" poured.kicad_pcb routed.kicad_pcb --nets "*" --layers F.Cu B.Cu --ordering inside_out \
    $pw $ka --keep-input-copper $common ${KRT_ARGS:---max-ripup 4 --ripup-blocker-select cost} > route.log 2>&1 || true
grep -h "JSON_SUMMARY_MIN" route.log | sed "s/^/route: /" | cut -c1-400
$PY "$K/py_router/route.py" routed.kicad_pcb finished.kicad_pcb --nets "*" --layers F.Cu B.Cu --ordering inside_out \
    $pw $ka $common --max-ripup 8 --ripup-blocker-select near-target > finish.log 2>&1 || cp routed.kicad_pcb finished.kicad_pcb
grep -h "JSON_SUMMARY_MIN" finish.log | sed "s/^/finish: /" | cut -c1-400
"$KICAD_PYTHON" "$here/tools/finish_v1.py" finished.kicad_pcb 2>/dev/null | grep "^finish" || true
"$KICAD_PYTHON" "$here/tools/silk_fix.py" finished.kicad_pcb 2>/dev/null | grep "^silk: [0-9]" || true
kicad-cli pcb drc --refill-zones --severity-all -o drc.txt finished.kicad_pcb >/dev/null 2>&1 || true
echo "DRC items (all severities): $(grep -c '^\[' drc.txt || true) ($(grep '^\[' drc.txt | cut -d']' -f1 | tr -d '[' | sort | uniq -c | tr '\n' ' ')); $(grep -i 'unconnected' drc.txt | tail -1)"
cd - >/dev/null
cp "$work/finished.kicad_pcb" "$out"
