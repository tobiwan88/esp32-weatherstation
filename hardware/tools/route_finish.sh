#!/bin/sh
# Finishing pass on an already routed board: route every open net again with rip-up allowed (no --keep-input-copper:
# earlier unlocked routes may be ripped; locked hand-drawn copper never is). Same widths and fab floors as route_krt.sh.
# Usage: route_finish.sh routed.kicad_pcb out.kicad_pcb [route.py options, e.g. --max-ripup 8]
set -e
here="$(cd "$(dirname "$0")/.." && pwd)"
K="$here/.tools/KiCadRoutingTools"; P="$K/.venv/bin/python"; F="$here/rules/krt-fab.txt"
export PYTHONHASHSEED="${KRT_SEED:-1}"
in="$(cd "$(dirname "$1")" && pwd)/$(basename "$1")"; out="$2"; shift 2
pro="$here/weatherstation-v1/weatherstation-v1"
work="$(mktemp -d)"; logs="${KRT_LOGS:-$here/out/route}"
trap 'mkdir -p "$logs"; cp "$work"/finish.log "$logs"/ 2>/dev/null; rm -rf "$work"' EXIT
cd "$work"
cp "$in" in.kicad_pcb
for f in in out; do cp "$pro.kicad_pro" $f.kicad_pro; cp "$pro.kicad_dru" $f.kicad_dru; done
CHARGE="USB_VBUS VBUS PMID SYS BAT_PACK /Battery/BAT_CON /Battery/BAT_N /Battery/PB_MID /Charger/SW1 /Charger/SW2 /Charger/PV_IN /Input/PV_RAW /Input/PV_N_RAW /Input/ACF1_MID /Input/ACF2_MID"
POWER="+3V3 3V3_SW 5V_SW /Rails/BUCK_L1 /Rails/BUCK_L2 /Rails/GAS_SW"
widths=""; for n in $CHARGE; do widths="$widths ${CHARGE_W:-0.65}"; done; for n in $POWER; do widths="$widths 0.4"; done
$P "$K/py_router/route.py" in.kicad_pcb out.kicad_pcb --nets "*" --layers F.Cu B.Cu --ordering inside_out \
    --power-nets $CHARGE $POWER GND --power-nets-widths $widths 0.3 --track-width 0.2 --clearance 0.15 \
    --fab-overrides "$F" --no-fix-drc-settings --same-net-pad-clearance 0.15 "$@" > finish.log 2>&1 || true
grep -h "JSON_SUMMARY_MIN" finish.log | sed "s/^/finish: /" | cut -c1-600
cd - >/dev/null
cp "$work/out.kicad_pcb" "$out"
