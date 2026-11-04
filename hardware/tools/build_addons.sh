#!/bin/sh
# Regenerate the Qwiic add-on boards: schematic (+ net check) -> ERC -> netlist -> board (all copper by hand) -> DRC
# with parity -> render in hardware/out/review/<board>/. Usage: hardware/tools/build_addons.sh [bmp585] [veml6030]
set -e
cd "$(dirname "$0")/../.."
. scripts/kicad-env.sh >/dev/null 2>&1
work="$(mktemp -d)"; trap 'rm -rf "$work"' EXIT
for key in ${@:-bmp585 veml6030}; do
    B=hardware/$key-board
    P=$B/$key-board
    echo "== $key"
    uv run --package weatherstation-hardware python hardware/gen/addon_boards.py "$key" 2>&1 | grep -v Fontconfig
    kicad-cli sch export netlist -o $P.net $P.kicad_sch >/dev/null 2>&1
    rm -f $P.kicad_pcb
    "$KICAD_PYTHON" hardware/gen/addon_pcb.py "$key" $P.net $P.kicad_pcb 2>&1 | grep -v -e Fontconfig -e stdpbase -e swig -e "^$" || true
    kicad-cli sch erc --severity-all -o "$work/erc.txt" $P.kicad_sch >/dev/null 2>&1 || true
    grep -E "ERC messages" "$work/erc.txt" | sed 's/^ */ERC: /'
    grep '^\[' "$work/erc.txt" | cut -d']' -f1 | tr -d '[' | sort | uniq -c | sed 's/^/ERC /' || true
    kicad-cli pcb drc --refill-zones --schematic-parity --severity-all -o "$work/drc.txt" $P.kicad_pcb >/dev/null 2>&1 || true
    grep -E "^\*\* Found" "$work/drc.txt"
    grep '^\[' "$work/drc.txt" | cut -d']' -f1 | tr -d '[' | sort | uniq -c || true
    mkdir -p hardware/out/review/$key
    kicad-cli pcb render --side top --width 900 --height 1200 --quality basic --background opaque \
        -o hardware/out/review/$key/top.png $P.kicad_pcb >/dev/null 2>&1 || true
done
