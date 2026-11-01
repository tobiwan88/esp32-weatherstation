# esp32-weatherstation v1: PCB requirements (v0.4, schematic v1, pre-layout)

Rewritten 2026-11-01 for the schematic in `hardware/gen/weatherstation_v1.py` (BQ25798, LFP 26700, TPS63802). v0.3 described
the CN3791/TP4056/AP2112K/18650 design, which is gone. Details and part numbers: `BOARD.md`, `bom.csv`, `PARTS-REVIEW.md`.
Status: needs user acceptance (Gate 1, `GATES.md`).

## 1. Scope
Custom 4-layer PCB (In1 and In2 solid GND), at most 50 x 50 mm: ESP32-S3-WROOM-1-N8, one BQ25798 charger for USB-C and a
6 V solar panel, one 1S LiFePO4 cell (CBAK 26700LT) with HY2112-CB protection, TPS63802 3.3 V buck-boost, switched sensor
rail 3V3_SW, SEN66 (PM, CO2, T/RH, VOC/NOx index) on a GH connector, SHT45 off-board in a radiation shield, a spare Qwiic
port, and an optional ZE25-O3 ozone module on its own 5 V boost. NO2 is out of scope for v1.

## 2. Functional requirements
- F1 Measure PM1/2.5/4/10, CO2, VOC/NOx index (SEN66) and outdoor T/RH (SHT45 in a radiation shield). Optional O3 (ZE25-O3, J8).
- F2 Wake every 10-15 min (longer in winter if the energy budget needs it), measure, send over WiFi (MQTT / Home Assistant),
  deep sleep.
- F3 Charge the cell from USB-C (VBUS, VAC1) or the solar panel (VAC2) through one charger, U3 BQ25798. Each input has its
  own back-to-back N-FET pair (ACFET/RBFET, AO3400A); the chip selects the input. Solar uses the chip's VOC-based MPPT.
- F4 Fail-safe charge enable: CE is pulled high (R20 to +3V3), so the charger does not charge until firmware has written
  the LFP settings (section 6). A blank or reset MCU means no charging. After that, charging stays enabled at all times,
  including deep sleep (CE held low by GPIO hold; user decision 2026-11-01).
- F5 Temperature: NTC TH1 next to the battery connector on the TS pin. Default state: the chip's JEITA limits apply. During an
  awake charge session firmware may take over (cold charging, `charge-policy.md`).
- F6 Report battery voltage, input voltages and currents, charge state and TS through the charger ADC over I2C
  (charger bus); INT to the MCU.
- F7 Program and debug over native USB-C (USB-JTAG and serial on IO19/IO20); RESET (SW10) and BOOT (SW11, IO0) buttons;
  UART0 header J7 as a fallback.
- F8 Sensor rail 3V3_SW switched by Q40 (P-FET), driven by SENSOR_EN (IO11) through Q41; off by default (R40 pull-up).
- F9 Gas module rail GAS_VCC 5 V from U7 TPS61023 on SYS, EN = GAS_EN (IO12), R45 pull-down: off by default, output
  disconnected when off.

## 3. Electrical requirements
- Cell: 1S LFP, 3.20 V nominal, 3.65 V charge, 3.75 V limit, 2.0 V cut-off, 3900 mAh minimum (CBAK 26700LT spec A/03).
- Protection: HY2112-CB with M60/M61 (AO3400A) in the cell minus: overcharge 3.75 V, overdischarge 2.10 V, charge and
  discharge overcurrent by the FET drop. F1 PTC 3 A hold between the connector and the battery node. Cell reverse polarity is
  not protected (keyed JST PH).
- Charge current: ICHG at most 1.5 A (HY2112 charge overcurrent margin and L1 rating, `power_budget.py`). Input current clamp
  ILIM_HIZ = 1.59 A (R15/R16); firmware sets IINDPM per source.
- Order of cut-offs: cell 2.0 V <= HY2112 2.10 V < firmware cut-off 2.4 V (sensors off, long sleep).
- 3.3 V: U2 TPS63802 from SYS, 1.3-5.5 V in (1.8 V to start), 2 A, FB 220k/39k = 3.32 V. Covers the whole LFP range.
- SEN66: 3.15-3.6 V including ripple, peak 0.35 A (datasheet table 12); 22 uF + 22 uF on 3V3_SW at the connector side.
- Gas module: GAS_VCC 5.06 V (FB 510k/68k) to ZE25-O3 Vin (3.7-5.5 V). J8 7-pin, numbered 1:1 to the module (Winsen table 2):
  2 DAC (0.4-2.0 V = 0-10 ppm) to IO7, 3 GND, 4 Vin, 5 RXD (0-3.0 V) from IO17 through R46 1k / R47 10k, 6 TXD (0-3.0 V) to
  IO18, 1 and 7 reserved. Supply current and cable pitch open.
