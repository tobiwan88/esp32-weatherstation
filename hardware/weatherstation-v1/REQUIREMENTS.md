# esp32-weatherstation v1: PCB requirements (v0.3, pre-layout)

## 1. Scope
Custom 4-layer PCB (two full ground planes): ESP32-S3 controller, solar MPPT charger for one Li-ion 18650, switched sensor rail, connectors for SEN66 (PM, CO2, T/RH, NOx index) and an off-board SHT45. NO2 is out of scope for this revision; J4 is a spare I2C port.

## 2. Functional requirements
- F1 Measure PM1/2.5/4/10, CO2, VOC/NOx index (SEN66) and outdoor T/RH (SHT45 in radiation shield).
- F2 Wake every 10-15 min, measure, send over WiFi (MQTT / Home Assistant), then deep sleep.
- F3 Charge one protected 1S Li-ion cell from either source: a 6 V (about 6 W) solar panel with MPPT (CN3791), or USB-C 5 V (TP4056, about 400 mA). USB has priority: when VBUS is present, hardware (Q4) turns the solar charger off so the two chargers never fight over the cell. Either source works alone; no firmware needed for the switchover.
- F4 Inhibit charging below about 2 C (firmware reads NTC, drives one CHG_INH GPIO that turns on Q3 (solar charger off) and Q5 (TP4056 CE low, USB charger off); GPIO held through deep sleep). Default state (MCU off) = charging enabled on both paths, so a flat battery can recover.
- F5 Report battery voltage, charge status (CHRG, DONE) and battery temperature.
- F6 Program and debug over native USB-C (BOOT + EN buttons). USB also powers the board and charges the cell through U6 (TP4056), subject to the cold-inhibit in F4.
- F7 Sensor rail (3V3_SW) off during sleep via Q2.

## 3. Electrical requirements
- Battery 3.5-4.2 V usable. Firmware cutoff at 3.5 V (sensors off, long sleep): at 3.35 V the AP2112K leaves only about +33 mV over the SEN66 minimum supply at a 0.35 A peak (calc/power_budget.py).
- LDO AP2112K: 3.3 V, 600 mA. Peak load ESP32 TX plus SEN66 fan start can approach this; keep 3x22 uF + 10 uF near load.
- SEN66: supply 3.3 V +/-5 % (3.15-3.45 V), 3.3 V logic OK, I2C address 0x6B.
- Deep-sleep board current target: <100 uA with sensors off (excluding battery divider 2 uA, LDO Iq 55 uA).
- Average budget target: <10 mA at a 10-min cycle (about 1 Wh/day), per research estimate.
- Charger: 22 uH, sense resistor 0.12 ohm (1 A), MPPT divider for panel Vmp. Follow CN3791 datasheet Fig.1 layout (short switching loop, input cap close to VCC).
- Power path: Q1 (gate = VBUS) isolates battery from the system rail when USB is present; D3 feeds VSYS from USB. The battery node is charged only by U6 (TP4056, from VBUS) and U3 (CN3791, from solar), never through D3. Verify no back-feed into the battery node.
- USB charging: TP4056 VCC = VBUS (4-8 V), BAT = battery node, PROG resistor 3k = about 400 mA, TEMP pin grounded (its built-in NTC window is disabled; cold inhibit is done by Q5/firmware instead), CE pulled up to VBUS with 100k, CHRG/STDBY pulled up to 3V3 and read by the ESP32. Exposed pad to GND with thermal vias.
- Charger priority: VBUS drives Q4 (10k series, 100k pull-down) which pulls the CN3791 MPPT pin low, disabling solar charging while USB is plugged in. A 100k/100k divider gives the ESP32 a VBUS-present input.
- USB load budget: system load plus 400 mA charge current should stay near or under typical USB host limits; lower the charge current with a bigger PROG resistor if the host browns out.

## 4. Environmental / mechanical
- Operating -10 to +50 C (SEN66/SEN5x class limit; confirm SEN66 datasheet). Li-ion must not charge below 0 C.
- Vented enclosure with rain baffle for the PM inlet; board conformal-coated. ESP32 antenna not under metal or near battery.
- Target board about 50 x 45 mm, M3 mounting holes, antenna at board edge with keepout.

