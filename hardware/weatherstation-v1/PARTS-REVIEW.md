# Parts and circuit review (gate 2), 2026-11-01

Scope: every BOM line and every IC connection in `hardware/gen/weatherstation_v1.py` (PARTS, NETS) against the datasheets on
file. Nothing here is applied yet: each finding needs an engineer decision (column "Decision"). Severity: **A** = the circuit does
not work as intended or exceeds a rating; **B** = works, but a margin or a rule is broken; **C** = cleanup.

Sources: BQ25798 SLUSDV2C (table 5-1 pin functions, table 7-1 PROG, section 7.3.2 POR defaults, figures 8-1/8-2 typical
application, section 9 layout); HY2112 DS-HY2112-V08 section 10 (connection example, page 10); TPS63802 SLVSEU9 table 7-1;
Winsen ZE25-O3 manual v1.4 (as recorded in BOARD.md); LCSC data from `hardware/tools/jlcparts.py`.

## A: probably wrong

Decided 2026-11-01: A1, A2, A3, A7 accepted and applied in the generator. A6: 6 V class panel of about 10 W (board.yaml
solar.panel_w): D1 is SMBJ10A (Littelfuse, C151250) and L3 is CMF4532F-900-2P-T (C963746, 3 A, 70 mohm; the 1 kohm part
was rated 1 A). A4 and A5 decided 2026-11-01: two I2C buses (charger IO4/IO5 with pull-ups to +3V3; sensors IO13/IO14 with
pull-ups and U5 VBUS on 3V3_SW) and a TPS61023 5 V boost on GAS_VCC (C919459, EN from GAS_EN IO12, R45 pull-down, true
disconnect when off; Q42/Q43 and their resistors removed). No A finding is open. Confirmed by the engineer 2026-11-01: boost
inductor L5 = same part as L1 (VLS252010, Isat 3 A) and output 5.07 V. B1 accepted as drawn (inrush seldom a problem; check
the +3V3 dip on the first board). Also decided 2026-11-01: B2 applied (TH1 to GND), C R21 removed (QON open), B4 keep L1
with ICHG <= 1.5 A, B5 keep D+/D- shared (firmware AUTO_INDET_EN = 0 after the first detection), B3 written into
REQUIREMENTS.md section 6. B6 and B7 done 2026-11-01: project footprints from the maker drawings
(`hardware/gen/build_footprints.py`): U2 TPS63802_DLA_VSON-HR-10_2x3mm (TI DLA0010A example board layout 4223750/D),
L4 L_Sunlord_WPN201610H (Sunlord a 0.7 / b 0.7 / c 1.7; the KiCad Cenker pattern had a 0.3 mm pad gap), L1/L5
L_TDK_VLS252010 (TDK 0.6 / 1.3 / 0.6 x 2.0; the generic 1008 pattern had a 0.9 mm gap). L1 numbers from the TDK table:
Isat 3.22 A (rated), Itemp 2.55 A, Rdc 65 mohm max. The CMF4532F courtyard was smaller than its pads (fixed). No B item
is open.

