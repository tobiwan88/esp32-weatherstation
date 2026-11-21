# main-board

**State (2026-11-21):** schematic generated (phase A split from `../weatherstation-v1/`, same parts and nets); no layout,
no fab files. Gate: nets OK, ERC 0 errors 0 warnings, review checks 0, `tools/split_check.py` OK.

## Purpose
ESP32-S3, USB-C, 3.3 V and 5 V rails, sensor ports. Runs from SYS on J10 (power board, a bought charger module, or a
bench supply). Contract and pin table: `../ARCHITECTURE.md`.

## Sheets (`main-board.kicad_sch` + 5 sheets)
| Sheet | Content |
|---|---|
| USB | J1 USB-C, CC pull-downs R9/R10, USBLC6 U4; USB_VBUS and D+/D- on to J10 |
| Header | J10 2x9 2.54 mm, charger host pull-ups R20 (CE 100k), R22 (INT), R54/R55 (I2C) on +3V3, pin map note |
| MCU | ESP32-S3-WROOM-1-N8 U1, decoupling, EN/IO0 strapping, JP1/JP2, R32/R33, J7 debug UART, LEDs |
| Rails | TPS63802 U2 (SYS -> +3V3), Q40/Q41 3V3_SW switch, TPS61023 U7 (SYS -> 5V_SW), TP1/TP2 |
| Sensors | J2 PMS7003, J3 Qwiic (SHT head), U8 SCD41 (DNP), I2C pull-ups R50/R51 and USBLC6 U5, J8 ZE25-O3 |

## Decisions
- Carried-over circuit and pin map are the reviewed weatherstation-v1 design (designators kept).
- USB_DP/USB_DN and SEN_SDA/SEN_SCL are joined by labels inside their blocks (as in v1); on the root, USB_DP/USB_DN
  keep labels because three sheets share them and no crossing-free wire exists (`ROOT_LABELLED` in main_board.py).
- #FLG22 marks USB_VBUS as driven (J1 and U4 pins are passive), #FLG21 marks SYS from J10.
- 4 layers, In1/In2 GND, at most 50 x 50 mm. J2, J7, J8, J10 hand-soldered; JP1/JP2/TP pads only.

## Cost (JLCPCB Economic PCBA, 2026-11-21 first-tier prices)
60 parts on 32 BOM lines, 8 Extended types (USB-C, USBLC6, ESP32 module, TPS63802, L4, TPS61023, L5 1 uH, JST SH).
Parts about USD 7.78 per board; qty 5: 38.89 + 8.18 + 1.53 + 8 x 3.07 = USD 73.16 without bare PCB, joints and
shipping. The 4-layer bare PCB and shipping can push this close to USD 100: get the cart quote before adding Extended parts.

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
