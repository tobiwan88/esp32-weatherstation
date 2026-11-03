#!/bin/sh
# Route weatherstation-v1 end to end: placed board (build_pcb.sh) -> KRT planes, power, rest (route_krt.sh) ->
# rip-up finishing pass (route_finish.sh) -> Charge tracks widened where they fit (widen_charge.py) -> via nudge,
# dangling cleanup, zone refill (finish_v1.py) -> kicad-cli DRC summary.
# Settings = routing trial 12 (2026-11-03): all nets routed. Hand-drawn copper in gen/pcb_v1.py carries the charge
# trunks, U3's fan-out and bottom-row bundle, the boost/buck-boost local nodes.
# Usage: hardware/tools/route_v1.sh [out.kicad_pcb]   (default: the board in place, hardware/weatherstation-v1/)
set -e
cd "$(dirname "$0")/../.."
. scripts/kicad-env.sh >/dev/null 2>&1
P=hardware/weatherstation-v1/weatherstation-v1
out="${1:-$P.kicad_pcb}"
work="$(mktemp -d)"; trap 'rm -rf "$work"' EXIT
export KRT_LOGS="${KRT_LOGS:-hardware/out/route}"
KRT_STAGES="${KRT_STAGES:-power rest}" KRT_ARGS="${KRT_ARGS:---max-ripup 4 --ripup-blocker-select cost}" \
    hardware/tools/route_krt.sh $P.kicad_pcb "$work/r.kicad_pcb"
hardware/tools/route_finish.sh "$work/r.kicad_pcb" "$work/f.kicad_pcb" --max-ripup 8 --ripup-blocker-select near-target
for f in f w; do cp $P.kicad_pro "$work/$f.kicad_pro"; cp $P.kicad_dru "$work/$f.kicad_dru"; done
"$KICAD_PYTHON" hardware/tools/widen_charge.py "$work/f.kicad_pcb" "$work/w.kicad_pcb" 2>/dev/null | head -1
"$KICAD_PYTHON" hardware/tools/finish_v1.py "$work/w.kicad_pcb" 2>/dev/null | grep "^finish"
kicad-cli pcb drc --refill-zones --severity-error -o "$work/drc.txt" "$work/w.kicad_pcb" >/dev/null 2>&1 || true
echo "DRC errors: $(grep -c '^\[' "$work/drc.txt" || true) ($(grep '^\[' "$work/drc.txt" | cut -d']' -f1 | tr -d '[' | sort | uniq -c | tr '\n' ' '))"
cp "$work/w.kicad_pcb" "$out"
