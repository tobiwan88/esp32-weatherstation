# main-board

**State (2026-11-21):** schematic generated: phase A split from `../weatherstation-v1/` (same parts and nets), then phase B
(pressure sensor U9, Qwiic J4, I2C header J11, rain/wind/vane port J12; sensor pull-ups 2.2k), then the review fixes of
2026-11-21 and the 5-sheet partition. Placement done (2026-11-21, section Layout): not routed, no fab files.
Gate: nets OK, ERC 0 errors 0 warnings, review checks 0, `tools/split_check.py` OK. Order at qty 5: USD 85.60 before the bare PCB,
joints and shipping (`calc/bom_check.py --stock --qty 5`); open decisions: PARTS-REVIEW.md, last section.

## Purpose
ESP32-S3, USB-C, 3.3 V and 5 V rails, sensor ports. Runs from SYS on J10 (power board, a bought charger module, or a
bench supply). Contract and pin table: `../ARCHITECTURE.md`.

## Sheets (`main-board.kicad_sch` + 5 sheets)
| Sheet | Content |
|---|---|
| USB | J1 USB-C, CC pull-downs R9/R10, USBLC6 U4, C35 on USB_VBUS; J10 keyed 2x10 2.54 mm male (pin 3 pulled) with the charger host pull-ups R20 (CE 1M), R22 (INT), R54/R55 (I2C) on +3V3 and the pin map note |
| MCU | ESP32-S3-WROOM-1-N8 U1, decoupling, EN/IO0 strapping, JP1/JP2, R32/R33, J7 debug UART, LEDs |
| Rails | TPS63802 U2 (SYS -> +3V3), Q40/Q41 3V3_SW switch with the R76/C48 ramp and the R78 22k bleed, TPS61023 U7 (SYS -> 5V_SW), TP1/TP2 |
| I2C | Sensor bus on 3V3_SW: J3 outdoor SHT cable (feed R77 100 ohm, USBLC6 U5 between J3 and the bus), pull-ups R50/R51 (2.2k), BMP580 U9 (0x46) with C90/C91, Qwiic J4 and 2.54 mm header J11 (GND, 3V3_SW, SDA, SCL), U8 SCD41 and C47 (DNP) |
| Sensors | UART/analog/pulse: J2 PMS7003 (R48/R49), J8 ZE25-O3 (R46/R47), J12 rain/wind/vane port with U10/U11, R70-R75, C70-C72 |

## Decisions
- Carried-over circuit and pin map are the reviewed weatherstation-v1 design (designators kept).
- USB_DP/USB_DN and SEN_SDA/SEN_SCL are joined by labels inside their blocks (as in v1); on the root, USB_DP/USB_DN
  keep labels because three sheets share them and no crossing-free wire exists (`ROOT_LABELLED` in main_board.py).