- PV input: 6 V class panel, Voc must stay at or below 10 V cold (SMBJ10A standoff). Reference panel Voltaic P110: Vmp 5.71 V,
  Voc 6.94 V, 9.5 W (`board.yaml` panel).
- I2C: charger bus CHG_SDA/CHG_SCL on IO1/IO2 (RTC I2C pins usable by the ULP RISC-V core) with 10k pull-ups to +3V3; sensor bus SEN_SDA/SEN_SCL on IO13/IO14 with 10k
  pull-ups to 3V3_SW (no back-power into unpowered sensors).
- MCU pins: IO1/IO2 charger I2C, IO7 GAS_DAC, IO9 CHG_CE, IO10 CHG_INT, IO11 SENSOR_EN, IO12 GAS_EN, IO17 GAS_TXD, IO18 GAS_RXD, IO19/IO20 USB, IO43/IO44 UART0.
  Strapping pins (IO0, IO3, IO45, IO46) carry no load except BOOT on IO0.
- USB: CC1/CC2 5.1k to GND (sink), D+/D- through 22 ohm to the ESP32 and shared with the BQ25798 D+/D- (BC1.2 detection once,
  then AUTO_INDET_EN = 0).
- Deep-sleep board current target: under 100 uA with 3V3_SW and GAS_VCC off (TPS63802 Iq 11 uA, FB divider 13 uA; measure
  the charger and HY2112 share on the first board).
- Energy: average about 10.8 mA at a 600 s cycle, 0.96 Wh/day; 12 days autonomy from 80 % of 3900 mAh; worst-month solar
  4.2 Wh/day with a 10 W panel (`power_budget.py`).

## 4. Environmental / mechanical
- Outdoor station in Germany: -20 to +40 C ambient. Cell: discharge -40 to 60 C, charge -10 to 50 C (spec). SEN66 recommended
  10-40 C (accepted winter limit, readings outside are flagged).
- Vented enclosure with rain baffle for the PM inlet; board conformal-coated except connectors and the SEN66 inlet.
- Board at most 50 x 50 mm, M3 mounting holes, ESP32 antenna at the board edge with a keepout on all layers.

## 4a. Thermal
- T1 Heat sources: BQ25798 + L1 (up to 1.5 A charge), TPS63802 + L4, TPS61023 + L5 when on, ESP32 during WiFi TX, SEN66.
  Group the converters in one heat corner, away from TH1, the antenna and the sensor connectors.
- T2 TH1 next to J6 and the cell holder, outside the heat corner; sense trace not under a converter. TH1 reads the board next
  to the cell: measure the TH1-to-cell offset on the samples (`charge-policy.md`).
- T3 J2/J3/J4 on the side opposite the heat corner. The SHT45 is off-board in a radiation shield.
- T4 BQ25798 exposed pad, TPS63802 GND bar and ESP32 EP on via arrays into both GND planes.
- T5 Keep the board temperature rise under 25 C at 1.5 A charge in the closed enclosure; verify on the first board.
- T6 Optional milled slots between the heat corner and the sensor side if measurement shows coupling; slots must not cut
  return paths.

## 4b. EMC
- E1 Targets (personal use): EN 55032 Class B emissions, IEC 61000-4-2 +/-4 kV contact / +/-8 kV air on external ports.
  Selling in the EU would need RED testing of the whole product.
- E2 In1 and In2 solid GND, no splits under signals; stitching vias along the edge every 5 mm or closer.
- E3 Switching loops (BQ25798 SW1/SW2 + L1 + PMID/SYS caps, TPS63802, TPS61023) as small as the datasheet layouts; input caps
  next to the pins; no signals under the inductors on the outer layers.
- E4 Antenna keepout on all layers per the WROOM-1 guideline, at least 15 mm from the cell, the PV wiring and metal parts.
- E5 ESD: U4 USBLC6-2SC6 at J1 (D+/D-, VBUS); U5 USBLC6-2SC6 on SEN_SDA/SEN_SCL (outdoor SHT45 cable); D1 SMBJ10A across
  PV+/PV- before the common-mode choke L3 (CMF4532F-900, 90 ohm at 100 MHz, 3 A), C2 after it.
