# power-board

**State (2026-11-22):** schematic generated (phase A split from `../weatherstation-v1/`, same parts and nets); placed
and routed (2026-11-22, sections Layout and Routing): KiCad DRC 0 violations, 0 unconnected, all severities, no
waivers; no fab files; review fixes of 2026-11-21 and the 3-sheet partition. Gate: nets OK, ERC 0 errors 0 warnings, review checks 0,
`tools/split_check.py` OK. Open: panel choice (5 W 6 V, not bought), ICHG (review B5, FIRMWARE-RULES.md).
**2026-11-24:** R23 (CE pull-up to BAT_PACK) 1M -> 330k (C25778, engineer decision, review follow-up B2 / PARTS-REVIEW B5):
schematic regenerated, board updated value-only (`tools/sync_from_netlist.py`: Value, LCSC and symbol links; no copper
change), DRC 0 / 0 unconnected / 0 parity. Open follow-up: CE at a full cell with the GPIO released (PARTS-REVIEW B5).

## Purpose
Charger, solar and USB input, cell and its protection. Supplies SYS to the main board over J10 (J_PWR) and takes
USB_VBUS, D+/D-, and the charger I2C/INT/CE from it. Contract and pin table: `../ARCHITECTURE.md`.

## Sheets (`power-board.kicad_sch` + 3 sheets)
| Sheet | Content |
|---|---|
| Inputs | J10 keyed 2x10 2.54 mm socket (hole 3 blocked, key) with the pin map note; USB_VBUS from J10 into ACFET1/RBFET1 M1/M2 (C1, R11); PV: J5, SMBJ10A D1, CM choke L3, C2, ACFET2/RBFET2 M3/M4, R12 |
| Charger | BQ25798 U3, L1, VBUS/PMID/SYS/BAT caps (table 5-1), PROG R14, ILIM R15/R16, TS R17/R18, STAT R19/D2, CE pull-up R23 330k to BAT_PACK, QON pad TP3 |
| Battery | J6, F1 PTC, TH1 NTC, HY2112-CB U6 with R60/C60/R61, M60/M61 |

## Decisions
- Everything inside the board is the reviewed weatherstation-v1 circuit (reference designators kept; charger decisions
  in `../weatherstation-v1/charge-policy.md`, `usb-charger-bq25798.md`, `PARTS-REVIEW.md`).
- No 3.3 V rail here: the charger host pull-ups (CE, INT, I2C) are on the main board (ARCHITECTURE.md c).
- D+/D- come over J10 for BC1.2 detection (ARCHITECTURE.md b, engineer decision).
- 4 layers, In1/In2 GND, at most 50 x 50 mm (REQUIREMENTS-system.md 3, 7). J5, J6 and J10 hand-soldered.
- Silkscreen polarity next to the connectors (review B19/B20): J5 "PV 1+ 2-", J6 "CELL 1+ 2-" (JST PH leads are sold with both colour orders: check with a meter before plugging).
- TP3 = QON (pull low to leave ship mode or reset the system; BQ25798 datasheet QON section).

## Cost (JLCPCB Economic PCBA, 2026-11-24 first-tier prices, `calc/bom_check.py --stock --qty 5`)
50 parts on 26 BOM lines, 7 Extended types with a loading fee (BQ25798, SMBJ10A, CM choke, L1 1 uH, PTC, NTC, HY2112)
plus R23 330k (C25778), a JLC *preferred* Extended part without a loading fee (the offline `bom_check` without
`--stock` counts it, 8 x 3.07). Parts USD 4.76 per board; qty 5: parts 23.82 + setup 8.18 + stencil 1.53 + Extended
7 x 3.07 = **USD 55.02**, without the bare PCB, SMT joints and shipping (manual cart quote, REQUIREMENTS-system.md 10.4).
Under USD 100. History: USD 54.93 (2026-11-21 prices, R23 1M).

## Layout (placement 2026-11-21, routed 2026-11-22)
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

**Part moves for routing (2026-11-22):** C2 (VAC2 cap) to the PV_IN pin at U3 offset (-2.55, 3.95, 270); R23 (CE
pull-up, 330k since 2026-11-24) below J10.16 at (24.22, 38.4), because its BAT_PACK feed cannot cross the south band; TP3 (QON) at
(25.55, 26.15), R19 (27.8, 27.4, -90) and D2 (26.8, 29.51) pinned in FIXED, because the rule placement had put them in
the south band, where CE/SCL/SDA run.

