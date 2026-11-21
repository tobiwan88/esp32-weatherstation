# System requirements v2 (interview 2026-11-21)

Supersedes the single-board scope in `weatherstation-v1/REQUIREMENTS.md` where they differ (that file stays as the record of the
single-board design). Status: agreed in the user interview, not yet implemented. Open items are marked **OPEN**.

## 1. Goal
Outdoor air-quality and weather stations for **our own use** (Munich): they give the same features aqicn.org offers (PM2.5/PM10 with
AQI index, temperature, humidity, pressure, trends and health hints) but locally in Home Assistant over MQTT. Publishing to
https://aqicn.org / Sensor.Community is an optional later add-on, not a requirement (decided 2026-11-21: "just for myself"), so no
WAQI acceptance is needed. Solar plus optional USB, deep-sleep duty cycle, WiFi.
Station sites are mixed: some sheltered with USB nearby, some exposed on a roof/pole on solar only, so the design target is the exposed case.

## 2. Budget and quantities
- Build 2-3 complete stations plus 2-3 development sets (about 5 boards of each design in total).
- **Each JLCPCB PCBA order stays under USD 100; the whole project (all orders, cells, panels, enclosures, sensors) stays under USD 500.**
- Fixed JLC fees are per order (Economic PCBA setup 8.18 + stencil 1.53 + 3.07 per unique Extended part), so fewer designs and
  fewer Extended part types are cheaper than small parts savings. Bought modules and AliExpress parts are allowed wherever cheaper.
- Check with a real JLC quote per order before paying (`hardware/ORDER*.md`).

## 3. Architecture: three boards plus bought parts
| Board | Content | Layers | Order |
|---|---|---|---|
| **Power board** | BQ25798 charger (USB VBUS and PV input, firmware-set VREG), cell protection IC with charge/discharge FETs, NTC, PV input TVS/choke, PTC fuse, cell connector, PV connector | 4 (as the current design) | PCBA order 1 |
| **Main board** | ESP32-S3 module, USB-C (programming, debug, VBUS to the power board), 3V3 buck-boost, 3V3_SW switch, 5 V boost with 5V_SW, all sensor ports, status LEDs | **4** (decided 2026-11-21: solid GND planes make EMC easier) | PCBA order 2 |
| **SHT head** | SHT40 (+ JST SH in/out) on its own small 2-layer board in the radiation shield | 2 | PCBA order 3 |
Bought: solar panel, cell, PM sensor modules, rain gauge, anemometer, extra I2C modules, cables, enclosure.
Light (VEML6030) and BMP585 add-on boards are retired as ordered designs (generators stay in the repo); pressure moves to the main board.

### 3.1 Power-board header (board-to-board contract)
One 2.54 mm header, hand-soldered (no JLC fee), about 10-12 pins, stacked or side by side; the ESP32 antenna keepout end of
the main board stays free of the power board.
| Signal | Direction | Note |
|---|---|---|
| GND (2-3 pins) | | |
| SYS (2 pins) | power -> main | system rail, cell-referred 1.5-5.5 V window, at least 1 A |
| VBUS (1-2 pins) | main -> power | from USB-C on the main board, to the charger input |
| CHG_SDA, CHG_SCL | main <-> power | charger I2C (IO1/IO2 on the ULP-capable pins) |
| CHG_INT | power -> main | |
| CHG_CE | main -> power | pulled so that charging is off until firmware has written VREG |
The contract is documented so a bought charger module that supplies SYS (and ignores the I2C pins) can replace the power board.
The 3.3 V and 5 V rails are made on the main board from SYS, so the header carries no regulated rail.
Main board alone (development): SYS from a bench supply on the header or a pad; USB programming works without the power board.

## 4. Power
- Cell: 1S, **chemistry flexible by BOM and firmware**: default **LiFePO4 26700** (CBAK 26700LT samples in hand, 3.2 V, charge 3.65 V,
  charge window -10 to 50 C, firmware cold-charge policy `weatherstation-v1/charge-policy.md`).
  Sodium-ion (about 3.0 V nominal, 1.5-4.1 V window, vendor-dependent; HAKADI 26700 class) is allowed as an alternative:
  firmware sets VREG for the cell, the protection IC is swapped in the same SOT-23-6 footprint (HY2112-CB trips at 3.75 V overcharge and
  is wrong for sodium-ion). Never charge below 0 C for either chemistry (firmware).
  Sodium-ion remains **OPEN** until a cell with a readable datasheet and a protection IC with matching thresholds are chosen; verify the
  BQ25798 charge-voltage floor and low-voltage precharge with TI before any sodium board.