- #FLG22 marks USB_VBUS as driven (J1 and U4 pins are passive), #FLG21 marks SYS from J10.
- 4 layers, In1/In2 GND, at most 50 x 50 mm. J2, J7, J8, J10, J11, J12 hand-soldered; JP1/JP2/TP pads only.
- Silkscreen: J7 pin 1 "3V3 only" (do not feed an adapter's VCC into it); J3 "SHT", J12 "GND RAIN WIND VANE".
- Sensor bus pull-ups 2.2k (was 10k): 2 m cable + 7 devices = 276 pF, rise 514 ns < 1 us at 100 kHz; one bought 2.2k
  module pair in parallel is still inside 3 mA (`calc/i2c_bus.py`). More module pull-ups: cut their jumpers.
- Bus addresses: SHT45 0x44, BMP580 0x46, SCD41 0x62, VEML6030 0x10 (add-on; the BMP585 add-on is also 0x46: never both). Check each bought module's address.
- Pulse port J12 (JST PH 4-pin: 1 GND, 2 RAIN, 3 WIND, 4 VANE): RAIN IO15, WIND IO16 (RTC GPIO, the ULP counts in deep
  sleep), VANE IO8 (ADC1_CH7). Not strapping (0, 3, 45, 46), not USB (19/20), free in v1. Pull-ups 1M to +3V3: 3.3 uA per
  closed contact, 6.6 uA worst case = 7 % of the 100 uA sleep budget; 1k + 4.7 nF debounce: 77 Hz max (PARTS-REVIEW B6).
  Vane divider top 10k from 3V3_SW (no sleep current). USBLC6 U10 (RAIN, WIND), U11 (VANE) on the cable lines.
- Root diagram (sheets USB, MCU, Rails, I2C, Sensors): `ROOT_SIDE` puts the I2C sheet's sensor-bus pins on its left side (facing the MCU); boardgen labels each separate hand-wire group of a net.

## Cost (JLCPCB Economic PCBA, 2026-11-21 first-tier prices, `calc/bom_check.py --stock --qty 5`)
Current (BMP580 U9, review fixes incl. R78): parts USD 48.26 at qty 5 (9.65 per board), 9 Extended types (USB-C, USBLC6,
ESP32 module, TPS63802, L4, TPS61023, 1 uH, JST SH, BMP580); order at qty 5: 48.26 + setup 8.18 + stencil 1.53 + 9 x 3.07 =
**USD 85.60** before the 4-layer bare PCB, SMT joints and shipping (manual cart quote). R78 (C25768) is a Basic 0402 at
USD 0.001. Fallback if the real quote passes USD 100: hand-solder J3/J4 (engineer 2026-11-21, not applied).
History: phase A USD 73.16; phase B with the BMP585 USD 96.95 (review A5, replaced by the BMP580).

## Layout (placement only, 2026-11-21; not routed)
Generator `gen/main_pcb.py` on the shared engine `gen/pcbkit.py` (adapted from `gen/pcb_v1.py`), stack geometry in
`gen/stack.py` (shared with the power board), build `tools/build_board.sh main-board`, renders in
`hardware/out/review/pcb-main-board/` (git-ignored). 4 layers F.Cu / In1 GND / In2 GND / B.Cu, 1.6 mm, JLC04161H-7628,
JLC rules `rules/jlc-4layer.json` + `rules/main-board.kicad_dru`. Outline 50 x 50 mm. Front courtyards 55 % of the board
(module counted without its off-board antenna keepout, holes excluded): below the 60 % mark, no options needed.

**Stack (recommended): stacked, main board on top.** Same 50 x 50 outline on both boards, outlines on top of each other,
identical M3 holes and J10 at the same top-view position (`tools/stack_check.py`, in the gate). J10 = 2x10 2.54 mm male
header here (pin 3 pulled), 2x10 socket on the power board (hole 3 blocked); both footprints on F.Cu, unmirrored. The
male header is fitted from this board's underside (plastic body below, pins soldered on top: same pads in top view).
Board gap = socket + header plastic = about 11 mm (8.5 + 2.5 mm typical, UNVERIFIED for the bought parts) = standoff
length. Consequence: this board's back faces the power board, so every connector body is on the FRONT (deviation from
the v1 back-side decision; the power board keeps J5/J6 on its back). Antenna: overhangs the top edge of both boards.
Alternative: side by side with a 2x10 ribbon (keyed IDC both ends): no gap or standoffs, both boards flat in the housing,
but SYS (1 A) and the BC1.2 D+/D- stubs run through the cable (needs the 22 uF SYS cap at J10, PARTS-REVIEW B2) and the
socket side needs a male-ended cable; choose it only if the housing is flat.

