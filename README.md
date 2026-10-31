# esp32-weatherstation

Solar + USB powered ESP32-S3 air-quality weather station: temperature, humidity, CO2, particulate matter (PM1/2.5/4/10) and a NOx index,
reported over WiFi. Custom 4-layer PCB assembled by JLCPCB. Work in progress: hardware requirements, BOM and checks are in place; layout and firmware come next.

| Part | What |
|---|---|
| MCU | ESP32-S3-WROOM-1-N8, deep-sleep duty cycle (10-15 min) |
| Sensors | Sensirion SEN66 (PM, CO2, T/RH, VOC/NOx index), outdoor SHT45 in a radiation shield, spare Qwiic port |
| Power | one protected 18650, solar MPPT (CN3791) **or** USB-C (TP4056) charging, AP2112K 3.3 V LDO |
| Debug | USB-C native USB-JTAG/serial, UART0 header, test points |
| NO2 | not on v1 (optional external module later) |

Estimated cost: about EUR 240-300 for the first batch (5 boards) plus one complete station, about EUR 133 for each further station
(see `hardware/weatherstation-v1/REQUIREMENTS.md`, section 5a).

## Where to look
- `hardware/weatherstation-v1/`: `REQUIREMENTS.md`, `BOARD.md`, `bom.csv`, `ORDER.md`, `board.yaml`, `parts/`
- `hardware/PLAN.md`: done and next steps. `hardware/README.md`: map of the hardware tree.
- `.claude/skills/`: hardware agent skills (`hw-base`, `kicad-schematic`, `kicad-layout`, `hw-parts`); `CLAUDE.md`: agent notes.
- `scripts/check.sh`: gate (hardware checks, tests, privacy scan).

Base derived from [desk_notifier](https://github.com/tobiwan88/desk_notifier) (hardware skills, calc scripts, tools). MIT license.
