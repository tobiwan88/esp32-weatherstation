# esp32-weatherstation

Outdoor air-quality and weather stations for my own use (Munich): PM1 / PM2.5 / PM10, temperature, humidity and pressure, with an
optional ozone module, reported over WiFi to Home Assistant (MQTT). The AQI and trends are computed on the Home Assistant side.
Solar powered with optional USB, ESP32-S3, deep-sleep duty cycle (every 30 min; every 15 min only while USB or strong sun is
present). Custom PCBs assembled by JLCPCB. Some sites are sheltered with USB nearby, some are exposed on a roof or pole on solar
only; the design target is the exposed case.

**Status (2026-11-23):** the hardware is three boards plus bought parts. The power board and the main board have schematics,
placement and routing done and pass their checks (KiCad DRC clean, EMI rows OK); there are no fab files yet and nothing is ordered.
The sensor head board exists as an SHT45 design; the switch to the cheaper SHT40 decided in the requirements is not done yet.
Firmware is not started. Board by board: `hardware/README.md`.

## The system
| Part | What |
|---|---|
| Power board | BQ25798 charger fed from the solar panel (hardware MPPT) and USB, one 1S LiFePO4 26700 cell with protection IC, panel TVS and choke, cell fuse and NTC. 4 layers, at most 50 x 50 mm. No 3.3 V rail on this board |
| Main board | ESP32-S3-WROOM-1 module, USB-C (programming, debug, VBUS to the power board), 3.3 V buck-boost, switched 3V3_SW and 5V_SW rails, BMP580 pressure sensor, sensor ports (2 x Qwiic, 2.54 mm I2C header, 5 V UART, ozone module, rain/wind pulse port). 4 layers, at most 50 x 50 mm |
| Sensor head | temperature and humidity (Sensirion SHT4x) on its own small 2-layer board in a radiation shield, joined by a Qwiic cable |
| Bought | 5 W 6 V solar panel, LiFePO4 cell, PM sensor (DFRobot SEN0460 on I2C, or Plantower PMS7003 on UART), optional rain gauge, anemometer, ozone and UV modules, enclosure |
The power and main boards are joined by a keyed 2 x 10 header (J10: SYS, USB VBUS and D+/D-, charger I2C and interrupt, charge enable). A bought charger
module that supplies SYS can replace the power board. Contract and pin table: `hardware/ARCHITECTURE.md`.

## Numbers that drive the design
| | Value | Source |
|---|---|---|
| Budget | each JLCPCB assembly order under USD 100, whole project under USD 500 | `hardware/REQUIREMENTS-system.md` section 2 |
| Parts plus fees per order, 5 boards (before bare PCB, SMT joints, shipping) | power board USD 55.00, main board USD 85.57 (live stock and first price tier, 2026-11-23) | `hardware/calc/bom_check.py hardware/<board> --stock --qty 5` |
| Average current, 30 min cycle | 11.8 mA, 0.90 Wh/day | `hardware/calc/power_budget.py hardware/power-board` |
| Autonomy without sun | 11.1 days (at least 7 required) | same |
| Worst-month solar margin | 2.33 x (want 1.5 x) | same |
| Sleep current of the whole stack | 75 uA typical, 85 uA with datasheet maxima (target under 100 uA) | same |
The 15 min cycle draws 22 mA and gives 5.9 days, so it is allowed only with an external energy source. A real JLCPCB quote per
order is still needed: there is no scriptable quote.

## Where to look
- `hardware/README.md`: boards, status, and the map of the hardware tree. `hardware/PLAN.md`: what is done and what comes next.
- `hardware/REQUIREMENTS-system.md`, `hardware/ARCHITECTURE.md`, `hardware/DECISIONS.md`: requirements, how the boards fit, decisions.
- `hardware/GATES.md`: where each board stands in the six design gates.
- `firmware/`: ESP-IDF project (not started); the rules the hardware depends on are in `hardware/FIRMWARE-RULES.md`.
- `hw-kit/`: the reusable hardware kit (skills, agents, check scripts, templates) this project is built with; `CLAUDE.md`: agent notes.
- `scripts/check.sh`: the local gate (hardware checks, tests, privacy scan).

Built with the hardware kit in `hw-kit/`, which grew out of [desk_notifier](https://github.com/tobiwan88/desk_notifier). MIT license.