- E6 I2C at 100 kHz, short stubs. Ferrite plus 100 nF at a cable entry only if a scan shows a problem.
- E7 Analog (TS divider, NTC) over solid ground, away from switch nodes.
- E8 Verification: near-field scan, ESD gun on the connectors, scope on the switch nodes and +3V3 ripple, WiFi range with the
  box closed.

## 4c. USB programming and debugging
- U1 Native USB-C J1 on IO19/IO20: flashing, serial console, JTAG. RESET and BOOT buttons.
- U2 USB also powers the board and charges the cell through the BQ25798 (after firmware releases CE).
- U3 UART0 header J7 (3V3, TXD0, RXD0, GND); test points TP1 +3V3 and TP2 SYS.

## 5. Manufacturing (JLCPCB)
- 4 layers, 1.6 mm, ENIG preferred; standard stackup (JLC04161H-7628 or similar), no impedance control needed.
- Stackup: F.Cu parts, signals, power pours / In1 GND / In2 GND / B.Cu signals and power pours. Planes unbroken and stitched.
- SMT top side only (Economic PCBA if JLCPCB accepts the ESP32 module there). Hand-soldered: J5-J8 (JST PH, header).
- Deliverables at layout: Gerbers, drill, BOM, CPL with checked rotations; check exports for metadata before committing.

## 5a. Cost (2026-11-01, `bom.csv` and `hw-check.sh --stock`)
- Parts per board about USD 13.76; Extended fee 15 x USD 3.07 = USD 46.05 per order. 5 boards: about USD 115 in parts plus
  fees, before PCB, setup, stencil, shipping and VAT (Economic PCBA setup about USD 8.18 + stencil USD 1.53).
- Risk: Standard PCBA for the ESP32 module adds about USD 40-50 (check the quote).
- Per station, outside the board (estimates): SEN66 about EUR 60, SHT45 breakout about EUR 14, radiation shield about EUR 8,
  10 W 6 V panel EUR 20-60 (Voltaic P110 USD 65), CBAK 26700LT cell and holder (price open), enclosure about EUR 20, cables EUR 8.

## 6. Firmware requirements
- SEN66: start measurement after 3V3_SW is on, discard the first readings, stop before 3V3_SW off; fan-clean schedule.
- Enable 3V3_SW (IO11) -> SEN66 warm-up (about 30-60 s for stable PM) -> read -> disable. Task watchdog and RTC-timer wake.
- BQ25798 (PARTS-REVIEW B3/B5, 2026-11-01): at every boot write VREG 3.65 V and ICHG before releasing CE (CE is pulled high =
  charge off). Disable the charger I2C watchdog (WATCHDOG = 00), or re-write VREG before each sleep: on watchdog expiry the
  registers return to POR defaults (VREG 4.2 V, ICHG 1 A); the HY2112 3.75 V cut is only the backstop. Keep ICHG at 1.5 A or
  below (L1 Isat 3 A, B4). After the first BC1.2 detection set AUTO_INDET_EN = 0 so D+/D- stay free for the ESP32 USB.
- MPPT: EN_MPPT = 1, VOC_PCT 0.8125 for the reference panel (Vmp/Voc 0.823).
- Charging always on (user, 2026-11-01): CE low and held through deep sleep; TS_IGNORE = 0 in sleep (chip JEITA). Cold
  charging below the chip's limit only in an awake session or by the ULP core (`charge-policy.md`).
- I2C: charger bus IO1/IO2, sensor bus IO13/IO14. Set IO13/IO14 to input or low before switching 3V3_SW off.
- Gas: GAS_EN (IO12) high = TPS61023 on; drive GAS_TXD (IO17) low or input while the boost is off.
- Battery: below 2.4 V turn sensors off and sleep long; report the charger ADC values each cycle.

## 7. Open items before ordering
1. ZE25-O3 supply current and cable/connector pitch (J8).
2. CMF4532F-900 land pattern and pinout from a HongyeX drawing (the footprint uses the EMTEK drawing).
3. JLCPCB Standard vs Economic PCBA for the ESP32 module (quote).
4. Sensor set: SEN66 cost; cheaper alternatives under research (2026-11-01).
5. Layout not started; plan one prototype batch and bench-test charging, sleep current and the TH1-to-cell offset.
