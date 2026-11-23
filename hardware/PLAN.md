# Hardware plan

State 2026-11-23. Goal: outdoor solar + USB air-quality and weather stations (own use, Home Assistant over MQTT), built as a power
board, a main board and a sensor head, JLCPCB-assembled, with the generator-driven KiCad pipeline and human checkpoints
(`GATES.md`). Requirements: `REQUIREMENTS-system.md`. Board status: `README.md`.

## Done
- Research and requirements v2, agreed in the interview of 2026-11-21 (`REQUIREMENTS-system.md`); the single-board design in
  `weatherstation-v1/` stays as history (its requirements, parts review and charger notes are background).
- Split into a power board and a main board with a keyed header (J10), proven by `tools/split_check.py` (every v1 part and net
  exactly once), `tools/header_check.py` (wrong matings) and `tools/stack_check.py` (outline, holes, header pads).
- Schematics of both boards, an independent four-reviewer round on 2026-11-21 (`REVIEW-2026-11-21.md`: every item DONE, OPEN or
  firmware rule), and the fixes of that round.
- Placement and routing of both boards (2026-11-21 and 2026-11-22): KiCad DRC clean, `critical.py` and the routed EMI checks OK
  (`scripts/hw-check.d/`), a Routing review section in each `BOARD.md`.
- Sensor head board (SHT45 design) and two Qwiic add-on boards (pressure, light), DRC clean. The add-ons are retired as ordered
  designs; pressure moved to the main board.
- Firmware rules the hardware depends on, with one BQ25798 register plan: `FIRMWARE-RULES.md`.
- Reusable hardware kit `../hw-kit/` (skills, agents, scripts, templates).

## Next (proposed order; the engineer decides)
1. Decide the open items that change a board: SHT40 against SHT45 for the sensor head; the items still OPEN in
   `REVIEW-2026-11-21.md` (B11 current limit on the other cable outputs, B13 inductor saturation margin, B15 pulse port, B18
   USB-only operation of the main board, B22 cable capacitance, follow-up B2 the CE divider case, also in `ARCHITECTURE.md` d);
   stack against side-by-side mounting; and the hand-soldering fallback for the Qwiic connectors if the quote exceeds USD 100.
2. The engineer's KiCad review of both routed boards (gate 5). The independent render review of the routed boards is not recorded.
3. Order notes for the power board and the main board (`<board>/ORDER.md`, skill `hw-fab-order`), then fab files per board with
   `tools/fab_package.py --require-clean` on a clean committed tree, and the placement preview check.
4. A real JLCPCB quote per order against the USD 100 limit (bare PCB, joints and shipping are not computable offline), and a
   stock check right before ordering: `scripts/hw-check.sh --strict --stock --qty 5`.
5. Order and bring-up in the order of `REQUIREMENTS-system.md` section 8: main board alone on USB and a bench supply on SYS, then
   the power board with a cell (never feed a bench supply into SYS of a power board with a cell fitted), then the sensors.
6. Firmware (`../firmware/`, ESP-IDF): deep-sleep cycle, charger setup per `FIRMWARE-RULES.md`, sensor drivers (SEN0460 is new),
   MQTT to Home Assistant. Measure what the budget only estimates: ESP32 ULP sleep current, SEN0460 warm-up and sleep current.
7. Later: sodium-ion cell variant (needs a readable datasheet and a matching protection IC), UV, ozone and NO2 modules after a
   bench trial, optional upload to aqicn or Sensor.Community.

## Reuse
- Board-neutral kit: `../hw-kit/` (skills, agents, calc scripts, tools, rules, templates, installer). Edit there, install with
  `hw-kit/install.sh . --force`.
- `reference/desk_notifier/`: the earlier project's generators, routing and fab scripts and its plan with lessons, kept as
  copy-and-adapt material, not active.
