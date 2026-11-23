# esp32-weatherstation: agent notes

Solar + USB powered ESP32-S3 air-quality weather station (particulate sensor, outdoor temperature and humidity, optional CO2
and O3 modules), deep-sleep duty cycle, WiFi to Home Assistant/MQTT. Custom 4-layer PCBs, JLCPCB-assembled. Hardware is in
layout and routing, firmware not started; the board list and each board's status are in `hardware/README.md`.

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

## Project specifics
- Map of the hardware tree and board status: `hardware/README.md`. System requirements: `hardware/REQUIREMENTS-system.md`.
  Architecture and the header between boards: `hardware/ARCHITECTURE.md`. Decisions that must not be lost: `hardware/DECISIONS.md`.
  Plan: `hardware/PLAN.md`. Order notes: `hardware/ORDER-*.md` and the `ORDER.md` in a board folder.
- Checks between boards (split proof, header, stack fit) run from `scripts/hw-check.d/`.
- The kit is the folder `hw-kit/` (source of truth for `.claude/skills`, `.claude/agents`, the board-neutral scripts under
  `hardware/calc`, `hardware/tools`, `hardware/rules` and `scripts/`): edit there, then `hw-kit/install.sh . --force`.
- Tests: `python3 -m pytest -q` (or `uv run pytest`). Python 3.13, `uv`. ESP-IDF v6.1 (firmware, later): `source scripts/idf-env.sh`.
- `hardware/reference/`: pipeline of an earlier project, copy-and-adapt material, not active.
- Firmware: Kconfig defaults for personal values stay 0 / "". New binary or CAD exports (gerbers, STEP, images): check embedded
  metadata for names and paths first.
