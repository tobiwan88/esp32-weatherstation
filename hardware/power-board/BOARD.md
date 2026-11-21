# power-board

**State (2026-11-21):** schematic generated (phase A split from `../weatherstation-v1/`, same parts and nets); no layout,
no fab files. Gate: nets OK, ERC 0 errors 0 warnings, review checks 0, `tools/split_check.py` OK. Open: CE pull-up on
this board (PARTS-REVIEW.md A1), panel choice (5 W 6 V, not bought).

## Purpose
Charger, solar and USB input, cell and its protection. Supplies SYS to the main board over J10 (J_PWR) and takes
USB_VBUS, D+/D-, and the charger I2C/INT/CE from it. Contract and pin table: `../ARCHITECTURE.md`.

## Sheets (`power-board.kicad_sch` + 4 sheets)
| Sheet | Content |
|---|---|
| Inputs | USB_VBUS from J10 into ACFET1/RBFET1 M1/M2 (C1, R11); PV: J5, SMBJ10A D1, CM choke L3, C2, ACFET2/RBFET2 M3/M4, R12 |
| Charger | BQ25798 U3, L1, VBUS/PMID/SYS/BAT caps (table 5-1), PROG R14, ILIM R15/R16, TS R17/R18, STAT R19/D2 |
| Battery | J6, F1 PTC, TH1 NTC, HY2112-CB U6 with R60/C60/R61, M60/M61 |
| Header | J10 keyed 2x10 2.54 mm socket (hole 3 blocked, key) with the pin map note |

## Decisions
- Everything inside the board is the reviewed weatherstation-v1 circuit (reference designators kept; charger decisions
  in `../weatherstation-v1/charge-policy.md`, `usb-charger-bq25798.md`, `PARTS-REVIEW.md`).
- No 3.3 V rail here: the charger host pull-ups (CE, INT, I2C) are on the main board (ARCHITECTURE.md c).
- D+/D- come over J10 for BC1.2 detection (ARCHITECTURE.md b, engineer decision).
- 4 layers, In1/In2 GND, at most 50 x 50 mm (REQUIREMENTS-system.md 3, 7). J5, J6 and J10 hand-soldered.
- Silkscreen polarity next to the connectors (review B19/B20): J5 "PV 1+ 2-", J6 "CELL 1+ 2-" (JST PH leads are sold with both colour orders: check with a meter before plugging).
- TP3 = QON (pull low to leave ship mode or reset the system; BQ25798 datasheet QON section).

## Cost (JLCPCB Economic PCBA, 2026-11-21 first-tier prices from `tools/jlcparts.py`)
50 parts on 26 BOM lines, 7 Extended types (BQ25798, SMBJ10A, CM choke, L1 1 uH, PTC, NTC, HY2112).
Parts about USD 4.75 per board; qty 5: parts 23.73 + setup 8.18 + stencil 1.53 + Extended 7 x 3.07 = USD 54.93,
without the bare PCB, SMT joints and shipping (manual cart quote, REQUIREMENTS-system.md 10.4). Under USD 100.

## Commands
```
python3 hardware/gen/power_board.py                # regenerate sheets, bom.csv, project (never edit the .kicad_sch)
scripts/schematic-review.sh power-board            # ERC, review checks, PNGs in hardware/out/review/power-board/
python3 -I hardware/tools/split_check.py           # split proof against weatherstation-v1
python3 hardware/calc/power_budget.py hardware/power-board
python3 hardware/calc/bom_check.py hardware/power-board [--stock --qty 5]
scripts/hw-check.sh                                # gate (all boards)
```
Generator: `gen/power_board.py` (parts, nets), `gen/power_layout.py` (block drawing), shared engine `gen/boardgen.py`,
header `gen/boards_common.py`.

## Calc results (2026-11-21)
power_budget (2026-11-21, 30 min cycle): sleep sum 68.2 uA typ / 78.6 uA max (target 100), average 11.7 mA, 0.90 Wh/day,
autonomy 11.1 days (minimum 7, FAIL threshold), worst-month solar 2.10 vs 0.90 Wh/day = 2.33x. 15 min mode (USB or sun
only): 22.1 mA, 5.9 days.
track_width: Charge class 0.65 mm for 1.7 A OK. bom_check: OK, stock OK at qty 5. No MISSING rows. critical.py and
buck.py: not applicable yet (no layout; no plain buck).
