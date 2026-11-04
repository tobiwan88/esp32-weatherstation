# Sensor set (decision 2026-11-01: option A)

The SEN66 (PM, CO2, T/RH, VOC/NOx; about USD 58.55 at DigiKey, SEK-SEN66 kit about EUR 84 excl. VAT at SOS Electronic)
was dropped for cost. Reasoning:
- **Outdoor CO2** stays near 420 ppm, so it adds little information.
- **VOC/NOx index** (Sensirion gas index algorithm) needs about 1 Hz sampling, so it does not work with 10 min deep sleep.
- **What matters outdoors:** PM2.5/PM10 plus outdoor T/RH.

## Option A (chosen)
| Function | Part | Where | Key data (source) |
|---|---|---|---|
| PM1/2.5/10 | Plantower PMS7003 | J2, 2x5 1.27 mm, hand-soldered, on 5V_SW | 4.5-5.5 V, <= 100 mA active, <= 200 uA standby, stable data >= 30 s after wake-up, -10..60 C, 0-99 %RH, MTTF >= 3 years, 48 x 37 x 12 mm; pins 1/2 VCC, 3/4 GND, 5 RESET, 7 RX, 9 TX, 10 SET (low = sleep), 6/8 NC; data 3.3 V TTL (Plantower PMS7003 manual V2.5, `datasheets/PMS7003_manual_V2.5.pdf`) |
| Outdoor T/RH | Sensirion SHT45 (or SHT40) | own small PCB in the radiation shield, cable to J3 (Qwiic order) | LCSC SHT45-AD1B-R2 C5221601 USD 5.73, 7280 in stock; SHT40-AD1B-R3 C2848306 USD 1.86, 15786 in stock (jlcparts.py, 2026-11-01). Board still to design |
| CO2 (optional) | Sensirion SCD41-D-R2 | U8 footprint on the main board, DNP | LCSC C3659294 USD 19.49, 1993 in stock. VDD 2.4-5.5 V, peak 175/205 mA at 3.3 V, ripple <= 30 mV, single shot 0.45 mA average at one reading per 5 min, VDD and VDDH tied at the sensor (SCD4x datasheet v1.7, `datasheets/SCD4x_v1.7.pdf`) |
| O3 (optional) | Winsen ZE25-O3 | J8 on 5V_SW | 3.7-5.5 V, warm-up <= 3 min, response <= 90 s, 0-10 ppm, UART 3 V and DAC 0.4-2.0 V, life 2 years in air, -10..55 C (winsen-sensor.com product page). Current 10 mA at 5 V (user, 2026-11-04; not in the manual pages read) |

Cost per station for the sensors: about EUR 20-25 without CO2 and O3 (PMS7003 about USD 12-18 retail, research snippets;
SHT45 board a few EUR). Prices other than the LCSC rows are from search results, not quotes: check before buying.

## Alternatives kept on file
- **Sensirion SPS30** (PM, about EUR 35 at Farnell IE): better accuracy evidence. AQ-SPEC field test PM2.5 R2 0.64-0.85 against
  reference (1 h means); PM10 weak. It fits the same 5 V / UART-or-I2C slot if the PMS7003 data is not good enough.
- **Winsen MH-Z19C** (NDIR CO2, about EUR 15-17.50 with cable): cheaper CO2 module. 5 V, peak about 125 mA. Turn its
  auto-calibration (ABC) off outdoors.
- **SEN55/SEN54** (PM, T/RH, VOC/NOx, 5 V supply): no CO2. Same deep-sleep problem for the gas index.

## Open
- **ZE25-O3:** warm-up (3 min) and response (90 s) do not fit the 45 s window. Decided (user): a firmware feature keeps
  5V_SW on longer for ozone (e.g. 4 min once per hour). `power_budget.py` counts it with an ASSUMED 80 mA at the cell;
  measure the module and replace the number.
- **SHT45 board:** schematic in `hardware/sht45-board/` (SHT45-AD1F with membrane, 100 nF, JST SH).
- The research was a first pass (English sources). A Chinese-language search (szlcsc.com, AliExpress) for PM modules
  sold by LCSC was not done.

## Sources
- Plantower PMS7003 manual V2.5: https://github.com/hackerspace-silesia/Smogomierz/files/3746439/PMS7003_manual.pdf
- PyPMS sensor notes (pinout cross-check): https://github.com/avaldebe/PyPMS/blob/master/docs/sensors/Plantower.md
- Sensirion SCD4x datasheet v1.7 (April 2025): https://sensirion.com/media/documents/48C4B7FB/67FE0194/CD_DS_SCD4x_Datasheet_D1.pdf
- Winsen ZE25-O3: https://www.winsen-sensor.com/product/ze25-o3.html
- AQ-SPEC SPS30 summary: https://www.aqmd.gov/docs/default-source/aq-spec/summary/sensirion-sps30---summary-report.pdf?sfvrsn=8
- Farnell SPS30: https://ie.farnell.com/sensirion/sps30/particulate-sensor-dust-laser/dp/3804199
- SOS Electronic SEK-SEN66: https://soselectronic.com/en-ch/products/sensirion/sek-sen66-413026
- DigiKey SEN66: https://www.digikey.com/short/384rbwtj
- Tinytronics MH-Z19C: https://www.tinytronics.nl/shop/en/sensors/air/gas/winsen-mh-z19c-co2-sensor-with-cable
