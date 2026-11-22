#!/usr/bin/env bash
# Install the reusable hardware kit (skills, helper agents, templates; optionally the board-neutral tooling) into another
# repository or into the user-level Claude folder.
#
#   scripts/hw-kit-install.sh TARGET_REPO [--tooling] [--force]
#   scripts/hw-kit-install.sh --user [--force]          # skills and agents into ~/.claude (all projects on this machine)
#
# Never overwrites an existing file unless --force. Prints the files it skipped because they exist and differ.
# Skills and agents are board-neutral. With --tooling the board-neutral scripts are copied too (calc checks, fab and render
# helpers, schematic/layout kit, fab rules, gate scripts); the files marked "adapt" in hw-base/references/bootstrap.md
# (board lists, build and route scripts) are NOT copied: write them for the new board.
set -euo pipefail

SRC="$(cd "$(dirname "$0")/.." && pwd)"
SKILLS="hw-base hw-requirements hw-parts hw-fab-order hw-review kicad-schematic kicad-layout"
TOOLING="hardware/calc/bom_check.py hardware/calc/buck.py hardware/calc/critical.py hardware/calc/emi_check.py
hardware/calc/i2c_bus.py hardware/calc/impedance.py hardware/calc/pcb.py hardware/calc/power_budget.py
hardware/calc/rail_switch.py hardware/calc/track_width.py
hardware/tools/fab_package.py hardware/tools/jlcparts.py hardware/tools/silk_fix.py hardware/tools/swap_footprint.py
hardware/tools/render_review.py hardware/tools/board_geom.py hardware/tools/drc_summary.py hardware/tools/pcb_from_netlist.py
hardware/tools/pcb_parts.py hardware/tools/write_project.py hardware/tools/setup_tools.sh
hardware/gen/schkit.py hardware/gen/pins.py hardware/gen/review_checks.py
hardware/rules/jlc-2layer.json hardware/rules/jlc-4layer.json hardware/rules/kicad-erc.json hardware/rules/krt-fab.txt
scripts/privacy-check.sh scripts/kicad-env.sh"

TARGET="" ; USER_MODE=0 ; WITH_TOOLING=0 ; FORCE=0
for a in "$@"; do
    case "$a" in
        --user) USER_MODE=1 ;;
        --tooling) WITH_TOOLING=1 ;;
        --force) FORCE=1 ;;
        -h|--help) sed -n '2,12p' "$0"; exit 0 ;;
        -*) echo "unknown option $a" >&2; exit 2 ;;
        *) TARGET="$a" ;;
    esac
done
if [ "$USER_MODE" = 1 ]; then
    [ -z "$TARGET" ] || { echo "--user takes no target" >&2; exit 2; }
    [ "$WITH_TOOLING" = 0 ] || { echo "--tooling needs a target repo" >&2; exit 2; }
    DEST="$HOME"
else
    [ -n "$TARGET" ] && [ -d "$TARGET" ] || { echo "usage: $0 TARGET_REPO|--user [--tooling] [--force]" >&2; exit 2; }
    DEST="$(cd "$TARGET" && pwd)"
    [ "$DEST" != "$SRC" ] || { echo "target is the source repo" >&2; exit 2; }
fi

copy_file() {   # copy_file SRC_FILE DEST_FILE
    if [ -e "$2" ] && [ "$FORCE" = 0 ]; then
        cmp -s "$1" "$2" || echo "skip (exists, differs): ${2#$DEST/}"
        return
    fi
    mkdir -p "$(dirname "$2")"; cp "$1" "$2"
}
copy_tree() {   # copy_tree SRC_DIR DEST_DIR
    (cd "$1" && find . -type f ! -name '.DS_Store' ! -path '*/__pycache__/*') | while read -r f; do
        copy_file "$1/$f" "$2/$f"
    done
}

CL="$DEST/.claude"
[ "$USER_MODE" = 1 ] && CL="$HOME/.claude"
for s in $SKILLS; do copy_tree "$SRC/.claude/skills/$s" "$CL/skills/$s"; done
for f in "$SRC"/.claude/agents/hw-*.md; do copy_file "$f" "$CL/agents/$(basename "$f")"; done
if [ "$WITH_TOOLING" = 1 ]; then
    for f in $TOOLING; do copy_file "$SRC/$f" "$DEST/$f"; done
fi
n_sk=$(find "$CL/skills" -path '*/hw-*/SKILL.md' -o -path '*/kicad-*/SKILL.md' | wc -l | tr -d ' ')
n_ag=$(find "$CL/agents" -name 'hw-*.md' | wc -l | tr -d ' ')
echo "kit in $CL: $n_sk skills, $n_ag agents$([ "$WITH_TOOLING" = 1 ] && echo ", tooling copied to $DEST")"
echo "next: read .claude/skills/hw-base/references/bootstrap.md"
