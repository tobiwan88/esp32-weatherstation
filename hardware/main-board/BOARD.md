# main-board

**State (2026-11-21):** schematic generated: phase A split from `../weatherstation-v1/` (same parts and nets), then phase B
(pressure sensor U9, Qwiic J4, I2C header J11, rain/wind/vane port J12; sensor pull-ups 2.2k), then the review fixes of
2026-11-21 and the 5-sheet partition. Placement done (2026-11-21, section Layout); routed 2026-11-22 (sections Routing,
Routing review): DRC clean, no fab files yet. 2026-11-24 (engineer): status LEDs D10/D11 are side-view red LTST-S270KRKT
(C125114) at the right board edge; only the LED nets were re-placed and re-routed (section Status LEDs).
Gate: nets OK, ERC 0 errors 0 warnings, review checks 0, `tools/split_check.py` OK. Order at qty 5: USD 88.91 before the bare PCB,
joints and shipping (`calc/bom_check.py --stock --qty 5`); open decisions: PARTS-REVIEW.md, last section.

## Purpose
ESP32-S3, USB-C, 3.3 V and 5 V rails, sensor ports. Runs from SYS on J10 (power board, a bought charger module, or a
bench supply). Contract and pin table: `../ARCHITECTURE.md`.

## Sheets (`main-board.kicad_sch` + 5 sheets)
| Sheet | Content |
|---|---|
| USB | J1 USB-C, CC pull-downs R9/R10, USBLC6 U4, C35 on USB_VBUS; J10 keyed 2x10 2.54 mm male (pin 3 pulled) with the charger host pull-ups R20 (CE 1M), R22 (INT), R54/R55 (I2C) on +3V3 and the pin map note |
| MCU | ESP32-S3-WROOM-1-N8 U1, decoupling, EN/IO0 strapping, JP1/JP2, R32/R33, J7 debug UART, status LEDs D10/D11 (side-view red, R34/R35 1k) |
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
2026-11-24: D10/D11 0603 red (C2286, Basic) -> side-view LTST-S270KRKT (C125114, Extended, USD 0.032, stock 29060):
parts USD 48.50 (9.70 per board), 10 Extended types, **USD 88.91** at qty 5 (+3.31: one more Extended fee 3.07 and
+0.24 parts). Still below USD 100 before the bare PCB.
History: phase A USD 73.16; phase B with the BMP585 USD 96.95 (review A5, replaced by the BMP580).

## Layout (placement 2026-11-21, routed 2026-11-22)
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
| right edge between H2 and H4 | J2 PMS7003 2x5 1.27 at (45.5, 29.5); TP1 (+3V3), TP2 (SYS) beside it; status LEDs D10 (49.14, 35.0) and D11 (49.14, 39.3), side view, lens out of the right edge; R34 at (48.3, 27.73) between H2 and J2 | PM cable; test points reachable from the top (main board is the top board); LEDs visible from the side of the stack (engineer 2026-11-24): the only edge strip without the antenna, a cable or a connector (section Status LEDs) |

**Holes** (same on both boards, `gen/stack.py`): H1 (3.5, 3.5), H2 (46.5, 24.0), H3 (3.5, 46.5), H4 (46.5, 46.5), M3
(ISO 7380 head, 3.2 mm copper keepout). H2 is pulled down under the module, so the pattern has no mirror or 180-degree
symmetry (stack_check). Courtyards: big parts by hand (FIXED), small parts by `place_near` next to their pins (courtyards
never overlap, 0.35 mm halo except the decoupling and termination parts).

**Checks at placement (2026-11-21, superseded by section Routing):** `calc/critical.py hardware/main-board --placement`: all placement rows OK (switcher loops, FB
dividers, decoupling, series R, thermal); FB trace length and USB skew/vias SKIP (not routed). KiCad DRC (all
severities, schematic parity, project rules): 0 errors, 4 warnings `silk_edge_clearance` (J1 and U1 silkscreen cross
the edge: both overhang on purpose; JLC clips silk at the edge), 205 unconnected items (52 nets, no routing yet; not
waived). `tools/stack_check.py`: OK.

Placement changes made during routing (2026-11-22, all in `gen/main_pcb.py`): U4 turned 180 degrees (pair fan-out
without a crossing on F.Cu), R9/R10/C35/C48/C42/C43/R32/R33/R40/R76/C90/C91/Q41/D10/D11 pinned by hand (FIXED; D10/D11 and R34/R35 moved or pinned again 2026-11-24), the
anemometer filter block (R70-R75, C70-C72) re-placed in columns, J8 1.5 mm further right, B.Cu crossing window under the
pair's straight run widened to about 4.7 mm (to the bend).

