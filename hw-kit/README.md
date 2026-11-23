# hw-kit: Claude Code kit for new PCB projects

Board-neutral skills, subagents, check scripts and templates for taking any number of boards from requirements to a JLCPCB
order, with an engineer who decides and agents who find, build and review. Nothing in here names a board or a project.

## Use it in a new project
```
git clone <this repo> /tmp/kit            # or copy this folder
/tmp/kit/hw-kit/install.sh ~/path/to/new-project
cd ~/path/to/new-project
scripts/new-board.sh my-board             # board profile from templates, per board
scripts/hw-check.sh                       # passes with MISSING rows = your to-do list for gates 1 and 2
```
Updates: rerun the installer from the newer kit with `--force` after diffing. A repo that holds `hw-kit/` itself (the kit's
own home) gets the drift check in `scripts/check.sh`. For every project on this machine: `hw-kit/install.sh --user` (skills and agents into `~/.claude`;
a project's own `.claude/` wins). Options: `--no-tooling`, `--claude-md` (append the block to an existing CLAUDE.md), `--force`
(overwrite differing files: diff first). Nothing is committed for you.

Requirements on the machine: Python 3 with PyYAML, numpy, scipy, Pillow, PyMuPDF; KiCad 7+ (`kicad-cli` and its Python) for
ERC/DRC/plots; `pdftotext`; network for stock lookups. `hw-base/references/bootstrap.md` has the first-session order.

## What it covers
| Work | Skill | Agents | Checks (run from the repo root) |
|---|---|---|---|
| Requirements, cost model, power cycle, pin plan, splitting into boards | `hw-requirements` | `hw-researcher` | `calc/power_budget.py`, `calc/bom_check.py` |
| Part check: datasheet facts, circuit against app notes, regulators | `hw-parts` | `hw-datasheet-extractor`, `hw-part-lookup`, `hw-datasheet-reviewer` | `calc/buck.py`, `calc/rail_switch.py`, `calc/i2c_bus.py`, parts cards |
| BOM creation and review: fab numbers, stock, price tiers, fees | `hw-parts` | `hw-part-lookup`, `hw-consistency-reviewer` | `calc/bom_check.py [--strict] [--stock --qty N]` |
| Schematic design and check | `kicad-schematic` | `hw-render-reviewer`, `hw-visual-check`, `hw-datasheet-reviewer` | `gen/review_checks.py`, ERC, net-intent |
| Layout: placement, routing, EMI | `kicad-layout` | `hw-builder`, `hw-drc-triage`, `hw-render-reviewer` | `calc/critical.py`, `calc/emi_check.py`, `calc/track_width.py`, `calc/impedance.py`, DRC |
| Review rounds, findings A/B/C, decisions | `hw-review` | all reviewers | `scripts/hw-check.sh`, `REVIEW-<date>.md` |
| Fab files and JLCPCB order | `hw-fab-order` | `hw-part-lookup` | `tools/fab_package.py`, footprint fit, `bom_check --stock` |

Gates in order: 1 requirements, 2 BOM accepted, 3 schematic, 4 placement, 5 routing, 6 fab/order (`hw-base`, `templates/GATES.md`).

## Layout of the kit
```
hw-kit/
  install.sh            installer and drift check
  CLAUDE.block.md       board-neutral block put into the project's CLAUDE.md (between hw-kit markers)
  VERSION
  skills/               hw-base (read first, templates/, references/), hw-requirements, hw-parts, kicad-schematic,
                        kicad-layout, hw-review, hw-fab-order            -> <project>/.claude/skills/
  agents/               hw-researcher, hw-datasheet-extractor, hw-part-lookup, hw-drc-triage, hw-visual-check,
                        hw-datasheet-reviewer, hw-consistency-reviewer, hw-render-reviewer, hw-builder -> <project>/.claude/agents/
  tooling/              copied to the project root at the same relative paths:
                        scripts/  hw-check.sh (gate, any number of boards), check.sh, new-board.sh, privacy-check.sh, kicad-env.sh
                        hardware/calc/   board profile checks (BOM, power, tracks, regulators, I2C, critical blocks, EMI, impedance)
                        hardware/tools/  stock lookup, fab package, DRC summary, render review, footprint swap, netlist to board
                        hardware/gen/    schkit.py (schematic sheet writer), review_checks.py
                        hardware/rules/  fab capability rules, ERC severities
```

## What stays project specific (write it per project)
Board generators (`hardware/gen/<board>*.py`), build and route scripts, custom DRC rules per board, project checks between
boards (put them in `scripts/hw-check.d/*.sh`, the gate runs them), `schkit` title-block defaults (optional
`hardware/gen/schkit_defaults.py`), the project's `.privacy-ignore` and `.privacy-patterns`. Details: `skills/hw-base/references/bootstrap.md`.

## Improving the kit
Fold lessons from each project into the skills (a rule or a pitfall row with symptom and fix; delete rules that proved wrong),
edit in `hw-kit/`, then `hw-kit/install.sh . --force` and `scripts/check.sh` (the drift check fails when an installed copy was
edited instead of the kit). Keep every skill under about 150 lines with detail in `references/`.