- Sodium-ion research (Haiku, English and Chinese sources 2026-11-21; datasheets mostly unreadable, values from search summaries, **unverified**):
  - Cells: 18650 (about 1.2-1.5 Ah) and 26700 (about 3.3-3.5 Ah), nominal labelled 3.0-3.2 V depending on seller, charge limit 3.9-4.1 V
    (Zhonghuajia 26700E: 0.5C to 4.10 V, discharge to 1.50 V; Hina 32140 sheet: cut-off 3.95 V above 0 C, 3.9 V at 0 to -10 C, 3.8 V at -10 to -20 C),
    discharge floor 1.5-2.0 V. Alibaba prices about USD 1.2-2.3 per 26700 (MOQ 2-10); no AliExpress, 1688 or Taobao prices found. Class 9 shipping (UN3551).
  - No sodium-specific protection IC found. Lithium 1S families with a selectable threshold exist (ABLIC S-8200A/S-8240B: overcharge 3.5-4.5 V,
    overdischarge 2.0-3.4 V) but need an ordered part and a datasheet check. HY2112-CB (3.75 V overcharge) cannot protect a cell charged to 3.9-4.1 V.
  - BQ25798: 1S VREG window 3.0-4.99 V (so 3.65 V and about 3.9-4.0 V are programmable), set CELL before VREG (changing CELL resets VREG to its POR default);
    precharge below about 2.25 V. Read the datasheet sections directly before relying on this.
  - Cheaper chargers found do not fit: CN3791 float fixed 4.2 V, BQ25170 fixed options (4.05-4.4 V), SC8886 multi-cell; LT3652 (float adjustable, MPPT by input
    regulation, standby about 85 uA, input from 4.95 V) is the only simple MPPT alternative and it idles higher than the BQ25798 design.
  - Conclusion: keep the BQ25798 power board; a sodium variant needs only a different protection IC and firmware VREG/cold limits, so sodium-ion stays a later
    option once a cell with a readable datasheet is bought (buy 2-4 test cells; ask the vendor which charge limit they qualify).
- No software MPPT (decided): the load is about 1 Wh/day, the panel is oversized, the BQ25798 has hardware MPPT (VOC-based). No extra MCU for charging.
- Panel: **5 W 6 V class** (about EUR 14; Voc below 10 V cold for the TVS). About 2 Wh/day in the worst month against a target load of at most 1 Wh/day.
- Cycle: measure and report every **15-30 min**; **7 days autonomy** from 80 % of the cell. Verify with `calc/power_budget.py` after the
  PM window is lengthened (section 6); sleep current of the whole stack under 100 uA with 3V3_SW and 5V_SW off.
- USB-C charging is optional on every station; solar charging continues in deep sleep (charge policy as decided 2026-11-01).
- Safety (self-built, personal use, not an approved product): fuse (PTC) at the cell, cell protection IC, NTC on the cell with charge inhibited
  below 0 C, panel TVS, reverse-polarity-safe keyed cell connector, no charging above 50 C, enclosure vented and the cell away from the heat corner.

## 5. Sensors and ports
### 5.1 Core measurements (same set aqicn uses, computed locally)
- **PM1/2.5/10:** DFRobot SEN0460 (on hand; I2C 0x19, 3.3-5 V, 100 mA max, PM1/2.5/10 and particle counts, low-power register; warm-up and sleep current
  not stated, measure on the bench) or Plantower PMS7003 (UART on J2, 5V_SW). Both may be fitted on one station as two channels for cross-checking.
- **Temperature and humidity:** Sensirion **SHT40-AD1B-R3 (LCSC C2848306)** on the SHT head in the radiation shield (SHT45 is the upgrade, same footprint).
  Humidity is used to flag and correct PM above about 80-85 %RH.
