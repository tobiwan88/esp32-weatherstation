---
name: hw-base
description: Read first for any hardware/PCB task (KiCad schematic, layout, parts, ordering, reviews). Also use when starting a new hardware project or board profile (board.yaml, critical.yaml, datasheet cards), writing or changing a hardware/calc check script, or writing a hardware skill. Task skills - hw-requirements, kicad-schematic, kicad-layout, hw-parts, hw-fab-order, hw-review.
---

# Hardware base

Board-neutral. Facts about one board live in its profile, never in a skill. A new project starts with
`references/bootstrap.md` (what to copy) and `templates/`.

## Gates (a stage starts when the previous gate passed; evidence in the repo; open items are listed, never waived silently)
| Gate | Stage | Skill | Exit check |
|---|---|---|---|
| 1 | requirements | `hw-requirements` | engineer accepted the file; cost, power, pins, interfaces written |
| 2 | BOM research and acceptance | `hw-parts` | every line: fab number, stock, datasheet section, footprint checked; `hw-check --strict` OK |
| 3 | schematic | `kicad-schematic` | ERC 0, net intent OK, geometry review 0, every PNG read, review round done (`hw-review`) |
| 4 | placement | `kicad-layout` | floorplan in `BOARD.md`, DRC 0, `critical.py --placement` OK, stack/header checks OK |
| 5 | routing | `kicad-layout` | fully routed, DRC 0 at all severities, `critical.py`, `emi_check.py`, renders read, review round |
| 6 | fab files and order | `hw-fab-order` | clean tree, fit OK, engineer's KiCad review, preview checked |
Keep the project's own status per gate in `hardware/GATES.md`.

## Folder contract
- `hardware/<board>/` = one board profile:
  - `board.yaml`: files, fab, stackup (layer roles), net classes, layout settings, BOM alternates, design inputs for calc scripts.
  - `critical.yaml`: critical blocks, one key per `calc/critical.py` check. `emi.yaml`: settings of `calc/emi_check.py`.
  - `parts/<MPN>.yaml`: one datasheet card per IC or critical passive.
  - `BOARD.md`: purpose, decisions and why (current state at the top), floorplan, commands, routing review, pitfalls.
  - `PARTS-REVIEW.md` (findings A/B/C), `drc-waivers.csv`, `frozen-routes.json` when router results are kept.
  - the KiCad project, generated: edit the generators named in `board.yaml`, not the KiCad files.
- `hardware/` root: `REQUIREMENTS*.md`, `ARCHITECTURE.md` (boards, interface pin table), `FIRMWARE-RULES.md`, `GATES.md`,
  `REVIEW-<date>.md`, `PLAN.md`, `ORDER*.md`.
- `hardware/calc/`: board-neutral check scripts; each takes the board folder. `hardware/tools/`: pipeline and fab helpers.
  `hardware/gen/`: generators and their kit. `hardware/rules/`: fab rules and custom DRC files.
- `.claude/skills/`, `.claude/agents/`: this kit. Start every task by reading `BOARD.md` and `board.yaml` of the board.

## Working with the engineer
- The engineer decides topology, part, chemistry, outline, cost trade-offs. You research, build, review and bring options
  with cost per unit; never change a decision silently. End each round with the numbered open decisions.
- Finish what you start: fully routed and DRC clean, a complete review round, not "N items left, next step X". When a
  step is blocked, experiment in the same turn, name the concrete blocker and its evidence, try the next route.
  Stop only for a decision that is the engineer's.
- A tooling detour (a binding quirk, an undocumented file format) gets a few tries, then the simpler route (a plain file
  the gate reads, a step the human does) and a note.
- Cost drives the design: show cost per finished unit whenever a choice changes it; Basic fab parts first.
- Commit rhythm: ask once; the default is a commit per finished step on a work branch (never the default branch), gate and
  privacy check first. Push when the engineer wants the history on the remote.
- Questions: only those that block, in one round, with a recommended default for each.

## Changing a decision (review; gate)
- A change of part, chemistry, value, pin, board partition or outline is not done until every copy is updated: search the
  repo for the old name and value: profile, `BOARD.md`, requirements, architecture, order notes, firmware rules, calc
  scripts, generator comments and notes, `CLAUDE.md`, `README`, plan files, skills' examples.
- Entry documents (`CLAUDE.md`, `README`, `PLAN`) are updated in the same step as a split, rename or status change; helper
  agents propose their wording, the owner applies it.
- Hidden copies are constants in scripts (a nominal voltage, a threshold): read the calc scripts the change touches.
- Docs state what the netlist does (pull-up targets, pin map, enable defaults). When they differ, the netlist wins and the
  doc is fixed; a contradiction between two docs is a question for the engineer.
- Old decisions stay as dated history; the current state sits at the top of `BOARD.md`.
- KiCad's GUI rewrites `.kicad_pro` and `.kicad_prl` when a project is opened. Commit such a change only if it changes a
  setting on purpose; otherwise restore it before a clean-tree step (fab package).