## Routing (2026-11-22)
Two steps, both reproducible. (1) `tools/build_board.sh power-board`: `gen/power_pcb.py` places the parts and then
`gen/power_copper.py` draws the hand copper. Every coordinate comes from the placed pads, the code asserts the
orientations it needs, and all of it is locked: 245 segments, 126 vias, 3 pours. (2) `tools/route_power.sh`:
KiCadRoutingTools makes the GND plane vias on In1/In2, then routes all open nets on F.Cu/B.Cu (inside-out,
`PYTHONHASHSEED=1`). Soft keep-away: 0.6 mm from SW1/SW2 and 0.65 mm from the BC1.2 pair. A rip-up pass follows,
then `tools/finish_v1.py` and `tools/silk_fix.py`. Router copper: 230 segments, 26 vias, all of it on signal, sense
and pull-up branches: TS to TH1, INT, OD/OC/HY_CS/HY_VDD, ACDRV1/2, ACG2, ILIM, STAT/LED, the BAT_PACK feeds to R60
and R23, PV_IN to C2, USB_VBUS to VAC1 pin 9, and GND taps. Charge-class branches are routed at 0.3 mm (the neck
floor), with no neck-down.

**Hand-drawn (gen/power_copper.py):**
- **Charger stage (v1 CHARGER_COPPER port).** PMID/SYS/GND pours over the pin row. SW1/SW2: F pin stub, 2 vias,
  B.Cu 0.65 mm lane, 2 vias, L1. Bulk-cap GND vias. VBUS from pins 2/3 to C6, via to the B.Cu VBUS lane. REGN,
  BTST1/2, BATP on B.Cu to R13, ILIM, TS.
- **South band.** CE, SCL and SDA run on F.Cu from the U3 bottom row to J10.16/12/11, nested so they never cross.
  A diagonal row of escape vias serves VAC1, ACDRV2, ACDRV1 and QON. QON continues on B.Cu to TP3.
- **BC1.2 pair** (see the review below).
- **Inputs.** USB_VBUS: B.Cu 0.8 mm from J10.19/20 to M1. VBUS node between M2/M4 and C7/C8, then to the lane.
  ACF1/ACF2_MID at 0.8 mm. PV: J5 to the D1 clamp (1.0 mm, both pins), then L3, then M3. PV_N_RAW on B.Cu.
  L3.3 GND by 2 vias.
- **Battery.** BAT_CON on B.Cu around J6.2 to F1. BAT_N at 0.65 mm to M60 with the U6 VSS tap and the C60 return.
  PB_MID at 0.8 mm. M61 GND by 3 vias. BAT_PACK trunk at 1.0 mm along the north edge from F1 to C20. SYS: 4 vias
  between the SYS bulk caps, then B.Cu 1.0 mm to J10.1/2. THT pad landings end on the copper ring, not on the drill
  centre.
- **Own GND vias** at the decoupling and divider returns: C1, C2, C5, C6, C7, C8, C19, C20, C21, R18, R61, TH1. There
  was no spot for R14.2 or R16.2, so the planes router feeds them.
- **Edge fence:** 58 GND vias on a 3 mm pitch at 0.9 mm inset, plus the nearest legal spots beside each hole keepout.

**Widths** (`calc/power_route_check.py`, widest path pad to pad; IPC-2221 asks 0.62 mm for 1.7 A at 10 C,
`calc/track_width.py`). Every power branch is at least 0.6 mm except these short necks:
- VBUS to U3 pins 2/3: 0.3 mm over 1.63 mm. Pin pitch 0.4 mm; two pins in parallel.
- VBUS between the C7/C8 GND pads: 0.5 mm over 1.65 mm.
- SW pin stubs: 0.3 mm over 0.55 mm.
- BAT pins to C19: 0.3 mm over 0.25 mm.

**Weakest neck:** 0.3 mm over 1.63 mm (VBUS C7 to U3.2). Power paths use 0.6 mm vias (0.3 drill).

## Routing review (EMI and best practice, 2026-11-22)
Numbers are from `calc/power_route_check.py hardware/power-board`. It runs every `calc/emi_check.py` row with
`emi.yaml`, plus the charger rows.

