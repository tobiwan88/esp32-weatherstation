# esp32-weatherstation: agent notes

Solar + USB powered ESP32-S3 air-quality weather station: SEN66 (PM, CO2, T/RH, NOx index) plus an outdoor SHT45, deep-sleep
duty cycle, WiFi to Home Assistant/MQTT. Custom 4-layer PCB (two GND planes), JLCPCB-assembled. Status: hardware pre-layout, firmware not started.
Base created from desk_notifier (board-neutral hardware skills, calc scripts, tools and a working KiCad pipeline kept as reference).

## Start here
- Hardware: read `.claude/skills/hw-base` first, then `hardware/weatherstation-v1/BOARD.md` and `board.yaml`. Requirements: `hardware/weatherstation-v1/REQUIREMENTS.md`. Plan: `hardware/PLAN.md`.
- Skills (board-neutral, in `.claude/skills/`): `hw-base`, `kicad-schematic`, `kicad-layout`, `hw-parts`.
- Numbers come from scripts in `hardware/calc/` (rule in `hw-base`): `bom_check.py`, `power_budget.py`, `critical.py`, `buck.py`, `impedance.py`.

## Tooling
- Gate: `scripts/hw-check.sh [--strict] [--stock --qty N]` (must print `hardware checks: OK`; MISSING rows are open inputs). `scripts/check.sh` = gate + pytest + privacy scan.
- Tests: `python3 -m pytest -q` (or `uv run pytest`). Python 3.13, `uv`. Hardware tools: `uv run --package weatherstation-hardware ...` or plain `python3` for the calc scripts.
- KiCad: `source scripts/kicad-env.sh` (kicad-cli, `$KICAD_PYTHON`, symbol/footprint dirs). On Linux install KiCad 7+ from apt for kicad-cli/pcbnew.
- ESP-IDF v6.1 (firmware, later): `source scripts/idf-env.sh`.
- Stock and price: `python3 hardware/tools/jlcparts.py C123456` or `-s "keyword"`.

## Hardware decisions that must not be lost
- 4 layers, In1 and In2 both solid GND; outline at most 50 x 50 mm (cheapest JLCPCB tier).
- USB-C = programming, debug (native USB-JTAG) and charging. One charger for USB and solar: BQ25798 (two inputs via ACFET/RBFET pairs), 1S LiFePO4 cell with HY2112-CB protection (commit 7db8d9c). CE pulled high = charge off until the firmware has written VREG 3.65 V (POR default is 4.2 V); firmware handles cold charging. Open circuit findings: `hardware/weatherstation-v1/PARTS-REVIEW.md`.
- Sensor rail 3V3_SW switched by a P-FET; SHT45 off-board in a radiation shield; SEN66 on a GH connector; NO2 not on v1.
- Two I2C buses: charger on IO1/IO2 (RTC I2C, so the ULP core can manage charging in deep sleep; pull-ups to +3V3), sensors on
  IO13/IO14 (pull-ups on 3V3_SW). ZE25-O3 gas module (J8, 7-pin 1:1, UART IO17/IO18 with RXD divided to 3.0 V, DAC to IO7) on
  a TPS61023 5 V boost from SYS, EN = IO12, off by default (pull-down, true disconnect).
- Solar charging stays on during deep sleep (user, 2026-11-01): CE held low by GPIO hold, chip JEITA active (`charge-policy.md`).
- 3.3 V from a TPS63802 buck-boost on SYS (the LDO and its 3.5 V cutoff are gone); HY2112 overdischarge 2.10 V is the hardware floor.
- Thermal: heat corner away from the NTC and sensor connectors. EMC: solid planes, antenna keepout on all layers, ESD on USB and the outdoor I2C cable, TVS on solar input.

## Reference material (not active)
`hardware/reference/desk_notifier/`: generators (`gen/`), pipeline, routing and fab-package scripts (`tools/`), a full board profile and PLAN with lessons. Copy and adapt; rename `notifier-v1` and the net names together. Source commit: desk_notifier `fedb410`.

## Private data (this repo is public)
Never commit: Wi-Fi names/passwords, tokens, MAC addresses, host names, LAN IPs, serial ports, home paths, order/account data, photos of people or the home, KiCad/CAD files with user metadata. Kconfig defaults for personal values stay 0 / "". Device notes go in `CLAUDE.local.md` (gitignored).
- Before every commit that will be pushed, and before a push: `scripts/privacy-check.sh`. Fix findings, do not suppress them.
- New binary/CAD exports (gerbers, STEP, images): check embedded metadata for names and paths first.
