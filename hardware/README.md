# Hardware: where to look

Board profile: **`weatherstation-v1/`** (requirements, BOM, datasheet cards, order checklist). Pre-layout: no KiCad project yet.

| What | Where |
|---|---|
| Requirements (function, electrical, thermal, EMC, USB, manufacturing, cost) | `weatherstation-v1/REQUIREMENTS.md` |
| BOM with LCSC numbers and verification status | `weatherstation-v1/bom.csv` |
| Board notes, decisions, open items, commands | `weatherstation-v1/BOARD.md` |
| Facts the scripts read | `weatherstation-v1/board.yaml`, `critical.yaml`, `parts/` |
| Order checklist, bring-up | `weatherstation-v1/ORDER.md` |
| Plan and next steps | `PLAN.md` |
| Board-neutral checks | `calc/` (`bom_check.py`, `power_budget.py`, `critical.py`, `buck.py`, `impedance.py`, `pcb.py`) |
| Stock lookup, DRC summary | `tools/` (`jlcparts.py`, `drc_summary.py`) |
| Fab design floors | `rules/` |
| Helper-agent prompts | `agents/` |
| Working KiCad pipeline to copy from (desk_notifier) | `reference/desk_notifier/` |

Agent skills (board-neutral): `hw-base` (read first), `kicad-schematic`, `kicad-layout`, `hw-parts` in `.claude/skills/`.