| # | Where | Finding | Evidence | Proposed fix |
|---|---|---|---|---|
| A1 | Battery: M60, M61 | The protection FETs are wired **common-source** (M60 drain on BAT_N, sources joined at PB_MID). The HY2112 example uses **common-drain**: M1 (discharge) source on cell negative, M2 (charge) source on PB-, drains joined. As drawn, M60's body diode conducts in the discharge direction, so OD cannot stop a discharge, and OD/OC gate drive is not referenced to the FET source. | HY2112 section 10 figure; AO3400A pins 1 G, 2 S, 3 D | M60: S = BAT_N, D = PB_MID. M61: D = PB_MID, S = GND (PB-). |
| A2 | Charger: R23 | 10 mOhm 2512 between VBUS and PMID. The BQ25798 senses input current **inside** the IC between VBUS and PMID (RSNS 8 mOhm, electrical table). An external resistor sits in parallel with that path, takes part of the current, and makes IINDPM read low (about half), so the input current limit no longer holds. The "Rs" in figure 8-2 is inside the IC outline. | table 5-1 VBUS "input current sensing circuit is connected between VBUS and PMID"; RSNS spec | Remove R23. VBUS and PMID are separate nets, each with its own capacitors only. |
| A3 | Charger: C19, C20 | The 2 x 10 uF battery capacitors are on BATP (behind the 100 ohm R13), not on BAT. BAT (pins 22-23) has no capacitor; BATP gets a 2 ms RC filter it should not have. | table 5-1 BAT "recommended capacitors at BAT are 2 pieces of 10 uF"; BATP "100 ohm series"; layout rule 5 "BAT capacitors close to BAT and GND" | Move C19, C20 to BAT_PACK (BAT pins). BATP keeps only R13 (optional 47 nF per figure 8-2 note 2, not needed for 1S). |
| A4 | Sensors: U5 and the shared I2C bus | I2C pull-ups go to +3V3 so the charger stays readable with the sensors off, but (1) U5 (USBLC6) has its VBUS pin on 3V3_SW: with the rail off its internal diodes clamp SDA/SCL to about 0.6 V and the bus (charger included) stops; (2) the unpowered SEN66 and SHT45 are back-powered through their I/O protection from the pulled-up bus. | USBLC6 topology (diodes from I/O to VBUS); NETS I2C_SDA/SCL and 3V3_SW | Recommended: two buses. I2C0 = charger (IO4/IO5, pull-ups to +3V3). I2C1 = sensors (two free GPIOs, pull-ups and U5 VBUS on 3V3_SW). Alternative: one bus plus a bus switch. Needs a GPIO choice. |
| A5 | Rails/Sensors: GAS_VCC | GAS_VCC is SYS switched by Q42. On battery SYS is about the cell voltage (LFP 3.0-3.4 V). The ZE25-O3 needs 3.7-5.5 V. BOARD.md says both "no 5 V boost needed" (line ~102) and "needs a 5 V rail" (line ~146). | ZE25-O3 manual v1.4 supply range (BOARD.md); BQ25798 SYS = VBAT when no input | Decide: add a small 5 V boost (enable from GAS_EN) on J8, or leave J8 unpopulated in v1 and drop Q42/Q43/R43-R45/C44. |
| A6 | Input: D1 SMBJ24A | Clamp voltage 38.9 V at rated pulse is above the VAC2/VBUS/PMID absolute maximum (30 V) and the AO3400A Vds (30 V). The panel is a 6 V class (Vmp about 6 V, Voc about 7-8 V cold), so a 24 V standoff is far too high to protect anything. | BQ25798 6.1 abs max; board.yaml panel.vmp_v; SMBJ series clamp table | SMBJ10A (standoff 10 V, clamp about 17 V), for example LCSC C353406 or C151250 (stock checked 2026-11-01; class and datasheet to verify). Only if no higher-voltage panel is planned. |
| A7 | Charger: CE pull-up R20 to REGN | REGN is about 5 V; CE is also driven by ESP32 IO9 (3.3 V I/O, abs max VDD + 0.3 V). When the GPIO is high-Z the pin sees 5 V through 100k. | BQ25798 table 5-1 REGN; ESP32-S3 abs max | Pull R20 to +3V3 instead. Keep "CE high = charge off by default" (needed: POR default VREG is 4.2 V, table 7-2; firmware must write VREG 3.65 V before releasing CE). |

## B: works, margin or rule broken