Placement change 2026-11-24 (status LEDs, `gen/main_pcb.py`): D10/D11 moved from (41.24, 22.86)/(28.74, 20.59) below
the module to the right edge; R34 from (39.5, 21.11) to (48.3, 27.73); R35 stays at (37.0, 21.09), now pinned. All other
footprints at their old positions (compared footprint by footprint).

**For the reviewer, first (placement):** the stack direction (connectors on the front here, back on the power board); U9 position
against the "near an edge" wish; J3 14 mm from the antenna end; the module's right pad column 0.5 mm from the right
edge (pins 28-40 must leave by vias under the module); BC1.2 stubs from the pair down to J10 pins 7/8 (about 16 mm).

## Routing (2026-11-22)
Two-step and reproducible from the repo (deterministic: KRT seed pinned, frozen copper stored as data):
1. `tools/build_board.sh main-board` draws the placed board plus **locked copper** from `gen/main_copper.py`:
   - hand copper (`usb`, `vbus`, `sys_`, `buckboost`, `boost`, `mcu`, `bmp`, `gate`, `anemometer`, `cluster`,
     `sen_trunk`, `chg_trunk`, `boost_en`, `gas_dac`, `pm_pocket`, `gas_pair`): USB pair and BC1.2 stubs, both
     switchers' power loops and decoupling, BMP580, the 3V3_SW gate network, ESD order at J3/J12, the anemometer
     bundle, sensor and charger I2C trunks, BOOST_EN, GAS_DAC, the PM/gas UART pocket bundle through the window;
   - frozen router copper (`main-board/frozen-routes.json`, written by `tools/main_freeze.py` from chosen router runs,
     minus the hand copper): every other net. The router alone plateaus at 2-6 open nets on this board (the order it
     meets the nets in decides); freezing a good run and hand-leading the last nets through the bottlenecks fixed that.
2. `tools/route_main.sh` (KiCadRoutingTools): GND planes on In1/In2 (solid), the router finds every net connected
   and adds nothing, `tools/finish_v1.py`, `tools/main_stitch.py` (edge fence and grid GND vias, outer GND pours),
   `tools/silk_fix.py`, kicad-cli DRC. Writes the board in place.

Numbers (final board): 1312 track segments (F.Cu 1040 mm, B.Cu 1172 mm), 250 vias (184 x 0.6/0.3 stitch and router
vias, 45 x 0.45/0.25 hand vias, 19 x 0.45/0.2 router, 2 x 0.54/0.29). Widths: signals 0.15/0.2 mm, router neck-downs
0.127/0.142 mm at congested pads (fab floor in `rules/krt-fab.txt` = board minimum in the .kicad_pro: track 0.127,
via 0.45/0.2, clearance 0.15), Rail 0.3 mm, Power 0.65 mm, USB 0.27 mm.

**Checks (2026-11-22):** KiCad DRC (refill, schematic parity, all severities): 0 errors, 0 unconnected, 0 parity, 3
warnings waived in `drc-waivers.csv` (`lib_footprint_mismatch` U1/J1/U4: silk_fix clipped or moved silk only).
`calc/critical.py`: OK (USB copper skew 0.21 mm, 4 vias; FB traces 2.92/2.84 mm). `calc/emi_check.py`: OK, 2 WARN
(below). `calc/track_width.py`: OK. `scripts/hw-check.sh`: OK.

## Routing review (2026-11-22)
- **USB pair** (F.Cu 0.27/0.15 mm over In1, 90 ohm, hand-drawn): path A (plug side A) P 26.57 / N 26.46 mm copper,
  skew 0.11 mm; path B 25.57 / 25.57 mm; net copper P 52.17 / N 52.38 mm (critical.py metric, 0.21 mm). 4 vias: 2 in
  the J1 pad interleave on DN, 2 BC1.2 tap vias. With via barrels path A reads 2.95 mm skew (emi_check WARN): about
  18 ps, far below the USB 2.0 HS budget. Spacing to other nets outside the fan-out min 0.64 mm (rule 0.6 mm), 0
  crossings of the main run in plan view. BC1.2 stubs on B.Cu to J10 pins 7/8: stub skew 0.23 mm, round trip 318 ps
  = 7.9 % of the 4 ns edge (lumped). Nets crossing the stubs on F.Cu (screened by In1/In2): +3V3, BOOST_EN, CHG_CE,
  ESP_DN, IO0, LED2_A, GND, SYS.
- **B.Cu crossing window:** the pair and J1 wall off the top-left pocket on F.Cu. Under the pair's straight run (about
  4.7 mm up to the bend) B.Cu is open, two solid GND planes away from the pair; everything else under the pair is B.Cu
  keepout. Lanes west to east: PM_RXIN, +3V3, WIND/RAIN/VANE (0.3 mm pitch, 0.15 mm tracks), PM_SETIN, GAS_RXIN,
  GAS_RXD. Stitch vias beside the pair: south side at +0.5 and +4.2 mm, north side only at +0.5 mm (the second north
  via gave way to the pocket bundle; next north via is on the diagonal, 8.6 mm on; the pair references In1 all along).
