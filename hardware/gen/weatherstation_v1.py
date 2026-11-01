"""weatherstation-v1 schematic: BQ25798 charger for USB-C and a PV panel, ESP32-S3-WROOM-1, 3.3 V LDO,
switched sensor rail, PMS7003 PM sensor and ZE25-O3 on a switched 5 V rail, SHT45 cable, optional SCD41 (DNP).

PARTS and NETS are the source of truth. check_nets() compares them with KiCad's own netlist.
Drawing: each pin gets a short stub with a net label (global label when the net crosses sheets,
local label otherwise). GND and +3V3 are power symbols. Unused pins get no-connect markers.
Values marked "candidate" or "confirm" are not final: see hardware/weatherstation-v1/usb-charger-bq25798.md.

Run: uv run --package weatherstation-hardware python hardware/gen/weatherstation_v1.py [out_dir]
"""

import math
import re
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kicad_sch_api as ksa  # noqa: E402

# Project symbols (TPS63802 DLA, HY2112-CB) are not in the KiCad libraries: written by build_symbols.py.
ksa.get_symbol_cache().add_library_path(Path(__file__).resolve().parent / "lib" / "weatherstation.kicad_sym")

from schkit import Sheet, Router, part_boxes, root_sheet, check_nets  # noqa: E402
from layout_v1 import BLOCKS, HAND_LABELS, HAND_ROUTES, TAG_POS, TAGS_BELOW, SHEET_NOTES, ROOT_BOX, SHEET_COLOR, SHEET_PURPOSE  # noqa: E402

R0603, C0603, C0805 = "Resistor_SMD:R_0603_1608Metric", "Capacitor_SMD:C_0603_1608Metric", "Capacitor_SMD:C_0805_2012Metric"
JST_PH2 = "Connector_JST:JST_PH_B2B-PH-K_1x02_P2.00mm_Vertical"
TP = "TestPoint:TestPoint_Pad_D1.5mm"
SHEET_FILES = {"Input": "input.kicad_sch", "Charger": "charger.kicad_sch", "Battery": "battery.kicad_sch", "MCU": "mcu.kicad_sch",
               "Rails": "rails.kicad_sch", "Sensors": "sensors.kicad_sch"}
SHEET_NOTE = SHEET_NOTES