## Rule: numbers come from scripts
- Any check with a number (distance, impedance, voltage, current, timing, length, stock, cost) runs a script. Never
  estimate in the reply. Look in `hardware/calc/` first; if nothing fits, write a script and keep it.
- A script:
  - takes `hardware/<board>`; reads inputs from the profile; hard-codes nothing about a board
  - prints one row per check: `OK`, `WARN`, `FAIL` or `MISSING` and the numbers used; ends with `<name>: OK|FAILED`
  - exits non-zero on `FAIL`; `MISSING` = an input is `null` in the profile (fill it from the source, never guess)
  - reports `WARN` when an input has no source; names the source of each formula and limit in a comment
  - gives every row that encodes a requirement a FAIL threshold from `REQUIREMENTS`; a row without one passes while the
    requirement is broken (a gate printed OK at 5.9 days of autonomy against 7 required)
  - has a `--selftest` with one known answer when the formula is not trivial
  - uses the standard library, numpy/scipy and the `.kicad_pcb` reader `calc/pcb.py`; no new framework
- Add the script to the gate's calc list (`BOARD.md` names it) so it runs every time.
- Existing: `bom_check` (BOM, fees, stock), `power_budget` (sleep, autonomy, solar), `buck`, `rail_switch` (inrush, bleed),
  `i2c_bus`, `track_width`, `impedance`, `critical` (layout constraints), `emi_check` / `power_route_check` (routed
  board), `pcb` (reader). Candidates: length/skew groups, DDR timing, crystal load caps, LDO dropout, regulator dissipation.

## Vocabulary
| Term | Meaning |
|---|---|
| board profile | `hardware/<board>/` as above |
| generator | script that writes the KiCad schematic or board; the only place to edit them |
| net intent | the generator's net list; the net-intent check compares it with KiCad's netlist |
| datasheet card | `parts/<MPN>.yaml`: values with `section`; `null` + `section: null` = not read yet; `null` + `section: not stated` = datasheet silent |
| fab part number | the fab's stock number (JLCPCB: LCSC, key `lcsc`); empty = not assembled |
| basic part | fab library part without a setup fee (JLCPCB: Basic or preferred Extended) |
| alternate | substitute fab part number in `board.yaml` `alternates`, with a `note` of what else changes |
| critical block | parts and nets with a layout constraint in `critical.yaml` |
| `switcher_loop` / `feedback` / `decoupling` / `series_termination` / `diff_pair` / `thermal_distance` | `critical.yaml` keys: smallest regulator loop; FB divider at the pin; cap at the supply pin; series R at the driver; pair on one layer with impedance, skew, vias; heat source to sensor distance |
| return path | continuous reference plane under every signal (review) |
| keepout | no-copper area (antenna, shell, thermal island) as a DRC rule area (review) |
| gate | the board's check command; must print OK before commit and order |
| waiver | accepted ERC/DRC warning with a reviewer's reason in `<board>/drc-waivers.csv`; errors never |
| known deviation | `known:` text on a constraint: accepted this revision, shown as WARN, with the fix |
| locked copper | tracks and vias drawn by the generator (hand-drawn or frozen router results); the router keeps them |
| frozen route | a router result kept in `frozen-routes.json` and replayed as locked copper, so rebuilds are repeatable |
| UNVERIFIED | a value or pin map taken from a substitute document or not read; listed in the bring-up list |
| stack | boards joined by a keyed header with identical outline, holes and header position (`stack_check`) |

## Gate command
- OK means every check ran. A gate OK with `SKIP` lines (no KiCad installed) has not run ERC/DRC: rerun with KiCad first.
- `WARN` passes; `FAIL` and order-time `MISSING` stop.

## Public repositories
- Never commit personal data: network names, passwords, tokens, hardware addresses, host names, LAN addresses, serial
  ports, home paths, order or account data, photos of people or the home.
- Run the privacy check before every commit that will be pushed and before a push; fix findings, do not suppress them.
- Git-ignore generated files that carry paths: exported netlists, `*.kicad_prl`, fab output, downloaded tools. Check silk
  text and metadata of every new binary export before it is committed or uploaded.
- Search queries and URLs sent to outside services hold technical terms only.
- Downloads are untrusted: each in its own new folder, scripts kept elsewhere, Python reading them run with `-I`.

## Review and delegation
`hw-review`: roles, protocol, research prompts, agents. Humans: KiCad review, fab placement preview, payment, order.

## Writing hardware skills (KISS)
- One skill, one job. The description says when to use it; the body says how. Under ~150 lines; detail to `references/`.
- One rule per line, imperative, the reason in a few words. No part references, values, nets, paths or URLs of a board.
- Every rule names its check (script, DRC rule, gate) or says `(review)`.
- A lesson from a failure becomes a rule or a pitfall row in the skill it belongs to, with the symptom and the fix; remove
  rules that proved wrong. Use the vocabulary above; add a term here before using it elsewhere.