- **Switcher loops** (emi_check, cap -> VIN -> GND pin -> cap): TPS63802 input 6.2 mm (copper), output 12.5 mm (WARN,
  target 12, fail 15: the return runs through a via and In1), TPS61023 output 11.6 mm. Switch-node copper outside the
  pads: BUCK_L1 0.67 mm2, BUCK_L2 0.67 mm2, BOOST_SW 1.12 mm2 (max 3). No I2C or FB run parallel to a switch node
  (0.00 mm within 1.0/0.5 mm).
- **GAS_DAC** (ZE25 analog output to the ADC): B.Cu 1.7 mm east of the DN stub (was 1.0 mm: emi_check flagged 9.2 mm of
  parallel run within 1.0 mm of USB copper), then F.Cu between J10 columns 3/5 and B.Cu into J8.
- **Planes and stitching:** In1 and In2 solid GND (only antipads); longest signal run over a plane void 0.10 mm.
  Edge fence 40 vias (main_stitch pitch 3.5 mm, 0.85-1.65 mm inside the edge), 25 grid vias, outer GND pours on
  F.Cu/B.Cu. Largest unexempted edge gap at most 5.0 mm. Exempt (emi.yaml): J1 overhang, the module's right pad column
  (0.5 mm from the edge), the antenna strip, the M3 hole keepouts and the H3/H4 corners (5.2 mm between the vias either
  side of the hole; a corner via would float, the planes cannot fill the sliver).
- **Long routes (router results, accepted):** PM_RXD (about 70 mm, 0.127 mm neck-down, 8 vias) and PM_RXIN, PM_SETIN,
  CHG_INT, TXD0/RXD0 take long detours round the board's middle: the module's left column, the pair and the stubs
  leave few exits. All are slow UART/GPIO lines (9600 baud, interrupt, strap). An earlier PM_RXD run hugged the board
  edge and blocked the fence; it was re-routed with a temporary 1.45 mm edge keepout.
- **Hand fixes in the pocket:** PM_SET as one F.Cu diagonal pin 6 -> R49.1 (freed R48.2, which was boxed in), PM_RXIN
  under JP1 at y 8.2, JP1's GND on its own via (replaces a GND track that crossed the channel).

