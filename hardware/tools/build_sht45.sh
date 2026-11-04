#!/bin/sh
# Regenerate the SHT45 sensor head: schematic (+ net check) -> netlist -> board (all copper by hand) -> DRC summary.
# Usage: hardware/tools/build_sht45.sh
set -e
cd "$(dirname "$0")/../.."
. scripts/kicad-env.sh >/dev/null 2>&1
B=hardware/sht45-board
P=$B/sht45-board
uv run --package weatherstation-hardware python hardware/gen/sht45_board.py "$B" 2>&1 | grep -v Fontconfig
kicad-cli sch export netlist -o $P.net $P.kicad_sch >/dev/null 2>&1
rm -f $P.kicad_pcb
"$KICAD_PYTHON" hardware/gen/sht45_pcb.py $P.net $P.kicad_pcb 2>&1 | grep -v -e Fontconfig -e stdpbase -e swig -e "^$" || true
work="$(mktemp -d)"; trap 'rm -rf "$work"' EXIT
kicad-cli pcb drc --refill-zones --schematic-parity --severity-all -o "$work/drc.txt" $P.kicad_pcb >/dev/null 2>&1 || true
grep -E "^\*\* Found" "$work/drc.txt"
grep '^\[' "$work/drc.txt" | cut -d']' -f1 | tr -d '[' | sort | uniq -c || true
mkdir -p hardware/out/review/sht45
kicad-cli pcb render --side top --width 900 --height 1600 --quality basic --background opaque \
    -o hardware/out/review/sht45/top.png $P.kicad_pcb >/dev/null 2>&1 || true
