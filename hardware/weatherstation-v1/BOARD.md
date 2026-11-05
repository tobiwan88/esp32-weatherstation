# weatherstation-v1: board notes

Board-specific facts for the board-neutral skills (`hw-base`, `kicad-schematic`, `kicad-layout`, `hw-parts`).
Numbers the scripts check live in `board.yaml`, `critical.yaml` and `parts/`. Full requirements: `REQUIREMENTS.md`.
BOM: `bom.csv` (JLCPCB columns plus Class/Status/notes). Order checklist: `ORDER.md`.

## Board
Solar + USB-C powered ESP32-S3 air-quality weather station, about 50 x 45 mm, 4 layers (In1 and In2 both solid GND),
JLC04161H-7628, JLCPCB Economic PCBA (one side, SMT; connectors J5/J6/J7 and the battery are hand-soldered).
ESP32-S3-WROOM-1-N8 (C2913198), TPS63802 3.3 V buck-boost, BQ25798 charger (USB + PV), HY2112-CB 1S protection, one 26700 LFP cell,
switched 3V3_SW sensor rail (Q40), switched 5 V rail 5V_SW (TPS61023), PMS7003 PM sensor on J2 (5V_SW, UART IO4/IO5), SHT45 on
its own small board in a radiation shield (cable to J3), spare Qwiic port, optional SCD41 CO2 (U8, DNP) and ZE25-O3 (J8).
USB-C = programming, debug (native USB-JTAG) and charging.
Status: schematic v1 generated (`hardware/gen/weatherstation_v1.py`, ERC 0 errors, net check OK). Layout: first placement.

## Sensor set (2026-11-01, user: option A)
SEN66 dropped for cost; see `sensors.md`. PMS7003 (PM) + own SHT45 board + SCD41 footprint (DNP) + ZE25-O3 (optional).
No VOC/NOx index (needs continuous 1 Hz sampling). Sections below that mention the SEN66 are history.

## Cell choice and cost (2026-11-01)
- **Latest decision (user): CBAK 26700LT with firmware-managed cold charging** (`charge-policy.md`). The standard 26650
  bullet below is superseded. The chip's temperature checks are switched off during a session only; sleep and default keep them.
- Accepted residual risk (user): no hardware cold or hot stop during a session. Mitigations in `charge-policy.md`.
- Earlier bullet, superseded: standard LFP 26650, 0-45 C charge.
- **Cell: standard LFP 26650, 0-45 C charge** (not the 26700LT). Reason: the BQ25798 cold cut-off is fixed at about 0 C; no
  verified charger IC allows cold charging (see cells.md).
- **CBAK 26700LT spec A/03 read (2026-11-01, `datasheets/CBAK_26700LT_A03.pdf`):** 3900 mAh min, 3.65 V standard charge
  (limit 3.75 V), 2.0 V cut-off, charge -10..50 C at 0.2C below 0 C, 0.5C at 0-20 C, 1C at 20-40 C; -20 C capacity >= 80 %.
  board.yaml cell values match.
- **Cost basis:** the parts cost is per board. The Extended fee is per unique part per order, so it is paid once and is shared by
  all boards in the order. Recommendation: cost the order for **5 boards** (the fee is then spread over five) and use 1 board only
  for a prototype.
  - Parts per board (JLCPCB unit price from jlcparts.py, no volume break, bom.csv 2026-11-01): **USD 13.76**.
  - Extended fee: 15 unique Extended parts x USD 3.07 = **USD 46.05 per order** (8 passives moved to Basic on 2026-11-01:
    C3/C4, C21, R15, R17, R18, R43, R52, R53, R61; no Basic power inductor or NTC exists, so L1/L4/L5 and TH1 stay Extended).
  - 1 board: 13.76 + 46.05 = **USD 59.81** (plus PCB and assembly).
  - 5 boards: 5 x 13.76 + 46.05 = **USD 114.85**, i.e. USD 22.97 per board (plus PCB and assembly).
  - Not in these numbers: PCB fabrication (4-layer, 50 x 50 mm), assembly labour, hand-soldered parts (J5-J8, J7, test points),
  the battery holder, cells, panel, enclosure, sensors. Get the JLCPCB quote for 5 and 1 boards before ordering.
