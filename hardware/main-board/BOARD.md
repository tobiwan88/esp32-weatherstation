# main-board

**State (2026-11-21):** schematic generated: phase A split from `../weatherstation-v1/` (same parts and nets), then phase B
(pressure sensor U9, Qwiic J4, I2C header J11, rain/wind/vane port J12; sensor pull-ups 2.2k), then the review fixes of
2026-11-21 and the 5-sheet partition. No layout, no fab files.
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
| Rails | TPS63802 U2 (SYS -> +3V3), Q40/Q41 3V3_SW switch with the R76/C48 ramp, TPS61023 U7 (SYS -> 5V_SW), TP1/TP2 |
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
- Root diagram: `ROOT_SIDE` puts the Ports bus pins on the left; boardgen labels each separate hand-wire group of a net.

## Cost (JLCPCB Economic PCBA, 2026-11-21 first-tier prices)
Phase A: 60 parts, 8 Extended types; USD 7.78 per board, order at qty 5 USD 73.16 (without bare PCB, joints, shipping).
Phase B: 77 parts on 39 BOM lines, 9 Extended types (USB-C, USBLC6, ESP32 module, TPS63802, L4, TPS61023, 1 uH, JST SH,
BMP585). Parts USD 11.92 per board; qty 5: 59.61 + 8.18 + 1.53 + 9 x 3.07 = **USD 96.95** before the 4-layer bare PCB,
SMT joints and shipping: over the USD 100 limit once the PCB is added. Decision in PARTS-REVIEW.md A1.

## Commands
```
python3 hardware/gen/main_board.py
scripts/schematic-review.sh main-board
python3 hardware/gen/pins.py --board main_board MCU U1      # pin/net listing of a part
python3 hardware/calc/power_budget.py hardware/main-board
python3 hardware/calc/bom_check.py hardware/main-board [--stock --qty 5]
scripts/hw-check.sh
```

## Calc results (2026-11-21)
power_budget: buck-boost input at cutoff 2.30 V vs 1.3 V minimum, OK (path 0.17 ohm incl. J10, assumption).
track_width: Power class 0.65 mm for 1.7 A OK. bom_check: OK, stock OK at qty 5. No MISSING rows.
i2c_bus: rise 514 ns (limit 1000), pull-up strength 2.64 mA with one 2.2k module (limit 3), pulse leakage 6.6 uA (7 %),
pulse edge 77 Hz (need 42). Inputs marked `assumption` (cable pF/m and length, anemometer rate) need a measurement.
