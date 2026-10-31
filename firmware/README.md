# Firmware (not started)

ESP-IDF v6.1 project for the ESP32-S3 (`source scripts/idf-env.sh`). Planned:
- Deep-sleep duty cycle (10-15 min): enable 3V3_SW, SEN66 warm-up, read SEN66 + SHT45, send over WiFi (MQTT / Home Assistant), sleep.
- Battery voltage, charge status (CHRG/DONE, TP4056 CHRG/STDBY), VBUS-present input; cutoff at 3.5 V; cold inhibit via one CHG_INH GPIO with GPIO hold in sleep.
- Native USB serial/JTAG console; task watchdog; OTA.
- Avoid strapping pins (GPIO0/3/45/46) for the new signals.

Reusable from desk_notifier (copy and adapt, keep the `core/` + `idf/` split with host tests): `components/sensor/core/sht4x.*` (SHT4x driver),
`net`, `web`, `clock`, `settings`, `ble` provisioning. The SEN66 driver is new.
