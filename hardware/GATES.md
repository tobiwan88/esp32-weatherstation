# Design gates

A stage starts only when the previous gate is passed. A gate is passed when every exit check is true and the evidence is in the
repo (or named here). Open items are listed, never waived silently. Status as of 2026-11-23; update the line when a check changes.
Boards: power board (`power-board/`), main board (`main-board/`), sensor head (`sht45-board/`); the first single-board design
`weatherstation-v1/` is history: not gated, though its profile still runs in `hw-check.sh` as a regression check. Gate definitions: skill `hw-base`, templates in `hw-kit/skills/hw-base/templates/GATES.md`.

| Gate | System | Power board | Main board | Sensor head |
|---|---|---|---|---|
| 1 requirements | agreed in the interview 2026-11-21 | | | |
| 2 BOM accepted | | strict check OK | strict check OK | no profile, not covered by the scripts |
| 3 schematic | | ERC 0, nets OK, review round done | ERC 0, nets OK, review round done | ERC 0, nets OK (2026-11-04) |
| 4 placement | | done | done | done |
| 5 routing | | routed, DRC 0, checks OK; review pending | routed, DRC clean, checks OK; review pending | DRC 0 (2026-11-04) |
| 6 fab and order | | not started | not started | files built 2026-11-05 for the SHT45 design; not ordered |

## Gate 1: requirements
Source: `REQUIREMENTS-system.md` (supersedes `weatherstation-v1/REQUIREMENTS.md`).
- [x] power cycle, autonomy, budget, sensor set, ports, environment and fab limits written down (sections 2 to 8)
- [x] the engineer's decisions recorded with dates (section 9)
- [ ] every requirement numbered with a check column: the document is prose plus a decision log; autonomy, sleep current and cost
  are checked by `calc/power_budget.py` and `calc/bom_check.py`, the rest are reviewed by reading
Status: agreed in the interview of 2026-11-21. Open items: section 10 (SEN0460 bench numbers, sodium-ion cell, per-order quote,
stack against side-by-side mounting, optional sensors) and the EAQI breakpoints in section 5.1a.

## Gate 2: BOM research and acceptance
Source: `<board>/bom.csv` (generated), `calc/bom_check.py`, `tools/jlcparts.py`, datasheet cards in `<board>/parts/`.
- [x] `scripts/hw-check.sh --strict` prints OK for both boards (no MISSING rows), 2026-11-23
- [x] fab number, class, stock and price at the order quantity: `bom_check.py --stock --qty 5` OK for both boards, 2026-11-23
  (power board USD 55.00, main board USD 85.57 before bare PCB, joints and shipping; limit USD 100)
- [ ] a datasheet on file for every IC with the section cited. Known gaps: BMP580 has no public datasheet (circuit and footprint
  from the BMP581 datasheet, marked in `main-board/parts/BMP580.yaml`); the power-board choke L3 (CMF4532F-900) has a text
  specification only; the ZE25-O3 pinout on J8 and the SEN0460 are not verified (`main-board/PARTS-REVIEW.md`); sodium-ion
  parts are not chosen (`weatherstation-v1/datasheets/SOURCES.md` lists the files that are on hand)
- [ ] the real JLCPCB quote per order (bare PCB, joints, shipping): manual, not scriptable
Status: BOM checks pass; the datasheet gaps and the quote are open.

## Gate 3: schematic
Source: `hardware/gen/` (generators, review checks), `hardware/out/review/` (renders, gitignored).
- [x] ERC zero errors and warnings, net-intent check OK, geometry review 0 issues, `split_check` OK (power and main board)
- [x] independent review round 2026-11-21 (four reviewers): `REVIEW-2026-11-21.md`, every item DONE, OPEN or a firmware rule
- [ ] open decisions of that review answered by the engineer: B11, B13, B15, B18, B22 and follow-up B2 (see `PLAN.md`)
- [ ] the engineer's KiCad review of the schematics: not recorded
Status: generated and independently reviewed; open decisions listed.

## Gate 4: placement and Gate 5: routing
- [x] floorplan with datasheet citations in each `BOARD.md`; `critical.py` OK; stack, header and split checks OK
- [x] fully routed: power board DRC 0 at all severities with no waivers; main board DRC clean with 3 waived silk-only warnings
  (`main-board/drc-waivers.csv`); `calc/power_route_check.py` (power board) and `calc/emi_check.py` (main board) OK, run by the
  gate through `scripts/hw-check.d/20-routed-checks.sh`
- [x] Routing review section in each `BOARD.md` with the numbers and the residual risks that need a bench
- [ ] independent render review of the routed boards: not recorded
- [ ] the engineer's KiCad review of both routed boards: not recorded
Status: routed and checked by scripts; the human review is the next step.

## Gate 6: fab files and order
- [ ] clean committed tree; `tools/fab_package.py --require-clean` per board; footprint fit OK; placement preview checked
- [ ] `scripts/hw-check.sh --strict --stock --qty 5` right before ordering; JLCPCB capability page checked
- [ ] order notes per board (`<board>/ORDER.md`); the sensor head's are in `ORDER-sensor-boards.md`
Status: not started for the power and main boards. Sensor head: SHT45 files built 2026-11-05, SHT40 switch pending.

## Working rules (all gates)
- Helper agents gather; the owner checks every number that drives a decision against the source.
- Every number has a source; every gate has evidence in the repo.