# ref: (symbol, value, footprint, LCSC or None, sheet)
PARTS = {
    # --- Input -------------------------------------------------------------------------------
    "J1": ("Connector:USB_C_Receptacle_USB2.0_16P", "USB-C", "Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12", "C165948", "Input"),
    "U4": ("Power_Protection:USBLC6-2SC6", "USBLC6-2SC6 (USB)", "Package_TO_SOT_SMD:SOT-23-6", "C7519", "Input"),
    "R9": ("Device:R", "5.1k", R0603, "C23186", "Input"),
    "R10": ("Device:R", "5.1k", R0603, "C23186", "Input"),
    "M1": ("Transistor_FET:AO3400A", "AO3400A ACFET1 (N-channel, BQ25798 back-to-back)", "Package_TO_SOT_SMD:SOT-23", "C20917", "Input"),
    "M2": ("Transistor_FET:AO3400A", "AO3400A RBFET1 (N-channel, BQ25798 back-to-back)", "Package_TO_SOT_SMD:SOT-23", "C20917", "Input"),
    "M3": ("Transistor_FET:AO3400A", "AO3400A ACFET2 (N-channel, BQ25798 back-to-back)", "Package_TO_SOT_SMD:SOT-23", "C20917", "Input"),
    "M4": ("Transistor_FET:AO3400A", "AO3400A RBFET2 (N-channel, BQ25798 back-to-back)", "Package_TO_SOT_SMD:SOT-23", "C20917", "Input"),
    "R11": ("Device:R", "300 (candidate; figure 294)", R0603, "C23025", "Input"),
    "R12": ("Device:R", "300 (candidate; figure 294)", R0603, "C23025", "Input"),
    "C1": ("Device:C", "0.1u", C0603, "C14663", "Input"),
    "C2": ("Device:C", "0.1u", C0603, "C14663", "Input"),
    # 6 V class PV panel (Voc about 8 V cold): SMBJ10A standoff 10 V, clamp 17 V, below the 30 V abs max of VAC2/AO3400A
    # (PARTS-REVIEW A6, decided 2026-11-01). Littelfuse part.
    "D1": ("Device:D_TVS", "SMBJ10A (PV surge, standoff 10 V, clamp 17 V)", "Diode_SMD:D_SMB", "C151250", "Input"),
    # 2-line common-mode choke on the PV pair, >= 1 A. Pinout from EMTEK spec T-0602-102D (equivalent circuit):
    # winding A = 1 (in, top left) -> 2 (out, top right); winding B = 4 (in, bottom left) -> 3 (out, bottom right).
    # Footprint: project library weatherstation:CMF4532F_4P (land pattern from section 7-1).
    # 10 W 6 V panel: up to 1.7 A. The -900 variant: 3 A, 70 mohm DCR, 90 ohm at 100 MHz (the -102/-601 have 300-400 mohm
    # per winding: about 1 V lost at 1.5 A). Same family and land pattern; its own datasheet page still to check.
    "L3": ("weatherstation:CMC_2line", "CM choke 90 ohm 3 A (CMF4532F-900-2P-T; datasheet page to confirm)", "weatherstation:CMF4532F_4P", "C963746", "Input"),
    "J5": ("Connector_Generic:Conn_01x02", "PV IN", JST_PH2, None, "Input"),
    "#FLG1": ("power:PWR_FLAG", "PWR_FLAG", None, None, "Input"),
    "#FLG2": ("power:PWR_FLAG", "PWR_FLAG", None, None, "Input"),
    "#FLG12": ("power:PWR_FLAG", "PWR_FLAG", None, None, "Input"),
    # --- Charger -----------------------------------------------------------------------------
    "U3": ("Battery_Management:BQ25798", "BQ25798RQMR", "Package_DFN_QFN:Texas_RQM0029A_VQFN-29_4x4mm_P0.4mm", "C2876593", "Charger"),
    "L1": ("Device:L", "1uH (TDK VLS252010HBX-1R0M-1: Isat 3.22 A, Itemp 2.55 A, 65 mohm max)", "weatherstation:L_TDK_VLS252010", "C88211", "Charger"),
    # Cell overcurrent backup: PTC hold 3 A, trip 5 A, 8 V. Backup to the HY2112 overcurrent cut.
    "F1": ("Device:Fuse", "PTC 3 A hold (SMD1812P300TF)", "Fuse:Fuse_1812_4532Metric", "C21004", "Battery"),
    "C3": ("Device:C", "47n", C0603, "C1622", "Charger"),
    "C4": ("Device:C", "47n", C0603, "C1622", "Charger"),
    "C5": ("Device:C", "4.7u", C0603, "C19666", "Charger"),
    "C6": ("Device:C", "0.1u", C0603, "C14663", "Charger"),
    "C7": ("Device:C", "10u", C0805, "C15850", "Charger"),
    "C8": ("Device:C", "10u", C0805, "C15850", "Charger"),
    "C9": ("Device:C", "0.1u", C0603, "C14663", "Charger"),
    "C10": ("Device:C", "10u", C0805, "C15850", "Charger"),
    "C11": ("Device:C", "10u", C0805, "C15850", "Charger"),
    "C12": ("Device:C", "10u", C0805, "C15850", "Charger"),
    "C13": ("Device:C", "0.1u", C0603, "C14663", "Charger"),
    "C14": ("Device:C", "10u", C0805, "C15850", "Charger"),
    "C15": ("Device:C", "10u", C0805, "C15850", "Charger"),
    "C16": ("Device:C", "10u", C0805, "C15850", "Charger"),
    "C17": ("Device:C", "10u", C0805, "C15850", "Charger"),
    "C18": ("Device:C", "10u", C0805, "C15850", "Charger"),
    "C19": ("Device:C", "10u", C0805, "C15850", "Charger"),
    "C20": ("Device:C", "10u", C0805, "C15850", "Charger"),
    "C21": ("Device:C", "1n", C0603, "C1588", "Charger"),
    "R13": ("Device:R", "100", R0603, "C22775", "Charger"),
    "R14": ("Device:R", "3.0k (PROG: 1S, 1.5 MHz)", R0603, "C4211", "Charger"),
    "R15": ("Device:R", "120k (ILIM: REGN 5 V x 100/220 = 2.27 V -> 1.59 A clamp)", R0603, "C25808", "Charger"),
    "R16": ("Device:R", "100k", R0603, "C25803", "Charger"),
    "R17": ("Device:R", "5.1k (TS top; thresholds about +0.9 C vs 5.24k/30.31k)", R0603, "C23186", "Charger"),
    "R18": ("Device:R", "30k (TS bottom)", R0603, "C22984", "Charger"),
    "R19": ("Device:R", "2.2k", R0603, "C4190", "Charger"),
    "D2": ("Device:LED", "STAT red", "LED_SMD:LED_0603_1608Metric", "C2286", "Charger"),
    "R20": ("Device:R", "100k", R0603, "C25803", "Charger"),
    "R22": ("Device:R", "10k", R0603, "C25804", "Charger"),
    # Charger I2C bus (IO1 SDA / IO2 SCL: the RTC I2C pins of the ULP RISC-V driver) has its own 10k pull-ups to +3V3: readable while the sensor rail is off (PARTS-REVIEW A4).
    "R54": ("Device:R", "10k", R0603, "C25804", "Charger"),
    "R55": ("Device:R", "10k", R0603, "C25804", "Charger"),
    # Battery connector (hand-soldered): 1 BAT+, 2 BAT-. The cell NTC TH1 is on the board next to J6 (same cell temperature
    # as far as a board can tell; mount the holder close to the board edge where TH1 sits). TH1 bottom on GND like the TS
    # divider R18 (figure 8-1), not on the cell negative: PARTS-REVIEW B2.
    "J6": ("Connector_Generic:Conn_01x02", "BATTERY", JST_PH2, None, "Battery"),
    "TH1": ("Device:Thermistor_NTC", "10k NTC NCP18XH103F03RB (TS, next to J6)", R0603, "C13564", "Battery"),
    "#FLG3": ("power:PWR_FLAG", "PWR_FLAG", None, None, "Charger"),
    "#FLG13": ("power:PWR_FLAG", "PWR_FLAG", None, None, "Battery"),
    "#FLG14": ("power:PWR_FLAG", "PWR_FLAG", None, None, "Battery"),
    # HY2112-CB (LiFePO4 1-cell protection, OVP 3.75 V / release 3.60 V, ODP 2.10 V / release 2.30 V, discharge OC 200 mV,
    # charge OC -200 mV, 0 V charge available). Pack negative = two common-drain N-FETs: M60 (OD, discharge, source on cell -), M61 (OC, charge, source on PB-).
    # Wiring follows HY2112 datasheet section 10: VDD via R60 100 ohm + C60 0.1 uF, CS via R61 2 kohm to PB- (system GND).
    "U6": ("weatherstation:HY2112-CB", "HY2112-CB LiFePO4 protection", "Package_TO_SOT_SMD:SOT-23-6", "C168764", "Battery"),
    "M60": ("Transistor_FET:AO3400A", "AO3400A discharge FET (OD)", "Package_TO_SOT_SMD:SOT-23", "C20917", "Battery"),
    "M61": ("Transistor_FET:AO3400A", "AO3400A charge FET (OC)", "Package_TO_SOT_SMD:SOT-23", "C20917", "Battery"),
    "R60": ("Device:R", "100 (HY2112 VDD)", R0603, "C22775", "Battery"),
    "C60": ("Device:C", "0.1u (HY2112 VDD)", C0603, "C14663", "Battery"),
    "R61": ("Device:R", "2k (HY2112 CS)", R0603, "C22975", "Battery"),
    # --- MCU ---------------------------------------------------------------------------------
    "U1": ("RF_Module:ESP32-S3-WROOM-1", "ESP32-S3-WROOM-1-N8", "RF_Module:ESP32-S3-WROOM-1", "C2913198", "MCU"),
    "C30": ("Device:C", "22u", C0805, "C45783", "MCU"),
    "C31": ("Device:C", "100n", C0603, "C14663", "MCU"),
    "C32": ("Device:C", "1u", C0603, "C15849", "MCU"),
    "R30": ("Device:R", "10k", R0603, "C25804", "MCU"),
    "C33": ("Device:C", "1u", C0603, "C15849", "MCU"),
    "SW10": ("Switch:SW_Push", "RESET", "Button_Switch_SMD:SW_SPST_TL3342", "C318884", "MCU"),
    "R31": ("Device:R", "10k", R0603, "C25804", "MCU"),
    "SW11": ("Switch:SW_Push", "BOOT", "Button_Switch_SMD:SW_SPST_TL3342", "C318884", "MCU"),
    "R32": ("Device:R", "22", R0603, "C23345", "MCU"),
    "R33": ("Device:R", "22", R0603, "C23345", "MCU"),
    "J7": ("Connector_Generic:Conn_01x04", "DEBUG UART", "Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical", None, "MCU"),
    # --- Rails -------------------------------------------------------------------------------
    # 3.3 V buck-boost (replaces the AP2112K LDO: the LDO needs about 3.55 V in, and both cells sit below that).
    # Symbol: project library (pins from TI SLVSEU9D table 7-1). Footprint: project library, drawn from the TI DLA0010A example
    # board layout (build_footprints.py; PARTS-REVIEW B6).
    "U2": ("weatherstation:TPS63802DLA", "TPS63802DLA 3.3 V buck-boost", "weatherstation:TPS63802_DLA_VSON-HR-10_2x3mm", "C2845237", "Rails"),
    "L4": ("Device:L", "0.47uH (Sunlord WPN201610HR47MT: Isat 4.0 A max, Irms 2.7 A)", "weatherstation:L_Sunlord_WPN201610H", "C97009", "Rails"),
    "R52": ("Device:R", "220k 1% (FB top: 0.5 V x (1 + 220k/39k) = 3.32 V)", R0603, "C22961", "Rails"),
    "R53": ("Device:R", "39k 1% (FB bottom, datasheet max 100k)", R0603, "C23153", "Rails"),
    "C40": ("Device:C", "10u", C0603, "C19702", "Rails"),
    "C41": ("Device:C", "22u (TPS63802 output: 22 uF per table 10-1)", C0805, "C45783", "Rails"),
    "Q40": ("Transistor_FET:AO3401A", "AO3401A 3V3_SW switch", "Package_TO_SOT_SMD:SOT-23", "C15127", "Rails"),
    "R40": ("Device:R", "100k", R0603, "C25803", "Rails"),
    "Q41": ("Transistor_FET:2N7002", "2N7002 (sensor enable)", "Package_TO_SOT_SMD:SOT-23", "C8545", "Rails"),
    "R41": ("Device:R", "1k", R0603, "C21190", "Rails"),
    "R42": ("Device:R", "100k", R0603, "C25803", "Rails"),
    "C42": ("Device:C", "22u", C0805, "C45783", "Rails"),
    "C43": ("Device:C", "22u", C0805, "C45783", "Rails"),
    # 5V_SW 5 V boost for the ZE25-O3 (3.7-5.5 V; PARTS-REVIEW A5, decided 2026-11-01). TPS61023 (TI SLVSF14B): VIN 0.5-5.5 V
    # (start 1.8 V), true input/output disconnect and 0.1 uA in shutdown, so EN low = J8 unpowered. EN from BOOST_EN (IO12),
    # R45 pulls EN low = off by default (reset, deep sleep without hold). Figure 8-1 circuit: 1 uH, 10 uF in, 2 x 22 uF out.
    # FB: VREF 0.595 V x (1 + 510k/68k) = 5.06 V (580-610 mV: 4.93-5.18 V, OVP 5.5 V min). Values reuse BOM lines.
    "U7": ("weatherstation:TPS61023DRL", "TPS61023DRLR 5 V boost", "Package_TO_SOT_SMD:SOT-563", "C919459", "Rails"),
    "L5": ("Device:L", "1uH (VLS252010HBX-1R0M-1, same as L1)", "weatherstation:L_TDK_VLS252010", "C88211", "Rails"),
    "R43": ("Device:R", "510k 1% (boost FB top: 0.595 V x (1 + 510k/68k) = 5.06 V)", R0603, "C23192", "Rails"),
    "R44": ("Device:R", "68k 1% (boost FB bottom)", R0603, "C23231", "Rails"),
    "R45": ("Device:R", "100k (EN pull-down: boost off by default)", R0603, "C25803", "Rails"),
    "C44": ("Device:C", "10u (boost input)", C0603, "C19702", "Rails"),
    "C45": ("Device:C", "22u (boost output)", C0805, "C45783", "Rails"),
    "C46": ("Device:C", "22u (boost output)", C0805, "C45783", "Rails"),
    "TP1": ("Connector:TestPoint", "+3V3", TP, None, "Rails"),
    "TP2": ("Connector:TestPoint", "SYS", TP, None, "Rails"),
    "#FLG10": ("power:PWR_FLAG", "PWR_FLAG", None, None, "Rails"),
    # --- Sensors -----------------------------------------------------------------------------
    # PM sensor (option A, user 2026-11-01): Plantower PMS7003 on its 2x5 1.27 mm cable (manual V2.5): 1/2 VCC 5 V (4.5-5.5 V,
    # <= 100 mA, standby <= 200 uA), 3/4 GND, 5 RESET (internal pull-up, open), 6/8 NC, 7 RX, 9 TX, 10 SET (high/open = run,
    # low = sleep); data pins 3.3 V TTL. Stable data 30 s after wake-up. R48/R49 1k limit current into an unpowered module.
    "J2": ("Connector_Generic:Conn_02x05_Odd_Even", "PMS7003 (2x5 1.27 mm)", "Connector_PinHeader_1.27mm:PinHeader_2x05_P1.27mm_Vertical", None, "Sensors"),
    "R48": ("Device:R", "1k (PM RX series)", R0603, "C21190", "Sensors"),
    "R49": ("Device:R", "1k (PM SET series)", R0603, "C21190", "Sensors"),
    # optional CO2: Sensirion SCD41-D-R2 (LCSC C3659294), footprint only (DNP) until CO2 is wanted. Datasheet SCD4x v1.7:
    # VDD 2.4-5.5 V, peak 205 mA max at 3.3 V, ripple <= 30 mV; VDD and VDDH tied at the sensor; single shot 0.45 mA avg (1/5 min).
    "U8": ("Sensor_Gas:SCD41-D-R2", "SCD41 DNP (C3659294)", "Sensor:Sensirion_SCD4x-1EP_10.1x10.1mm_P1.25mm_EP4.8x4.8mm", None, "Sensors"),
    "C47": ("Device:C", "10u (SCD41 VDD)", C0603, "C19702", "Sensors"),
    "J3": ("Connector_Generic:Conn_01x04", "SHT45 cable", "Connector_JST:JST_SH_SM04B-SRSS-TB_1x04-1MP_P1.00mm_Horizontal", "C160404", "Sensors"),
    "J4": ("Connector_Generic:Conn_01x04", "spare port", "Connector_JST:JST_SH_SM04B-SRSS-TB_1x04-1MP_P1.00mm_Horizontal", "C160404", "Sensors"),
    "U5": ("Power_Protection:USBLC6-2SC6", "USBLC6-2SC6 (I2C)", "Package_TO_SOT_SMD:SOT-23-6", "C7519", "Sensors"),
    # Sensor I2C bus (IO13/IO14): pull-ups and U5 VBUS on 3V3_SW, so nothing back-powers the sensors when the rail is off.
    # Firmware sets IO13/IO14 to input (or low) before switching 3V3_SW off (PARTS-REVIEW A4).
    "R50": ("Device:R", "10k", R0603, "C25804", "Sensors"),
    "R51": ("Device:R", "10k", R0603, "C25804", "Sensors"),
    # ZE25-O3 7-pin (Winsen table 2, user screenshot 2026-11-01): 1 reserved, 2 DAC 0.4-2.0 V = 0-10 ppm, 3 GND,
    # 4 Vin 3.7-5.5 V, 5 RXD (0-3.0 V input), 6 TXD (0-3.0 V output), 7 reserved. Pin numbers 1:1 to the module.
    "J8": ("Connector_Generic:Conn_01x07", "ZE25-O3 (cable pitch to confirm)", "Connector_JST:JST_PH_B7B-PH-K_1x07_P2.00mm_Vertical", None, "Sensors"),
    # module RXD accepts 0-3.0 V: ESP32 TX (3.3 V) through R46 1k with R47 10k to GND = 3.0 V
    "R46": ("Device:R", "1k (GAS RXD level: 3.3 V x 10/11 = 3.0 V)", R0603, "C21190", "Sensors"),
    "R47": ("Device:R", "10k", R0603, "C25804", "Sensors"),
}

