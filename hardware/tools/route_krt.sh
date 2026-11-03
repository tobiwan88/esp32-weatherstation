#!/bin/sh
# Route a placed weatherstation-v1 board with KiCadRoutingTools: GND planes on In1 and In2, then every other net on
# F.Cu/B.Cu only, so both planes stay solid (REQUIREMENTS E2). Fab floors pinned (rules/krt-fab.txt).
# Usage: route_krt.sh placed.kicad_pcb routed.kicad_pcb
# Stage boards live in a temp dir (no stray KiCad projects in the repo); logs go to hardware/out/route/.
set -e
. "$(dirname "$0")/../../scripts/kicad-env.sh" >/dev/null 2>&1
# Pin Python's hash order (KRT_SEED, default 1); the result also depends on the object ids of the input board.
export PYTHONHASHSEED="${KRT_SEED:-1}"
here="$(cd "$(dirname "$0")/.." && pwd)"
K="$here/.tools/KiCadRoutingTools"; P="$K/.venv/bin/python"; F="$here/rules/krt-fab.txt"
[ -x "$P" ] || { echo "KiCadRoutingTools missing: run hardware/tools/setup_tools.sh" >&2; exit 1; }
in="$(cd "$(dirname "$1")" && pwd)/$(basename "$1")"; out="$2"
work="$(mktemp -d)"; logs="${KRT_LOGS:-$here/out/route}"
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
widths=""; for n in $CHARGE; do widths="$widths ${CHARGE_W:-0.65}"; done; for n in $POWER; do widths="$widths 0.4"; done
pw="--power-nets $CHARGE $POWER GND --power-nets-widths $widths 0.3 --track-width 0.2 --clearance 0.15"
# Stages run in order on one board; each stage's copper is locked before the next (unlocked earlier copper gets
# ripped). Hand-drawn copper from gen/pcb_v1.py arrives locked. KRT_STAGES picks the stages (default below):
#   fanout  45-degree stubs on the charger IC's signal pins (its power pins carry hand-drawn pours)
#   power   Charge and Power class nets at class width on the otherwise empty board
#   ctrl    the long control nets (CTRL, or KRT_CTRL) before the rest
#   rest    every net (inside-out order); KRT_ARGS adds route.py options (e.g. --max-ripup 6)
lock() { "$KICAD_PYTHON" -c 'import pcbnew, sys
b = pcbnew.LoadBoard(sys.argv[1])
for t in b.GetTracks():
    t.SetLocked(True)
pcbnew.SaveBoard(sys.argv[1], b)' "$1" 2>/dev/null; }
ESC="/Charger/* !/Charger/SW1 !/Charger/SW2 !/Charger/PV_IN REGN /Battery/TS /USB_DP /USB_DN USB_VBUS VBUS BAT_PACK"
# long control nets from the charger and the rails to the MCU: routed before the short local nets take the channels
CTRL="/Charger/CHG_SCL /Charger/CHG_SDA /Charger/CHG_CE /Charger/CHG_INT /MCU/BOOST_EN /Rails/FB /Rails/GAS_FB"
cur=poured
for s in ${KRT_STAGES:-fanout power rest}; do
    case $s in
    fanout) $P "$K/py_router/qfn_fanout.py" $cur.kicad_pcb -o $s.kicad_pcb -c U3 --nets $ESC --width 0.2 \
                --clearance 0.15 --fab-overrides $F --no-fix-drc-settings > $s.log 2>&1 || cp $cur.kicad_pcb $s.kicad_pcb
            grep -h "^JSON_SUMMARY" $s.log | cut -c1-200 ;;
    usb)    $P "$K/py_router/route_diff.py" $cur.kicad_pcb --output $s.kicad_pcb --nets "/USB_D*" --layers F.Cu B.Cu \
                --track-width 0.27 --diff-pair-gap 0.15 --clearance 0.15 --keep-input-copper $common > $s.log 2>&1 \
                || cp $cur.kicad_pcb $s.kicad_pcb ;;
    power)  $P "$K/py_router/route.py" $cur.kicad_pcb $s.kicad_pcb --nets $CHARGE $POWER --layers F.Cu B.Cu \
                $pw --keep-input-copper $common ${KRT_PARGS:-} > $s.log 2>&1 || true ;;
    ctrl)   $P "$K/py_router/route.py" $cur.kicad_pcb $s.kicad_pcb --nets ${KRT_CTRL:-$CTRL} --layers F.Cu B.Cu $pw \
                --keep-input-copper $common ${KRT_ARGS:-} > $s.log 2>&1 || true ;;
    rest)   $P "$K/py_router/route.py" $cur.kicad_pcb $s.kicad_pcb --nets "*" --layers F.Cu B.Cu --ordering inside_out \
                $pw --json-out route.json --keep-input-copper $common ${KRT_ARGS:-} > $s.log 2>&1 || true
            cp $s.log route.log ;;
    esac
    grep -h "JSON_SUMMARY_MIN" $s.log | sed "s/^/$s: /" | cut -c1-600
    cp poured.kicad_pro $s.kicad_pro; cp poured.kicad_dru $s.kicad_dru
    cur=$s
    [ "$s" = rest ] || lock $s.kicad_pcb  # the final stage stays unlocked (editable; marks the board as routed)
done
cd - >/dev/null
cp "$work/$cur.kicad_pcb" "$out"
