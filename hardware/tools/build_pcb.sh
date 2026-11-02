#!/bin/sh
# Regenerate weatherstation-v1: schematic (+ net check) -> netlist -> placed board. Routing is separate (route_krt.sh).
# Usage: hardware/tools/build_pcb.sh [--no-schematic]
set -e
cd "$(dirname "$0")/../.."
. scripts/kicad-env.sh
B=hardware/weatherstation-v1
P=$B/weatherstation-v1
if [ "$1" != "--no-schematic" ]; then
    uv run --package weatherstation-hardware python hardware/gen/weatherstation_v1.py "$B" 2>&1 | grep -v Fontconfig
fi
kicad-cli sch export netlist -o $P.net $P.kicad_sch >/dev/null 2>&1
work="$(mktemp -d)"; trap 'rm -rf "$work"' EXIT
# KiCad's Python has no yaml: hand the net classes over as JSON
uv run --package weatherstation-hardware python -c 'import json, sys, yaml; print(json.dumps(yaml.safe_load(open(sys.argv[1]))["net_classes"]))' \
    $B/board.yaml > "$work/classes.json"
rm -f $P.kicad_pcb
"$KICAD_PYTHON" hardware/gen/pcb_v1.py $P.net $P.kicad_pcb "$work/classes.json" 2>&1 | grep -v -e Fontconfig -e stdpbase -e swig || true
# placement review: annotated render (no pours, nets coloured, mm grid) in hardware/out/review/pcb/
mkdir -p hardware/out/review/pcb
"$KICAD_PYTHON" hardware/tools/board_geom.py $P.kicad_pcb hardware/out/geom.json 2>&1 | grep -v -e Fontconfig -e stdpbase -e swig
uv run --package weatherstation-hardware python hardware/tools/render_review.py hardware/out/geom.json hardware/out/review/pcb \
    heat=0,20,30,50 top=0,0,50,22 sensors=22,20,50,50
# KiCad's own top view (3D renderer, real footprints and copper) next to the annotated renders
kicad-cli pcb render --side top --width 1600 --height 1600 --quality basic --background opaque \
    -o hardware/out/review/pcb/kicad_top.png $P.kicad_pcb 2>&1 | grep -v -e Fontconfig -e "^Successfully" || true
