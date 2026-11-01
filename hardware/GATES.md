# Design gates (weatherstation-v1)

A stage starts only when the previous gate is passed. A gate is passed when every exit check is true and the evidence is in the repo (or named here). Open items are listed, never waived silently.

## Gate 1: requirements
Source: `weatherstation-v1/REQUIREMENTS.md`.
Exit checks:
- [ ] every requirement has a number, a source or a stated assumption, and a test or check that proves it
- [ ] power, temperature range, sensor set, enclosure, outdoor use and the fab limits (4 layers, at most 50 x 50 mm) are written down
- [ ] the user has accepted the list
Status: document exists. Not yet accepted in this gate. Decision for the user: accept REQUIREMENTS.md as it stands.

## Gate 2: BOM research and acceptance
Source: `weatherstation-v1/bom.csv` (generated from `hardware/gen/weatherstation_v1.py`), `bom_check.py`, `hardware/tools/jlcparts.py`, datasheets in `weatherstation-v1/datasheets/` (PDFs git-ignored, sources in `datasheets/SOURCES.md`).
Exit checks, for every BOM line:
- [ ] LCSC number present, class (Basic/Extended) and stock checked, unit price noted
- [ ] a datasheet is on file, and the values the design uses are read from it (section cited)
- [ ] footprint checked against the datasheet land pattern
- [ ] `hw-check.sh --strict` prints OK
Status: open. Parts and circuit review done 2026-11-01: `weatherstation-v1/PARTS-REVIEW.md`. All seven A findings
decided and applied 2026-11-01: A1-A3, A6 (SMBJ10A, 6 V 10 W panel, 3 A choke), A7 (CE pull-up to +3V3), A4 (two I2C buses:
charger IO4/IO5, sensors IO13/IO14) and A5 (TPS61023 5 V boost on GAS_VCC, EN from IO12). B items still open.
Datasheets: not found for Littelfuse SMBJ10A (C151250; LCSC link in jlcparts), CMF4532F-900 page, ST USBLC6-2SC6, CBAK 26700LT, TDK VLS252010HBX-1R0M-1 (exact suffix).
Not the maker's own file: Murata NCP18XH103F03RB, Hroparts TYPE-C-31-M-12. L4 is a Sunlord part (note fixed in the review).

## Gate 3: schematic
Source: `hardware/gen/` (generator, layout, review checks), `hardware/out/review/` (PNG review output, git-ignored).
Exit checks:
- [ ] ERC: zero errors and zero warnings (`scripts/schematic-review.sh`)
- [ ] net-intent check OK (netlist equals NETS)
- [ ] geometry review (`hardware/gen/review_checks.py`): no issue
- [ ] image review: every PNG read, findings in `hardware/out/review/review-notes.md`, all fixed or listed as open
- [ ] root overview: every sheet box connected by wires to the boxes it shares nets with
- [ ] no net on `UNWIRED` without a reason in `BOARD.md`
Status: in progress (2026-11-01, drawing rework).
- ERC 0; net-intent OK; `scripts/check.sh` OK.
- Geometry review: 0 issues. Root page: pins of two-sheet nets aligned across facing boxes (straight wires); only USB_DP/DN
  (three sheets) keep labels, placed outside the boxes.
- Rails are power symbols; wires inside blocks, labels between blocks. Unwired clusters 63 -> 8 (listed in BOARD.md).
- Image review: findings in `hardware/out/review/review-notes.md`.
- All A and B findings decided and applied (2026-11-01). Project footprints for U2, L1/L5, L4 from maker drawings.
- Image review 2026-11-01 (final): every page read; power stage, PV entry, battery protection and sensor bus hand-drawn.
  Open drawing items: only the labelled clusters listed in BOARD.md.

## Working rules (all gates)
- A subagent does research and gathering (datasheets, stock, application notes). The owner checks every number against the source before it goes into a design file.
- Every number has a source; every gate has evidence in the repo.