# Big parts placed by hand (cell x, cell y, rotation). Everything else is auto-placed on its sheet.
# net name -> pins (ref, pin). GND and +3V3 are power symbols; flags (#FLG) make a net powered for ERC.
NETS = {
    # Input sheet: USB-C, ESD, USB ACFET1/RBFET1, PV TVS, ACFET2/RBFET2
    "USB_VBUS": [("J1", "A4"), ("J1", "A9"), ("J1", "B4"), ("J1", "B9"), ("U4", "5"), ("M1", "3"), ("C1", "1"), ("U3", "9"), ("#FLG1", "1")],
    "ACF1_MID": [("M1", "2"), ("M2", "2")],
    "ACG1": [("M1", "1"), ("M2", "1"), ("R11", "1")],
    "ACDRV1": [("R11", "2"), ("U3", "11")],
    "VBUS": [("M2", "3"), ("M4", "3"), ("U3", "2"), ("U3", "3"), ("C6", "1"), ("C7", "1"), ("C8", "1"), ("#FLG3", "1")],
    "PV_RAW": [("J5", "1"), ("D1", "1"), ("L3", "1")],
    "PV_N_RAW": [("J5", "2"), ("D1", "2"), ("L3", "4")],
    "PV_IN": [("L3", "2"), ("C2", "1"), ("M3", "3"), ("U3", "8"), ("#FLG2", "1")],
    "ACF2_MID": [("M3", "2"), ("M4", "2")],
    "ACG2": [("M3", "1"), ("M4", "1"), ("R12", "1")],
    "ACDRV2": [("R12", "2"), ("U3", "10")],
    "CC1": [("J1", "A5"), ("R9", "1")],
    "CC2": [("J1", "B5"), ("R10", "1")],
    "USB_DP": [("J1", "A6"), ("J1", "B6"), ("U4", "1"), ("U4", "6"), ("U3", "6"), ("R32", "1")],
    "USB_DN": [("J1", "A7"), ("J1", "B7"), ("U4", "3"), ("U4", "4"), ("U3", "7"), ("R33", "1")],
    # Charger sheet
    "REGN": [("U3", "5"), ("C5", "1"), ("R15", "1"), ("R17", "1"), ("R19", "1")],
    "BTST1": [("U3", "4"), ("C3", "1")],
    "SW1": [("U3", "28"), ("C3", "2"), ("L1", "1")],
    "BTST2": [("U3", "19"), ("C4", "1")],
    "SW2": [("U3", "26"), ("C4", "2"), ("L1", "2")],
    "PMID": [("U3", "29"), ("C9", "1"), ("C10", "1"), ("C11", "1"), ("C12", "1")],
    "SYS": [("U3", "25"), ("C13", "1"), ("C14", "1"), ("C15", "1"), ("C16", "1"), ("C17", "1"), ("C18", "1"),
            ("U2", "10"), ("U2", "1"), ("C40", "1"), ("U7", "3"), ("L5", "1"), ("C44", "1"), ("TP2", "1")],
    "BAT_CON": [("J6", "1"), ("F1", "1")],
    # BAT caps C19/C20 on BAT (table 5-1: 2 x 10 uF at BAT); BATP only senses through R13 100 ohm (review A3)
    "BAT_PACK": [("U3", "22"), ("U3", "23"), ("R13", "1"), ("F1", "2"), ("R60", "1"), ("C19", "1"), ("C20", "1")],
    "BAT_N": [("J6", "2"), ("U6", "6"), ("C60", "2"), ("M60", "2"), ("#FLG14", "1")],
    "HY_VDD": [("R60", "2"), ("C60", "1"), ("U6", "5"), ("#FLG13", "1")],
    "OD": [("U6", "1"), ("M60", "1")],
    "OC": [("U6", "3"), ("M61", "1")],
    "PB_MID": [("M60", "3"), ("M61", "3")],  # common drain (HY2112 section 10, review A1)
    "HY_CS": [("U6", "2"), ("R61", "1")],
    "BATP": [("U3", "18"), ("R13", "2")],
    "SDRV": [("U3", "24"), ("C21", "1")],
    "PROG": [("U3", "20"), ("R14", "1")],
    "ILIM": [("U3", "17"), ("R15", "2"), ("R16", "1")],
    "TS": [("U3", "16"), ("R17", "2"), ("R18", "1"), ("TH1", "1")],
    "STAT": [("U3", "1"), ("D2", "1")],
    "LED_A": [("R19", "2"), ("D2", "2")],
    "CHG_CE": [("U3", "13"), ("R20", "2"), ("U1", "17")],
    # QON (pin 12) left open: internal pull-up (PARTS-REVIEW C, R21 removed 2026-11-01); no-connect marker.
    "CHG_INT": [("U3", "21"), ("R22", "1"), ("U1", "18")],
    # Two I2C buses (PARTS-REVIEW A4): charger on IO1/IO2 (always powered; RTC I2C, so the ULP core can manage charging in
    # deep sleep: ESP-IDF ulp_riscv_i2c allows SDA IO1/IO3, SCL IO0/IO2), sensors on IO13/IO14 (3V3_SW).
    "CHG_SDA": [("U3", "15"), ("U1", "39"), ("R54", "1")],
    "CHG_SCL": [("U3", "14"), ("U1", "38"), ("R55", "1")],
    "SEN_SDA": [("U1", "21"), ("U8", "10"), ("J3", "3"), ("J4", "3"), ("R50", "1"), ("U5", "1"), ("U5", "6")],
    "SEN_SCL": [("U1", "22"), ("U8", "9"), ("J3", "4"), ("J4", "4"), ("R51", "1"), ("U5", "3"), ("U5", "4")],
    # MCU sheet
    "EN": [("U1", "3"), ("R30", "2"), ("C33", "1"), ("SW10", "1")],
    "IO0": [("U1", "27"), ("R31", "2"), ("SW11", "1")],
    "ESP_DP": [("R32", "2"), ("U1", "14")],
    "ESP_DN": [("R33", "2"), ("U1", "13")],
    "TXD0": [("U1", "37"), ("J7", "2")],
    "RXD0": [("U1", "36"), ("J7", "3")],
    "SENSOR_EN": [("U1", "19"), ("R41", "1")],
    "BOOST_EN": [("U1", "20"), ("U7", "2"), ("R45", "1")],
    "GAS_TXD": [("U1", "10"), ("R46", "1")],
    "GAS_RXIN": [("R46", "2"), ("R47", "1"), ("J8", "5")],
    "GAS_RXD": [("U1", "11"), ("J8", "6")],
    "GAS_DAC": [("U1", "7"), ("J8", "2")],  # IO7 = ADC1: backup reading if the UART fails
    # Rails sheet
    "3V3_SW": [("Q40", "3"), ("C42", "1"), ("C43", "1"), ("U8", "7"), ("U8", "19"), ("C47", "1"), ("J3", "2"), ("J4", "2"), ("U5", "5"), ("R50", "2"), ("R51", "2"),
               ("#FLG10", "1")],
    "SEN_G": [("Q40", "1"), ("R40", "2"), ("Q41", "3")],
    "SEN_EN_G": [("Q41", "1"), ("R41", "2"), ("R42", "1")],
    "GAS_SW": [("U7", "5"), ("L5", "2")],
    "GAS_FB": [("U7", "1"), ("R43", "2"), ("R44", "1")],
    "5V_SW": [("U7", "6"), ("R43", "1"), ("C45", "1"), ("C46", "1"), ("J8", "4"), ("J2", "1"), ("J2", "2")],
    "PM_TXD": [("U1", "4"), ("R48", "1")],     # IO4 = UART2 TX
    "PM_RXIN": [("R48", "2"), ("J2", "7")],
    "PM_RXD": [("U1", "5"), ("J2", "9")],      # IO5 = UART2 RX
    "PM_SET": [("U1", "6"), ("R49", "1")],     # IO6: low = PMS7003 sleep (fan off) while 5V_SW stays on for the O3 module
    "PM_SETIN": [("R49", "2"), ("J2", "10")],
    # Power symbols
    # R20 (CE pull-up) on +3V3, not REGN: CE is also an ESP32 GPIO (3.3 V I/O). PARTS-REVIEW A7.
    "+3V3": [("R20", "1"), ("U1", "2"), ("C30", "1"), ("C31", "1"), ("C32", "1"), ("R30", "1"), ("R31", "1"), ("J7", "1"), ("R22", "2"),
             ("R54", "2"), ("R55", "2"), ("TP1", "1"), ("U2", "6"), ("C41", "1"), ("Q40", "2"), ("R40", "1"), ("R52", "1")],
    "BUCK_L1": [("U2", "9"), ("L4", "1")],
    "BUCK_L2": [("U2", "7"), ("L4", "2")],
    "FB": [("U2", "4"), ("R52", "2"), ("R53", "1")],
    "GND": [("J1", "A1"), ("J1", "A12"), ("J1", "B1"), ("J1", "B12"), ("J1", "SH"), ("U4", "2"), ("R9", "2"), ("R10", "2"),
            ("C1", "2"), ("C2", "2"), ("L3", "3"), ("M61", "2"), ("R61", "2"), ("R53", "2"), ("U2", "2"), ("U2", "3"), ("U2", "8"),
            ("U3", "27"), ("TH1", "2"), ("C5", "2"), ("C6", "2"), ("C7", "2"), ("C8", "2"),
            ("C9", "2"), ("C10", "2"), ("C11", "2"), ("C12", "2"), ("C13", "2"), ("C14", "2"), ("C15", "2"), ("C16", "2"),
            ("C17", "2"), ("C18", "2"), ("C19", "2"), ("C20", "2"), ("C21", "2"), ("R14", "2"), ("R16", "2"), ("R18", "2"),
            ("U1", "1"), ("U1", "40"), ("U1", "41"), ("C30", "2"), ("C31", "2"), ("C32", "2"),
            ("C33", "2"), ("SW10", "2"), ("SW11", "2"), ("J7", "4"), ("C40", "2"), ("C41", "2"), ("Q41", "2"),
            ("R42", "2"), ("C42", "2"), ("C43", "2"), ("U7", "4"), ("R44", "2"), ("R45", "2"), ("C44", "2"), ("C45", "2"),
            ("C46", "2"), ("J2", "3"), ("J2", "4"), ("U8", "6"), ("U8", "20"), ("U8", "21"), ("C47", "2"), ("J3", "1"),
            ("J4", "1"), ("U5", "2"), ("J8", "3"), ("R47", "2"), ("#FLG12", "1")],
}
# Rails: drawn as a power symbol on every pin (never routed as a wire, no hierarchical label). This is how an engineer
# reads a schematic: a capacitor with a rail symbol on top and GND below is decoupling for that rail, no wire to trace.
POWER_SYMBOLS = ("GND", "+3V3", "3V3_SW", "SYS", "VBUS", "USB_VBUS", "PMID", "REGN", "5V_SW", "BAT_PACK")
RAIL_LIB = {"GND": "power:GND", "+3V3": "power:+3V3", "VBUS": "power:VBUS"}  # others: power:VCC with the net as value


