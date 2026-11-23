# Firmware (not started)

ESP-IDF v6.1 project for the ESP32-S3 on the main board (`source scripts/idf-env.sh`). Nothing is written yet. The binding
requirements are in `../hardware/FIRMWARE-RULES.md` (charger register plan, GPIO and rail rules the hardware depends on) and
`../hardware/REQUIREMENTS-system.md` section 6. Planned:
- Deep-sleep duty cycle: every 30 min, every 15 min only while USB or strong sun is present. Wake, set up the charger before CE goes
  low, switch 3V3_SW and 5V_SW on, wait for the sensor warm-up, read at about 1 Hz over a 30 to 60 s window, keep value, min, max,
  median and standard deviation, flag high humidity, publish over WiFi to Home Assistant (MQTT), switch the rails off, sleep.
- Charging stays on in deep sleep (CE held low by GPIO hold; the ULP core manages the charger on the RTC I2C bus, IO1/IO2).
  The firmware sets VREG, current limits, cold and hot rules and clamps ICHG (`FIRMWARE-RULES.md`).
- Sensors: DFRobot SEN0460 PM sensor (own driver with error checks; the vendor library has none), SHT4x temperature and humidity,
  BMP580 pressure, optional PMS7003 on J2 and ozone module on J8 (two UARTs), rain and wind pulses counted by the ULP core. Pin states before a rail
  is switched off are in `FIRMWARE-RULES.md` sections 4 and 5.
- Native USB serial/JTAG console, task watchdog, OTA. Avoid strapping pins (GPIO0/3/45/46) for new signals.
- Wi-Fi names, passwords and tokens never go into the repo: Kconfig defaults 0 / "".

Reusable from desk_notifier (copy and adapt, keep the `core/` + `idf/` split with host tests): `components/sensor/core/sht4x.*`
(SHT4x driver), `net`, `web`, `clock`, `settings`, `ble` provisioning.
