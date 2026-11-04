# sht45-board: outdoor T/RH sensor board (sensor option A)

A small PCB in the radiation shield, connected to J3 of the main board (weatherstation-v1) by a 4-wire JST SH (Qwiic) cable.
Generators: `hardware/gen/sht45_board.py` (schematic, `bom.csv`, net check) and `hardware/gen/sht45_pcb.py` (board, all copper
by hand). One command: `hardware/tools/build_sht45.sh` (schematic -> netlist -> board -> DRC with parity -> render in
`hardware/out/review/sht45/`). Status (2026-11-04): ERC 0, nets OK, layout done: 0 DRC errors, 0 unconnected, parity
clean; silkscreen warnings only (library footprint outlines at the 0.15 mm silk clearance).

## Circuit
- U1 SHT45-AD1F-R2 (LCSC C5360602, Extended, 4019 in stock, USD 6.53): SHT45 with an on-package polyimide membrane
  (datasheet v7.3 section 6.1: IP68, 200 nm particle filtration, RH response time unchanged). Same DFN-4 1.5 x 1.5 mm package;
  footprint without central pad (datasheet 5.3: die pad not connected, soldering it not recommended). Address 0x44.
  Fallback without the membrane: SHT45-AD1B-R2 (C5221601, USD 5.73).
- C1 100 nF on VDD (datasheet figure 1). The 10k I2C pull-ups are on the main board (R50/R51 on 3V3_SW), and the USBLC6 (U5)
  there protects the cable lines.
- J1 JST SH 4-pin SM04B-SRSS-TB (C160404, same part as main-board J3): 1 GND, 2 VDD, 3 SDA, 4 SCL (Qwiic order). Cable in.
- J2 same part, wired 1:1 to J1: chain out. Same LCSC part, so no extra Extended fee.
- H1 M3 mounting hole (NPTH) in the base.
- Supply: 3V3_SW from the main board (3.32 V; SHT45 1.08-3.6 V). Off between measurements.

## Extending it (2026-11-04)
- The board is one link in an I2C chain: J2 carries the same four wires as J1. Any Qwiic / STEMMA QT board (SparkFun,
  Adafruit, or our own) plugs into J2: pressure, light, a second T/RH point. Rules for a chained board: 3.3 V I2C, an
  address free on the sensor bus (SHT45 0x44, SCD41 0x62 on the main board), its own pull-ups off or removed (the main
  board has 10k on 3V3_SW; parallel pull-ups lower the total, keep it at or above about 2k), and a total cable length the
  10k pull-ups can drive at 100 kHz (keep the whole chain short; a few hundred pF in total).
- 3V3_SW is switched off between measurements, so chained sensors lose their state each cycle (fine for one-shot reads).
- Flex: the sensor island on its neck is the part a flex version would replace (a flex tail with the SHT45 at the tip
  into the shield, the Qwiic base staying rigid). Rigid FR4 first: a flex PCB at JLCPCB costs several times the rigid
  board for the same size (check the quote), and the neck already gives the thermal isolation. The pinout and the base
  stay the same, so a flex head or a different sensor head is a new generator on the same connector.

## Layout (2026-11-04, `gen/sht45_pcb.py`, 2 layers, 17 x 36 mm)
- Sensor island 9 x 8 mm at the top, on a 3.4 mm wide, 9 mm long neck that carries only four 0.2 mm traces; base
  17 x 19 mm with J1 (IN) and J2 (OUT) on the bottom edge (cables leave downward, away from the sensor) and the M3 hole.
- Island: U1 and its 100 nF C1 only; no pour, no via. Every U1 pin is entered from outside the package (the footprint's
  rule area keeps copper off the body).
- Base: GND pours on both layers (base only). Two identical connectors side by side cannot be joined on one layer
  (same pin order, same hand), so J2's VDD/SDA/SCL drop to B.Cu in three straight rows to vias on J1's F.Cu lines.
  The GND/VDD order is swapped for the sensor pin order through a GND via from the B.Cu pour at the neck root.
- Rules: `rules/jlc-2layer.json` (through holes from 0.3 mm), vias 0.6/0.3, clearance 0.15 mm, copper 0.3 mm from the edge.

## Layout rules (Sensirion SHT4x design guide, version 2, March 2024, section 3)
- 2 layers, small, one M2 or M3 hole at the connector end (done: 17 x 36 mm with the chain connector). The sensor goes at the far end, away from the connector.
- Milled slits around the sensor and thin traces to it; no copper pour under or around the sensor (design guide figure 8).
- No other heat source on the board. Sensor opening faces the shield's airflow and not upward (rain).
- Conformal coating: keep it off the sensor opening (the membrane protects against dust and splashes, not against coating).
- Reflow and handling per Sensirion's handling instructions (`weatherstation-v1/datasheets/appnotes/sht4x-handling.pdf`).

## Ordering
- As its own JLCPCB order this adds PCBA setup (about USD 8.18), stencil (USD 1.53), 2 Extended fees (USD 6.14) and the
  bare boards. Alternative: put it in the same panel as the main board (one PCBA order), but the main board is kept at or
  below 50 x 50 mm for the cheapest tier. Decide when the main-board layout is known.
