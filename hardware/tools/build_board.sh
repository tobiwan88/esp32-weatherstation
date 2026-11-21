#!/bin/sh
# Regenerate one split board: schematic (+ net check) -> netlist -> placed board (no routing) -> renders.
# Usage: hardware/tools/build_board.sh power-board|main-board [--no-schematic]
# Output: hardware/<board>/<board>.kicad_pcb (+ .kicad_pro board section, .kicad_dru), renders in
# hardware/out/review/pcb-<board>/ (git-ignored). Generators: gen/<board>.py (schematic), gen/<board>_pcb.py (layout).
set -e
cd "$(dirname "$0")/../.."
. scripts/kicad-env.sh
NAME="$1"
case "$NAME" in power-board|main-board) ;; *) echo "usage: $0 power-board|main-board [--no-schematic]"; exit 2;; esac
B=hardware/$NAME
P=$B/$NAME
GEN=$(echo "$NAME" | tr - _)
LGEN=hardware/gen/${GEN%_board}_pcb.py
if [ "$2" != "--no-schematic" ]; then
    uv run --package weatherstation-hardware python hardware/gen/$GEN.py "$B" 2>&1 | grep -v Fontconfig
fi
kicad-cli sch export netlist -o $P.net $P.kicad_sch >/dev/null 2>&1
work="$(mktemp -d)"; trap 'rm -rf "$work"' EXIT
# KiCad's Python has no yaml: hand the net classes over as JSON
uv run --package weatherstation-hardware python -c 'import json, sys, yaml; print(json.dumps(yaml.safe_load(open(sys.argv[1]))["net_classes"]))' \
    $B/board.yaml > "$work/classes.json"
rm -f $P.kicad_pcb
"$KICAD_PYTHON" $LGEN $P.net $P.kicad_pcb "$work/classes.json" 2>&1 | grep -v -e Fontconfig -e stdpbase -e swig
OUT=hardware/out/review/pcb-$NAME
mkdir -p $OUT
"$KICAD_PYTHON" hardware/tools/board_geom.py $P.kicad_pcb $OUT/geom.json 2>&1 | grep -v -e Fontconfig -e stdpbase -e swig
REGIONS=$(sed -n 's/^REGIONS = "\(.*\)"$/\1/p' $LGEN)   # render regions named in the layout generator
uv run --package weatherstation-hardware python hardware/tools/render_review.py $OUT/geom.json $OUT $REGIONS
kicad-cli pcb render --side top --width 1600 --height 1600 --quality basic --background opaque \
    -o $OUT/kicad_top.png $P.kicad_pcb 2>&1 | grep -v -e Fontconfig -e "^Successfully" || true
kicad-cli pcb render --side bottom --width 1600 --height 1600 --quality basic --background opaque \
    -o $OUT/kicad_bottom.png $P.kicad_pcb 2>&1 | grep -v -e Fontconfig -e "^Successfully" || true
