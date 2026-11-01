# Charger: BQ25798 for USB and PV (schematic base)

Source: TI BQ25798 datasheet, SLUSDV2C (May 2020, revised June 2026), https://www.ti.com/lit/ds/symlink/bq25798.pdf
Read 2026-10-31 from the rendered pages (PDF pages cited). Values from figures are marked FIG; register values are REG.
Status: schematic base and register plan. Not in `bom.csv` or `board.yaml` yet. Not a KiCad schematic yet.

## Decision (user, 2026-10-31)
One charger, the BQ25798, for USB and solar. CN3795 and TP4056 are dropped. Battery: one cell per variant (LFP 26700LT or
sodium 32140NH 7 Ah), end voltage set in firmware over I2C per variant. Cell values: `cells.md` (vendor specs, 2026-11-01).

## Two-input topology (USB + PV), figure 8-2 (p.131)
PV and USB each have an ACFET/RBFET pair (back-to-back N-channel, common source, gate driven from ACDRV1 / ACDRV2 5 V above the source; datasheet 7.3.5) into VBUS. The PV path is marked
"Optional" in the datasheet figure; here it is required. Table 7-6 (single input) and Table 7-7 (two inputs) decide the
ACDRV/VAC wiring; Table 7-7 not read yet (OPEN).
- Input 1 (USB): VBUS side, ACFET1 / RBFET1, gate ACDRV1, 294 ohm gate resistors (FIG).
- Input 2 (PV): ACFET2 / RBFET2, gate ACDRV2, 294 ohm gate resistors (FIG). VAC2 senses PV.
- Priority: the datasheet mux (section 7.3.5) selects the input; USB priority rule to be confirmed (OPEN).
- PV panel up to 24 V operating (30 V absolute maximum). A 12 V-class panel (Voc 21-24 V) is inside the rating but close
  at the top: choose a panel with Voc at or below about 22 V, or check the cold Voc (OPEN).

## Buck-boost power stage (figure 8-1 / 8-2)
The datasheet features list says the chip integrates the four switching MOSFETs and the BATFET. So Q1-Q4 and the BATFET
in the figures are internal: no external power FETs. External parts are only the input pairs (ACFET/RBFET) and the ship FET
(not used here).
| Item | Value | Note |
|---|---|---|
| Inductor | 1.0 uH at 1.5 MHz (FIG), or 2.2 uH at 750 kHz | Isat >= max(IIN, ICHG) + ripple/2 and >= 2 A (eq. 4) |
| Switching frequency | 1.5 MHz | Set by PROG resistor (see below) |
| BTST1, BTST2 | 47 nF, 10 V+ | FIG |
| REGN | 4.7 uF, 10 V ceramic | FIG |
| VBUS | 0.1 uF + 2 x 10 uF (25 V+) | FIG, input cap rating 25 V or more (8.2.2.3) |
| PMID | 0.1 uF + 3 x 10 uF; add 2 x 33 uF POSCAP if backup mode is used | FIG, 8.2.2.3 |
| SYS | 1 uF + 5 x 10 uF | FIG (schematic uses 0.1 uF + 6 x 10 uF) |
| BAT | internal BATFET between SYS and BAT | |
| BATP | 100 ohm + 2 x 10 uF | FIG; optional 47 nF for hot plug on long leads |
| Rs (VBUS to PMID) | none (removed 2026-11-01) | The "Rs" in figures 8-1/8-2 is the internal sense element (RSNS 8 mohm, electrical table); no external resistor. PARTS-REVIEW A2 |

## Pin-level netlist (single-input base; add the PV pair for the two-input board)
| Pin | Connection | Value / note |
|---|---|---|
| 1 STAT | REGN -> 2.2 kohm -> LED -> STAT | FIG, LED optional |
| 2, 3 VBUS | input node | see above |
| 4 BTST1 | SW1 | 47 nF |
| 5 REGN | LDO output | 4.7 uF |
| 6 D+, 7 D- | USB data (BC1.2 detect) | USBLC6 ESD on board |
| 8 VAC2 | PV sense | two-input; tie to VBUS in single-input |
| 9 VAC1 | USB sense | tie to VBUS in single-input |
| 10 ACDRV2 | PV FET gate drive | two-input only; shorted to GND in single-input (Table 7-6) |
| 11 ACDRV1 | USB FET gate drive | per Table 7-6 / 7-7 |
| 12 QON | host (reset / ship) | optional pull-up |
| 13 CE | host, active low | EN_CHG = 1 and CE low to charge; CE default high = disabled |
| 14 SCL, 15 SDA | I2C, address 0x6B (section 7.3.14) | pull-ups to 3V3 (not the 3V3_SW rail), 10 kohm |
| 16 TS | battery NTC divider | REGN -> 5.24 kohm -> TS; TS -> 30.31 kohm -> GND; 10 kohm NTC TH1 (NCP18XH103F03RB, B 3434 K) to GND (FIG 8-1); TS ratio checked against the 103AT JEITA rows (BOARD.md); REG18 thresholds reference these values |
| 17 ILIM_HIZ | REGN -> 127 kohm -> ILIM_HIZ -> 100 kohm -> GND | FIG; input current limit from the divider; formula OPEN |
| 18 BATP | battery pack sense | see above |
| 19 BTST2 | SW2 | 47 nF |
| 20 PROG | resistor to GND, sets default cell count and frequency | **3.0 kohm = 1.5 MHz, 1S** (Table 7-1). 6.04 kohm in FIG 8-1 is 2S. Use 3.0 kohm. |
| 21 INT | host interrupt | pull-up to 3V3 |
| 22, 23 BAT | battery | |
| 24 SDRV | ship FET drive | 1 nF in FIG 8-1 without ship FET |
| 25 SYS | system node | |
| 26 SW2, 28 SW1 | inductor | |
| 27 GND | GND | |
| 29 PMID | PMID | |