- Charger cold rule with the 26650: the chip suspends below about 0.5 C (matches the cell's 0 C), and reduces charge from
  45 C (matches the cell's 45 C). Limit: TH1 senses the board, not the cell (see the NTC note below).

## Power and EMC review (2026-11-01, after the cell spec sheets; updated same day)
Cell values: `cells.md`. **Decision (2026-11-01): v1 is LFP only (26700LT, 3.2 V nominal).** The sodium 32140NH 7 Ah was dropped: its
3.35 V limit and 1.5 V cut-off are outside the HY2112-CB thresholds. Sections older than this one that mention 32140NS, 3.95 V,
the CN3791/TP4056 or the AP2112K are superseded.

### Changes made (schematic regenerated, ERC: 2 footprint warnings only)
- **3.3 V: AP2112K replaced by TPS63802DLA (C2845237) buck-boost.** The LDO needs about 3.55 V at its input (3.3 V + 250 mV
  dropout at 600 mA); battery-only SYS follows the cell (LFP 3.2 V nominal, sodium 3.0 V), so the old rail dropped out near 3.5 V.
  TPS63802: input 1.3-5.5 V (1.8 V to start), 2 A, 11 uA Iq, output 3.3 V from R52 220k / R53 39k (0.5 V x (1 + 220/39) = 3.32 V; Basic parts, datasheet table 10-5 uses 511k/91k),
  L4 0.47 uH WPN201610HR47MT (2.7 A, C97009), C41 22 uF output (table 10-1), C40 10 uF input, MODE low (power save).
  Symbol: project library `hardware/gen/lib/weatherstation.kicad_sym`, written by `hardware/gen/build_symbols.py` from the
  datasheet pin table (VIN 10, EN 1, MODE 2, AGND 3, GND 8, VOUT 6, L1 9, L2 7, FB 4, PG 5). EN is tied to SYS (always on).
  PG is left unconnected. Footprint: `weatherstation:VSON10_DLA_custom` (open: the DLA land pattern is not in the KiCad library).
- **1-cell protection: HY2112-CB (C168764, Extended, about 19800 in stock)** (U6). Datasheet DS-HY2112 V08 read (table 1, section 9
  and section 10 wiring). Overcharge 3.75 V (release 3.60 V, 1.3 s delay), overdischarge 2.10 V (release 2.30 V), discharge
  overcurrent 200 mV, charge overcurrent -200 mV, short circuit 0.85 V. Two AO3400A (C20917, Basic) in the pack negative:
  M60 discharge (OD gate), M61 charge (OC gate), common source at PB_MID, drains to the cell minus (BAT_N, VSS) and to system GND.
  VDD from the cell plus through R60 100 ohm and C60 0.1 uF; CS through R61 2 kohm to GND (datasheet maximum 2 kohm).
  Datasheet rule: after an overcharge trip the release needs a load or the charger removed (section 11.2), so a fault latches.
- **Charge current 1.5 A (was 2 A):** the HY2112 charge overcurrent trips at -170 mV minimum. 2 x 48 mOhm x 2 A = 192 mV would
  trip it. 1.5 A gives 144 mV. `power_budget.py` checks this every run. The panel supplies about 1 A anyway.
- **Charger VREG check:** BQ25798 VREG accuracy from the datasheet (section 6.5, VREG_ACC -0.45 % to +0.95 %, specified at 4.2 V):
  worst case 3.65 V + 35 mV = 3.685 V, below the 3.75 V cell limit. Note: the chip's own battery overvoltage stop (VBAT_OVP) is
  104 % of VREG = 3.80 V at VREG 3.65 V, which is above the cell's 3.75 V limit: HY2112 is the backstop, not the chip.
- **Temperature: NTC TH1 on the board, next to the battery connector J6.** TH1 = NCP18XH103F03RB (Murata 10k, B 3434 K,
  C13564, Extended, about 142k in stock). It sits on the charger sheet at the same column as J6, so both are placed together
  and both are hand-soldered or reflow-soldered as the BOM says. TS divider R17 5.1k / R18 30k (Basic; was 5.23k / 30.1k), NTC TS-to-BAT- (BAT- is the
  cell minus, so the NTC has no current through the pack path).
  Verified against the BQ25798 JEITA table (section 6.5, 103AT rows): with 5.1k/30k and B 3434 the TS ratio crosses VT1 73.3 % at 1.9 C,
  VT2 68.4 % at 11.2 C, VT3 44.8 % at 45.3 C, VT5 34.2 % at 60.8 C (5.23k/30.1k: 1.0 / 10.3 / 44.4 / 59.9 C). A B 3950 NTC would move the cold
  cut-off to about +3 C, so the B value is part of the design: keep 3380-3455 K.
  Limit: TH1 senses the board next to the cell, not the cell. Keep the holder thermally close to TH1 (same board area, not
  under the charger or the buck-boost) and measure the offset with the samples.
  The chip then applies: no charge below about 0.5 C, 20 % current 0-10 C, reduced charging from 45 C, stop at 60 C.
  The NTC plus firmware is the temperature protection; there is no separate temperature IC.
- **Cell PTC F1** SMD1812P300TF (C21004, Extended): 3 A hold, between the battery connector and the battery node. Overcurrent backup.
- **EMC on the PV input:** common-mode choke L3 CMF4532F-900-2P-T (C963746, Extended, 90 Ohm at 100 MHz, 3 A, 70 mOhm; was the 1 A -102, too small
  for a 10 W 6 V panel) on PV+ and PV-; the TVS D1 (SMBJ10A, was SMBJ24A, see PARTS-REVIEW A6) moved in front of it (across PV+ and PV-); C2 0.1 uF after it. Ratings confirmed from the HongyeX spec D2
  (the LCSC maker is HongyeX, not EMTEK). Open: land pattern and pinout still from the EMTEK T-0602-102D drawing; check them
  against a HongyeX drawing before layout. SMBJ10A (Littelfuse rev. 07/04/25) and USBLC6-2 (ST DS4260 rev 7) read: values as designed.

### Still open (decisions and checks)
1. **Sodium: dropped for v1** (see the decision above). Re-open only with a new cell spec and a matching protection part.
2. **Firmware and protection:** CE is pulled high (R20), so no charge happens until firmware releases it. Firmware must write
   VREG 3.65 V before releasing CE. If CE were released with the 4.2 V default, the cell would charge to 4.2 V until HY2112 trips
   at 3.75 V (cell not damaged by that trip alone, but the cell is over its limit for the time it takes). The HY2112 is the
   hardware backstop for LFP; it is not a substitute for the firmware order.
3. **Cold charge:** LFP allows 0.2C (0.8 A) below 0 C and 0.5C (1.95 A) at 0-20 C. The chip suspends charging below about 0 C
   (T1 not a register) and charges at 20 % (0.3 A) from 0 to 10 C, both inside the cell limits. Above 10 C it charges at 1.5 A. The rule holds only if the
   chip's cold threshold is at or above 0 C at the cell: measure the offset between TH1 and the cell.
4. **Hot:** LFP charge stops at 50 C (spec); the chip's warm band starts at 45 C (TS_WARM default). The chip's hot-stop threshold
   is not recorded in this review: check figure 7-11 before relying on it.
5. **Reverse polarity** of the cell is not protected (JST PH keyed). PV reverse is blocked by the ACFET/RBFET pairs (N-channel, back-to-back; body diodes oppose each other).
6. **Open technical items:** L1 Isat (VLS252010 candidate); PV: reference panel Voltaic P110 (Vmp 5.71 V, Voc 6.94 V, about 7.9 V at -20 C; board.yaml panel), Voc must stay at or below 10 V (SMBJ10A standoff); avoid "6 V" panels rated Vmp 9 V / Voc 11 V; TPS63802 and HY2112
   footprints (to verify against the land patterns); `power_budget.py` path resistance 0.15 ohm is an assumption.
   Resolved 2026-11-01: ACFET/RBFET are N-channel (datasheet 7.3.5: ACDRV 5 V above the common source), so AO3401A was replaced by
   AO3400A (C20917). L3 pinout and footprint come from EMTEK T-0602-102D (winding 1→2 and 4→3).

## Schematic v1 architecture (2026-10-31, supersedes the older charger, LDO and cell sections below)
- One charger for USB-C and PV: BQ25798 (C2876593). USB and PV each have a back-to-back N-FET pair (ACFET/RBFET, AO3400A
  C20917) into VBUS; PV is protected by SMBJ10A (6 V class panel). CN3791, TP4056, Q1/D3 (ideal diode), CN3791 FETs, Q3/Q4/Q5 are removed.
- Battery: BQ25798 BATFET (integrated) to SYS; J6 battery connector (hand-soldered holder). Battery voltage and temperature
  are read over I2C (BQ25798 ADC and TS), so the battery divider R16/R17 is removed.
- Variant values (written by firmware over I2C at every boot, before CE is released): VREG 3.65 V (LFP only; the sodium
  value is dropped); ICHG 1.5 A (was 2 A, see the review); VSYSMIN 4.0 V. Cell values: `cells.md`.
  PROG 3.0 kohm sets 1S and 1.5 MHz. CE is held high by R20 to +3V3 (charge disabled) until firmware releases it.
- Cold: the chip suspends charging below about 0 C (default; T1 is not a register). Between 0 and 10 C it charges at 20 %
  (JEITA_ISETC default). TS network 5.1k / 30k / 10k NTC (Basic parts; datasheet 5.24k / 30.31k). With B 3434 the thresholds move about +0.9 C: cold 1.9 C, cool 11.2 C, warm 45.3 C, hot 60.8 C (5.23k/30.1k gave 1.0 / 10.3 / 44.4 / 59.9 C); cold shifts to the safe side.
- 3.3 V: TPS63802 buck-boost from SYS (2026-11-01; the AP2112K LDO was dropped, see the review). 3V3_SW: AO3401A switch (Q40) with 2N7002 enable.
- Gas (ZE25-O3, 3.7-5.5 V; PARTS-REVIEW A5, decided 2026-11-01): J8 (and since option A the PMS7003 J2) on 5V_SW from a TPS61023 boost U7 (C919459) on SYS,
  5.06 V (FB 510k/68k, VREF 0.595 V). EN = BOOST_EN (IO12) with R45 100k pull-down: off by default; off = input and output
  disconnected, 0.1 uA. L5 1 uH (same part as L1), 10 uF in, 2 x 22 uF out (datasheet SLVSF14B figure 8-1).
  Firmware: drive GAS_TXD (IO17) low or set it to input while the boost is off (else the ESP32 back-powers the module RX).
- I2C: two buses (PARTS-REVIEW A4, decided 2026-11-01). CHG_SDA/CHG_SCL (IO1/IO2, moved 2026-11-01 from IO4/IO5 to the RTC I2C pins for the ULP core): BQ25798 only, R54/R55 10k to +3V3, readable
  with the sensors off. SEN_SDA/SEN_SCL (IO13/IO14): SHT45 cable, spare port, SCD41 (DNP), R50/R51 10k and U5 VBUS on 3V3_SW, so nothing
  is back-powered. Firmware sets IO13/IO14 to input or low before it switches 3V3_SW off.
- GPIO map (module pin, GPIO): LED1/LED2 34/35 (IO41/IO42); CHG_SDA/CHG_SCL 39/38 (IO1/IO2); SEN_SDA/SEN_SCL 21/22 (IO13/IO14); CHG_CE 17 (IO9); CHG_INT 18 (IO10); SENSOR_EN 19 (IO11);
  PM_TXD 4 (IO4, via R48 1k to J2.7); PM_RXD 5 (IO5, J2.9); PM_SET 6 (IO6, via R49 1k to J2.10); BOOST_EN 20 (IO12); GAS_TXD 10 (IO17, to J8.5 through R46 1k / R47 10k = 3.0 V); GAS_RXD 11 (IO18, J8.6); GAS_DAC 7 (IO7, ADC1, J8.2); USB D-/D+ 13/14 (IO19/IO20); UART0 36/37; BOOT 27 (IO0).
- Open items that the schematic does not settle: L1 Isat (VLS252010 candidate, 1 uH, needs 2.5 A+ check), ZE25-O3 cable pitch
  (pinout from Winsen table 2: J8 7-pin 1:1; supply current 10 mA at 5 V, user 2026-11-04), SMBJ10A vs PV Voc (6 V class panel only; Voc at or below 10 V). ACDRV wiring: common-source
  N-FET pair with ACDRV on the gates (datasheet 7.3.5); Table 7-7 detail still to check on the final netlist.
- Generated files: `weatherstation-v1.kicad_sch` (root) and six sheets (`input`, `charger`, `battery`, `mcu`, `rails`, `sensors`). Block layout: `hardware/gen/layout_v1.py`.
  `bom.csv` is written by the generator from the same PARTS list. Run:
  `uv run --package weatherstation-hardware python hardware/gen/weatherstation_v1.py hardware/weatherstation-v1`.

## Commands
- Gate: `scripts/hw-check.sh [--strict] [--stock --qty N]`: profile files parse, `calc/bom_check.py`, `calc/power_budget.py`
  (and `calc/critical.py` once a routed `.kicad_pcb` exists). Must print `hardware checks: OK` before commit and order.
  `MISSING` rows are open inputs (fill them from the source); `--strict` (order time) makes them fail.
- BOM only: `python3 hardware/calc/bom_check.py hardware/weatherstation-v1 [--stock] [--qty 5] [--strict]` (`--stock` needs network).
- Power/charger/energy: `python3 hardware/calc/power_budget.py hardware/weatherstation-v1` (`--selftest` for the formulas).
- Stock and price of one part: `python3 hardware/tools/jlcparts.py C123456` or `-s "keyword" -n 20`.
- Schematic (after `source scripts/kicad-env.sh`): generator `uv run --package weatherstation-hardware python hardware/gen/weatherstation_v1.py hardware/weatherstation-v1`;
  review loop `scripts/schematic-review.sh` (ERC, geometry, PNGs in `hardware/out/review/`); pin positions for hand routes
  `uv run --package weatherstation-hardware python hardware/gen/pins.py <Sheet> [ref|net ...]`.
- Second board (outdoor SHT45): `uv run --package weatherstation-hardware python hardware/gen/sht45_board.py` (`hardware/sht45-board/`).
- Layout: `hardware/tools/build_pcb.sh --no-schematic` (placed board from the generator), then
  `hardware/tools/route_v1.sh` (routes it in place, prints DRC errors; `KRT_ARGS=...` to try router settings).
- Reference pipeline (schematic generator, placement, KRT routing, fab package) from desk_notifier: `hardware/reference/desk_notifier/`
  (copy and adapt, see `hardware/PLAN.md`; the board-neutral skills assume that layout).

## Decisions (why)
- 4 layers with two solid GND planes (user requirement): EMC, thermal spreading, one cheap tier under 50 x 50 mm.
  Power is distributed on the outer layers. Two adjacent GND planes give no plane capacitance: a GND/PWR/GND stackup is the fallback.
- LDO (AP2112K), not a buck: the load is a few mA average and the rail only needs to hold 3.15 V for the SEN66; battery usable 3.5-4.2 V (cutoff 3.5 V).
  `calc/power_budget.py` reports the dropout headroom at the cutoff.
- Two chargers on one cell: CN3791 (solar MPPT) and TP4056 (USB). USB has priority by hardware (Q4 pulls the CN3791 MPPT pin low
  while VBUS is present), so they never fight. Q3/Q5 (firmware CHG_INH) stop both when the cell is cold; default (MCU off) = charging allowed
  so a flat cell recovers. The CN3791 has no temperature pin; the TP4056 TEMP pin is grounded (its fixed NTC window does not fit).
- Battery path: Q1 (P-FET with gate = VBUS) isolates the cell from the rail while USB is plugged in; D3 feeds the rail from USB.
  The cell is charged only by U3/U6, never through D3.
- SHT45 off-board in a radiation shield: board heat (charger, LDO, SEN66 fan) cannot bias outdoor T/RH.
- Sensor rail switched by Q2 (P-FET, pull-up gate = off in deep sleep); I2C pull-ups on 3V3_SW so nothing is back-powered.
- NO2 not on this revision (electrochemical cell is 2 years life, ozone cross-sensitivity, about 130-300 EUR); the J4 spare Qwiic port was dropped for board area (2026-11-01).
- ESD/EMC set kept pragmatic: USBLC6 on USB data and on the outdoor SHT45 I2C cable, SMBJ12A on the solar input, FB1 DNP footprint.

## Outdoor sensor decision (2026-10-31)
- PM sensor: **SEN63C** (PM, CO2, T/RH; no VOC/NOx), the lowest-cost Sensirion option on the 3V3_SW rail. About EUR 23 ex VAT
  (SOS 23.30, Farnell 23.89); the SEN66 is about EUR 71. Same 6-pin SEN6x pinout, so J2 stays. Supply 3.15-3.6 V,
  75 mA avg / 100 mA max, peak 140 / 200 mA (SEN6x datasheet Table 12). Recommended 10-40 C (accepted winter limit).
  CO2 accuracy is weaker than the SEN66: +/-(100 + 10 % m.v.), 12 h initial operation (datasheet Table 6). Revisit if CO2 matters.
- Rejected for v1: SPS30 and SDS011 / PMS5003 need a 5 V rail (SPS30 4.5-5.5 V, 55 mA avg, 80 mA peak, Sensirion catalogue).
  SEN65 has no EUR price in DE (US list about USD 28).
- Gas: an O3/NO2 module connector is added in v1 (not populated). Candidate: Winsen ZE25-O3 (manual v1.4, verified): **supply 3.7-5.5 V, no reverse protection**, so it cannot run on the 3V3_SW rail (3.3 V) or on a cell at the 3.5 V cutoff. UART is 3.0 V logic (compatible with the ESP32), 9600 baud, 0-10 ppm, warm-up <= 3 min, operating -10 to +55 C, 15-90 % RH, 2-year life in air. NO2 and Cl2 are interference gases, so it is O3-only in practice. Adding it needs a 5 V rail (boost from the cell) on J8, which the board does not have yet; decide with the PM rail question. NO2 electrochemical modules stay out of v1.
- The SEN66 VOC/NOx and CO2 accuracy are indoor-oriented; the outdoor station does not need them.
- Sourcing policy (2026-10-31): on-board parts must be assemblable by JLCPCB (LCSC stock, Basic or Extended). Off-board modules
  (sensors, gas module, panel) may come from AliExpress; counterfeit risk accepted for alternatives. No German distributor required.
- Gas connector power: J8 (ZE25-O3, 3.7-5.5 V) gets its own 5 V rail from a boost on the cell. Enable from an MCU GPIO, default off,
  so the boost does not draw in deep sleep. Boost candidates in JLCPCB stock (datasheets not yet read, values **unverified**):
  TPS61023DRLR (C919459, 45k, SOT-563), TPS61040DBVR (C7722, 31k, SOT-23-5), TPS61088RHLR (C87357, 5k, VQFN-20).
  Check light-load efficiency and minimum input at the 3.2-3.5 V cell voltage before choosing. Add to BOM and power budget
  once the ZE25-O3 supply current is known (the manual does not state it; it is an open input).
  Read 2026-10-31 (TI datasheets): TPS61023 (0.5-5.5 V in, 2.2-5.5 V out, 0.1 uA shutdown, true disconnect in shutdown,
  about 20 uA no-load) is the choice. TPS61040 has no disconnect in shutdown (output follows input through the inductor and
  Schottky, datasheet 6.3.3), so it needs a P-FET load switch. TPS61088-Q1 (10 A, 2.7-12 V, automotive grade, large external
  network) is overkill and is dropped.
  ZE25-O3 current: 10 mA at 5 V (user confirmed 2026-11-04; the manual pages read (1-6) do not state it). board.yaml
  `o3_ma` = 20 mA at the cell. Duty-cycled (4 min per hour): 18.2 mA average, 1.40 Wh/day, 7.1 days autonomy.
  Continuous (if the 24-48 h warm-up rules out duty cycling): about 37 mA average, 2.8 Wh/day, 1.48x margin on the
  4.2 Wh/day December yield, 3.5 days autonomy.
  At 10 mA continuous from the cell, the gas module adds about 1.4 Wh/day (boost efficiency about 85 %, assumed).
  The manual also requires a 24-48 h warm-up at first power-on, so duty-cycling it is not viable.
  Energy-based check (PVGIS-SARAH3 hourly, 2005-2023, 45 deg, December, 0.7 performance ratio, 3000 mAh cell from 80 %):
  base load (0.96 Wh/d) never runs the cell flat (0 of 19 years, Hamburg and Frankfurt, 6 W or 10 W).
  base + gas (2.36 Wh/d): 6 W panel runs flat in 5 of 19 Decembers in Hamburg (0 in Frankfurt, worst SOC 11 %);
  10 W panel runs flat in 0 of 19 in either city (worst SOC 39 % Hamburg).
  Decision: with a 10 W panel the ozone module fits the energy budget; with 6 W it does not in Hamburg.
  Not modelled: cold-cell derating and the 0 C charge inhibit (see below).
  Cold inhibit: about 16-19 % of December in-plane solar energy falls on sunlit hours with air below 0 C (PVGIS T2m).
  Charging is blocked below 0 C (Q3/Q5 inhibit), so that share is lost, possibly more than cloud losses. The enclosure cell
  temperature may run above air temperature in sun; to be measured.

## Subzero-charge cell candidates (2026-10-31) [SUPERSEDED 2026-11-01: LFP only, values in cells.md]
- Cells from the maker (CBAK, product pages en.cbak.com.cn/products_details/27.html and /38.html). The user opened a cell and
  confirmed the claimed charge window; treat as user-verified, not datasheet-verified.
  - 26700LT (LFP, 3.2 V nominal, 4 Ah): charge -10 to +50 C, discharge -40 to +60 C, 0.5C standard, 1C max, end of charge 3.65 V.
  - 32140NS (sodium-ion, 3 V nominal, 10 Ah): charge -20 to +65 C, discharge -40 to +65 C, 0.5C standard, 3C max, end of charge 3.95 V.
    Discharge cutoff not listed.
- Charger: TI BQ25798 (rejected: fixed 0 C cold cutoff). CN3795 (Consonance datasheet verified): multi-chemistry (Li-ion, LiFePO4,
  LTO), 6.6-30 V input, MPPT pin regulated to 1.205 V, charge current 120 mV / Rcs, end-of-charge set by the FB divider (formula
  not read yet), C4 = 220 nF. No TEMP pin, so cold control must be external (MCU + NTC + MOSFET on the MPPT pin, like Q3 now).
- Open: cold-charge current limit (the vendor page gives only the window; the 0.5C value is for normal temperatures), the FB
  divider formula for 3.65 V and 3.95 V, and the 32140NS discharge cutoff.
- CN3795 formulas (datasheet, verified): VREG = 1.205 x (1 + R1/R2) + 60 nA x R1 (FB divider, max 25 V); ICH = 120 mV / Rcs;
  VMPPT = 1.205 x (1 + R5/R6); trickle below 66.5 % of VREG at 17.5 % current; termination at 16 %; recharge at 58.8 %;
  loop compensation 220 nF + 120 ohm from COM to GND (matches C4 and R4).
- **UVLO: the charger is off when VCC is below 6.5 V.** A 6 V-class panel regulates to about 5.9 V, so it cannot work with the
  CN3795. Use a 12 V-class panel (Voc about 21-24 V, below the 30 V input maximum) with the MPPT divider set to about 17 V.
- Worst-case design (user rule: lower C as the maximum charge current): LFP 26700LT 0.5C = 2 A; sodium 32140NS 0.5C = 5 A,
  above the CN3795's 4 A. The panel limits the real current to about 0.6-1 A anyway.
- Both chemistries sit below 3.3 V for part of their discharge (LFP 3.2 V nominal, sodium 3.0 V nominal), so the LDO cannot hold
  3.3 V. A buck-boost is required for either cell.

## Cell variants on one board (2026-10-31) [SUPERSEDED 2026-11-01: LFP only]
Variant A = LFP 26700LT (samples in hand). Variant B = sodium 32140NS (not yet sourced). Same PCB; per variant only the BOM
value of R1 (FB divider) and the battery holder (hand-soldered BT1) change. Charger, inductor, Rcs and buck-boost are common.

| Item | A: LFP 26700LT | B: sodium 32140NS |
|---|---|---|
| Charge end voltage (CN3795 FB) | R1 20.5 k, R2 10 k: 3.68 V | R1 22.6 k, R2 10 k: 3.93 V (limit 3.95 V) |
| Charge current design (Rcs 0.06 ohm, 120 mV / Rcs) | 2 A (0.5C, lower C rating) | 2 A (set below its 0.5C = 5 A and the 4 A CN3795 limit) |
| Cold charge window (vendor page, user-verified) | -10 to +50 C | -20 to +65 C |
| Cell cut-off to firmware | TBD: measure with the samples | TBD: not published, measure |
| Holder (BT1, hand-soldered) | 26700 holder | 32140 holder |
| Energy (nominal) | about 12.8 Wh | about 30 Wh |

Common solar path (CN3795, from a 12 V-class panel, MPPT pin R5/R6 about 130 k / 10 k for Vmp about 17 V):
- Inductor 22 uH with Isat at least 3 A (candidate SWPA8040S220MT, C15857, 2k stock, not read).
- Rcs 0.06 ohm, 2512, 1 W (2 A worst case; the panel limits the real current to about 0.6-1 A).
- P-FET on DRV with Vds at least 30 V (the panel's Voc is 21-24 V; the CN3795 input maximum is 30 V).
- Input capacitance rated for 35 V or more. Loop compensation 220 nF + 120 ohm (C4, R4 as in the BOM).
- The CN3795 has no TEMP pin: the cold rule is in firmware, a MOSFET on the MPPT pin (like Q3 now) and an NTC.

3.3 V rail: TPS63802 (C2845237, 2.4k stock, datasheet read). Input 1.3-5.5 V (start above 1.8 V), output 3.3 V,
2 A at Vin of 2.3 V or more, 11 uA quiescent, 0.47 uH inductor, true load disconnect in shutdown. Both cells stay above 1.8 V.
It replaces the AP2112K LDO on both variants, because both cells sit below 3.3 V for part of their discharge.

**USB charger (decided 2026-10-31, user approved): TI BQ25798 (C2876593, about 3.8k stock) for both variants.** It replaces the
TP4056, which charges to 4.2 V and would overcharge both cells. End-of-charge voltage is set over I2C per variant (3.65 V LFP,
3.95 V sodium). Its cold cutoff at 0 C is fixed inside the chip, so USB charging stops below 0 C (accepted). The solar path
(CN3795) still charges below 0 C. CN3795 cannot run from USB: its UVLO is 6.5 V and USB gives 5 V.
- Safety item to confirm in the datasheet: the register default end voltage. If the default is 4.2 V, firmware must write the
  variant value before any charge, or a cell plugged into USB before first boot is overcharged. Check whether a hardware
  strap or OTP option exists instead.
- The BQ25798 has its own power path (PMID/SYS/BAT). Evaluate whether it replaces Q1/D3 in the power path; do not assume it.
- Not yet read: I2C address, charge current register and sense resistor, input range, required passives, end-voltage accuracy.

**Sodium discharge cut-off lead (2026-10-31, UNVERIFIED):** two web searches (standard and extended) found no CBAK
datasheet for 32140NS. A battery distributor listing for a 10 Ah 3 V sodium 32140 cell gives discharge end 1.5 V above 0 C
and 1.2 V at or below 0 C, with charge end 3.95 V (snippet only, page not opened: https://www.delongtop.com/product/3v-10ah-32140-rechargeable-cylindrical-sodium-ion-battery-cells/).
A DIY forum resource page lists a "CBAK 32140NS.pdf" marked partial; not opened (https://diysolarforum.com/resources/cbak-cell-datasheets.410/).
Not a CBAK specification. Do not design to it until the CBAK datasheet confirms it.

**Impact when the cut-off is known:** the 3.5 V cut-off in `board.yaml` was set for the AP2112K LDO (LDO headroom). With the
TPS63802 buck-boost, the LDO check no longer limits the cut-off; the cut-off is then set by the cell and the firmware policy.
Recompute `battery.vcutoff_v` and the autonomy check when the LFP or sodium cut-off is known. TPS63802 starts above 1.8 V, so a
cell cut-off of 1.5 V is below its start threshold but above its 1.3 V input minimum once running.

**Monday checklist (samples and datasheets at work):**
1. LFP 26700LT: discharge at a light load (10-20 mA) with a DC supply or a load to find the voltage where the cell is
   at about 20 % capacity; record cut-off in `board.yaml`. Confirm end-of-charge 3.65 V at the cell with the BQ25798 setting.
2. Sodium 32140NS: CBAK datasheet (ask CBAK sales if none online). Confirm charge end 3.95 V (maximum or nominal), the discharge
   cut-off, and the cold-charge limits. Until then the variant B holder and R1 stay open.
3. BQ25798 datasheet: register default for charge voltage, I2C address, end-voltage step size and accuracy, charge current
   setting, cold cutoff, passives, and whether it runs without firmware.
4. CN3795 R1 values (20.5 kΩ, 22.6 kΩ with R2 10 kΩ, both E96) against the actual FB pin tolerance; formula checked:
   3.677 V and 3.928 V.
5. Inductor (SWPA8040S220MT), P-FET for 30 V, and input capacitor datasheets (not read yet).
6. Update `bom.csv` only after items 3 and 4 are confirmed: remove TP4056 (C16581), R26 (C4211), D2/D3/Q1 only if the BQ25798
   power path replaces them, add BQ25798 and passives, and set R14 to 0.06 ohm (2512) for the CN3795 Rcs.

## Layout (generator `hardware/gen/pcb_v1.py`, build `hardware/tools/build_pcb.sh`, route `hardware/tools/route_v1.sh`)
- Outline 50 x 50 mm, 4 layers: F.Cu parts and signals, In1 GND, In2 GND, B.Cu signals (`board.yaml` stackup). M3 holes
  (ISO 7380 head) in the four corners, 3.2 mm copper keepout; board-only footprints H1-H4 (not in the schematic or BOM).
- Floorplan: module top centre, antenna over the top edge (its footprint keepout lies off the board; a 1 mm strip along
  the edge has no pours or vias). Battery top-left (J6 on the left edge, TH1 beside it, HY2112 and its FETs, F1). Debug
  corner top-right (J7, RESET, BOOT). Heat corner bottom-left (J1 USB-C and J5 PV on the left edge, BQ25798 with L1 above
  it between SW1 and SW2, TPS63802, TPS61023). Sensors bottom-right, opposite the heat corner (J8 on the right edge, J3
  and J4 on the bottom edge, J2, U8 SCD41 footprint).
- Placement: big parts by hand (`FIXED`); passives by rule (`NEAR`: each pad next to the pin it serves, critical blocks
  first, courtyards never overlap). The build prints the courtyard share of the board and renders
  `hardware/out/review/pcb/annot_*.png`.
- Net classes from `board.yaml` (Charge 0.65 mm for 1.7 A, Power 0.4 mm, USB 0.27/0.15; `calc/track_width.py`). Custom
  DRC: `hardware/rules/weatherstation.kicad_dru` (no via in SMD pads, via to edge, J1 shell, charge path neck >= 0.3 mm).
- Rule areas: no tracks or vias under L4/L5 on B.Cu (REQUIREMENTS E3; L1 carries its own SW tracks, see below); only GND
  on F.Cu under the J1 shell (B.Cu under it is screened by In1/In2 and is a routing lane; a track/via keepout, since
  the router does not read the custom rule).
- Critical blocks: `critical.yaml` (switching loops of BQ25798, TPS63802, TPS61023; FB dividers; decoupling; series
  resistors; USB pair; heat-to-NTC and heat-to-sensor distances).
- Test points TP1 (+3V3) and TP2 (SYS); UART0 header J7 as fallback debug.
- Routing trial 2026-11-01 (KRT 0.23, first placement, courtyards 76 % of the board): 53 of 71 nets routed, 18 open
  (GND, SYS, PMID, REGN, USB pair, TS, 5V_SW and others), 19 vias in pads, power tracks necked to 0.2 mm in many places.
  The board is too dense for single-sided parts on 50 x 50 mm: engineer decision open (THT connector bodies on the back,
  smaller buttons, fewer connectors or holes, or a bigger board).
- Decision 2026-11-01 (engineer): hand-soldered THT connectors J2, J5, J6, J7, J8 with their bodies on the back (cables
  plug in from below), J4 spare port dropped; outline stays 50 x 50 mm. Front courtyards 67 %. Routing trial 2: 60 of 71
  nets, 11 open, all in the charger corner or the USB pair (PMID, SYS, BAT_PACK, USB_VBUS, REGN, BATP, +3V3, SEN_SDA,
  GAS_SW, USB_DP/DN), 2 vias in pads. Next: draw the charger power copper (PMID/SYS/BAT/VBUS) and the USB pair in the
  generator and lock them (kicad-layout order of work step 6), then route the rest.
- Charger power stage drawn by hand (2026-11-02, `CHARGER` and `CHARGER_COPPER` in `gen/pcb_v1.py`, TI SLUSDV2C
  8.4.1/Figure 8-21): C9/C13 (now 0402, 100 nF 50 V C307331, Basic) on top of the PMID-SW1-GND-SW2-SYS pin row sharing
  the GND pin; SW1/SW2 drop through 2 vias each under the IC to 0.6 mm B.Cu tracks and come back up at L1 above the
  caps (engineer: vias and the SW tracks under L1 are fine, the B.Cu keepout stays for L4/L5); PMID and SYS bulk caps in
  a column each, joined by F.Cu pours, one GND via per cap. All locked; the placer keeps parts off it and keeps escape
  bands free beside U3's signal pins. KiCad DRC on the drawn copper: clean. Critical checks of both BQ25798 loops OK.
- Why by hand: no autorouter order (power first, signals first, QFN fanout first, 0.4 mm charge tracks) closed the
  charger at 50 x 50 or 55 x 55; each order walled in the other half of U3's 0.4 mm pitch pins, and the routed switch
  nodes wandered (vias at the pins, PMID across the block). Routing trial 3 with the hand-drawn stage: 10 of 71 nets
  open at 50 x 50 and at 55 x 55, almost all U3 signal pins (BTST1/2, PROG, ILIM, INT, SDA/SCL) and the USB pair.
  Next: place the charger's small parts by hand and script U3's signal escapes the same way; then route the rest.
  Engineer allows a slightly bigger outline (55 x 55) if needed; JLCPCB assembly takes 10x10 to 470x500 mm boards.
- 0402 pass (engineer 2026-11-02: 0402 wherever a Basic part exists, same part numbers where possible): 34 passives to
  0402 Basic (5.1k C25905, 100R C25076, 100k C25741, 2.2k C25879, 10k C25744, 2k C4109, 22R C25092, 1k C11702,
  100n 50 V C307331, 1n C1523, 1u 25 V C52923). Stay 0603: values without a Basic 0402 (3k, 120k, 30k, 220k, 39k,
  510k, 68k, 47n, 300R) and caps that lose too much capacitance at their DC bias in 0402 (C5 4.7u on REGN, 10u on
  SYS/3V3). Extended parts unchanged (14). Front courtyards 69 % -> 65 %.
- Charger small parts placed by hand in a ring in pin order (`CHARGER`): BAT cap beside the BAT pins, PROG, BTST2,
  ILIM, TS rows on the right, BATP sense and SDRV cap further out; VBUS 100n, BTST1 and REGN caps on the left. The
  charger's INT/CE/SDA/SCL pull-ups moved to the MCU end of those nets. Routing trial 4 (one pass): 5 of 71 nets open
  (PV_IN, Rails/FB, USB_DP, 3V3_SW, BAT_PACK). Next: TPS63802 block by hand (FB divider at the pin), USB pair drawn.
- TPS63802 block placed by hand (`BUCKBOOST` in `gen/pcb_v1.py`, layout per TI SLVSEU9D section 12.1): U2 at
  (28.3, 41.5), input cap C40 above VIN, L4 right beside L1/L2, output cap C41 below VOUT, FB divider R52/R53 at the
  FB pin. Critical checks pass (loops 1.3-2.95 mm, FB divider 0.9/1.7 mm). Routing trial 5: 6 of 71 open (CHG_SCL,
  CHG_SDA, PV_IN, USB_DP, 3V3_SW, REGN); FB now closes. The unrouted board shows 8 isolated-copper warnings on
  In1/In2: these are GND plane pieces that no via reaches yet, and they go away after the plane stage adds vias.
- USB pair drawn by hand (`USB_COPPER` in `gen/pcb_v1.py`, 2026-11-02): the diff-pair router (route_diff.py) found no
  launch room at J1/U4. U4 rotated 270 (flow-through: DN left, DP right on both rows); J1 B7/A7 (DN) join on F.Cu,
  A6/B6 (DP) drop to B.Cu and come back up beside U4; R9 moved below R10, CC1 on B.Cu outside the shell keepout; BC1.2
  stubs to U3 pins 6/7 through vias under U3's body (clear of the SW1 vias) on B.Cu. USB closes in every routing run.
  Engineer 2026-11-03: C1 5.0 mm from U4 VBUS accepted (critical.yaml `known:`); USB via limit 6 (J1 to U1 path has 2
  on DP, 0 on DN; full speed 12 Mbit/s); BC1.2 D+/D- to the BQ25798 stays (chargers were not detected without it).
- USB impedance check (2026-11-04, `calc/impedance.py`, JLC04161H-7628): the net class 0.27/0.15 mm on F.Cu gives
  90.6 ohm differential (90.0 with JLC's calculator inputs: 8.6 mil prepreg, 1.6 mil copper; 87.0 with 1.2 mil mask
  between the traces). The routed pair does not use that geometry: 0.2 mm at 0.3-1.6 mm gap (B.Cu and the U4/J1/U3
  stubs) and 0.27 mm at 0.8-1.6 mm gap, so it is 115-135 ohm, loosely coupled. Lengths: DP about 29 mm, DN about
  30 mm (J1 to U1), skew under 1 mm. Accepted: the ESP32-S3 USB is full speed only (12 Mbit/s, edges >= 4 ns); the
  length where impedance starts to matter is about 165 mm (4 ns rise), or 61 mm at the strict 10 % rule. 30 mm is
  under both. No impedance control ordered. A high-speed design would need the pair redrawn at 0.27/0.15.
- TPS61023 block placed by hand (`BOOST`, SLVSF14B Figure 10-1): inductor below the IC from VIN to SW, output cap at
  VOUT/GND, input cap left of VIN, FB divider above FB. Placer keeps courtyards 0.15 mm inside the edge (pads 0.3 mm).
- Routing trial 6 (50 x 50, all hand blocks): 7 of 71 open (TS, ACDRV2, CHG_CE, CHG_SCL, PV_IN, 3V3_SW, SYS). 55 x 55
  with the same blocks was worse (9-12 open): the outline transform pulls the blocks apart and stretches long nets.
- 2026-11-03: SYS bulk caps C17/C18 fixed above C16 and joined to the SYS pour by a hand track (the router left the
  pour an island). RESET/BOOT buttons (5.1 mm) replaced by tweezer pads JP1/JP2 (engineer); two red status LEDs D10/D11
  on IO41/IO42 with 1k (engineer). Courtyards 66 %. Scripted escape of U3's bottom row (`_FAN`, off by default): it closed
  those nets but its via row blocked the channel under U3 (10 open vs 6). Routing trial 8: 6 of 73 open (ACDRV2, BATP,
  CHG_INT, CHG_SDA, STAT, SW1); the open set moves between runs, always U3's signal pins.
- **Routing trial 12 (2026-11-03): fully routed, DRC clean.** `hardware/tools/route_v1.sh` (placed board in place ->
  routed board): KRT planes, power, rest (`--max-ripup 4 --ripup-blocker-select cost`), rip-up finishing pass
  (`route_finish.sh`), Charge tracks widened where they fit (`widen_charge.py`), via nudge and dangling cleanup
  (`finish_v1.py`). Result: 0 DRC errors, 0 unconnected pads, schematic parity clean, no copper on In1/In2 (both solid
  GND), 1444 tracks, 210 vias; `critical.py` OK (C1 WARN accepted). Five of six router settings give the same clean
  result, so the hand copper, not the seed, carries it. Remaining DRC warnings are silkscreen only (7). What closed it:
  - Hand-drawn (`gen/pcb_v1.py`, locked): U3's right column fan (PROG, BTST2, BATP via, ILIM, TS, INT via); U3's bottom
    row as one nested B.Cu bundle (ACDRV1 west, up the left edge under J1 to R11; ACDRV2, CE, SDA, SCL east at
    y 38.35-40.25 and north at x 26.0-27.8, inner lane turns first); REGN B.Cu lane to R15/R17; BAT_PACK trunk C20 to F1
    (0.65 mm B.Cu, 0.6/0.3 vias) and USB_VBUS trunk J1 A4/B9 to M1 (0.5-0.65 mm); C19-C20 link (SDRV moved to B.Cu);
    boost EN/FB/VIN, buck-boost FB and VIN links; USBLC6 flow-through links under U4; TS divider, CC2, LED_A; escape vias
    for R48/R49 (the router dropped vias into those pads).
  - Router settings: the J1 shell area is a real track/via keepout on F.Cu (KRT ignores the custom DRC rule; B.Cu under
    the shell is screened by both planes and is a lane); KRT fab floors pinned to the project DRC (clearance 0.15,
    via to edge 0.35, `rules/krt-fab.txt`); no `ctrl` stage, no automatic QFN fan-out stage.
  - Rule "charge path neck" exempts USB_VBUS: its current path is the locked trunk, the rest are taps without load
    current (U3 VAC1 sense, U4, C1, the second VBUS pad pair).
  - Parts pinned where the new copper reservation pushed NEAR parts off (M1, R11, R12, R20, R45, R48, R49, C20, F1,
    M60, C60, R60); C44 turned 180 degrees (SYS pad to VIN), R19 turned (REGN pad toward C5).
  - Tried and dropped: Freerouting 2.5 as router (43 open) and as finisher on the KRT board (100 open, it re-counts the
    plane nets); a `ctrl` stage for the long control nets (6-11 open).
  - VBUS layer change at U3 (engineer 2026-11-04, hand copper OK): the C6-side via is now 0.6/0.3 like the M2 side,
    with a 0.65 mm B.Cu link. STAT runs 0.15 mm higher beside it (PMID pour edge -2.8); its west diagonal stays where
    it was, because the router's only USB_VBUS path to U4/J1 A9 runs past it at x 10.4 (shifting it left 3 open).
    A second parallel via has no room (C10, C6, STAT, the DP track on B.Cu). Rating at the 1.59 A ILIM clamp: the
    IPC-2221 outer formula on the barrel (0.3 mm, 18 um plating) gives 1.47 A at 10 C rise and 2.0 A at 20 C. That
    formula is for long conductors. The 1.6 mm barrel is 1.5 mOhm and drops about 4 mW at 1.59 A into the copper on
    both ends, so the real rise is negligible. Re-routed: 0 DRC errors, gate OK.
  - J1 A9/B4 (second VBUS pad pair, engineer 2026-11-04: draw wider): hand link under R10 to the USB_VBUS node,
    0.4 mm with a 2.4 mm neck at 0.25 mm between R10 and R9 (the router had 9 mm at 0.127 mm). R9's GND pad got its own
    plane via (8.9, 33.4), because the link takes the path the router used for it. U4 pin 5 (USBLC6 VBUS reference)
    stays with the router at 0.2 mm (was 0.127). A hand link up to it needs the only F.Cu gap across the DP B.Cu
    fence, and the C3 bootstrap (SW1) path needs that gap too. With both by hand: 15 DRC errors in all six router
    settings. Widening it further means moving the CC resistors or C3 (engineer call). 0 DRC errors, gate OK.

## Production files (2026-11-05)
- `python3 -I hardware/tools/fab_package.py [--require-clean] hardware/weatherstation-v1/weatherstation-v1.kicad_pcb`
  (after `source scripts/kicad-env.sh`): DRC gate, gerbers + drill zip, BOM, CPL into `hardware/out/fab/`. Order
  options, rails remark and fit results: `ORDER.md`.
- CPL from a fit of JLC's own (EasyEDA) footprint onto our pads, not from a rotation table (`fab_package.py` docstring).
- **L3 land pattern fixed (2026-11-05):** the CMF4532F footprint had 0.7 x 1.15 mm pads at y +/-1.55; in EMTEK
  T-0602-102D 7-1 the 0.7 mm is the gap between the pad rows. Now 1.15 x 1.55 mm pads at (+/-1.825, +/-1.125): they
  cover the D1 1.0 x D2 1.2 mm terminals, and JLC's footprint for C963746 is the same pattern turned 90 deg. Swapped on
  the routed board with `tools/swap_footprint.py`; one router GND track under the choke (now in the 0.7 mm row gap) was
  removed, GND stays connected through the planes (0 unconnected).
- Silk: `tools/silk_fix.py` (last step of `route_v1.sh`) clips outlines at the board edge (J1, U1 overhang), moves
  two pin-1 marks and one outline 0.02-0.16 mm. The five footprints it edits differ from the library on purpose:
  `drc-waivers.csv` (warning type and reference only; the fab gate accepts nothing else).

## Open before ordering (updated 2026-11-01)
The CN3791/TP4056/AP2112K items of the old list are gone with the BQ25798 design (commit 7db8d9c).

1. **Parts and circuit review: `PARTS-REVIEW.md`.** A1-A3 applied 2026-11-01 (common-drain protection FETs, R23 removed,
   BAT caps on BAT); A6 and A7 applied (SMBJ10A, 3 A choke, 6 V 10 W panel; CE pull-up to +3V3). A4 (two I2C
   buses) and A5 (TPS61023 5 V boost, enable IO12) applied 2026-11-01. B1 (3V3_SW inrush) accepted as drawn,
   measure the +3V3 dip on the first board. B2, B4, B5, C (R21) decided and applied; B3
   in REQUIREMENTS section 6. B6/B7 land patterns
   drawn from the maker drawings (project footprints). No A or B item open.
2. Datasheets missing: SMBJ10A maker PDF (ratings from DigiKey: 10 V standoff, 17 V clamp at 35.3 A), CMF4532F-900 page (land
   pattern settled 2026-11-05, see Production files), USBLC6-2SC6, CBAK 26700LT. On file 2026-11-01: TPS61023, Sunlord WPN, TDK VLS252010HBX-1.
3. **Decided: accept reduced winter accuracy** of the SEN66 below 10 C (no heater; log the enclosure temperature).
   REQUIREMENTS.md section 4 still says -10 to +50 C for operation; amend it to "short-term" for the SEN66.
4. `design.panel.vmp_v` is still an assumption (6.0 V). Choose the panel; the TVS choice (A6) depends on its Voc.
5. Whether JLCPCB forces Standard PCBA for the ESP32 module (check the quote).
6. ZE25-O3 cable pitch (J8; pinout from Winsen table 2, 2026-11-01). Supply current closed: 10 mA at 5 V (2026-11-04).
7. Production files built (2026-11-05): choose ENIG and the rails remark in `ORDER.md`.

### Schematic: nets that keep labels (generator `UNWIRED`, 2026-11-01)
Each is readable as drawn; listed so a reviewer knows they are labels on purpose, not missing wires.
- Input: CC2 (R10 sits below J1 next to R9; the CC1 wire blocks the direct path), USB_DP/USB_DN at J1/U4 (four stacked
  connector pins plus the ESD part; labelled per pin like a connector).
- Battery: BAT_N (cell negative: J6, C60, U6 VSS, M60; a wire would loop around the protection IC and its gate lines).
- Sensors: SEN_SDA/SEN_SCL at the pull-up and ESD block (the connector bus is wired; the block below joins by label).
- Hand-drawn (layout_v1.HAND_ROUTES): charger BTST/SW/L1, PV entry J5-D1-L3-PV_IN, HY2112 VDD/OD/OC/CS/PB_MID, sensor bus.
- Root page: USB_DP, USB_DN span three sheets and keep labels (outside the boxes). All other sheet-to-sheet nets are wires.

## Pitfalls (carried over from desk_notifier, see its PLAN.md/BOARD.md for details)
| Symptom | Cause | Fix |
|---|---|---|
| Part rotated wrong in JLC preview | rotation tables differ per footprint | correction entry in the fab package script, check ICs/connectors in the preview |
| Pin 1 or centre pad unclear | fab package name vs KiCad footprint differ | compare land patterns with the datasheet drawing |
| LDO headroom WARN/FAIL | cutoff too low for the SEN66 peak | raise `battery.vcutoff_v` or drop the load |
| Extended-part fees | each unique Extended part adds a loading fee | prefer Basic/Preferred Extended equivalents |