| # | Where | Finding | Proposed fix |
|---|---|---|---|
| B1 (accepted 2026-11-01, measure on first board) | Rails: Q40, C42, C43 | 44 uF on 3V3_SW is switched hard onto +3V3, which only has C41 + C30 (44 uF). The rail dips by about half at turn-on: ESP32 brown-out. | Slow the P-FET turn-on (gate RC, for example 100 nF gate-source plus series resistor in the Q41 drain) or cut 3V3_SW bulk to 10 uF and check the SEN66 inrush. Same check for GAS_VCC if kept. |
| B2 | Battery: TH1 | NTC bottom on BAT_N (cell negative, before the protection FETs); R18 (TS divider bottom) is on GND. While the FETs are on the difference is millivolts; when they open the TS reading is wrong. | TH1 pin 2 to GND, as in figure 8-1. |
| B3 | Charger: firmware dependency | BQ25798 watchdog: on expiry all registers return to POR defaults (VREG 4.2 V, ICHG 1 A). If the ESP32 holds CE low through deep sleep and the watchdog expires, the charger aims at 4.2 V; only the HY2112 overcharge cut (3.75 V) stops it. | Firmware: write WATCHDOG = 00 (disable) or release CE before sleep. Record in REQUIREMENTS and firmware notes. Hardware backstop stays HY2112. |
| B4 | Charger: L1 VLS252010HBX-1R0M-1 | 1 uH, Isat 3 A, DCR 54 mOhm. On USB (1.5 A in, SYS + charge out at about 3.3 V) the peak inductor current is about 2.7 A: inside the rating, little margin, 0.3-0.4 W loss. | Acceptable for v1 if ICHG stays at 1.5 A; a 4 x 4 mm 1 uH with Isat >= 4 A is safer. |
| B5 | Charger: D+/D- shared | BQ25798 D+/D- (BC1.2 detection) share the USB data lines with the ESP32. Detection runs at plug-in and can disturb enumeration. | Keep, firmware sets AUTO_INDET_EN = 0 after the first detection, or leave D+/D- open and set IINDPM by firmware. Engineer choice. |
| B6 | Rails: U2 footprint | TPS63802**DLA** is a VSON-HR package; the BOM footprint is a WSON-10 with an exposed pad. | Draw the DLA land pattern from the datasheet (already open in BOARD.md). |
| B7 | Rails: L4 WPN201610HR47MT | Sunlord part (not Wurth as earlier notes said). 0.47 uH, Isat 4.7 A, Irms 2.7 A: fine for the load. Footprint is a Cenker 2016 pattern. | Fix the note to Sunlord; compare the land pattern with the Sunlord drawing. |
| B8 | Input: R11, R12 | 300 ohm ACDRV gate resistors are marked "candidate (figure 294)". The 294 in figure 8-2 sits next to ACDRV, so the value is plausible. | Confirm in the BQ25798 EVM user guide before ordering. |

## C: cleanup

- F1 comment in PARTS says "no cell protection IC"; HY2112 is on the board now.
- R21 (QON pull-up to REGN): QON has an internal pull-up; R21 can go (one part less).
- BOM note "SYS 6 x 10 uF" in the block note: the design has 5 x 10 uF + 0.1 uF (matches table 5-1).
- CLAUDE.md "Hardware decisions" still lists CN3791, TP4056, LDO cutoff 3.5 V and "default = charge allowed". The schematic now uses BQ25798 with CE high by default (charge off until firmware sets VREG).

## Checked and fine
BQ25798 pin map (all 29 pins), VBUS 2 x 10 uF + 0.1 uF, PMID 3 x 10 uF + 0.1 uF, SYS 5 x 10 uF + 0.1 uF, BTST 47 nF, REGN 4.7 uF,
PROG 3.0k (1S, 1.5 MHz), ILIM 120k/100k (figure 8-2 127k; Basic, 1.59 A clamp), TS 5.1k/30k (figure 5.24k/30.31k; Basic, +0.9 C), SDRV 1 nF (no ship FET),
ACFET/RBFET common-source pairs, VAC1/VAC2 before the FETs, STAT LED from REGN 2.2k. TPS63802 pins (table 7-1) and FB divider
3.31 V. HY2112 R1 100 ohm, C1 0.1 uF, R2 2k (section 10 table). ESP32-S3 pins: USB IO19/IO20, no strapping pin used except IO0,
EN RC 10k/1 uF. SEN66 GH pinout 1 VDD, 2 GND, 3 SDA, 4 SCL; SHT45 cable in Qwiic order. USB-C CC 5.1k.
