#!/usr/bin/env bash
# Review the drawn schematic: regenerate, run ERC, and export one PNG per sheet for a human to read.
# Output goes to hardware/out/review/ (git-ignored). Usage: scripts/schematic-review.sh [dpi]
set -euo pipefail
cd "$(dirname "$0")/.."
source scripts/kicad-env.sh
DPI="${1:-110}"
BOARD=hardware/weatherstation-v1
OUT=hardware/out/review
rm -f "$OUT"/page-*.png "$OUT"/erc.json "$OUT"/geometry.txt "$OUT"/schematic.pdf  # keep review-notes.md
mkdir -p "$OUT"

echo "== generate"
uv run --package weatherstation-hardware python hardware/gen/weatherstation_v1.py "$BOARD"

echo "== ERC (zero errors and warnings expected)"
kicad-cli sch erc --severity-all --format json -o "$OUT/erc.json" "$BOARD/weatherstation-v1.kicad_sch" >/dev/null
python3 -I -c '
import json, sys
from collections import Counter
d = json.load(open(sys.argv[1]))
v = [x for s in d.get("sheets", []) for x in s.get("violations", [])]
print("ERC violations:", len(v), dict(Counter(x["type"] for x in v)))
' "$OUT/erc.json"

echo "== geometry (labels on labels, wires through text, small text)"
python3 -I hardware/gen/review_checks.py "$BOARD" | tee "$OUT/geometry.txt" | tail -1

echo "== pages"
kicad-cli sch export pdf --output "$OUT/schematic.pdf" "$BOARD/weatherstation-v1.kicad_sch" >/dev/null
pdftoppm -r "$DPI" -png "$OUT/schematic.pdf" "$OUT/page"
ls "$OUT"/page-*.png
echo "Read every PNG (the image review): labels readable, wires follow the blocks, no text over a wire or part,"
echo "and the root page shows how the blocks connect. Record findings in $OUT/review-notes.md."