**Floorplan** (mm from the top-left corner, top view):
| Area | Parts | Why (source) |
|---|---|---|
| top-right corner | U1 ESP32-S3-WROOM-1 at (40, 6.75), antenna up and fully off the board | HW design guidelines 1.4.7 (p30-31) fig. 24 position 3 (feed point right, as on the WROOM-1 meander, module datasheet fig. 10-1 p42); module datasheet 11.2; antenna keepout (local y < -6.75) outside the outline as on v1; 1.2 mm strip below the antenna edge without copper or vias on any layer (rule area `antenna_strip`) |
| left edge, level with the module's USB pins | J1 USB-C at (3.4, 12, 270) (face 0.3 mm past the edge, as v1), U4 ESD at the receptacle, C35, R9/R10 at CC, R32/R33 22 ohm at U1 pins 13/14 | guidelines 1.4.8: series R at the chip, pair short and straight; free lane y 10.3-12.7 reserved for the pair; J1 shell rule area `j1_shell` |
| top edge, left (cool) | J3 SHT45 cable (SH horizontal, opening up) at (12.8, 3.4) with U5 ESD, R77, pull-ups R50/R51 | outdoor cable: ESD at the connector; 14 mm from the antenna's left end (Espressif 15 mm clearance is for the housing; flag) |
| left edge | J4 Qwiic (SH, opening left) at (3.4, 23.5); J11 2.54 I2C header at (3.3, 30.6) | I2C cables leave left/top |
| interior left | U9 BMP580 at (13, 22): 11.8 mm from the left edge, 22 mm from the top, 21 mm from H1, 26 mm from H3, 18 mm from U1's body; C90/C91 at its pins; rule area `bmp580_body` (no tracks/vias on F.Cu/B.Cu, no pour) | BMP581 DS004-13 8.2 (p69) no vias/traces under the part; BMP5xy handling note HS000-00 3.2 (p6), 7.1 (p13): not near an edge, hot spots, the MCU or anchor points (holes), fig. 8/9. The task asked "near an edge"; the datasheet says not near an edge: followed the datasheet |
| lower left | U8 SCD41 (DNP option) at (11, 37) | cool side, 15 mm from U9, 21 mm from U7 and 29 mm from U2 (critical.yaml) |
| centre-left | Q40/Q41 3V3_SW switch with R40-R42, R76, C48, C42/C43/C47, R78 | between +3V3 (U2) and the sensor side |
| right, under the module | U2 TPS63802 block at (38.5, 26.5), U7 TPS61023 block at (29.5, 26.5), both above J10 pin 1/2 (SYS) | SLVSEU9D 12.1/12.2 fig. 12-1 and SLVSF14B 10.1/10.2 fig. 10-1, offsets as v1 (routed there); B.Cu keepout under L4/L5 (REQUIREMENTS E3) |
| band y 31.7-37.8 | J10 pin 1 at (42, 33.5, 270): pin 1/2 SYS at the right end, 19/20 USB_VBUS at the left end, 7/8 D+/D- at x 34.4 | same position on the power board (stack.py) |
| bottom edge | J12 wind/rain/vane PH4 at (9.2, 46.5) with U10/U11 ESD and R70-R75/C70-C72 above it; J8 ZE25-O3 PH7 at (26, 46.5) with R47; J7 debug UART under J10 | outdoor cables leave downward |
| right edge between H2 and H4 | J2 PMS7003 2x5 1.27 at (45.5, 29.5); TP1 (+3V3), TP2 (SYS) beside it | PM cable; test points reachable from the top (main board is the top board) |

**Holes** (same on both boards, `gen/stack.py`): H1 (3.5, 3.5), H2 (46.5, 24.0), H3 (3.5, 46.5), H4 (46.5, 46.5), M3
(ISO 7380 head, 3.2 mm copper keepout). H2 is pulled down under the module, so the pattern has no mirror or 180-degree
symmetry (stack_check). Courtyards: big parts by hand (FIXED), small parts by `place_near` next to their pins (courtyards
never overlap, 0.35 mm halo except the decoupling and termination parts).

**Checks (2026-11-21):** `calc/critical.py hardware/main-board --placement`: all placement rows OK (switcher loops, FB
dividers, decoupling, series R, thermal); FB trace length and USB skew/vias SKIP (not routed). KiCad DRC (all
severities, schematic parity, project rules): 0 errors, 4 warnings `silk_edge_clearance` (J1 and U1 silkscreen cross
the edge: both overhang on purpose; JLC clips silk at the edge), 205 unconnected items (52 nets, no routing yet; not
waived). `tools/stack_check.py`: OK.

**For the reviewer, first:** the stack direction (connectors on the front here, back on the power board); U9 position
against the "near an edge" wish; J3 14 mm from the antenna end; the module's right pad column 0.5 mm from the right
edge (pins 28-40 must leave by vias under the module); BC1.2 stubs from the pair down to J10 pins 7/8 (about 16 mm).

## Commands
```
python3 hardware/gen/main_board.py
scripts/schematic-review.sh main-board
python3 hardware/gen/pins.py --board main_board MCU U1      # pin/net listing of a part
hardware/tools/build_board.sh main-board                    # schematic, netlist, placed board, renders (no routing)
python3 hardware/calc/critical.py hardware/main-board --placement
python3 -I hardware/tools/stack_check.py                    # J10, holes and outline line up with the power board
python3 hardware/calc/power_budget.py hardware/main-board
python3 hardware/calc/bom_check.py hardware/main-board [--stock --qty 5]
scripts/hw-check.sh
```

## Calc results (2026-11-21)
power_budget: buck-boost input at cutoff 2.30 V vs 1.3 V minimum, OK (path 0.17 ohm incl. J10, assumption).
track_width: Power class 0.65 mm for 1.7 A OK. bom_check: OK, stock OK at qty 5. No MISSING rows.
i2c_bus: rise 514 ns (limit 1000), pull-up strength 2.64 mA with one 2.2k module (limit 3), pulse leakage 6.6 uA (7 %),
pulse edge 77 Hz (need 42). Inputs marked `assumption` (cable pF/m and length, anemometer rate) need a measurement.
