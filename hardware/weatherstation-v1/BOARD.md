# weatherstation-v1: board notes

Board-specific facts for the board-neutral skills (`hw-base`, `kicad-schematic`, `kicad-layout`, `hw-parts`).
Numbers the scripts check live in `board.yaml`, `critical.yaml` and `parts/`. Full requirements: `REQUIREMENTS.md`.
BOM: `bom.csv` (JLCPCB columns plus Class/Status/notes). Order checklist: `ORDER.md`.

## Board
Solar + USB-C powered ESP32-S3 air-quality weather station, about 50 x 45 mm, 4 layers (In1 and In2 both solid GND),
JLC04161H-7628, JLCPCB Economic PCBA (one side, SMT; connectors J5/J6/J7 and the battery are hand-soldered).
ESP32-S3-WROOM-1-N8 (C2913198), AP2112K 3.3 V LDO, CN3791 solar MPPT charger, TP4056 USB charger, one protected 18650,
switched 3V3_SW sensor rail (Q2), SEN66 on a GH connector (PM, CO2, T/RH, NOx index), SHT45 off-board on a Qwiic cable in a
radiation shield, spare Qwiic port. USB-C = programming, debug (native USB-JTAG) and charging.
Status: pre-layout. No generators or KiCad files yet.

## Commands
- Gate: `scripts/hw-check.sh [--strict] [--stock --qty N]`: profile files parse, `calc/bom_check.py`, `calc/power_budget.py`
  (and `calc/critical.py` once a routed `.kicad_pcb` exists). Must print `hardware checks: OK` before commit and order.
  `MISSING` rows are open inputs (fill them from the source); `--strict` (order time) makes them fail.
- BOM only: `python3 hardware/calc/bom_check.py hardware/weatherstation-v1 [--stock] [--qty 5] [--strict]` (`--stock` needs network).
- Power/charger/energy: `python3 hardware/calc/power_budget.py hardware/weatherstation-v1` (`--selftest` for the formulas).
- Stock and price of one part: `python3 hardware/tools/jlcparts.py C123456` or `-s "keyword" -n 20`.
- Reference pipeline (schematic generator, placement, KRT routing, fab package) from desk_notifier: `hardware/reference/desk_notifier/`
  (copy and adapt, see `hardware/PLAN.md`; the board-neutral skills assume that layout).

## Decisions (why)
- 4 layers with two solid GND planes (user requirement): EMC, thermal spreading, one cheap tier under 50 x 50 mm.
  Power is distributed on the outer layers. Two adjacent GND planes give no plane capacitance: a GND/PWR/GND stackup is the fallback.
- LDO (AP2112K), not a buck: the load is a few mA average and the rail only needs to hold 3.15 V for the SEN66; battery usable 3.5-4.2 V (cutoff 3.5 V).
  `calc/power_budget.py` reports the dropout headroom at the cutoff.
- Two chargers on one cell: CN3791 (solar MPPT) and TP4056 (USB). USB has priority by hardware (Q4 pulls the CN3791 MPPT pin low
  while VBUS is present), so they never fight. Q3/Q5 (firmware CHG_INH) stop both when the cell is cold; default (MCU off) = charging allowed
  so a flat cell recovers. The CN3791 has no temperature pin; the TP4056 TEMP pin is grounded (its fixed NTC window does not fit).
- Battery path: Q1 (P-FET with gate = VBUS) isolates the cell from the rail while USB is plugged in; D3 feeds the rail from USB.
  The cell is charged only by U3/U6, never through D3.
- SHT45 off-board in a radiation shield: board heat (charger, LDO, SEN66 fan) cannot bias outdoor T/RH.
- Sensor rail switched by Q2 (P-FET, pull-up gate = off in deep sleep); I2C pull-ups on 3V3_SW so nothing is back-powered.
- NO2 not on this revision (electrochemical cell is 2 years life, ozone cross-sensitivity, about 130-300 EUR); J4 Qwiic is a spare port.
- ESD/EMC set kept pragmatic: USBLC6 on USB data and on the outdoor SHT45 I2C cable, SMBJ12A on the solar input, FB1 DNP footprint.

## Layout specifics (to carry into the layout generator)
- Antenna at a board edge with a copper keepout on all layers; 15 mm from battery and solar wiring.
- Heat corner: CN3791, L1, D2, M1, TP4056 (exposed pad on vias), AP2112K together; NTC at the cell; SEN66/SHT45 connectors on the far side.
- Solar charger switching loop minimal; no signal under L1; stitching vias every 5 mm along the edge and at every layer change.
- Keep the outline within 50 x 50 mm (`board.yaml layout.max_board_mm`).
- Test points: GND, 3V3, 3V3_SW, VSYS, BAT, MPPT; UART0 header J7 as fallback debug.

## Open before ordering
1. LCSC numbers still TBD in `bom.csv` (0.12 ohm 1206, 39k, 1M, 220 nF, NTC 10k, 3k PROG): the gate lists them as MISSING.
2. `design.panel.vmp_v` in `board.yaml` (real panel datasheet) so `power_budget.py` can check the MPPT divider.
3. Datasheet cards: fetch manufacturer PDFs, record revision and section for every value (cards were seeded from search results).
4. Class (Basic/Extended) of SS34, 100k, 4.7k, inductor, tact switch (`bom_check.py --stock` fills this in).
5. Whether JLCPCB forces Standard PCBA for the ESP32 module (check the quote).
6. SEN66 operating temperature range (winter) and the cell's low-temperature behaviour.

## Pitfalls (carried over from desk_notifier, see its PLAN.md/BOARD.md for details)
| Symptom | Cause | Fix |
|---|---|---|
| Part rotated wrong in JLC preview | rotation tables differ per footprint | correction entry in the fab package script, check ICs/connectors in the preview |
| Pin 1 or centre pad unclear | fab package name vs KiCad footprint differ | compare land patterns with the datasheet drawing |
| LDO headroom WARN/FAIL | cutoff too low for the SEN66 peak | raise `battery.vcutoff_v` or drop the load |
| Extended-part fees | each unique Extended part adds a loading fee | prefer Basic/Preferred Extended equivalents |
