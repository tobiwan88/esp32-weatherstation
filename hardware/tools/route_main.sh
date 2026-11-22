#!/bin/sh
# Route the main board end to end (BOARD.md "Routing"): placed board with the locked hand copper of gen/main_copper.py
# (tools/build_board.sh main-board) -> KiCadRoutingTools: GND planes on In1/In2 (stay solid), then the rails and every
# other net on F.Cu/B.Cu only -> rip-up finishing pass -> router leftovers (tools/finish_v1.py, board-neutral) ->
# GND stitching and outer GND pours (tools/main_stitch.py) -> silkscreen cleanup (tools/silk_fix.py) -> kicad-cli DRC.
# Usage: hardware/tools/route_main.sh [out.kicad_pcb]   (default: the board in place)
# Deterministic: PYTHONHASHSEED pinned (KRT_SEED, default 1); the result also depends on the input board's object ids.
set -e
cd "$(dirname "$0")/../.."
. scripts/kicad-env.sh >/dev/null 2>&1
here="$(pwd)/hardware"
K="$here/.tools/KiCadRoutingTools"; PY="$K/.venv/bin/python"; F="$here/rules/krt-fab.txt"
[ -x "$PY" ] || { echo "KiCadRoutingTools missing: run hardware/tools/setup_tools.sh" >&2; exit 1; }
export PYTHONHASHSEED="${KRT_SEED:-1}"
P="$here/main-board/main-board"
out="${1:-$P.kicad_pcb}"
work="$(mktemp -d)"; logs="${KRT_LOGS:-$here/out/route-main}"
trap 'mkdir -p "$logs"; cp "$work"/*.log "$logs"/ 2>/dev/null; rm -rf "$work"' EXIT
cp "$P.kicad_pcb" "$work/placed.kicad_pcb"
for f in placed planes power first rest finish; do cp "$P.kicad_pro" "$work/$f.kicad_pro"; cp "$P.kicad_dru" "$work/$f.kicad_dru"; done
cd "$work"
common="--fab-overrides $F --no-fix-drc-settings --same-net-pad-clearance 0.15"
$PY "$K/py_router/route_planes.py" placed.kicad_pcb planes.kicad_pcb --nets GND GND \
    --plane-layers In1.Cu In2.Cu --clearance 0.15 $common > planes.log 2>&1
# widths = board.yaml net classes (calc/track_width.py): Power 0.65 mm (SYS to TP2, 5V_SW to J2/J8), Rail 0.3 mm (min 0.15);
# signals 0.2 mm, or KRT_TW (0.15 mm doubles the lanes between J10's 2.54 mm pads)
pw="--power-nets SYS 5V_SW +3V3 3V3_SW GND --power-nets-widths 0.65 0.65 0.3 0.3 0.3 --track-width ${KRT_TW:-0.2} --clearance 0.15"
lock() { "$KICAD_PYTHON" -c 'import pcbnew, sys
b = pcbnew.LoadBoard(sys.argv[1])
for t in b.GetTracks():
    t.SetLocked(True)
pcbnew.SaveBoard(sys.argv[1], b)' "$1" 2>/dev/null; }
lock planes.kicad_pcb
# rails first on the open board, locked; then everything else (inside-out), then a rip-up pass on what is open
$PY "$K/py_router/route.py" planes.kicad_pcb power.kicad_pcb --nets 5V_SW +3V3 3V3_SW SYS --layers F.Cu B.Cu $pw \
    --keep-input-copper $common ${KRT_PARGS:-} > power.log 2>&1 || true
grep -h "JSON_SUMMARY_MIN" power.log | sed "s/^/power: /" | cut -c1-400
lock power.kicad_pcb
# long nets that cross the board (module right column to J10, pocket to the sensor side) before the local ones
first="${KRT_FIRST-/MCU/CHG_SCL /MCU/CHG_SDA /MCU/IO0 /MCU/CHG_INT /SEN_SDA /SEN_SCL /MCU/RAIN /MCU/WIND /MCU/VANE /MCU/LED2_A}"
if [ -n "$first" ]; then
  $PY "$K/py_router/route.py" power.kicad_pcb first.kicad_pcb --nets $first --layers F.Cu B.Cu $pw \
      --keep-input-copper $common --max-ripup 4 > first.log 2>&1 || cp power.kicad_pcb first.kicad_pcb
  grep -h "JSON_SUMMARY_MIN" first.log | sed "s/^/first: /" | cut -c1-300
  mv first.kicad_pcb power.kicad_pcb
fi
$PY "$K/py_router/route.py" power.kicad_pcb rest.kicad_pcb --nets "*" --layers F.Cu B.Cu --ordering inside_out $pw \
    --keep-input-copper $common ${KRT_ARGS:---max-ripup 4 --ripup-blocker-select cost} > rest.log 2>&1 || true
grep -h "JSON_SUMMARY_MIN" rest.log | sed "s/^/rest: /" | cut -c1-400
$PY "$K/py_router/route.py" rest.kicad_pcb finish.kicad_pcb --nets "*" --layers F.Cu B.Cu --ordering inside_out $pw \
    $common ${KRT_FARGS:---max-ripup 8 --ripup-blocker-select near-target} > finish.log 2>&1 || cp rest.kicad_pcb finish.kicad_pcb
grep -h "JSON_SUMMARY_MIN" finish.log | sed "s/^/finish: /" | cut -c1-400
# polish: more rip-up passes on what is still open, each kept only if KRT's improvement gate accepts it
k=0
for sel in ${KRT_POLISH-cost near-target bidir count mincut cost}; do
  k=$((k + 1))
  cp finish.kicad_pro p$k.kicad_pro; cp finish.kicad_dru p$k.kicad_dru
  $PY "$K/py_router/route.py" finish.kicad_pcb p$k.kicad_pcb --nets "*" --layers F.Cu B.Cu --ordering inside_out $pw \
      $common --max-ripup 12 --ripup-blocker-select $sel > p$k.log 2>&1 && mv p$k.kicad_pcb finish.kicad_pcb
  grep -h "JSON_SUMMARY_MIN" p$k.log | grep -o '"pad_pairs_open": {"count": [0-9]*' | sed "s/^/polish $sel: /"
done
mkdir -p "$logs"; cp finish.kicad_pcb "$logs/routed.kicad_pcb"
"$KICAD_PYTHON" "$here/tools/finish_v1.py" finish.kicad_pcb 2>/dev/null | grep "^finish" || true
"$KICAD_PYTHON" "$here/tools/main_stitch.py" finish.kicad_pcb 2>/dev/null | grep "^stitch" || true
"$KICAD_PYTHON" "$here/tools/silk_fix.py" finish.kicad_pcb 2>/dev/null | tail -1 || true
kicad-cli pcb drc --refill-zones --severity-all -o drc.txt finish.kicad_pcb >/dev/null 2>&1 || true
echo "DRC items (all severities; waivers in main-board/drc-waivers.csv): $(grep -c '^\[' drc.txt || true) ($(grep '^\[' drc.txt | cut -d']' -f1 | tr -d '[' | sort | uniq -c | tr '\n' ' '))"
grep -i "unconnected" drc.txt | head -2
cd - >/dev/null
cp "$work/finish.kicad_pcb" "$out"
