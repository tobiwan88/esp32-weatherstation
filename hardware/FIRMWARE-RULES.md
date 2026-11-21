# Firmware rules from the hardware (power board + main board)

Status 2026-11-21. Firmware is not started. These are the rules the hardware depends on. Each rule names the review item
(`REVIEW-2026-11-21.md`) or decision it comes from. **This file is the only BQ25798 register plan.** The older tables in
`weatherstation-v1/usb-charger-bq25798.md` and `weatherstation-v1/charge-policy.md` explain the background; where they
differ, this file wins. Field names follow the BQ25798 datasheet (SLUSDV2C) register map. Check every field's register
address and bit position against the datasheet when the driver is written: this file does not quote them.

## 1. Order at every boot and every wake, before CE goes low
1. Read the part information and fault/status flags. Any fault: leave CE high and log.
2. **WATCHDOG = disabled.** An expired chip watchdog resets the registers to their POR values (VREG 4.2 V, ICHG 1 A), which
   would overcharge the LFP cell until the HY2112 trips at 3.75 V.
3. **Check the cell count first** (PROG resistor R14 3.0k = 1S, 1.5 MHz; read back the cell-count field). The VREG range and
   step depend on it, so VREG is written only after 1S is confirmed.
4. **VREG = 3.65 V** (cell maximum 3.75 V). Read it back. Verify with a DMM on the first samples.
5. **ICHG = 1.2 A: OPEN** (review B5, the engineer has not decided). At a hot cell the HY2112 charge-overcurrent trip can be
   about 1.48 A (AO3400A 48 mOhm x 1.2 per FET), so 1.5 A could trip the protection. 1.2 A is the default until B5 is
   decided (alternatives: a lower-Rds dual FET, or a bench measurement). **Clamp in firmware:** never write more than this
   value anywhere in the code (review B6: the chip accepts up to 5 A; the only hardware backstops are L1 Isat 3.22 A and
   the HY2112).
6. **VSYSMIN = 3.0 V** (review B3, range 2.5-3.0 V). The old 4.0 V kept the BATFET in linear mode for the whole charge
   (about 1 W, about 18 % of the solar energy lost); its reason, the AP2112K LDO, is gone (TPS63802 runs down to 1.3 V in).
7. **VAC_OVP = 12 V** (review B4). The POR value is not clear from the datasheet (26 V or 7 V). 7 V would block a cold
   6 V panel (Voc about 8 V). Write it every boot; confirm the POR value on a sample.
8. **JEITA hot side** (review B2): JEITA_VSET = 0 (charge suspended in the warm band), or TS_WARM at its lowest setting
   with JEITA_VSET = 0. The defaults would charge a 3.0-3.25 V cell at full current up to about 61 C (cell limit 50 C).
   Cold side as in `weatherstation-v1/charge-policy.md` (JEITA_ISETC; TS_IGNORE = 0 whenever firmware is not running a
   session).
9. **Input current** (review B8): set IINDPM explicitly for each input, AUTO_INDET_EN = 0 after the first detection,
   **never enable HVDCP** (9 V/12 V would exceed the 6 V clamp of U4 USBLC6 on the main board). BC1.2 shares D+/D- with the
   ESP32's own USB and may misread the port type: bench test.
10. MPPT VOC_PCT for the bought panel (Vmp/Voc from its label; board.yaml `panel`).
11. Only now drive CE low (IO9).

## 2. CE and GPIO hold
- CE (IO9) is active low. It is pulled high on both boards: R20 1M to +3V3 (main) and R23 1M to BAT_PACK (power). An ESP32
  reset or power-on releases the pin, CE goes high, charging stops. This is the fail-safe; do not defeat it.
- Deep sleep with charging on (decision 2026-11-01): CE low through deep sleep with GPIO hold (`gpio_hold_en` +
  `gpio_deep_sleep_hold_en`), TS_IGNORE = 0, all of section 1 written in the same wake. Cost: 3.3 + 3.2 uA through the two
  pull-ups (`calc/power_budget.py` sleep sum).
- A chip POR in sleep drops SYS, resets the ESP32 and releases CE: safe.
- Charger I2C on IO1/IO2 (RTC I2C): the main CPU and the ULP never use it at the same time.

## 3. Watchdogs
- Chip watchdog: disabled (section 1.2). Firmware never leaves CE low without the registers written in the same wake.
- ESP32 task watchdog and RTC watchdog on: a hung session resets the MCU, which releases CE (charge off).
- Charge sessions with TS_IGNORE = 1 (cold charging, `charge-policy.md`) are limited in time (for example 10 min) and only
  while awake or under the ULP.

## 4. Sensor rail 3V3_SW (SENSOR_EN IO11)
- Turn-on ramp is 0.3-0.4 ms (R76/C48, `calc/rail_switch.py`); wait at least 1 ms before talking to the sensors.
- Turn-off takes up to about 8 ms at light load: wait 10 ms after SENSOR_EN low before turning it on again.
- **Before SENSOR_EN goes low** (review B9): set IO13/IO14 (sensor I2C) to input without pull or drive them low. An I2C
  line held high with the sensor's VDDIO off back-powers 3V3_SW through the pull-ups' clamps and can damage the BMP5xx
  (Bosch handling note: interface pins high with VDDIO off). Same in deep sleep (hold them low or as inputs).
- **Never use the SHT4x heater** behind R77 (100 ohm cable feed): the heater draws 6-100 mA and the supply would collapse.

## 5. 5 V rail 5V_SW (BOOST_EN IO12)
- **Before BOOST_EN goes low** (review B10): set PM_TXD (IO4), PM_SET (IO6) and GAS_TXD (IO17) low or to input. A high
  UART line back-powers an unpowered module through its clamps (2-3 mA) and the GAS_TXD divider R46/R47 draws 0.3 mA with
  IO17 high. Keep them low or as inputs through deep sleep (GPIO hold).
- PM_SET low = PMS7003 fan off while 5V_SW stays on for the ozone module.

## 6. Measurement cycle
- 30 min default; 15 min only with USB present or strong sun (charger status: input present and charging). 15 min on the
  battery alone would give 5.9 days of autonomy against the 7-day minimum (`calc/power_budget.py`, review A4).

## 7. Bring-up checks on the first samples
- VREG and VAC_OVP read back and measured; POR value of VAC_OVP noted here.
- BC1.2 result with a PC port, a DCP charger and PV connected first (B8).
- First cell insertion: if SYS stays dead, connect USB or PV once (HY2112 may start with discharge off, B7).
