# Charge policy: firmware-managed cold charging (LFP, CBAK 26700LT)

Decision (2026-11-01, user): the firmware handles cold charging and checks the temperature. The BQ25798 chip's own
temperature limits are switched off during charge sessions (TS_IGNORE = 1). No hardware temperature comparator is added.
This file is the firmware requirement. Firmware is not started (CLAUDE.md).

## Cell limits (CBAK 26700LT spec A/03, cell surface)
| Band (cell surface) | Charge current | Rule |
|---|---|---|
| below -10 C | none | no charge (spec charge range -10 to 50 C) |
| -10 to 0 C | 0.2C = 0.78 A | cell limit |
| 0 to 20 C | 0.5C = 1.95 A | chip limit 1.5 A |
| 20 to 40 C | 1C | chip limit 1.5 A |
| 40 to 50 C | 0.5C | chip limit 1.5 A |
| above 50 C (surface 55 C) | none | no charge |
Voltage: 3.65 V CV, cell maximum 3.75 V. Discharge: -40 to 60 C; cut-off 2.0 V.

## Firmware margins (chosen here, to be confirmed on the samples)
- Stop charging below -8 C and above 48 C (2 C inside the cell limits).
- Cold band -8 to 0 C: 0.5 A (about 0.13C, well under 0.2C).
- The NTC TH1 sits on the board, not on the cell. Measure the offset between TH1 and the cell surface on the samples
  (cold soak and warm soak) and widen the margin if the offset is more than about 2 C.

## Chip register rules (BQ25798)
1. **Boot and every wake:** write VREG = 3.65 V, ICHG = 1.5 A, VSYSMIN as in usb-charger-bq25798.md, before CE is released.
2. **Default and sleep state:** CE low (charging on), TS_IGNORE = 0 (chip JEITA on). The chip then stops charging below its
   cold threshold (about 1.9 C at TH1 with R17/R18 5.1k/30k) and above its hot threshold, even when firmware is asleep. Do not
   charge in deep sleep with TS_IGNORE = 1 unless the ULP core is running the band table and checks TS at least every 30 s.
3. **Charge session (awake only):** TS_IGNORE = 1, ICHG set per band from the table, CE low. The firmware reads TS every
   30 s and applies the band table. Stop the session (CE high, TS_IGNORE = 0) on any reading outside the margins.
4. **Chip watchdog:** an expired watchdog resets all registers to defaults (VREG 4.2 V, ICHG 1 A, TS_IGNORE 0; datasheet
   section 7.3.x). Default VREG 4.2 V with CE low would overcharge the cell until the HY2112 trips at 3.75 V. Therefore the
   chip watchdog is disabled (WATCHDOG = 00) and firmware never leaves CE low without a live session.
5. **Read on each wake:** the TS status bits, VBAT_OVP and the other flags. Any fault stops the session.

## CE pin and the fail-safe chain
- CE is pulled high to +3V3 by R20 (charge off; netlist net CHG_CE, R20 pin 1 on +3V3). Firmware drives CE low only during a session.
- ESP32 reset or power-on: the GPIO becomes an input, R20 holds CE high, charging stops. This is the main fail-safe.
- Deep sleep: **decided (user, 2026-11-01): charging stays on.** Hold CE low through deep sleep (GPIO hold) with
  TS_IGNORE = 0 (chip JEITA active: no charge below about 1.9 C at TH1), VREG 3.65 V and WATCHDOG = 00 already written in the
  same wake. A chip POR during sleep also drops SYS, which resets the ESP32 and releases CE high through R20.
- ULP option: the charger I2C is on IO1/IO2 (RTC I2C, ESP-IDF ulp_riscv_i2c: SDA IO1/IO3, SCL IO0/IO2), and CE (IO9) and
  INT (IO10) are RTC GPIOs. The ULP RISC-V core can therefore read TS and the status in deep sleep, apply the band table
  (including cold charging with TS_IGNORE = 1) and stop charging on a fault, without waking the main CPU. The main CPU and
  the ULP must not use the RTC I2C at the same time.
- Use the ESP32 task watchdog so a hung session resets the MCU, which drives CE high through R20.

## Residual risks (accepted by the user for v1, with the mitigation above)
1. No hardware cold or hot stop during a session. A firmware bug in the band table could charge at 1.5 A near 0 C.
   Mitigation: session length limit (for example 10 min), the ESP32 watchdog, and the margins above.
2. The HY2112-CB protects overvoltage, overdischarge and overcurrent only. It does not protect against temperature.
3. The board NTC is an estimate of the cell temperature (offset to be measured).
4. The watchdog and CE rules must be implemented exactly; this file is the reference for the firmware review.