## Register plan (written by firmware at every boot before any charge). v1 is LFP only (sodium column dropped 2026-11-01).
The chip powers up with 1S defaults: VREG = 4.2 V, ICHG = 1 A, VSYSMIN = 3.5 V, TS JEITA default (REG00-REG03 and REG17/18).
The 4.2 V default would overcharge both cells. Firmware must write before enabling charge (or hold CE high until written).

| Register | Field | LFP 26700LT | Sodium 32140NH 7 Ah | Note |
|---|---|---|---|---|
| REG01 VREG | 10 mV steps, 3.00-4.99 V for 1S (Table 7-2) | 3.65 V (cell limit 3.75 V) | **3.30 V** (cell maximum 3.35 V; spec 5.2) | Corrected 2026-11-01: the old 3.95 V belonged to the unverified 10 Ah listing and would overcharge the 32140NH. Verify with a DMM |
| REG03 ICHG | 10 mA steps, 1 A default | 1.5 A | 1.5 A | 0.5C of the minimum 3.9 Ah is 1.95 A; 1.5 A also keeps the HY2112 charge overcurrent (-170 mV minimum) clear: 2 x 48 mOhm x 1.5 A = 144 mV (2026-11-01 review) |
| REG00 VSYSMIN | 2.5-16 V, 250 mV steps, default 3.5 V (1S) | 4.0 V (charging only; SYS on battery alone follows the cell) | 4.0 V | Battery-only SYS follows the cell voltage; the former AP2112K LDO needed about 3.55 V in; replaced by the TPS63802 buck-boost (BOARD.md power review)
| REG15 MPPT | VOC_PCT (bits 7-5), default 0x5 = 0.875; EN_MPPT bit 0 | 0x4 = 0.8125 | 0x4 = 0.8125 | Panel Vmp/Voc ratio; panel datasheet value replaces 0.8125 when known |
| REG16 | TREG, TSHUT, PD enables | defaults | defaults | Thermal regulation 120 C default |
| REG17 NTC_0 | JEITA_ISETC (cool band 0-10 C): default 20 % ICHG; 0 = suspend | 0 (suspend) or 1 (20 %) | same | Choose the cool-band policy here (see cold below) |
| REG18 NTC_1 | TS_COOL 10 C default, TS_WARM 45 C default | defaults | defaults | |
| REG08-REG0E | precharge, termination, timers | defaults (120 mA precharge, 200 mA termination, 12 h charge timer) | | |

Cold behaviour (from figure 7-11 and REG17/18). Cell limits from `cells.md`: LFP 0.2C below 0 C, sodium charge allowed to -10 C:
- Below T1 (0 C, inferred; not a register): charge suspended. Figure 7-11 shows the default; T1 is not in the register list.
- T1 to T2 (0 to 10 C default): charge current at 20 % of ICHG by default (JEITA_ISETC = 1). Set JEITA_ISETC = 0 to
  suspend charging below 10 C instead. This replaces the firmware cold inhibit (Q3/Q5) of the earlier design.
- The TS network above (5.23 kohm / 30.1 kohm / NCP18XH103F03RB, B 3434 K) defines the thresholds; the datasheet JEITA rows for 103AT match it (BOARD.md).
- Sodium 32140NH charge window is -10 to +65 C (CBAK spec 5.2). The chip suspends below about 0 C, so sodium cold charging
  between -10 and 0 C is blocked. This is stricter than the cell and accepted (sun energy in the -10 to 0 C band is lost;
  not quantified yet). Open item 9 closed.

## Battery-only power-up
- REGN LDO on battery only needs VBAT > 3.2 V and ADC TS on (section 7.3.4.1). LFP at 3.2 V nominal is at this threshold; a
  cell below about 3.2 V does not wake the charger from battery alone. Solar or USB restarts it. Check on the samples.

## Power budget and sensing (for the existing scripts later)
- Quiescent 17 uA battery only, 500 nA in charger shutdown (features, p.1).
- ADC conversion can be disabled to save power (section 7.3.10).

## Open items before schematic
1. Table 7-7 (two-input ACDRV/VAC wiring) and section 7.3.5 input priority (USB first?).
2. Rs value and the ILIM_HIZ current formula (section 7.3.4.3).
3. Power FET part numbers, roles (Q1-Q4), Vds and Ids; BATFET Vds; ACFET/RBFET parts.
4. Inductor 1.0 uH: part, Isat, DCR (JLCPCB stock; SWPA6045S220MT is 22 uH, not valid here).
5. Input/output capacitor voltage ratings (25 V minimum per 8.2.2.3).
6. JLCPCB stock and class of BQ25798 (C2876593), QFN-29 4x4 assembly (Extended or Basic), and the FET parts.
7. VSYSMIN: choose a value below the chosen cell cutoff so the system does not drop out early.
8. Verify end-voltage accuracy at 3.65 V and 3.95 V with the samples (DMM).
9. Closed 2026-11-01: sodium 32140NH 7 Ah spec read (`cells.md`). Charge end 3.30 V (max 3.35 V), cut-off 1.5 V, charge -10 to 65 C.
