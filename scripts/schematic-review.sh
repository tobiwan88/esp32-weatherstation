#!/usr/bin/env bash
# Review the drawn schematic of one board: regenerate, run ERC, geometry checks, and export one PNG per sheet.
# Usage: scripts/schematic-review.sh [board] [dpi]   board = weatherstation-v1 (default), power-board, main-board
# Output: hardware/out/review/<board>/ (git-ignored). Exit 1 when the net check, ERC or the geometry check fails.
set -euo pipefail
cd "$(dirname "$0")/.."
source scripts/kicad-env.sh
NAME="${1:-weatherstation-v1}"
DPI="${2:-110}"
BOARD=hardware/$NAME
GEN=hardware/gen/${NAME//-/_}.py
OUT=hardware/out/review/$NAME
rm -f "$OUT"/page-*.png "$OUT"/erc.json "$OUT"/geometry.txt "$OUT"/schematic.pdf  # keep review-notes.md
mkdir -p "$OUT"
rc=0

echo "== generate ($GEN)"
uv run --package weatherstation-hardware python "$GEN" "$BOARD" || rc=1

echo "== ERC (zero errors and warnings expected)"
kicad-cli sch erc --severity-all --format json -o "$OUT/erc.json" "$BOARD/$NAME.kicad_sch" >/dev/null
python3 -I -c '
import json, sys
from collections import Counter
d = json.load(open(sys.argv[1]))
v = [x for s in d.get("sheets", []) for x in s.get("violations", [])]
print("ERC violations:", len(v), dict(Counter(x["type"] for x in v)))
for x in v:
    print("  ", x["severity"], x["type"], x["description"], [i.get("description") for i in x.get("items", [])])
sys.exit(1 if v else 0)
' "$OUT/erc.json" || rc=1

echo "== geometry (labels on labels, wires through text, small text)"
python3 -I hardware/gen/review_checks.py "$BOARD" --strict > "$OUT/geometry.txt" || rc=1
tail -1 "$OUT/geometry.txt"

echo "== pages"
kicad-cli sch export pdf --output "$OUT/schematic.pdf" "$BOARD/$NAME.kicad_sch" >/dev/null
pdftoppm -r "$DPI" -png "$OUT/schematic.pdf" "$OUT/page"
ls "$OUT"/page-*.png
echo "Read every PNG (the image review): labels readable, wires follow the blocks, no text over a wire or part,"
echo "and the root page shows how the blocks connect. Record findings in $OUT/review-notes.md."
exit $rc
