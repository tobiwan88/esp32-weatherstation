<!-- hw-kit:begin (managed by hw-kit; edit the kit, then `hw-kit/install.sh . --force`) -->
## Hardware (hw-kit)
- Start here: `.claude/skills/hw-base`, then `hardware/README.md` (boards and their status) and the `BOARD.md` of the board you work on.
- Skills by task: `hw-requirements` (gate 1), `hw-parts` (part check, BOM), `kicad-schematic`, `kicad-layout` (placement, routing),
  `hw-review` (independent reviews), `hw-fab-order` (fab files, order). Agents `hw-*` in `.claude/agents/`: helpers (researcher,
  datasheet extractor, part lookup, DRC triage, one-image check), reviewers (datasheet, consistency, render), `hw-builder`.
- Gate: `scripts/hw-check.sh [--strict] [--stock --qty N]` runs every board in `hardware/*/board.yaml` and must print
  `hardware checks: OK`; MISSING rows are open inputs. `scripts/check.sh` = gate + tests + privacy scan + kit drift check.
- New board: `scripts/new-board.sh <name>`. Numbers come from `hardware/calc/*.py`, never from memory (rule in `hw-base`).
- KiCad: `source scripts/kicad-env.sh`. Stock and price: `python3 hardware/tools/jlcparts.py C123456` or `-s "keyword"`.
  Production files: `python3 -I hardware/tools/fab_package.py --require-clean hardware/<board>/<board>.kicad_pcb` -> `hardware/out/fab/`.
- Working rules: the engineer decides topology, part, value, outline and cost; agents find, build and report. Gates in order,
  evidence in the repo. Commit and push after each finished step once the gate and the privacy check pass. Update this file,
  `hardware/README.md` and the board's `BOARD.md` in the same step as a decision; agents propose wording, they do not edit them.
- Never hand-edit generated files (`*.kicad_sch`, `*.kicad_pcb`); change the generator and rebuild.
- Private data (public repo): never commit Wi-Fi names or passwords, tokens, MAC addresses, host names, LAN IPs, serial ports,
  home paths, order or account data, photos of people or the home, CAD files with user metadata. Personal notes go in
  `CLAUDE.local.md` (gitignored). Run `scripts/privacy-check.sh` before every push; fix findings, do not suppress them.
<!-- hw-kit:end -->
