# Starting a new hardware project with this kit

## 1 Install
- Into another repo: `scripts/hw-kit-install.sh <repo> [--tooling]` (from the repo that holds the kit). It copies the skills,
  the `hw-*` helper agents and the templates, and with `--tooling` the board-neutral scripts listed in its header. It
  never overwrites a differing file without `--force`.
- For every project on this machine: `scripts/hw-kit-install.sh --user` (skills and agents into `~/.claude`). A project's
  own `.claude/` wins over the user level, so a project can pin its own copy.
- The kit improves with each project: after a project, fold its lessons into the skills (rule or pitfall row with the
  symptom and the fix; remove rules that proved wrong), then reinstall elsewhere with `--force` after reviewing the diff.

## 2 Tooling that is NOT board-neutral (write or adapt per project)
| File | What to adapt |
|---|---|
| `scripts/hw-check.sh` | the board list, which calc scripts run per board, the stack/split checks |
| `scripts/schematic-review.sh`, `scripts/check.sh`, `scripts/idf-env.sh` | board names, firmware environment |
| `hardware/tools/build_board.sh`, `route_*.sh`, `finish_*.py`, `main_freeze.py`, `main_stitch.py`, `widen_charge.py` | board names, net names, route stages |
| `hardware/tools/split_check.py`, `stack_check.py`, `header_check.py`, `gen/boards_common.py`, `gen/stack.py` | only for multi-board designs: header pins, outline, holes |
| `hardware/gen/<board>.py`, `<board>_layout.py`, `<board>_pcb.py`, `<board>_copper.py`, `boardgen.py`, `pcbkit.py` | the generators; `schkit.py` (sheet writer, router) is shared |
| `hardware/calc/power_route_check.py` | charger-specific routed-board checks; copy only as a pattern |
| `hardware/rules/<board>.kicad_dru` | custom DRC rules per board |
Rename the board and its net names together; a half rename leaves `critical.yaml` and net classes pointing at nothing.

## 3 Order of the first session
1. `CLAUDE.md` for the new project: what the product is, "start here" (hardware: `hw-base`, then `BOARD.md`), the gate
   command, the decisions that must not be lost, the privacy rules, the commit rhythm. Keep it current at every status change.
2. Environment: KiCad 7+ with `kicad-cli` and KiCad's bundled Python (`scripts/kicad-env.sh`), Python 3.x with PyYAML, numpy,
   scipy, Pillow, PyMuPDF; `pdftotext`; a Java runtime only if the fallback router is used; the router tools via `setup_tools.sh`.
3. Repo hygiene: `.gitignore` for `hardware/out/`, downloaded tools, exported netlists, `*.kicad_prl`, `*-backups/`, secrets;
   `scripts/privacy-check.sh` wired into `scripts/check.sh`.
4. Gate 1 with `hw-requirements`: `REQUIREMENTS.md` from the template, the interview, the cost model, the power cycle.
5. Profile per board from `templates/`: `board.yaml`, `critical.yaml`, `emi.yaml`, `BOARD.md`, `bom.csv` (header only; the
   generator fills it), `parts/<MPN>.yaml` per IC, `drc-waivers.csv`, plus `GATES.md`, `ARCHITECTURE.md` (several boards),
   `FIRMWARE-RULES.md`. A skeleton passes the calc scripts with `MISSING` rows for the values still to fill: that is the to-do list.
6. Gate 2: parts, stock, datasheets (`hw-parts`, researcher and extractor agents).
7. Gate 3 onward: `kicad-schematic`, `kicad-layout`, `hw-review` rounds, `hw-fab-order`.

## 4 Habits that paid off (from the first project)
- Cost per finished unit and the sleep/autonomy budget are computed at gate 1, not after the drawing.
- Every review is independent and rebuilds the facts; builders' reports are verified by rerunning the gate.
- The engineer decides; you bring numbered decisions with options and cost.
- Commit per step, push after the gate and the privacy check; agents commit locally in small steps.
- Entry docs and order notes are updated in the same step as the decision they describe.