- **Pressure:** BMP585 (C18184976, I2C 0x46) on the main board.
- Not needed for aqicn: CO2 (SCD41 footprint stays DNP), light (VEML7700 or similar via a bought Qwiic module if wanted), NO2/SO2/CO (no economic accurate module).
- O3: ZE25-O3 on J8 stays an optional, unproven add-on (0-10 ppm range against ambient 20-100 ppb: check resolution before relying on it).

### 5.1a Optional sensors ranked for health value (Haiku research 2026-11-21, prices and several figures unverified)
Munich context: PM2.5 year-round, NO2 from traffic (city centre about 39 ug/m3 in 2024, EU 2030 limit 20), ozone in summer heat. The EU EAQI
uses PM2.5, PM10, NO2, O3 and SO2 (worst pollutant sets the index), so a PM-only station gives an incomplete EAQI. Pollen and UV are not in the EAQI.
| Rank | Sensor | Verdict | Notes |
|---|---|---|---|
| 1 | PM (SEN0460 / PMS7003) | must | field R2 for PM2.5 about 0.6-0.9 (AQ-SPEC SPS30; Plantower over-reads at high RH): RH correction needed, SHT40 provides it. SPS30/SEN54 are the accuracy upgrade |
| 2 | O3 (ZE25-O3, J8) | worth building, unproven | related electrochemical O3 studies R2 0.8-0.9 for daily means, not peaks; no ZE25-O3 outdoor study found; NO2 and temperature cross-sensitivity, treat as Ox |
| 3 | UV index (LTR390 or VEML6075, Qwiic module) | worth it, about USD 5-10 | needs a diffuser and a one-time calibration against a weather service; formula valid at 18x gain, 20-bit |
| 4 | NO2 (electrochemical, e.g. Alphasense B43F class) | later | best traffic signal but weakest: field R2 0.3-0.7; needs co-located O3; about USD 40-60 per module would break the per-station budget; not on v1 |
| 5 | Noise (I2S MEMS mic) | cheap extra | relative level only without calibration |
Skip: CO2 and VOC outdoors (low health value), pollen hardware (use the DWD pollen forecast in Home Assistant), HCHO, radon, soil.
Lightning (AS3935): storm alerts only, not health. Wind and rain: context, kept on the pulse port.
Decision for the build: PM + SHT40 + BMP585 core; ozone, UV and noise are optional Qwiic/header modules; NO2 only after a bench trial with one bought module.
Official Bavarian LfU station data (Munich) can be used to check our PM, NO2 and O3 readings.
**OPEN:** verify the current EAQI breakpoints (including PM2.5 and PM10, not found in the research) before they go into Home Assistant.

### 5.2 Ports on the main board
| Port | Connector | Power | Use |
|---|---|---|---|
| 2 x Qwiic | JST SH 4-pin SMD (C160404, same Extended part as the SHT head connectors: no new fee) | 3V3_SW | SHT head chain, SEN0460, bought modules; I2C pull-ups 10 k on 3V3_SW, ESD (USBLC6) on the cable bus |
| I2C header | 4-pin 2.54 mm, hand-soldered, pinout GND, 3V3_SW, SDA, SCL | 3V3_SW | AliExpress GY-style modules and Gravity/Dupont cables |
| UART/5 V port J2 | 2x5 1.27 mm (PMS7003) | 5V_SW | PMS7003, SPS30 (cable), other 5 V UART sensors |
| ZE25-O3 J8 | 7-pin JST PH, hand-soldered | 5V_SW | optional ozone module |
| Pulse/analog port | JST PH hand-soldered (no fee) | 3V3 | rain gauge and anemometer pulse inputs on free RTC GPIOs, one ADC pin for a wind vane; ULP polls, so wake on the first tip then count |
All sensor power sits behind the switched rails; bus pull-ups switch with the rail (no back-power into unpowered sensors).
I2C addresses on the sensor bus: SHT4x 0x44, SEN0460 0x19, BMP585 0x46, VEML 0x10, SCD41 0x62 (no clashes).