def _dedupe() -> None:
    for name, pins in NETS.items():
        assert len(pins) == len(set(pins)), f"duplicate pins in net {name}"
    used: dict[tuple[str, str], str] = {}
    for name, pins in NETS.items():
        for p in pins:
            assert p not in used, f"pin {p} in both {used[p]} and {name}"
            used[p] = name


_dedupe()


def sheets_of(net: str) -> set[str]:
    return {PARTS[ref][4] for ref, _ in NETS[net]}


SHEET_VALUE = {"L3": "CMC 90R 3A", "L4": "0.47uH", "U4": "USBLC6-2SC6", "U5": "USBLC6-2SC6", "F1": "PTC 3A",
               "TH1": "10k NTC", "U6": "HY2112-CB", "U2": "TPS63802",
               **{m: "AO3400A" for m in ("M1", "M2", "M3", "M4", "M60", "M61")}, "Q40": "AO3401A",
               "Q41": "2N7002", "U7": "TPS61023", "L5": "1uH"}


def short_value(ref: str) -> str:
    """Sheet value: the part name without the design note (the full text stays in the BOM comment)."""
    return SHEET_VALUE.get(ref) or re.split(r" \(|;", PARTS[ref][1])[0].strip()


UNWIRED: list[str] = []  # nets that kept labels because no clean wire route exists