## 4a. Thermal requirements (thermal decoupling)
Interpreted as thermally isolating heat sources from temperature-sensitive parts, plus managing local heat. (Capacitor decoupling is covered in section 3.)
- T1 Heat sources: CN3791 + inductor L1 + D2 + M1 (solar charger), TP4056 (linear USB charger, about 0.5 W at 400 mA: (5 V - 3.7 V) x 0.4 A; exposed pad on a via array into the ground planes; the two chargers never run together), AP2112K LDO, ESP32 module during WiFi TX, SEN66 fan/laser. Group the charger and LDO together in one corner, away from the ESP32 antenna and from the NTC.
- T2 NTC (TH1) must sit against the battery cell/holder, outside the charger and LDO heat zone, with the sense trace not routed under heat sources. NTC reading reflects battery, not board, temperature.
- T3 Place J2/J3 (SEN66, SHT45) and their cables on the opposite side of the board from charger/LDO. No SHT45 on the PCB: it stays in the radiation shield, so board heating cannot bias outdoor T/RH. SEN66 T/RH is secondary and may be offset-corrected in firmware.
- T4 Charger: L1, D2, M1, R14 on wide copper pours on L1 tied to L2/L3 through multiple thermal vias (0.3 mm drill, at least 4 per pad); AP2112K tab/GND via array. Dissipation budget: LDO worst case (4.2 V - 3.3 V) x 0.2 A about 0.2 W, charger about 0.3-0.5 W at 1 A; keep temperature rise under 25 C inside the closed enclosure.
- T5 ESP32 module: thermal pad (EP) soldered to ground with a via array per Espressif's footprint guidance; no copper heat pour under the antenna area.
- T6 Optional thermal isolation: milled slots or narrow bridges between the charger corner and the sensor-connector area if prototype measurement shows interaction. Use thermal reliefs on THT/hand-soldered pads so hand soldering is practical.
- T7 Enclosure: radiation-shielded outdoors, vented, solar panel shaded from the electronics box, board mounted vertically so convection cools it. Verify rise at full sun and 1 A charge.