## 6. Firmware (later), local AQI and optional publishing
- Wake, power the sensor rail, 30 s warm-up (SEN0460 value to be measured), then readings at 1 Hz for a 30-60 s window; compute value,
  **min, max, median and standard deviation** (kept so a later aqicn upload meets WAQI's rule for particle counters), flag high RH, sleep. Sensor-on time grows from 45 s
  to about 90 s per cycle, so `board.yaml` and the power budget are updated.
- Upload per cycle to the aqicn upload API (HTTPS POST to https://aqicn.org/sensor/upload/, token from aqicn.org/data-platform/token/, explicit units,
  ISO 8601 time, `averaging` in seconds) and to Home Assistant over MQTT. **Tokens, WiFi names and passwords stay out of the repo**
  (Kconfig defaults 0 / "").
- Own driver for SEN0460 with error checks (the vendor library has none). Optional calibration against a nearby LfU station on aqicn.
- AQI (US EPA scale and the European EAQI) is computed on the Home Assistant side from the PM readings; the station sends raw values and statistics.
- Optional later: aqicn / Sensor.Community upload (question to WAQI only if we decide to publish).

## 7. Mechanical and environment
- Outdoor, Germany, -20 to +40 C ambient. Vented enclosure with rain baffle for the PM inlet, SHT head in a radiation shield, cell away from heat.
- Main board and power board each at most 50 x 50 mm (cheapest JLC tier), M3 holes, antenna keepout on all layers.
- Metal shell of the SEN0460 is at power ground: mount it isolated.

## 8. Manufacturing
- JLCPCB Economic PCBA, top side, ENIG, edge rails by JLC where the quote asks. Hand-soldered: headers, JST PH, J2, J8, test pads.
- Fab files from `hardware/tools/fab_package.py` per board (DRC clean at all severities, schematic parity, placement fit, privacy scan).
- Bring-up order: main board alone on USB and bench SYS, then power board with a cell, then sensors.

## 9. Decision log (interview 2026-11-21)
| Decision | Reason |
|---|---|
| Split power and main boards with a 2.54 mm header | meets the per-order budget, swappable power part and chemistry, independent development |
| USB-C on the main board | programming and debug work without the power board |
| No software MPPT, keep the BQ25798 on the power board | negligible gain at about 1 Wh/day, hardware MPPT exists |
| LiFePO4 default, chemistry flexible (BOM + firmware) | easier to source and in hand; sodium-ion possible once a datasheet and protection IC are chosen |
| 5 W 6 V panel, 15-30 min cycle, 7 days autonomy | budget, energy margin about 2x in the worst month |
| SHT40 instead of SHT45; BMP585 on main; VEML6030 and BMP585 add-on orders retired | fixed fees dominate, about USD 4.7 per station |
| Ports: 2 x Qwiic, I2C 2.54 mm header, 5 V UART J2, rain/wind port | plug-in sensors without redesign |
| SEN0460 on hand used as PM sensor (I2C), PMS7003 stays supported | free PM sensor, I2C needs no 5 V |
| Budget: each PCBA order under USD 100, total under USD 500 | user |

## 10. Open items
1. (closed 2026-11-21: own use, no WAQI dependency.)
2. SEN0460 warm-up time, sleep current and PM10 behaviour (bench, later).
3. Sodium-ion: cell with a readable datasheet, selectable-threshold protection IC (see section 4), BQ25798 VREG/precharge check in the datasheet.
4. Main board is 4 layers (decided). Per-order JLC quote against the USD 100 limit: **no self-serve quote API exists** (research 2026-11-21: the
   official api.jlcpcb.com is partner-only with an application and review; unofficial cart endpoints need a logged-in session and risk the account; no maintained
   script quotes end to end). Plan: an offline estimator `hardware/tools/pcba_quote.py` (stdlib, no network) with the published PCBA fee table in its own data file
   (JLC page "pcb-assembly-price", updated 2026-10-22: Economic setup 8.18, stencil 1.53, SMT 0.0016 per joint, 3.07 per Extended part, hand-solder labour 3.58,
   confirm placement 0.45), joints from CPL and footprint pad counts, Extended count from the BOM, and the stock/price from the existing `hardware/tools/jlcparts.py`.
   Not reproducible offline: bare-PCB price (layers, size, finish, quantity) and shipping: take those from one manual cart.jlcpcb.com quote per board revision and
   store them as inputs. Optionally apply for the official API later (keys in a gitignored `.env`).
5. Stack versus side-by-side mounting of the two boards in the enclosure.
6. Which optional sensors are built: ranked by information value for air quality and health (research running); candidates O3, UV, CO2 (indoor/near-source), noise, rain/wind, light.