def _text_box(x_cell: float, y_cell: float, text: str, size: float, rot: int = 0):
    """Estimated text box of a label or note at a sheet point given in cells (returns mm)."""
    from review_checks import _box
    return _box(x_cell * 2.54, y_cell * 2.54, rot % 360, text, size)


def _route_sheet(s: Sheet, items: dict, refs: list[str], extra: list, hand: dict | None = None) -> tuple[set, list, list]:
    """Route every (net, block) cluster of this sheet: wires inside a block, labels between blocks.
    items: {(net, block): [pin items]}. extra: (box_mm, owner) obstacles (notes, labels, power symbols).
    Returns (wired cluster keys, route segments, stubs)."""
    boxes = [(b, "*") for b in part_boxes(s, refs)] + [(b, o) for b, o in extra]
    router = Router([b for b, _ in boxes], [o for _, o in boxes])
    stubs = []
    hand = hand or {}
    wired: set = set()
    segs: list = []
    hand_keys = set()  # (net, block) clusters whose pins all lie on hand-drawn wires
    for net, hsegs in hand.items():  # hand-drawn wires first: fixed, and obstacles for every other net
        for a, b in hsegs:
            router.add_stub(net, a, b)
        segs.extend(hsegs)
        hand_keys.update(k for k, its in items.items()
                         if k[0] == net and all(any(_on_seg(it["pos"], s) for s in hsegs) for it in its))
    wired.update(hand_keys)
    HAND_KEYS.clear()
    HAND_KEYS.update(hand_keys)
    for key, its in items.items():
        net = key[0]
        for it in its:
            if key in hand_keys:
                continue
            router.add_stub(net, it["pos"], it["exit"])
            stubs.append((it["pos"], it["exit"]))
    for key in sorted(items, key=lambda k: (len(items[k]), k)):
        if len(items[key]) < 2 or key[0] in POWER_SYMBOLS or key in hand_keys:
            continue
        found = router.connect(key[0], [it["exit"] for it in items[key]])
        if found is not None:
            wired.add(key)
            segs.extend(found)
    return wired, segs, stubs


HAND_KEYS: set = set()  # (net, block) clusters drawn by hand on the sheet being drawn (set by _route_sheet)


def _on_seg(p, seg) -> bool:
    (ax, ay), (bx, by) = seg
    return (ax == bx == p[0] and min(ay, by) <= p[1] <= max(ay, by)) or (ay == by == p[1] and min(ax, bx) <= p[0] <= max(ax, bx))


def _clear_item(net: str, its: list, segs: list, hand: bool = False) -> dict:
    """The pin (and text direction) of a wired cluster whose name label lies clear of every wire: the stub
    direction first, then across the wire (a label on a vertical wire reads horizontally). Else the first pin."""
    from review_checks import _hits_box
    exits = {it["exit"] for it in its}
    # candidate points: the pin exits, then the middle of a wire that starts at one of them (on the 1.27 grid)
    # hand-routed: the label goes on a wire, never on the pin (it would cover the pin name), text beside the wire
    points = [] if hand else [(it["exit"], it["deg"]) for it in its]
    for a, b in segs:
        if a in exits or b in exits or (hand and any(_on_seg(e, (a, b)) for e in exits)):
            mid = (round((a[0] + b[0]) / 2 / 1.27) * 1.27, round((a[1] + b[1]) / 2 / 1.27) * 1.27)
            horiz = a[1] == b[1]
            points.append(((round(mid[0], 2), round(mid[1], 2)), (0 if horiz else 90) if hand else (90 if horiz else 0)))
    if hand:  # longest horizontal wire first: the name reads along the wire, away from the parts at its ends
        lengths = {}
        for a, b in segs:
            if a[1] == b[1] and any(_on_seg(e, (a, b)) for e in exits) or (a in exits or b in exits):
                mid = (round(round((a[0] + b[0]) / 2 / 1.27) * 1.27, 2), round(round((a[1] + b[1]) / 2 / 1.27) * 1.27, 2))
                lengths[mid] = (a[1] == b[1], abs(a[0] - b[0]) + abs(a[1] - b[1]))
        points.sort(key=lambda p: (not lengths.get(p[0], (False, 0))[0], -lengths.get(p[0], (False, 0))[1]))
    for pt, first in points:
        for deg in (first, 0, 180, 90, 270):
            box = _text_box(pt[0] / 2.54, pt[1] / 2.54, net, 1.27, deg)
            if hand:  # KiCad draws a local label beside its wire: test that box, not the wire itself
                from review_checks import _label_box
                box = _label_box(pt[0], pt[1], deg, net, 1.27)
            if not any(_hits_box((a[0], a[1], b[0], b[1]), box) for a, b in segs):
                return dict(its[0], exit=pt, deg=deg, above=hand)
    return its[0]


def _labels_for(items: dict, wired: set, segs: list | None = None) -> list:
    """(net, anchor item): a power symbol on every rail pin; one name label per wired cluster (on a pin where the
    text is clear of wires); a label on every pin of a cluster that could not be wired. Duplicate points are dropped."""
    out, seen = [], set()
    for key, its in items.items():
        net = key[0]
        if net in POWER_SYMBOLS and key in HAND_KEYS:  # hand-drawn rail: one symbol, on a pin that points up
            anchors = [next((it for it in its if it["deg"] == 90), its[0])]
        else:
            anchors = its if net in POWER_SYMBOLS or key not in wired else [_clear_item(net, its, segs or [], key in HAND_KEYS)]
        for it in anchors:
            if (net, it["exit"]) not in seen:
                seen.add((net, it["exit"]))
                out.append((net, it))
    return out


PASSIVE_LIBS = {"Device:R", "Device:C", "Device:L", "Device:Fuse", "Device:Polyfuse", "Device:Thermistor_NTC", "Device:LED"}


def _is_passive(ref: str) -> bool:
    return PARTS[ref][0] in PASSIVE_LIBS


def _net_of(ref: str, pin: str) -> str:
    return next(n for n, pins in NETS.items() if (ref, pin) in pins)


def _pin_offset(lib: str, number: str, rot: int) -> tuple[float, float]:
    """Pin position relative to the symbol origin in sheet mm (y down), for rotation rot (degrees)."""
    pin = next(p for p in ksa.get_symbol_info(lib).pins if p.number == number)
    r = math.radians(rot)
    x = pin.position.x * math.cos(r) - pin.position.y * math.sin(r)
    y = pin.position.x * math.sin(r) + pin.position.y * math.cos(r)
    return (x, -y)


def _passive_box(lib: str, x: float, y: float, rot: int) -> tuple:
    """Body plus reference/value text of a 2-pin passive at origin (x, y) mm: vertical parts carry the text on
    the right, horizontal ones above (see Sheet._auto_tags)."""
    pts = [_pin_offset(lib, p.number, rot) for p in ksa.get_symbol_info(lib).pins]
    xs, ys = [x + p[0] for p in pts], [y + p[1] for p in pts]
    if max(xs) - min(xs) < 0.1:  # vertical
        return (min(xs) - 1.6, min(ys), max(xs) + 7.0, max(ys))
    return (min(xs), min(ys) - 6.5, max(xs), max(ys) + 1.6)


