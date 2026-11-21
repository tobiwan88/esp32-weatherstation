# power-board

**State (2026-11-21):** schematic generated (phase A split from `../weatherstation-v1/`, same parts and nets); placed
(2026-11-21, section Layout, not routed), no fab files; review fixes of 2026-11-21 and the 3-sheet partition. Gate: nets OK, ERC 0 errors 0 warnings, review checks 0,
`tools/split_check.py` OK. Open: panel choice (5 W 6 V, not bought), ICHG (review B5, FIRMWARE-RULES.md).

## Purpose
Charger, solar and USB input, cell and its protection. Supplies SYS to the main board over J10 (J_PWR) and takes
USB_VBUS, D+/D-, and the charger I2C/INT/CE from it. Contract and pin table: `../ARCHITECTURE.md`.

## Sheets (`power-board.kicad_sch` + 3 sheets)
| Sheet | Content |
|---|---|
| Inputs | J10 keyed 2x10 2.54 mm socket (hole 3 blocked, key) with the pin map note; USB_VBUS from J10 into ACFET1/RBFET1 M1/M2 (C1, R11); PV: J5, SMBJ10A D1, CM choke L3, C2, ACFET2/RBFET2 M3/M4, R12 |
| Charger | BQ25798 U3, L1, VBUS/PMID/SYS/BAT caps (table 5-1), PROG R14, ILIM R15/R16, TS R17/R18, STAT R19/D2, CE pull-up R23, QON pad TP3 |
| Battery | J6, F1 PTC, TH1 NTC, HY2112-CB U6 with R60/C60/R61, M60/M61 |

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

## Layout (placement only, 2026-11-21; not routed)
Generator `gen/power_pcb.py` on the shared engine `gen/pcbkit.py`, stack geometry `gen/stack.py`, build
`tools/build_board.sh power-board`, renders in `hardware/out/review/pcb-power-board/` (git-ignored). 4 layers F.Cu /
In1 GND / In2 GND / B.Cu, 1.6 mm, JLC04161H-7628, rules `rules/jlc-4layer.json` + `rules/power-board.kicad_dru`.
Outline 50 x 50 mm. Front courtyards 21 % of the board (back-side THT bodies J5/J6 and the hole standoffs 234 mm2 more).

**Stack:** this board sits UNDER the main board (recommendation and the side-by-side alternative: `../main-board/BOARD.md`
Layout). Same outline, identical holes and J10 position (`tools/stack_check.py`). J10 = 2x10 socket, hole 3 blocked, on
F.Cu unmirrored. J5 (PV) and J6 (cell) bodies on the back (v1 decision 2026-11-01): their cables leave below the stack,
not into the 11 mm gap; base standoffs must clear the PH body and plug (about 12 mm, UNVERIFIED). The main board's
antenna overhangs both outlines; nothing of this board lies beyond the top edge (stack_check).

**Floorplan** (mm, top view):
| Area | Parts | Why (source) |
|---|---|---|
| top-left (cell corner) | J6 cell (back) at (3.3, 14), TH1 beside it, F1, U6 HY2112 with M60/M61, C60/R60/R61 | v1 cell corner (pinned 2026-11-03); TH1 29 mm from U3 and 27.5 mm from L1 (REQUIREMENTS T1/T2, min 15); far from the main board's antenna |
| left edge below | J5 PV (back) at (3.3, 27), D1 SMBJ10A at the connector, L3 choke, M3/M4 (ACFET2/RBFET2) | surge clamp at the entry; BQ25798 fig. 8-2 port 2 |
| centre-right | U3 BQ25798 at (30, 21.5) with its power stage as on v1: C9/C13 0402 on top of the PMID-SW1-GND-SW2-SYS row, L1 above them, PMID bulk C10-C12 left, SYS bulk C14-C18 right, BAT C19/C20, REGN/BTST/VBUS caps, ILIM/TS/PROG ring; M1/M2 (ACFET1/RBFET1) at the top of the VBUS channel; escape bands kept free | SLUSDV2C 8.4.1 (p139) items 1-7, 8.4.2 fig. 8-21; offsets routed and DRC clean on v1 |
| band y 31.7-37.8 | J10 socket pin 1 at (42, 33.5, 270): SYS at the right end next to U3's SYS side, USB_VBUS at the left end toward M1 | stack.py |
| bottom (y 38-50) | free | room for routing SYS/USB_VBUS and GND stitching |

**Holes:** H1 (3.5, 3.5), H2 (46.5, 24.0), H3 (3.5, 46.5), H4 (46.5, 46.5), M3, same as the main board.

**Checks (2026-11-21):** `calc/critical.py hardware/power-board --placement`: all rows OK (switcher loops, decoupling,
BATP R13 at 5.85 mm against the 6 mm v1 limit, TH1 distances); BC1.2 stub skew/vias SKIP (not routed). KiCad DRC: 0
errors, 0 warnings, 109 unconnected items (41 nets, no routing yet; not waived). Net classes fixed to the netlist names
(`/Charger/PV_IN`, `/Charger/USB_DP`, `/Charger/USB_DN`).

## Commands
```
python3 hardware/gen/power_board.py                # regenerate sheets, bom.csv, project (never edit the .kicad_sch)
scripts/schematic-review.sh power-board            # ERC, review checks, PNGs in hardware/out/review/power-board/
python3 -I hardware/tools/split_check.py           # split proof against weatherstation-v1
python3 hardware/calc/power_budget.py hardware/power-board
python3 hardware/calc/bom_check.py hardware/power-board [--stock --qty 5]
hardware/tools/build_board.sh power-board          # schematic, netlist, placed board, renders (no routing)
python3 hardware/calc/critical.py hardware/power-board --placement
scripts/hw-check.sh                                # gate (all boards)
```
Generator: `gen/power_board.py` (parts, nets), `gen/power_layout.py` (block drawing), shared engine `gen/boardgen.py`;
layout `gen/power_pcb.py` + `gen/pcbkit.py` + `gen/stack.py`;
header `gen/boards_common.py`.

## Calc results (2026-11-21)
power_budget (2026-11-21, 30 min cycle): sleep sum 68.2 uA typ / 78.6 uA max (target 100), average 11.7 mA, 0.90 Wh/day,
autonomy 11.1 days (minimum 7, FAIL threshold), worst-month solar 2.10 vs 0.90 Wh/day = 2.33x. 15 min mode (USB or sun
only): 22.1 mA, 5.9 days.
track_width: Charge class 0.65 mm for 1.7 A OK. bom_check: OK, stock OK at qty 5. No MISSING rows. critical.py and
buck.py: not applicable yet (no layout; no plain buck).