**Residual risks / not verified:** the 0.127 mm neck-downs and 0.45/0.2 vias sit at the fab floor of `rules/krt-fab.txt`
(not re-checked against JLC's current capability page); loop buckboost_out 0.5 mm over target; the long UART
detours have not been checked for crosstalk beyond emi_check's parallel rules; USB eye and BC1.2 detection need a
board on the bench.

**For the reviewer, first (routing):** `out/review/pcb-main-board/annot_leds.png` (2026-11-24: LED1 past H2, D10/D11 at the edge), `annot_usb.png` (pair, window, stitch vias),
`annot_pocket.png` (pocket bundle), `annot_switchers.png` (U2/U7 loops, GAS_DAC beside the stubs), `annot_bottom.png`
(J10/J8/J12 escapes), then `kicad_top.png`/`kicad_bottom.png`.

## Status LEDs (2026-11-24, engineer: visible from the side of the stack)
- **Part:** Lite-On LTST-S270KRKT, side view, red 631 nm (C125114, Extended, USD 0.032, stock 29060 on 2026-11-24);
  data sheet DS22-2000-210 rev G: body 1.65 x 1.15 (with lens) x 0.60 mm, VF 2.0 typ / 2.4 max at 20 mA, IV 18-54 mcd
  at 20 mA, IF max 30 mA. Candidates and why: PARTS-REVIEW.md, section Changes 2026-11-24. Footprint
  `weatherstation:LED_LiteOn_LTST-S270_SideView` (`gen/build_footprints.py`, land pattern from p7); JLC's footprint fits
  by pad number, pad 1 = cathode, 0.10 mm pad offset (`tools/fab_package.py --fit-only`). Silk: one line behind the
  cathode half, on the inboard side.
- **Edge:** right edge between H2 and H4 (x 48.3-50, y 27-43). The top edge is the antenna, the left edge holds USB-C,
  Qwiic and J11, the bottom edge the outdoor cables (J12, J8); on the right only J2's vertical plug stands beside the
  strip, its cable leaves upward. Lens tip 0.05 mm inside the edge, pads 0.31 mm from it. `gen/main_pcb.py` asserts the
  orientation (lens +x, cathode pad 1 above anode pad 2, at the right edge).
- **Current:** `calc/led_current.py hardware/main-board`: 0.90-1.55 mA through 1k from 3.3 V, about 2.4-4.2 mcd typical
  (0.8 mcd lowest bin); was about 1.3 mA with the 0603. Awake only, no sleep load.
- **Routing (only the LED nets changed):** the old R34 spot below the module was boxed in on both layers (IO0, LED2,
  RXD0), and only one track fits past H2 (between the SYS corner and the H2 keepout). LED1 (GPIO side) takes that lane,
  hand-drawn in `frozen-routes.json`: from its old via at the module down B.Cu x 42.0, F.Cu round H2 to R34 at the strip's
  top; LED1_A on F.Cu x 48.2 down to D10. LED2_A (R35 stays below the module) is a router run with a 1.4 mm edge
  keepout and 0.45/0.2 vias (frozen): 74.5 mm, 8 vias, round J10's west end and along y 41.9 on B.Cu to a via beside
  D11. A DC LED line, so the length does not matter electrically; a shorter one needs another net moved (PARTS-REVIEW,
  open decisions). Cathodes reach GND through the plane vias of route_planes/main_stitch. All 48 other signal and power
  nets keep identical copper (segment by segment against the 2026-11-22 board); GND lost the 7 old LED cathode stubs and
  its stitch/pour copper moved a little round the LEDs.
- **Checks (2026-11-24):** KiCad DRC (refill, schematic parity, all severities): 0 errors, 0 unconnected, 0 parity, the
  same 3 waived silk warnings. `calc/emi_check.py`: OK, edge fence 41 vias, largest unexempted gap 4.4 mm; same 2 WARN.
  `calc/critical.py`: OK. Final board: 1364 track segments, 258 vias.

## Commands
```
python3 hardware/gen/main_board.py
scripts/schematic-review.sh main-board
# a regenerated schematic gives the symbols new uuids: refresh the routed board's symbol links (no copper change)
# kicad-cli sch export netlist -o /tmp/main.net hardware/main-board/main-board.kicad_sch && $KICAD_PYTHON hardware/tools/sync_from_netlist.py /tmp/main.net hardware/main-board/main-board.kicad_pcb
python3 hardware/gen/pins.py --board main_board MCU U1      # pin/net listing of a part
hardware/tools/build_board.sh main-board                    # schematic, netlist, placed board + locked copper, renders
hardware/tools/route_main.sh                                # planes, (router), stitch, pours, silk, DRC -> board in place
$KICAD_PYTHON hardware/tools/main_freeze.py ROUTED.kicad_pcb NET... --minus HAND.kicad_pcb   # store router copper
python3 hardware/calc/emi_check.py hardware/main-board      # USB, edge fence, loops, parallel runs (emi.yaml)
python3 -I -c "import sys; sys.path.insert(0,'hardware/tools'); from pathlib import Path; import fab_package as f; f.drc_gate(Path('hardware/main-board/main-board.kicad_pcb'), Path('/tmp'))"   # DRC gate with drc-waivers.csv
# renders: $KICAD_PYTHON hardware/tools/board_geom.py hardware/main-board/main-board.kicad_pcb hardware/out/review/pcb-main-board/geom.json
#          uv run --package weatherstation-hardware python hardware/tools/render_review.py hardware/out/review/pcb-main-board/geom.json hardware/out/review/pcb-main-board usb=0,6,36,22 switchers=26,19,46,34 pocket=14,3,34,24 bottom=0,36,50,50 leds=40,19,50,44
python3 hardware/calc/critical.py hardware/main-board          # routed checks (add --placement for placement only)
python3 -I hardware/tools/stack_check.py                    # J10, holes and outline line up with the power board
python3 hardware/calc/power_budget.py hardware/main-board
python3 hardware/calc/bom_check.py hardware/main-board [--stock --qty 5]
python3 hardware/calc/led_current.py hardware/main-board     # status LED current and brightness (board.yaml design.leds)
scripts/hw-check.sh
```

## Calc results (2026-11-21; 2026-11-24 LEDs and cost)
led_current: 0.90-1.55 mA, 2.4-4.2 mcd typical. bom_check --stock --qty 5: USD 88.91, 10 Extended types.
power_budget: buck-boost input at cutoff 2.30 V vs 1.3 V minimum, OK (path 0.17 ohm incl. J10, assumption).
track_width: Power class 0.65 mm for 1.7 A OK. bom_check: OK, stock OK at qty 5. No MISSING rows.
i2c_bus: rise 514 ns (limit 1000), pull-up strength 2.64 mA with one 2.2k module (limit 3), pulse leakage 6.6 uA (7 %),
pulse edge 77 Hz (need 42). Inputs marked `assumption` (cable pF/m and length, anemometer rate) need a measurement.