def _boxes_overlap(a, b, gap: float = 0.6) -> bool:
    return min(a[2], b[2]) - max(a[0], b[0]) > -gap and min(a[3], b[3]) - max(a[1], b[1]) > -gap


USED = {p for pins in NETS.values() for p in pins}


def _anchor_passives(s: Sheet, name: str, refs: list[str]) -> dict:
    """Wire passives directly: a 2-pin part whose pin shares a SIGNAL net with a host pin (IC, FET, connector)
    on this sheet is placed with that pin on the host's stub end and rotated so its body points away from the host.
    Rails are not anchors (rail pins get power symbols). An anchor that would overlap a part, another anchored
    passive or its text is skipped: the part stays at its block position and the router wires it.
    Returns {ref: (x_cell, y_cell, rot, own_pin)}. Each host pin takes at most one passive."""
    out: dict = {}
    taken: set[tuple[str, str]] = set()
    placed = part_boxes(s, [r for r in refs if not _is_passive(r) and not r.startswith("#")], margin=0.5)
    for ref in sorted(r for r in refs if _is_passive(r)):
        lib = PARTS[ref][0]
        for own in [p.number for p in ksa.get_symbol_info(lib).pins]:
            if ref in out:
                break
            net = _net_of(ref, own)
            others = [p for p in NETS[net] if not p[0].startswith("#")]
            other_pins = [p.number for p in ksa.get_symbol_info(lib).pins if p.number != own]
            # (a) the passive is the only other part on this net, (b) its other end is a rail (pull-up, pull-down,
            # decoupling): then it terminates the pin and reads best sitting on it
            if net in POWER_SYMBOLS or len(others) != 2 or not all(_net_of(ref, o) in POWER_SYMBOLS for o in other_pins):
                continue
            for href, hpin in others:
                if href == ref or PARTS[href][4] != name or href.startswith(("#", "TP")) or _is_passive(href):
                    continue
                if (href, hpin) in taken:
                    continue
                hx, hy = s.at(href, hpin)
                deg = pin_direction(s, href, hpin)
                # (c) no other used pin of the host on the same side within 7 mm: its text would sit on that row
                crowded = any(
                    (q != hpin and (href, q) in USED and pin_direction(s, href, q) == deg
                     and 0 < math.dist(s.at(href, q), (hx, hy)) < 7.0)
                    for q in [p.number for p in ksa.get_symbol_info(PARTS[href][0]).pins])
                if crowded:
                    continue
                d = math.radians(deg)
                ox, oy = math.cos(d), -math.sin(d)  # outward unit vector (sheet coordinates)
                ex, ey = hx + 2 * 2.54 * ox, hy + 2 * 2.54 * oy
                for rot in (0, 90, 180, 270):
                    dx, dy = _pin_offset(lib, own, rot)
                    length = math.hypot(dx, dy)
                    if length and abs(dx / length + ox) < 1e-6 and abs(dy / length + oy) < 1e-6:
                        box = _passive_box(lib, ex - dx, ey - dy, rot)
                        if any(_boxes_overlap(box, b) for b in placed):
                            break
                        out[ref] = (round((ex - dx) / 2.54, 4), round((ey - dy) / 2.54, 4), rot, own)
                        taken.add((href, hpin))
                        placed.append(box)
                        break
                if ref in out:
                    break
    return out


def draw(name: str, pos: dict, used: set[tuple[str, str]]) -> Sheet:
    s = Sheet(name, SHEET_FILES[name], PARTS, "A3", SHEET_NOTE[name])
    refs = [r for r, v in PARTS.items() if v[4] == name]
    edge, tint = SHEET_COLOR[name]
    note_boxes = []  # frame titles and block notes are obstacles for wires
    for title, note, (x, y, w, h), _parts in BLOCKS[name]:
        s.frame(x, y, x + w, y + h, title, edge, tint)
        s.text(x + 0.5, y + 2.4, note, 1.1)
        note_boxes.append((_text_box(x + 0.5, y + 2.4, note, 1.1), "*"))
        note_boxes.append((_text_box(x + 0.5, y + 0.4, title, 1.5), "*"))
    # place the non-passive parts first, then the passives: anchored ones at their host pin, the rest at their block spot
    for ref in refs:
        if not _is_passive(ref):
            x, y, rot, mirror = pos[ref]
            s.part(ref, x, y, rot, value=short_value(ref), mirror=mirror)
            if ref in TAG_POS:
                s.tag(ref, reference=TAG_POS[ref][0][:2], value=TAG_POS[ref][1][:2], just=TAG_POS[ref][0][2])
    anchors = _anchor_passives(s, name, refs)
    for ref in refs:
        if _is_passive(ref):
            x, y, rot, mirror = (anchors[ref][:3] + (None,) if ref in anchors else pos[ref])
            s.part(ref, x, y, rot, value=short_value(ref), mirror=mirror)
            if ref in TAGS_BELOW:
                s.tag(ref, reference=(0, 3.4), value=(0, 5.7), just="center")
    # 1. every pin on this sheet: position and the exit point of its stub (2 cells away from the body)
    items: dict[str, list[dict]] = {}
    for net, pins in NETS.items():
        for ref, pin in pins:
            if PARTS[ref][4] != name:
                continue
            x, y = s.at(ref, pin)
            deg = int(pin_direction(s, ref, pin))
            if ref in anchors and anchors[ref][3] == pin:
                ex, ey = x, y  # wired directly to the host pin: no stub
            else:
                ex = round(x + 2 * 2.54 * math.cos(math.radians(deg)), 2)
                ey = round(y - 2 * 2.54 * math.sin(math.radians(deg)), 2)
            items.setdefault((net, BLOCK_OF[ref]), []).append(dict(pos=(x, y), exit=(ex, ey), deg=deg))
    # 2. pass 1 decides which nets are wired and where labels go; pass 2 routes around those label boxes
    # label text blocks every wire (also its own net's): iterate until the labelled set is stable
    # power symbols sit at the stub ends of rail pins: obstacles for every wire
    for (net, _blk), its in items.items():
        if net not in POWER_SYMBOLS:
            continue
        for it in its:
            (px, py), (ex, ey) = it["pos"], it["exit"]
            d = math.radians(it["deg"])
            ux, uy = round(math.cos(d)), -round(math.sin(d))  # symbols point along their stub
            fx, fy = ex + 4.5 * ux, ey + 4.5 * uy
            pad_x, pad_y = (2.2, 2.2) if ux == 0 else (2.2 + 1.27 * 0.62 * len(net), 1.4)
            note_boxes.append(((min(ex, fx) - (2.2 if ux == 0 else 0.3), min(ey, fy) - pad_y,
                                max(ex, fx) + (2.2 if ux == 0 else pad_x), max(ey, fy) + pad_y), net))
    # hand-drawn wires (layout_v1.HAND_ROUTES): polylines in mm; their pins get no stub
    hand: dict = {}
    for net, lines in HAND_ROUTES.get(name, {}).items():
        for line in lines:
            pts = [s.at(*p) if isinstance(p[0], str) else (round(p[0] * 2.54, 2), round(p[1] * 2.54, 2)) for p in line]
            for a, b in zip(pts, pts[1:]):
                assert a[0] == b[0] or a[1] == b[1], f"hand route {net}: diagonal {a} -> {b}"
                hand.setdefault(net, []).append((a, b))
        for key, its in items.items():
            if key[0] == net:
                for it in its:
                    if any(_on_seg(it["pos"], s) for s in hand[net]):
                        it["exit"] = it["pos"]
    extra: list = list(note_boxes)
    previous = None
    for _ in range(4):
        wired, segs, stubs = _route_sheet(s, items, refs, extra, hand)
        label_pts = frozenset((net, it["exit"]) for net, it in _labels_for(items, wired) if net not in POWER_SYMBOLS)
        if label_pts == previous:
            break
        previous = label_pts
        extra = list(note_boxes) + [(_text_box(it["exit"][0] / 2.54, it["exit"][1] / 2.54, net, 1.27, it["deg"]), net)
                                    for net, it in _labels_for(items, wired) if net not in POWER_SYMBOLS]
    for a, b in stubs:
        if a != b:
            s.segs.append((a, b))
    s.segs.extend(segs)
    for key in items:
        if len(items[key]) >= 2 and key not in wired and key[0] not in POWER_SYMBOLS:
            UNWIRED.append(f"{name}:{key[0]}@{key[1]}")
    # 3. labels: one name per wired net (on its wire); power symbols; every other pin labelled
    cross_nets = {n for n, _b in items if len(sheets_of(n)) > 1}
    for net, it in _labels_for(items, wired, s.segs):
        cx, cy = it["exit"][0] / 2.54, it["exit"][1] / 2.54
        if net in POWER_SYMBOLS:
            # vertical stubs: GND down / rail up, mirrored when the stub runs the other way; side stubs: turned sideways
            deg = it["deg"] % 360
            if deg in (90, 270):
                s.power(net, cx, cy, flip=(deg == 90) if net == "GND" else (deg == 270), lib=RAIL_LIB.get(net, "power:VCC"))
            else:
                rot = (deg + 90) % 360 if net == "GND" else (deg - 90) % 360
                s.power(net, cx, cy, lib=RAIL_LIB.get(net, "power:VCC"), rot=rot)
        elif it.get("above") and net in HAND_LABELS.get(name, {}):
            hx, hy, hdeg = HAND_LABELS[name][net]
            s.label(net, hx, hy, hdeg, "hier" if net in cross_nets else "local")
        else:
            s.label(net, cx, cy, it["deg"], "hier" if net in cross_nets else "local", above=it.get("above", False))
    for ref in refs:
        if ref.startswith("#"):
            continue
        for number in [p.number for p in ksa.get_symbol_info(PARTS[ref][0]).pins]:
            if (ref, number) not in used:
                s.no_connect(ref, [number])
    s.text(5, 3, f"weatherstation v1: {name}. {SHEET_NOTE[name]}", 1.5, bold=True)
    return s


