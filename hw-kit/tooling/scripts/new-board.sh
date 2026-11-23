#!/usr/bin/env bash
# Scaffold a board profile from the hw-base templates:  scripts/new-board.sh <name>
# Creates hardware/<name>/ (board.yaml, critical.yaml, emi.yaml, BOARD.md, PARTS-REVIEW.md, bom.csv, drc-waivers.csv, parts/)
# and, when missing, the project files hardware/REQUIREMENTS.md and hardware/GATES.md. Never overwrites a file.
# The scaffold passes scripts/hw-check.sh with MISSING rows: those rows are the to-do list for gate 1 and 2.
set -euo pipefail
cd "$(dirname "$0")/.."
name="${1:-}"
[[ "$name" =~ ^[a-z0-9][a-z0-9-]*$ ]] || { echo "usage: $0 <board-name>   (lowercase letters, digits, '-')" >&2; exit 2; }
T=.claude/skills/hw-base/templates
[ -d "$T" ] || { echo "templates not found in $T (install the kit first)" >&2; exit 2; }
D="hardware/$name"
mkdir -p "$D/parts" "$D/datasheets" hardware/rules
put() {   # put TEMPLATE DEST
    [ -e "$2" ] && { echo "exists: $2"; return; }
    sed "s|<board>|$name|g" "$1" > "$2"; echo "created: $2"
}
put $T/board.yaml "$D/board.yaml"
put $T/critical.yaml "$D/critical.yaml"
put $T/emi.yaml "$D/emi.yaml"
put $T/BOARD.md "$D/BOARD.md"
put $T/PARTS-REVIEW.md "$D/PARTS-REVIEW.md"
put $T/bom.csv "$D/bom.csv"
put $T/drc-waivers.csv "$D/drc-waivers.csv"
[ -e hardware/REQUIREMENTS.md ] || { cp $T/REQUIREMENTS.md hardware/REQUIREMENTS.md; echo "created: hardware/REQUIREMENTS.md"; }
[ -e hardware/GATES.md ] || { cp $T/GATES.md hardware/GATES.md; echo "created: hardware/GATES.md"; }
[ -e hardware/README.md ] || printf '# Hardware: where to look\n\nOne row per board. Keep this file current; CLAUDE.md points here instead of naming boards.\n\n| Board | Status | Gate | Notes |\n|---|---|---|---|\n' > hardware/README.md
grep -q "^| $name " hardware/README.md || { echo "| $name | new | 1 requirements | $D/BOARD.md |" >> hardware/README.md; echo "added $name to hardware/README.md"; }
[ -e hardware/ARCHITECTURE.md ] || echo "several boards? copy $T/ARCHITECTURE.md to hardware/ARCHITECTURE.md"
echo "next: hw-requirements (gate 1), then scripts/hw-check.sh"
