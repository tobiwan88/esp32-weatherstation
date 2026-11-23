#!/usr/bin/env bash
# hw-kit installer: skills, helper agents, board-neutral tooling and the CLAUDE.md block, into a project or into ~/.claude.
#
#   hw-kit/install.sh TARGET_REPO [--no-tooling] [--no-claude-md] [--claude-md] [--force]
#   hw-kit/install.sh --user [--force]        skills and agents only, into ~/.claude (every project on this machine)
#   hw-kit/install.sh TARGET_REPO --check     report drift between the kit and the installed copies (exit 1 if any)
#
# Never overwrites a file that differs unless --force (it prints the skipped files; diff them, then decide).
# CLAUDE.md: created from a stub when missing; an existing one gets the kit block only with --claude-md (appended) and the
# block is refreshed with --force. Nothing is committed: review `git status` in the target.
set -euo pipefail

KIT="$(cd "$(dirname "$0")" && pwd)"
TARGET=""; MODE=install; FORCE=0; TOOLING=1; CLAUDE=auto
for a in "$@"; do
    case "$a" in
        --user) MODE=user ;;
        --check) MODE=check ;;
        --force) FORCE=1 ;;
        --no-tooling) TOOLING=0 ;;
        --no-claude-md) CLAUDE=off ;;
        --claude-md) CLAUDE=append ;;
        -h|--help) sed -n '2,11p' "$0"; exit 0 ;;
        -*) echo "unknown option $a" >&2; exit 2 ;;
        *) TARGET="$a" ;;
    esac
done

if [ "$MODE" = user ]; then
    [ -z "$TARGET" ] || { echo "--user takes no target" >&2; exit 2; }
    DEST="$HOME"; CL="$HOME/.claude"; TOOLING=0; CLAUDE=off
else
    [ -n "$TARGET" ] && [ -d "$TARGET" ] || { echo "usage: $0 TARGET_REPO [options] | --user | TARGET_REPO --check" >&2; exit 2; }
    DEST="$(cd "$TARGET" && pwd)"; CL="$DEST/.claude"
    [ "$DEST" != "$KIT" ] || { echo "target is the kit folder itself" >&2; exit 2; }
fi

DRIFT=0; COPIED=0; SKIPPED=0
sync_file() {   # sync_file SRC DST
    if [ -e "$2" ] && cmp -s "$1" "$2"; then return; fi
    if [ "$MODE" = check ]; then
        [ -e "$2" ] && echo "differs: ${2#$DEST/}" || echo "missing: ${2#$DEST/}"
        DRIFT=1; return
    fi
    if [ -e "$2" ] && [ "$FORCE" = 0 ]; then echo "skip (exists, differs): ${2#$DEST/}"; SKIPPED=$((SKIPPED+1)); return; fi
    mkdir -p "$(dirname "$2")"; cp -p "$1" "$2"; COPIED=$((COPIED+1))
}
sync_tree() {   # sync_tree SRC_DIR DEST_DIR
    local f
    while IFS= read -r f; do sync_file "$1/$f" "$2/$f"; done < <(cd "$1" && find . -type f ! -name '.DS_Store' ! -path '*/__pycache__/*' | sed 's|^\./||' | sort)
}

for s in "$KIT"/skills/*/; do sync_tree "${s%/}" "$CL/skills/$(basename "$s")"; done
for f in "$KIT"/agents/*.md; do sync_file "$f" "$CL/agents/$(basename "$f")"; done
[ "$TOOLING" = 1 ] && sync_tree "$KIT/tooling" "$DEST"

if [ "$CLAUDE" != off ] && [ "$MODE" != user ]; then
    python3 - "$KIT/CLAUDE.block.md" "$DEST/CLAUDE.md" "$FORCE" "$([ "$MODE" = check ] && echo 1 || echo 0)" "$([ "$CLAUDE" = append ] && echo 1 || echo 0)" <<'PY' || DRIFT=1
import pathlib, sys
kit, target = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
force, check, append = (sys.argv[i] == "1" for i in (3, 4, 5))
BEGIN, END = "<!-- hw-kit:begin", "<!-- hw-kit:end -->"
block = kit.read_text().strip("\n")
stub = "# <project name>: agent notes\n\n<What the product is, who uses it, its status: two or three lines. Keep it current.>\n\n"
if not target.exists():
    if check:
        print("missing: CLAUDE.md"); sys.exit(1)
    target.write_text(stub + block + "\n"); print("created: CLAUDE.md (fill in the project paragraph; keep board names out of it)"); sys.exit(0)
text = target.read_text()
i = text.find(BEGIN)
if i < 0:
    if check:
        print("CLAUDE.md has no kit block"); sys.exit(1)
    if append:
        target.write_text(text.rstrip("\n") + "\n\n" + block + "\n"); print("appended: kit block to CLAUDE.md")
    else:
        print("CLAUDE.md exists without the kit block: rerun with --claude-md to append it")
    sys.exit(0)
j = text.find(END, i) + len(END)
if text[i:j] == block:
    sys.exit(0)
if check:
    print("differs: CLAUDE.md kit block"); sys.exit(1)
if force or append:
    target.write_text(text[:i] + block + text[j:]); print("updated: CLAUDE.md kit block")
else:
    print("skip (exists, differs): CLAUDE.md kit block (--force to refresh)")
PY
fi

if [ "$MODE" = install ] && [ "$TOOLING" = 1 ]; then   # keep generated and private files out of git
    touch "$DEST/.gitignore"
    for l in 'hardware/out/' '.privacy-patterns' '*.kicad_prl' '*-backups/' '__pycache__/' 'CLAUDE.local.md' '.DS_Store'; do
        grep -qxF "$l" "$DEST/.gitignore" || { echo "$l" >> "$DEST/.gitignore"; echo "gitignore: + $l"; }
    done
fi

if [ "$MODE" = check ]; then
    [ "$DRIFT" = 0 ] && echo "hw-kit: installed copies match the kit" || { echo "hw-kit: DRIFT (edit the kit, then hw-kit/install.sh . --force)"; exit 1; }
    exit 0
fi
n_sk=$(find "$CL/skills" \( -path '*/hw-*/SKILL.md' -o -path '*/kicad-*/SKILL.md' \) 2>/dev/null | wc -l | tr -d ' ')
n_ag=$(find "$CL/agents" -name 'hw-*.md' 2>/dev/null | wc -l | tr -d ' ')
echo "hw-kit $(cat "$KIT/VERSION"): $COPIED file(s) copied, $SKIPPED skipped; $n_sk skills, $n_ag agents in $CL"
[ "$MODE" = user ] || echo "next: scripts/new-board.sh <name>, then read .claude/skills/hw-base/references/bootstrap.md"
