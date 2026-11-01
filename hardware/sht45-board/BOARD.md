# sht45-board: outdoor T/RH sensor board (sensor option A)

A small PCB in the radiation shield, connected to J3 of the main board (weatherstation-v1) by a 4-wire JST SH (Qwiic) cable.
Generator: `hardware/gen/sht45_board.py` (writes the schematic, `bom.csv`, net check). Status: schematic generated (ERC 0,
nets OK); layout not started.

## Circuit
- U1 SHT45-AD1F-R2 (LCSC C5360602, Extended, 4019 in stock, USD 6.53): SHT45 with an on-package polyimide membrane
  (datasheet v7.3 section 6.1: IP68, 200 nm particle filtration, RH response time unchanged). Same DFN-4 1.5 x 1.5 mm package;
  footprint without central pad (datasheet 5.3: die pad not connected, soldering it not recommended). Address 0x44.
  Fallback without the membrane: SHT45-AD1B-R2 (C5221601, USD 5.73).
- C1 100 nF on VDD (datasheet figure 1). The 10k I2C pull-ups are on the main board (R50/R51 on 3V3_SW), and the USBLC6 (U5)
  there protects the cable lines.
- J1 JST SH 4-pin SM04B-SRSS-TB (C160404, same part as main-board J3): 1 GND, 2 VDD, 3 SDA, 4 SCL (Qwiic order).
- Supply: 3V3_SW from the main board (3.32 V; SHT45 1.08-3.6 V). Off between measurements.

## Layout rules (Sensirion SHT4x design guide, version 2, March 2024, section 3)
- 2 layers, about 12 x 25 mm, one M2 or M3 hole at the connector end. The sensor goes at the far end, away from the connector.
- Milled slits around the sensor and thin traces to it; no copper pour under or around the sensor (design guide figure 8).
- No other heat source on the board. Sensor opening faces the shield's airflow and not upward (rain).
- Conformal coating: keep it off the sensor opening (the membrane protects against dust and splashes, not against coating).
- Reflow and handling per Sensirion's handling instructions (`weatherstation-v1/datasheets/appnotes/sht4x-handling.pdf`).

## Ordering
- As its own JLCPCB order this adds PCBA setup (about USD 8.18), stencil (USD 1.53), 2 Extended fees (USD 6.14) and the
  bare boards. Alternative: put it in the same panel as the main board (one PCBA order), but the main board is kept at or
  below 50 x 50 mm for the cheapest tier. Decide when the main-board layout is known.