def pin_direction(s: Sheet, ref: str, pin: str) -> float:
    from schkit import pin_away
    return pin_away(s.sch, ref, pin, s.mirror.get(ref))


BLOCK_OF = {ref: title for blocks in BLOCKS.values() for title, _n, _box, parts in blocks for ref in parts}


def layout_positions() -> dict:
    """Every part of every sheet placed once, inside its block (the hand layout in layout_v1.py)."""
    pos: dict = {}
    for name in SHEET_FILES:
        for title, _note, (bx, by, bw, bh), parts in BLOCKS[name]:
            for ref, spec in parts.items():
                x, y, rot = spec[:3]
                assert ref in PARTS and PARTS[ref][4] == name, f"{ref} is not on sheet {name}"
                assert ref not in pos, f"{ref} placed twice"
                assert bx <= x <= bx + bw and by <= y <= by + bh, f"{ref} at ({x},{y}) is outside block '{title}'"
                pos[ref] = (x, y, rot, {"m": "y", "my": "y", "mx": "x"}.get(spec[3]) if len(spec) > 3 else None)
        missing = [r for r, v in PARTS.items() if v[4] == name and r not in pos]
        assert not missing, f"{name}: parts not placed in any block: {missing}"
    return pos


def _side(a: tuple, b: tuple) -> str:
    """Edge of box a that faces box b (box = x, y, w, h in cells)."""
    (ax, ay, aw, ah), (bx, by, bw, bh) = a, b
    dx, dy = (bx + bw / 2) - (ax + aw / 2), (by + bh / 2) - (ay + ah / 2)
    if abs(dx) >= abs(dy):
        return "right" if dx > 0 else "left"
    return "bottom" if dy > 0 else "top"


def root_interfaces():
    """Root page: a sheet pin for every net shared by sheets, and the wires that join the pins.

    Each (net, sheet) pin sits on the box edge that faces the other sheets of that net. The wires are routed
    by the same maze router as the sheets, with the boxes as obstacles, so no two nets touch. A net that
    cannot be routed gets a root label at each pin instead (same name = same net).
    """
    from schkit import Router
    cell = 2.54
    boxes = dict(ROOT_BOX)
    nets = sorted(n for n in NETS if n not in POWER_SYMBOLS and len(sheets_of(n)) > 1)
    order = list(SHEET_FILES)
    def centre(sh):
        x, y, w, h = boxes[sh]
        return x + w / 2, y + h / 2
    pins: dict[str, list] = {n: [] for n in SHEET_FILES}
    anchor: dict[tuple, tuple] = {}
    for n in nets:
        for sh in sheets_of(n):
            others = [centre(o) for o in sheets_of(n) if o != sh]
            cx = sum(c[0] for c in others) / len(others)
            cy = sum(c[1] for c in others) / len(others)
            x, y, w, h = boxes[sh]
            dx, dy = cx - (x + w / 2), cy - (y + h / 2)
            side = ("right" if dx > 0 else "left") if abs(dx) >= abs(dy) else ("bottom" if dy > 0 else "top")
            anchor[(n, sh)] = (side, 0.0)
    # Pins of each (sheet, side), ordered by the position of the other end so wires do not cross. Smaller groups are
    # placed first (centred on the edge); a pin whose partner pin on a facing edge is already placed takes the same
    # coordinate when it can, so two-sheet nets become straight wires. Pins stay at least `step` cells apart.
    groups: dict[tuple, list] = {}
    for (n, sh), (side, _) in anchor.items():
        groups.setdefault((sh, side), []).append(n)
    point: dict[tuple, tuple] = {}
    facing = {"left": "right", "right": "left", "top": "bottom", "bottom": "top"}
    step = 2.0  # cells: a whole cell apart, on the 0.5-cell routing grid
    for (sh, side), group in sorted(groups.items(), key=lambda kv: (len(kv[1]), order.index(kv[0][0]))):
        x, y, w, h = boxes[sh]
        vertical = side in ("left", "right")
        lo, span = (y, h) if vertical else (x, w)
        def along(n, sh=sh, vertical=vertical):  # position of the other end(s) along this edge
            others = [centre(o) for o in sheets_of(n) if o != sh]
            return sum(c[1] if vertical else c[0] for c in others) / len(others)
        def desired(n, sh=sh, side=side, vertical=vertical, lo=lo, span=span):
            near = sorted(sheets_of(n), key=lambda o: (abs(centre(o)[0] - centre(sh)[0]) + abs(centre(o)[1] - centre(sh)[1]), o))
            for o in near:  # nearest placed partner on a facing edge (deterministic, not set order)
                if o != sh and (n, o) in point and anchor[(n, o)][0] == facing[side]:
                    c = point[(n, o)][1] if vertical else point[(n, o)][0]
                    if lo + 2 <= c <= lo + span - 2:
                        return c
            return None
        ranked = sorted(group, key=lambda n: (desired(n) is None, desired(n) or along(n), along(n), n))
        pos_of, prev = {}, None
        n_free = sum(desired(n) is None for n in group)
        for n in ranked:
            d = desired(n)
            if d is None and prev is None:
                d = lo + span / 2 - step * (n_free - 1) / 2
            pos = d if prev is None else max(d if d is not None else -1e9, prev + step)
            pos_of[n] = prev = round(pos * 2) / 2
        for n in group:
            pos = pos_of[n]
            point[(n, sh)] = {"left": (x, pos), "right": (x + w, pos), "top": (pos, y), "bottom": (pos, y + h)}[side]
            pins[sh].append((side, pos, n))
    # route each net: pins are the tree leaves; exits point out of their box
    router = Router([(bx * cell, by * cell, (bx + bw) * cell, (by + bh) * cell) for bx, by, bw, bh in boxes.values()])
    out_dir = {"left": (-1, 0), "right": (1, 0), "top": (0, -1), "bottom": (0, 1)}
    wires: list = []
    unrouted: list[tuple[str, str]] = []
    all_exits: dict[str, list] = {}
    for n in nets:  # every stub first, so no route can run over another net's pin
        exits = []
        for sh in sorted(sheets_of(n), key=order.index):
            side = anchor[(n, sh)][0]
            px, py = point[(n, sh)]
            ex, ey = px + out_dir[side][0], py + out_dir[side][1]  # one cell out of the box (cells)
            exits.append(((px * cell, py * cell), (ex * cell, ey * cell)))
        for pin, ext in exits:
            router.add_stub(n, pin, ext)
        all_exits[n] = exits
    for n in sorted(nets, key=lambda n: len(all_exits[n])):
        exits = all_exits[n]
        segs = router.connect(n, [e for _, e in exits], strict=False)
        if segs is None:
            unrouted.append((n, "unrouted"))
            continue
        wires.extend(((a[0] / cell, a[1] / cell), (b[0] / cell, b[1] / cell)) for a, b in segs)
        for pin, ext in exits:  # the stub from the pin out of its box
            wires.append(((pin[0] / cell, pin[1] / cell), (ext[0] / cell, ext[1] / cell)))
    texts = [(6, 6, "#weatherstation v1 (esp32-weatherstation): block diagram"),
             (6, 10, "Each box is a sheet. Wires join the sheet pins, which are the hierarchical labels inside each sheet."),
             (6, 96, "Power path: USB-C or PV -> Input (ACFET/RBFET pairs) -> VBUS -> Charger (BQ25798) -> SYS -> Rails (TPS63802) -> +3V3 -> 3V3_SW;"),
             (6, 98, "SYS -> TPS61023 5 V boost -> 5V_SW. Cell: Battery (HY2112, PTC) <-> BAT_PACK <-> Charger. Rails (GND, +3V3, SYS, VBUS, ...) are power symbols on each sheet, not wires here."),
             (6, 101, "Open engineer decisions: hardware/weatherstation-v1/PARTS-REVIEW.md (parts and circuit review, 2026-11-01).")]
    # unrouted nets: the reserved 1-cell exit stub out of the box with the label at its end, text pointing away from the box
    root_labels = []
    ang = {"left": 180, "right": 0, "top": 90, "bottom": 270}
    for n, _ in unrouted:
        for sh in sheets_of(n):
            side = anchor[(n, sh)][0]
            px, py = point[(n, sh)]
            ex, ey = px + out_dir[side][0], py + out_dir[side][1]
            wires.append(((px, py), (ex, ey)))
            root_labels.append((n, ex, ey, ang[side]))
    return pins, wires, texts, root_labels