## 4b. EMC requirements
- E1 Targets (design goals, personal/prototype use): emissions to EN 55032 Class B (conducted and radiated), immunity to IEC/EN 61000-4-2 ESD (+/-4 kV contact, +/-8 kV air) on all external ports. If the product is ever sold or distributed in the EU, WiFi radio rules (RED: EN 300 328, EN 301 489-1/-17) apply to the whole product; using a pre-certified ESP32 module helps but does not replace product-level testing.
- E2 Return paths: L2 and L3 solid grounds under every signal, no plane splits or slots under switching or I2C traces (slots from T6 must not cross signal paths). Stitching vias along the board edge every 5 mm or closer, and next to every layer-change via.
- E3 Charger switching loop (CN3791 DRV, L1, D2, C_out): minimal loop area, input and output caps within 3 mm of the IC/inductor, SW node copper as small as possible, no signal traces under or next to L1 on L1/L4, shielded inductor (as specified).
- E4 Antenna: ESP32 antenna at the board edge with a copper keepout on all layers (per Espressif's WROOM-1 guideline), no ground plane, traces or components under or beside it, at least 15 mm clear of battery, solar wiring and metal enclosure parts.
- E5 Cables: sensor cables (SEN66, SHT45) short, twisted/shielded where possible, ferrite bead plus 100 nF at the connector entry if I2C noise or radiated emissions appear. I2C kept at 100 kHz (SCD/SEN6x family), no stubs.
- E6 ESD (pragmatic hobby set): USBLC6-2SC6 (U4) next to the USB-C connector with a short, direct path to ground; USB shield tied straight to GND; SMBJ12A TVS (D4) on the solar input; a second USBLC6 (U5) on SDA/SCL at the SHT45 connector J3 because that cable runs outdoors; battery protected by the cell's own PCM. No ESD parts on J2 (SEN66 sits inside the enclosure on a short cable).
- E7 Power filtering: local 100 nF + 10 uF at every IC and 22 uF bulk on the sensor rail. Ferrite bead FB1 between VSYS and the sensor rail is a DNP footprint (bridged), populated only if fan noise appears on 3V3_SW. No ferrites on the solar input unless the pre-compliance scan shows a problem.

## 4c. USB programming and debugging
- U1 Native USB-C (J1) connected to ESP32-S3 GPIO19/20 gives flashing, serial console and built-in JTAG debugging; BOOT (SW2, GPIO0) and EN (SW1) buttons for download mode.
- U2 USB-C supplies VSYS through D3 and Q1 isolation, and charges the battery through U6 (TP4056). Solar charging is disabled while USB is plugged in.
- U3 Fallback: 1x4 UART0 header J7 (3V3, TXD0, RXD0, GND) and test points on GND, 3V3, 3V3_SW, VSYS, BAT, MPPT.
- U4 CC1/CC2 5.1 kohm to GND so any USB-C source supplies 5 V.
- E8 Layout: analog (battery divider, NTC) kept away from the switching node and routed over solid ground; digital I2C bus kept short and away from the antenna; no floating copper pours (ground-tie or remove).
- E9 Verification: pre-compliance scan (near-field probe), ESD gun test on the connectors, scope check of the CN3791 switch node and 3V3 ripple, WiFi range check with the box closed, before deployment.

## 5. Manufacturing (JLCPCB)
- 4 layers, 1.6 mm, ENIG preferred (flat pads for the SEN66/SH connectors and SSOP/QFN-style parts), impedance-controlled stackup not required (no fast signals) but JLC04161H-7628 or equivalent standard stackup. Minimum 5 boards for assembly.
- Stackup: L1 components + signals + local power pours / L2 solid GND / L3 solid GND / L4 signals + power pours + secondary components if needed. L2 and L3 are unbroken ground planes (no routing, no splits), stitched together with vias. Power is distributed by wide traces/pours on L1 and L4.
- Note: two adjacent ground planes give no inter-plane capacitance benefit. If EMC testing or noise shows a need, a GND / PWR / GND-style alternative can be considered, but the ground-plane requirement above stands.
- SMT assembly top side only. Each unique Extended part adds a $3 fee; Basic parts none.
- Hand-solder: JST-PH connectors and battery holder. Sensors and SHT45 are off-board on cables.
- Deliverables to generate at layout: Gerbers, drill, BOM.csv, CPL.csv with rotation fixes (USB-C, SOT-23-5, SSOP-10 often need checking in JLCPCB's viewer).

## 5a. Cost estimate (updated Oct 2026; USD from JLCPCB's published fees, part prices partly estimated)
JLCPCB fees (Economic PCBA): setup $8.18, stencil $1.53, SMT $0.0016 per joint, $3.07 per unique Extended part (Basic and Preferred Extended free). Standard PCBA instead charges $25.56 setup, $8.21 stencil and $1.53 per unique part (Basic or Extended). Economic supports 2/4/6 layers, single-sided placement only. A 4-layer board under 50 x 50 mm sits in JLCPCB's cheapest tier (about $2 for 5 pcs, per a community cost guide): keep the outline within 50 x 50 mm.

Batch of 5 boards, Economic PCBA (one side, all SMT):
| Item | Estimate |
|---|---|
| Bare 4-layer boards (5 pcs, HASL; ENIG costs extra, not priced) | $2-12 |
| Setup + stencil | $9.7 |
| Extended-part loading, about 8 verified + about 4 likely, 10-14 x $3.07 | $25-45 |
| SMT joints, about 300 x $0.0016 | $0.5 |
| Components, about $7-9 per board x 5 (ESP32 module is the largest line, about $3.5-5.4 each) | $35-45 |
| Subtotal | about $72-112 |
| Shipping to EU, plus 19 % import VAT (DE) | +$15-30 shipping, then VAT |
| Landed total, 5 boards | about $90-145 before VAT, roughly 19 % more with VAT |

Risk: if JLCPCB forces Standard PCBA for the ESP32 module (reported for some ESP32 modules in 2024; check the quote), add about $40-50 (higher setup and stencil, plus a fee on every unique part). Landed total then about $130-190 before VAT.

Per complete station (rest of the system, approx. EUR):
| Item | Estimate |
|---|---|
| SEN66 | 60 |
| SHT45 breakout (STEMMA QT) | 14 |
| Radiation shield (DIY) | 8 |
| Solar panel 6 V / 6 W (est.) | 15 |
| 18650 protected cell (est.) | 8 |
| Vented enclosure, rain baffle, glands (est.) | 20 |
| Hand-solder parts, cables, header (est.) | 8 |
| Subtotal without board | about 133 |

First batch plus one complete station: about EUR 240-300 (5 boards cost about EUR 100-160 landed). Marginal cost of each further station from the leftover boards: about EUR 133. Spread over 5 stations, about EUR 155-165 each. Optional NO2 module (DFRobot SEN0471) adds about EUR 130-160.

## 6. Firmware requirements
- ESPHome or Arduino; SEN66 stop/start measurement; discard first readings after power-up; fan-clean schedule.
- Enable Q2 -> wait for SEN66 warm-up (about 30-60 s for stable PM) -> read -> disable.
- Task watchdog and RTC-timer wake; GPIO hold for Q3 during sleep.
- BQ25798 (PARTS-REVIEW B3/B5, 2026-11-01): at every boot write VREG 3.65 V and ICHG before releasing CE (CE is pulled high =
  charge off). Disable the charger I2C watchdog (WATCHDOG = 00), or re-write VREG before each sleep: on watchdog expiry the
  registers return to POR defaults (VREG 4.2 V, ICHG 1 A); the HY2112 3.75 V cut is only the backstop. Keep ICHG at 1.5 A or
  below (L1 Isat 3 A, B4). After the first BC1.2 detection set AUTO_INDET_EN = 0 so D+/D- stay free for the ESP32 USB.
- I2C: charger bus IO4/IO5, sensor bus IO13/IO14. Set IO13/IO14 to input or low before switching 3V3_SW off.
- Gas: GAS_EN (IO12) high = TPS61023 on; drive GAS_TXD (IO17) low or input while the boost is off.

## 7. Open items before ordering
1. Find LCSC numbers marked TBD in the BOM (0.12 ohm 1206, 39k, 1M, 220 nF, NTC 10k, 3k PROG resistor). The 2N7002 (C8545) and SMBJ12A TVS (C3001973) are now filled in.
2. Confirm CN3791 Figure 1 values and MPPT divider against the actual panel's Vmp.
3. Check Class (Basic/Extended) for SS34, 100k, 4.7k, inductor, tact switch in JLCPCB's parts search.
4. Review SEN66 datasheet for temperature range and recommended pull-ups.
5. EMC protection parts are now in the BOM (TVS D4, second USBLC6 U5, optional FB1 pads, UART header J7, test points). Re-check after prototype EMC scan.
6. 4-layer cost: expect the bare board to cost more than a 2-layer one; quote it in JLCPCB's calculator.
7. Design is not yet laid out, simulated or built: plan one prototype batch and bench-test charger and sleep current before deployment.