**BQ25798 stage against SLUSDV2C 8.4.1 and figure 8-21:**
1. PMID/SYS caps C9/C13 (0402) sit on the pin row, with copper paths pin to cap to GND pin 27.
   - Hot loop areas: 1.19 / 1.21 mm2 (pad-centre polygon), perimeter 4.6 mm.
   - Loop path: cap to VIN 1.5 mm, VIN to GND pin 0.9 mm, GND to cap 1.8 mm, total 4.2 mm, 0.21 mm above In1.
2. L1 is not on the pins as in figure 8-21. It sits 3.93 mm away beyond the caps (v1 topology). SW goes through vias
   under the IC and a B.Cu lane.
   - SW copper: tracks 9.44 / 9.65 mm2 (F 2.2 + B 7.3), pads 2.25 mm2, 5 vias each.
   - Limit 10 mm2, a recorded deviation: figure 8-21 would give about 2 mm2.
3. REGN C5: 2.53 mm.
4. VBUS C6: 1.42 mm. C7/C8 each have their own GND via.
5. BAT C19: 2.80 mm.
6. BATP runs on B.Cu, 0.6 mm from the SW2 bootstrap lane. Its via under the body is 0.33 mm from SW2 (pin field).
   TS stays out of the 0.6 mm SW zone (parallel run 0).
7. Bootstraps: C3 at 1.80 mm. C4 at 2.70 mm, fed from the SW2 lane through a via in R14's pad gap. That shortened the
   SW2 copper from 12.3 to 9.65 mm2.

**PV filter order:** J5, then D1 (clamp at the connector, both legs 1.0 mm), then L3 (CM choke), then M3, then M4.
Neither PV_RAW nor PV_N_RAW has a branch before D1.