def build(out: Path) -> Path:
    out.mkdir(parents=True, exist_ok=True)
    Sheet.pwr_count = 0
    used = {p for pins in NETS.values() for p in pins}
    pos = layout_positions()
    sheets = [draw(n, pos, used) for n in SHEET_FILES]
    root_uuid = str(uuid.uuid5(uuid.NAMESPACE_URL, "root"))
    sd = []
    for i, n in enumerate(SHEET_FILES):
        x, y, w, h = ROOT_BOX[n]
        stroke, fill = SHEET_COLOR[n]
        sd.append(dict(name=n, file=SHEET_FILES[n], x=x, y=y, w=w, h=h, page=str(i + 2),
                       uuid=str(uuid.uuid5(uuid.NAMESPACE_URL, "sheet/" + n)), pins=[], stroke=stroke, fill=fill))
    root_pins, root_wires, texts, root_labels = root_interfaces()
    import textwrap
    for n in SHEET_FILES:  # what each box does, inside the box
        bx, by, bw, bh = ROOT_BOX[n]
        for k, line in enumerate(textwrap.wrap(SHEET_PURPOSE[n], 52)):
            texts.append((bx + 1.5, by + 1.5 + 2.0 * k, line))
    for sh in sd:
        sh["pins"] = root_pins[sh["name"]]
    path, _ = root_sheet(out, "root", sd, texts, root_wires, root_labels)
    for sh in sheets:
        sh.save(out, root_uuid, str(uuid.uuid5(uuid.NAMESPACE_URL, "sheet/" + sh.name)))
    return path


# JLCPCB class (Basic / Extended) and stock from hardware/tools/jlcparts.py, snapshot 2026-10-31.
JLC_CLASS = {"C165948": "Extended", "C7519": "Extended", "C23186": "Basic", "C15127": "Basic", "C23025": "Basic",
             "C14663": "Basic", "C2876593": "Extended", "C88211": "Extended", "C113811": "Extended",
             "C19666": "Basic", "C15850": "Basic", "C53084481": "Extended", "C22775": "Basic", "C4211": "Basic",
             "C22869": "Extended", "C25803": "Basic", "C23068": "Extended", "C23000": "Extended", "C13564": "Extended",
             "C4190": "Basic", "C2286": "Basic", "C25804": "Basic", "C2913198": "Extended", "C45783": "Basic",
             "C15849": "Basic", "C318884": "Basic", "C23345": "Basic", "C51118": "Extended", "C19702": "Basic",
             "C8545": "Basic", "C21190": "Basic", "C133065": "Extended", "C160404": "Extended",
             "C21004": "Extended",
             "C2845237": "Extended", "C151250": "Extended", "C963746": "Extended", "C97009": "Extended", "C227946": "Extended", "C23265": "Extended",
             "C168764": "Extended", "C20917": "Basic", "C177639": "Extended",
             "C919459": "Extended", "C23231": "Basic",
             # Basic swaps 2026-11-01
             "C1622": "Basic", "C1588": "Basic", "C25808": "Basic", "C22984": "Basic", "C22975": "Basic",
             "C22961": "Basic", "C23153": "Basic", "C23192": "Basic"}  # TPS61023DRLR 44.7k stock, 68k (2026-11-01)
HAND_SOLDER = {"J2", "J5", "J6", "J7", "J8"}  # JST PH and pin header: hand-soldered, not in the assembly BOM


def write_bom(path: Path) -> None:
    """bom.csv from PARTS: one row per (value, footprint, LCSC), designators sorted. Power symbols and flags excluded."""
    # One row per LCSC part (same part, same line, whatever the design note says); parts without LCSC group by value.
    groups: dict[tuple, list[str]] = {}
    for ref, (sym, value, fp, lcsc, _sheet) in PARTS.items():
        if ref.startswith("#") or ref.startswith("TP"):
            continue
        groups.setdefault((lcsc or value, fp or "", lcsc or ""), []).append(ref)
    cols = ["Comment", "Designator", "Footprint", "Quantity", "LCSC Part #", "Class", "Status", "Function / notes"]
    rows = []
    for (_key, fp, lcsc), refs in groups.items():
        refs = sorted(refs, key=lambda r: (r[0], int("".join(ch for ch in r if ch.isdigit()) or 0)))
        value = short_value(refs[0])  # clean part value; design notes per designator go to the notes column
        notes = "; ".join(f"{r}: {PARTS[r][1]}" for r in refs if PARTS[r][1] != value)
        if lcsc:
            cls, status = JLC_CLASS[lcsc], "VERIFIED LCSC part (class and stock 2026-10-31; datasheet values open)"
        else:
            cls = "n/a"
            status = "HAND-SOLDER" if all(r in HAND_SOLDER for r in refs) else "NOT ASSEMBLED"
        rows.append([value, ",".join(refs), fp, str(len(refs)), lcsc or "n/a", cls, status, notes])
    tp = [r for r, v in PARTS.items() if r.startswith("TP")]
    if tp:
        rows.append(["Test points", ",".join(sorted(tp)), TP, str(len(tp)), "n/a", "n/a", "PCB pads only", "GND/3V3 test pads"])
    import csv, io
    buf = io.StringIO()
    csv.writer(buf, lineterminator="\n").writerows([cols] + rows)  # quotes fields with commas or quotes
    path.write_text(buf.getvalue())


def drawing_issues() -> list[str]:
    """Review rule a net list alone cannot show: a net with a single pin goes nowhere (dangling).
    Unused pins are not errors: draw() puts a no-connect marker on each one."""
    out = []
    for net, pins in NETS.items():
        if net not in POWER_SYMBOLS and len([p for p in pins if not p[0].startswith("#")]) < 2:
            out.append(f"dangling net {net}: {pins}")
    return out


if __name__ == "__main__":
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("hardware/weatherstation-v1")
    path = build(out)
    write_bom(out / "bom.csv")
    errors = check_nets(path, NETS) + drawing_issues()
    print("\n".join(errors) or f"{path}: nets OK; bom.csv written")
    sys.exit(1 if errors else 0)
