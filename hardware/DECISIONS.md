# Hardware decisions that must not be lost

Current as of 2026-11-23. Each item names where the detail lives. When a decision changes, fix this file, the source named here
and `README.md` in the same step. The full decision log of the interview is `REQUIREMENTS-system.md` section 9.

## System
- Three boards plus bought parts: power board, main board, sensor head. Split by the engineer on 2026-11-21 to meet the per-order
  budget and to make the power part and the cell chemistry swappable (`REQUIREMENTS-system.md` section 3).
- Budget (engineer): each JLCPCB assembly order under USD 100, the whole project (orders, cells, panels, enclosures, sensors)
  under USD 500. Fixed fees per order dominate: fewer designs and fewer Extended part types beat small part savings.
- Stations are for own use. Home Assistant over MQTT is the target; publishing to aqicn.org or Sensor.Community is an optional later add-on.
- Design target is the exposed site on solar only; USB charging is optional on every station.

## Power
- One charger for USB and solar: BQ25798 on the power board (hardware MPPT, two inputs through ACFET/RBFET pairs), one 1S cell with a
  protection IC (HY2112-CB for LiFePO4). Default cell LiFePO4 26700 (3.65 V charge limit, charge window -10 to 50 C, never charge
  below 0 C); the chemistry stays flexible through the BOM and firmware, sodium-ion is open until a cell with a readable datasheet and
  a matching protection IC are chosen (HY2112-CB trips at 3.75 V and cannot protect a sodium cell).
- Charge enable CE is pulled high (charge off) until the firmware has written VREG 3.65 V (the power-on default is 4.2 V). The firmware
  sets VREG, current limit and the cold and hot rules (`FIRMWARE-RULES.md`, `weatherstation-v1/charge-policy.md`).
- No software MPPT, no extra MCU for charging. Panel 5 W, 6 V class (open circuit below 10 V cold, for the TVS).
- Solar charging stays on during deep sleep (engineer, 2026-11-01): CE held low by GPIO hold, chip JEITA active (`weatherstation-v1/charge-policy.md`).
- Cycle: 30 min by default, 15 min only while USB or strong sun is present. At least 7 days autonomy from 80 % of the cell
  (a FAIL threshold in `calc/power_budget.py`). Sleep current of the whole stack under 100 uA, checked as a sum of named loads.
- The power board has no 3.3 V rail. The main board makes 3.3 V (TPS63802 buck-boost from SYS, so there is no LDO and no 3.5 V
  cutoff) and 5 V (TPS61023 boost). The HY2112 overdischarge threshold of 2.10 V is the hardware floor.

## Boards and the header
- Power and main board: 4 layers, In1 and In2 both solid GND, at most 50 x 50 mm (cheapest JLCPCB tier), M3 holes in an asymmetric
  pattern, antenna keepout on all layers. Sensor head: 2 layers.
- Keyed 2 x 10 header J10 between the two boards, 2.54 mm, hand-soldered, pin 3 is the key: male pins on the main board, socket on
  the power board. The pin table and the contract decisions are in `ARCHITECTURE.md`; USB D+/D- (BC1.2 detection) are carried over it.
- USB-C is on the main board (programming and debug through native USB-JTAG). USB VBUS goes only to the power board, so the main
  board alone is powered from a bench supply on SYS.
- Never feed a bench supply into SYS of a power board with a cell fitted.

## Sensors and ports
- Core measurements: PM1/2.5/10 (DFRobot SEN0460 on I2C, on hand, or Plantower PMS7003 on UART), temperature and humidity on the
  sensor head in a radiation shield, pressure on the main board (BMP580, U9). RH is used to flag and correct PM above 80 to 85 %.
- Sensor head part: SHT40 decided 2026-11-21 (same footprint as the SHT45 the `sht45-board/` design still carries; **OPEN: board not yet switched**).
- Sensor rail 3V3_SW is switched by a P-FET (Q40) with a slow ramp and a bleed resistor; 5V_SW from the boost converter (EN = BOOST_EN,
  off by default, true disconnect). All sensor power sits behind the switched rails; bus pull-ups switch with the rail.
- Ports on the main board: 2 x Qwiic (JST SH), 2.54 mm I2C header, 5 V UART J2 (PMS7003), ozone module J8 (ZE25-O3, optional and unproven),
  rain/wind/vane pulse port J12. Two I2C buses: charger on IO1/IO2 (RTC I2C, so the ULP core can manage charging in deep sleep),
  sensors on IO13/IO14.
- Dropped: SEN66 (cost), VOC/NOx. CO2 (SCD41) footprint stays DNP. NO2 only after a bench trial with one bought module. The BMP585 and
  VEML6030 add-on boards are retired as ordered designs; never fit the BMP585 add-on together with U9 (both are address 0x46).

## Thermal, EMC, safety
- Heat corner (regulators, charger) away from the cell NTC and the sensor connectors. Solid planes, ESD on USB and on the outdoor I2C
  cable, TVS on the solar input.
- Self-built, personal use, not an approved product: PTC fuse at the cell, protection IC, NTC with charging inhibited below 0 C, no
  charging above 50 C, keyed cell connector with polarity marked, vented enclosure with the cell away from heat.