**BC1.2 pair** (J10.7/8 to U3.6/7, BC1.2 detection; a stub of the main board's USB bus):
- Geometry: one F.Cu pin stub and one via per line under U3, then a coupled pair on B.Cu. W 0.27, S 0.15 (pitch
  0.42), 90.6 ohm with mask (`calc/impedance.py`).
- Length: 18.10 / 18.10 mm (19.63 with via barrels). Skew 0.00 mm (DP has 2 meander bumps; limit 0.5). 2 vias.
- Round trip: 226 ps against a 4 ns full-speed edge (5.7 %, lumped; USB 2.0 7.1.2.1 rise time 4 to 20 ns).
- Spacing: other nets at least 0.60 mm outside U3's pin field (rule area `bc12_fanout`). GND stitch vias 0.6 mm
  off the pair edge.
- Crossings: TS, CHG_INT and REGN cross the pair on F.Cu. They start east of it and end west of it, and both GND
  planes lie between. Waived as `known:` in `emi.yaml`; `emi_check.py` alone prints FAIL.
- Inside the pin field, the DP via sits 0.26 mm from the SW1 lane end.

**Crosstalk:**
- CHG_INT 0.62 mm from SW2 (via), USB_DP 3.0, USB_DN 3.2, CE 5.9, SCL 6.3, SDA 8.6 mm, against a limit of 0.6 mm
  and 3x width. Parallel runs within 0.6 mm: 0.
- Closest nets to SW: VBUS 0.52 mm (B.Cu), BAT_PACK 0.55 mm, SYS 0.62 mm, PMID 0.64 mm. These are power nets with
  low impedance.

**Planes and stitching:**
- In1/In2 are solid GND with antipads only.
- No signal runs over a plane void (longest 0.00 mm).
- Edge fence gap at most 5.0 mm outside the hole keepouts. Pitch 3 mm, `layout.stitch_pitch_mm`.
- Via-to-edge rule: 0.35 mm.
- Vias in SMD pads: 0 (rule `no via in SMD pad`).
- Acid traps: the router uses 45-degree corners and none were seen in the renders. No script checks for them.

**J10 escapes:** SYS on B.Cu (1.0 mm) to pin 1 plus an F joiner to pin 2. USB_VBUS on B.Cu (0.8 mm) to pin 19 plus
an F joiner to pin 20. CE/SCL/SDA come down the column gaps on F.Cu. The DP/DN pair comes down between J10.9 and
J10.7.

**Kelvin sense:** BATP has its own track from U3.18 to R13.2 on B.Cu. HY2112 CS reaches R61 through its own branch
(router), and VDD has R60/C60 at U6 (C60 return to M60's source pad). TS goes to R18/R17 on F.Cu, then on to TH1.

**Residual risks:**
- SW area is about 4.5x the figure 8-21 layout (B.Cu lane, covered by In2 only on its plane side; the board bottom
  faces the enclosure).
- TS to TH1 is long (about 70 mm, router, around the north edge). It is a DC NTC divider, slow and away from SW,
  but it is an antenna for Wi-Fi bursts from the main board above. Consider 100 nF at TS if bench noise shows.
- The DP via is 0.26 mm from SW1 under the IC.
- Routed I2C and INT are long because they have to come around the pair (INT about 40 mm).

**Unverified:** thermal rise of the 0.3 mm pin necks (short, so the heat spreads); BC1.2 detection with this stub on
real hardware; SW ringing and EMI (no measurement); standoff height clearance of J5/J6 (see Stack).

**Checks (2026-11-22, routed):**
- `calc/critical.py hardware/power-board`: all rows OK. BC1.2 skew 0.00 mm, 2 vias.
- `calc/power_route_check.py`: OK, 1 known WARN.
- `calc/impedance.py`: 90.6 ohm OK.
- `calc/track_width.py`: OK.
- KiCad DRC with zones refilled and schematic parity: 0 violations, 0 unconnected, 0 footprint errors.
- Renders: `annot_board/charger/cell/j10.png`, `render_top/bottom.png` in `hardware/out/review/pcb-power-board/`.

## Commands
```
python3 hardware/gen/power_board.py                # regenerate sheets, bom.csv, project (never edit the .kicad_sch)
scripts/schematic-review.sh power-board            # ERC, review checks, PNGs in hardware/out/review/power-board/
python3 -I hardware/tools/split_check.py           # split proof against weatherstation-v1
python3 hardware/calc/power_budget.py hardware/power-board
python3 hardware/calc/ce_pullup.py hardware/power-board    # CE pull-up cases with the main board (R20) and alone (gate hook 30)
python3 hardware/calc/bom_check.py hardware/power-board [--stock --qty 5]
hardware/tools/build_board.sh power-board          # schematic, netlist, placed board + locked hand copper, renders
hardware/tools/route_power.sh                      # planes, router (seed 1), finish, DRC summary (in place)
# value-only schematic change (same footprints and nets) on the routed board, no rebuild (2026-11-24, R23 330k):
#   kicad-cli sch export netlist -o hardware/power-board/power-board.net hardware/power-board/power-board.kicad_sch
#   $KICAD_PYTHON hardware/tools/sync_from_netlist.py hardware/power-board/power-board.net hardware/power-board/power-board.kicad_pcb
python3 hardware/calc/critical.py hardware/power-board
python3 hardware/calc/power_route_check.py hardware/power-board   # emi_check rows + loops, widths, SW spacing
uv run --package weatherstation-hardware python hardware/calc/impedance.py hardware/power-board
kicad-cli pcb drc --refill-zones --severity-all --schematic-parity hardware/power-board/power-board.kicad_pcb
scripts/hw-check.sh                                # gate (all boards)
```
Generator: `gen/power_board.py` (parts, nets), `gen/power_layout.py` (block drawing), shared engine `gen/boardgen.py`;
layout `gen/power_pcb.py` + `gen/pcbkit.py` + `gen/stack.py`, hand copper `gen/power_copper.py`;
header `gen/boards_common.py`.

## Calc results (2026-11-24)
power_budget (2026-11-24, 30 min cycle, R23 330k): sleep sum 74.7 uA typ / 85.1 uA max (target 100; was 68.2 / 78.6 with
R23 1M), average 11.8 mA, 0.90 Wh/day, autonomy 11.1 days (minimum 7, FAIL threshold), worst-month solar 2.10 vs 0.90
Wh/day = 2.33x. 15 min mode (USB or sun only): 22.1 mA, 5.9 days.
ce_pullup (2026-11-24): alone high above BAT 1.63 V; both boards +3V3 dead CE = 0.752 x BAT, high above 1.73 V (2.06 V
with 1 uA leakage); GPIO released with +3V3 up 2.15-3.59 V (3.64 V at 3.75 V): WARN against the 3.6 V abs max; CE low
9.70 uA at 3.2 V.
track_width: Charge class 0.65 mm for 1.7 A OK. bom_check: OK, stock OK at qty 5. No MISSING rows. critical.py:
routed, all OK (2026-11-22). buck.py: not applicable (no plain buck).
