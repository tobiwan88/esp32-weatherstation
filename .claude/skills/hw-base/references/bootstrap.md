# Starting a new hardware project with this kit

## 1 Install
- Into a project: `<kit>/hw-kit/install.sh <project>`: skills, `hw-*` agents, tooling (scripts, calc, tools, rules), the
  CLAUDE.md block and `.gitignore` lines. It never overwrites a differing file without `--force`; nothing is committed.
- For every project on this machine: `hw-kit/install.sh --user` (skills and agents into `~/.claude`). A project's own
  `.claude/` wins over the user level, so a project can pin its own copy.
- Keep `hw-kit/` in the project to get the drift check in `scripts/check.sh` and later updates.
- The kit improves with each project: fold its lessons into `hw-kit/skills` (rule or pitfall row with the symptom and the
  fix; remove rules that proved wrong), then `hw-kit/install.sh . --force` and reinstall elsewhere after reviewing the diff.

## 2 What is NOT in the kit (write it per project)
| Item | What it holds |
|---|---|
| `hardware/gen/<board>.py`, `<board>_layout.py`, `<board>_pcb.py`, copper and route helpers, `boardgen.py`, `pcbkit.py` | the generators; `schkit.py` (sheet writer) is shared and takes its title-block defaults from an optional `hardware/gen/schkit_defaults.py` |
| `hardware/tools/build_<board>.sh`, `route_*.sh`, freeze and stitch scripts | build and route stages, net names |
| `hardware/rules/<board>.kicad_dru` | custom DRC rules per board |
| `scripts/hw-check.d/*.sh` | checks between boards: split proof, stack fit, header mating (only with several boards) |
| `.privacy-ignore`, `.privacy-patterns` | paths to skip (vendored code, CAD exports); private regexes (names, hosts), gitignored |
| `scripts/idf-env.sh` and similar | firmware environment |
`scripts/hw-check.sh` finds boards itself (`hardware/*/board.yaml`); `scripts/new-board.sh <name>` creates a profile.
Rename a board and its net names together; a half rename leaves `critical.yaml` and net classes pointing at nothing.

## 3 Order of the first session
1. `CLAUDE.md`: the installer creates a stub with the kit block (start here, gate command, working rules, privacy). Fill in
   the project paragraph; keep board names out of it (boards and status live in `hardware/README.md`, decisions that must not
   be lost in `hardware/DECISIONS.md`). Keep both current at every status change.
2. Environment: KiCad 7+ with `kicad-cli` and KiCad's bundled Python (`scripts/kicad-env.sh`), Python 3.x with PyYAML, numpy,
   scipy, Pillow, PyMuPDF; `pdftotext`; a Java runtime only if the fallback router is used; the router tools via `setup_tools.sh`.
3. Repo hygiene: the installer adds the `.gitignore` lines (`hardware/out/`, `*.kicad_prl`, `*-backups/`, private patterns);
   add downloaded tools and exported netlists; `scripts/check.sh` already runs `scripts/privacy-check.sh`.
4. Gate 1 with `hw-requirements`: `REQUIREMENTS.md` from the template, the interview, the cost model, the power cycle.
5. `scripts/new-board.sh <name>` per board (profile from `templates/`): `board.yaml`, `critical.yaml`, `emi.yaml`, `BOARD.md`, `bom.csv` (header only; the
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
