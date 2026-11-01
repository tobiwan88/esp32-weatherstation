"""weatherstation-v1 schematic: BQ25798 charger for USB-C and a PV panel, ESP32-S3-WROOM-1, 3.3 V LDO,
switched sensor rail, SEN66 / SHT45 connectors, ZE25-O3 gas-sensor connector.

PARTS and NETS are the source of truth. check_nets() compares them with KiCad's own netlist.
Drawing: each pin gets a short stub with a net label (global label when the net crosses sheets,
local label otherwise). GND and +3V3 are power symbols. Unused pins get no-connect markers.
Values marked "candidate" or "confirm" are not final: see hardware/weatherstation-v1/usb-charger-bq25798.md.

Run: uv run --package weatherstation-hardware python hardware/gen/weatherstation_v1.py [out_dir]
"""

import math
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kicad_sch_api as ksa  # noqa: E402

# Project symbols (TPS63802 DLA, HY2112-CB) are not in the KiCad libraries: written by build_symbols.py.
ksa.get_symbol_cache().add_library_path(Path(__file__).resolve().parent / "lib" / "weatherstation.kicad_sym")

from schkit import Sheet, root_sheet, check_nets  # noqa: E402

R0603, C0603, C0805 = "Resistor_SMD:R_0603_1608Metric", "Capacitor_SMD:C_0603_1608Metric", "Capacitor_SMD:C_0805_2012Metric"
JST_PH2 = "Connector_JST:JST_PH_B2B-PH-K_1x02_P2.00mm_Vertical"
TP = "TestPoint:TestPoint_Pad_D1.5mm"
SHEET_FILES = {"Input": "input.kicad_sch", "Charger": "charger.kicad_sch", "MCU": "mcu.kicad_sch",
               "Rails": "rails.kicad_sch", "Sensors": "sensors.kicad_sch"}
SHEET_NOTE = {
    "Input": "USB-C input (ACFET1/RBFET1); PV connector, TVS (D1), common-mode choke (L3), then ACFET2/RBFET2 into VBUS",
    "Charger": "BQ25798 charger (USB + PV, TS, PROG 1S 1.5 MHz); cell NTC TH1 next to J6; cell PTC F1; HY2112-CB LiFePO4 protection (M60/M61 in the pack negative)",
    "MCU": "ESP32-S3-WROOM-1 module, EN/BOOT, USB data series resistors, UART debug header",
    "Rails": "SYS -> TPS63802 buck-boost 3.3 V (L4, FB divider R52/R53), switched sensor rail 3V3_SW, switched gas-sensor supply GAS_VCC",
    "Sensors": "SEN66 (GH 6-pin), SHT45 cable (4-pin), spare port, I2C ESD and pull-ups, ZE25-O3 connector",
}

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
    "D1": ("Device:D_TVS", "SMBJ24A (PV surge, across the connector pair before L3)", "Diode_SMD:D_SMB", "C87268", "Input"),
    # 2-line common-mode choke on the PV pair, >= 1 A. Pinout from EMTEK spec T-0602-102D (equivalent circuit):
    # winding A = 1 (in, top left) -> 2 (out, top right); winding B = 4 (in, bottom left) -> 3 (out, bottom right).
    # Footprint: project library weatherstation:CMF4532F_4P (land pattern from section 7-1).
    "L3": ("Device:L_Coupled", "CM choke 1 kohm 1 A (CMF4532F-102-2P-T; pinout and footprint to confirm)", "weatherstation:CMF4532F_4P", "C963748", "Input"),
    "J5": ("Connector_Generic:Conn_01x02", "PV IN", JST_PH2, None, "Input"),
    "#FLG1": ("power:PWR_FLAG", "PWR_FLAG", None, None, "Input"),
    "#FLG2": ("power:PWR_FLAG", "PWR_FLAG", None, None, "Input"),
    "#FLG12": ("power:PWR_FLAG", "PWR_FLAG", None, None, "Input"),
    # --- Charger -----------------------------------------------------------------------------
    "U3": ("Battery_Management:BQ25798", "BQ25798RQMR", "Package_DFN_QFN:Texas_RQM0029A_VQFN-29_4x4mm_P0.4mm", "C2876593", "Charger"),
    "L1": ("Device:L", "1uH (candidate; Isat to confirm)", "Inductor_SMD:L_1008_2520Metric", "C88211", "Charger"),
    # Cell overcurrent backup: PTC hold 3 A, trip 5 A, 8 V. Only overcurrent protection on the pack (no cell protection IC).
    "F1": ("Device:Fuse", "PTC 3 A hold (SMD1812P300TF)", "Fuse:Fuse_1812_4532Metric", "C21004", "Charger"),
    "C3": ("Device:C", "47n", C0603, "C113811", "Charger"),
    "C4": ("Device:C", "47n", C0603, "C113811", "Charger"),
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
    "C21": ("Device:C", "1n", C0603, "C53084481", "Charger"),
    "R23": ("Device:R", "10m Rs (candidate; input current sense)", "Resistor_SMD:R_2512_6332Metric", "C2903462", "Charger"),
    "R13": ("Device:R", "100", R0603, "C22775", "Charger"),
    "R14": ("Device:R", "3.0k (PROG: 1S, 1.5 MHz)", R0603, "C4211", "Charger"),
    "R15": ("Device:R", "127k", R0603, "C22869", "Charger"),
    "R16": ("Device:R", "100k", R0603, "C25803", "Charger"),
    "R17": ("Device:R", "5.23k (candidate; figure 5.24k)", R0603, "C23068", "Charger"),
    "R18": ("Device:R", "30.1k (candidate; figure 30.31k)", R0603, "C23000", "Charger"),
    "R19": ("Device:R", "2.2k", R0603, "C4190", "Charger"),
    "D2": ("Device:LED", "STAT red", "LED_SMD:LED_0603_1608Metric", "C2286", "Charger"),
    "R20": ("Device:R", "100k", R0603, "C25803", "Charger"),
    "R21": ("Device:R", "100k", R0603, "C25803", "Charger"),
    "R22": ("Device:R", "10k", R0603, "C25804", "Charger"),
    # Battery connector (hand-soldered): 1 BAT+, 2 BAT-. The cell NTC TH1 is on the board next to J6 (same cell temperature
    # as far as a board can tell; mount the holder close to the board edge where TH1 sits).
    "J6": ("Connector_Generic:Conn_01x02", "BATTERY", JST_PH2, None, "Charger"),
    "TH1": ("Device:Thermistor_NTC", "10k NTC NCP18XH103F03RB (TS, next to J6)", R0603, "C13564", "Charger"),
    "#FLG3": ("power:PWR_FLAG", "PWR_FLAG", None, None, "Charger"),
    "#FLG13": ("power:PWR_FLAG", "PWR_FLAG", None, None, "Charger"),
    "#FLG14": ("power:PWR_FLAG", "PWR_FLAG", None, None, "Charger"),
    # HY2112-CB (LiFePO4 1-cell protection, OVP 3.75 V / release 3.60 V, ODP 2.10 V / release 2.30 V, discharge OC 200 mV,
    # charge OC -200 mV, 0 V charge available). Pack negative = two common-source N-FETs: M60 (OD, discharge), M61 (OC, charge).
    # Wiring follows HY2112 datasheet section 10: VDD via R60 100 ohm + C60 0.1 uF, CS via R61 2 kohm to PB- (system GND).
    "U6": ("weatherstation:HY2112-CB", "HY2112-CB LiFePO4 protection", "Package_TO_SOT_SMD:SOT-23-6", "C168764", "Charger"),
    "M60": ("Transistor_FET:AO3400A", "AO3400A discharge FET (OD)", "Package_TO_SOT_SMD:SOT-23", "C20917", "Charger"),
    "M61": ("Transistor_FET:AO3400A", "AO3400A charge FET (OC)", "Package_TO_SOT_SMD:SOT-23", "C20917", "Charger"),
    "R60": ("Device:R", "100 (HY2112 VDD)", R0603, "C22775", "Charger"),
    "C60": ("Device:C", "0.1u (HY2112 VDD)", C0603, "C14663", "Charger"),
    "R61": ("Device:R", "2k (HY2112 CS)", R0603, "C177639", "Charger"),
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
    # Symbol: project library (pins from TI SLVSEU9D table 7-1). Footprint: closest KiCad 10-pin 2x3 mm WSON with 0.5 mm pitch;
    # check against the DLA land pattern in the TI datasheet before layout.
    "U2": ("weatherstation:TPS63802DLA", "TPS63802DLA 3.3 V buck-boost", "Package_SON:WSON-10-1EP_2x3mm_P0.5mm_EP0.84x2.4mm", "C2845237", "Rails"),
    "L4": ("Device:L", "0.47uH 2.7 A (WPN201610HR47MT)", "Inductor_SMD:L_Cenker_CKCS201610", "C97009", "Rails"),
    "R52": ("Device:R", "511k 1% (FB top: 0.5 V x (1 + 511k/91k) = 3.31 V)", R0603, "C227946", "Rails"),
    "R53": ("Device:R", "91k 1% (FB bottom)", R0603, "C23265", "Rails"),
    "C40": ("Device:C", "10u", C0603, "C19702", "Rails"),
    "C41": ("Device:C", "22u (TPS63802 output: 22 uF per table 10-1)", C0805, "C45783", "Rails"),
    "Q40": ("Transistor_FET:AO3401A", "AO3401A 3V3_SW switch", "Package_TO_SOT_SMD:SOT-23", "C15127", "Rails"),
    "R40": ("Device:R", "100k", R0603, "C25803", "Rails"),
    "Q41": ("Transistor_FET:2N7002", "2N7002 (sensor enable)", "Package_TO_SOT_SMD:SOT-23", "C8545", "Rails"),
    "R41": ("Device:R", "1k", R0603, "C21190", "Rails"),
    "R42": ("Device:R", "100k", R0603, "C25803", "Rails"),
    "C42": ("Device:C", "22u", C0805, "C45783", "Rails"),
    "C43": ("Device:C", "22u", C0805, "C45783", "Rails"),
    "Q42": ("Transistor_FET:AO3401A", "AO3401A gas switch", "Package_TO_SOT_SMD:SOT-23", "C15127", "Rails"),
    "R43": ("Device:R", "100k", R0603, "C25803", "Rails"),
    "Q43": ("Transistor_FET:2N7002", "2N7002 (gas enable)", "Package_TO_SOT_SMD:SOT-23", "C8545", "Rails"),
    "R44": ("Device:R", "1k", R0603, "C21190", "Rails"),
    "R45": ("Device:R", "100k", R0603, "C25803", "Rails"),
    "C44": ("Device:C", "10u", C0603, "C19702", "Rails"),
    "TP1": ("Connector:TestPoint", "+3V3", TP, None, "Rails"),
    "TP2": ("Connector:TestPoint", "SYS", TP, None, "Rails"),
    "#FLG10": ("power:PWR_FLAG", "PWR_FLAG", None, None, "Rails"),
    # --- Sensors -----------------------------------------------------------------------------
    "J2": ("Connector_Generic:Conn_01x06", "SEN66 (GH 6-pin)", "Connector_JST:JST_GH_SM06B-GHS-TB_1x06-1MP_P1.25mm_Horizontal", "C133065", "Sensors"),
    "J3": ("Connector_Generic:Conn_01x04", "SHT45 cable", "Connector_JST:JST_SH_SM04B-SRSS-TB_1x04-1MP_P1.00mm_Horizontal", "C160404", "Sensors"),
    "J4": ("Connector_Generic:Conn_01x04", "spare port", "Connector_JST:JST_SH_SM04B-SRSS-TB_1x04-1MP_P1.00mm_Horizontal", "C160404", "Sensors"),
    "U5": ("Power_Protection:USBLC6-2SC6", "USBLC6-2SC6 (I2C)", "Package_TO_SOT_SMD:SOT-23-6", "C7519", "Sensors"),
    "R50": ("Device:R", "10k", R0603, "C25804", "Sensors"),
    "R51": ("Device:R", "10k", R0603, "C25804", "Sensors"),
    "J8": ("Connector_Generic:Conn_01x04", "ZE25-O3 (pinout confirm)", "Connector_JST:JST_PH_B4B-PH-K_1x04_P2.00mm_Vertical", None, "Sensors"),
    "#FLG11": ("power:PWR_FLAG", "PWR_FLAG", None, None, "Sensors"),
}

# Big parts placed by hand (cell x, cell y, rotation). Everything else is auto-placed on its sheet.
FIXED = {"J6": (150, 76, 0), "TH1": (150, 86, 0), "J1": (150, 30, 0), "U4": (150, 62, 0), "U3": (150, 50, 0), "U1": (150, 40, 0), "U2": (150, 40, 0),
         "U5": (150, 84, 0), "J2": (150, 14, 0), "J3": (150, 40, 0), "J4": (150, 66, 0), "J8": (150, 96, 0)}

# net name -> pins (ref, pin). GND and +3V3 are power symbols; flags (#FLG) make a net powered for ERC.
NETS = {
    # Input sheet: USB-C, ESD, USB ACFET1/RBFET1, PV TVS, ACFET2/RBFET2
    "USB_VBUS": [("J1", "A4"), ("J1", "A9"), ("J1", "B4"), ("J1", "B9"), ("U4", "5"), ("M1", "3"), ("C1", "1"), ("U3", "9"), ("#FLG1", "1")],
    "ACF1_MID": [("M1", "2"), ("M2", "2")],
    "ACG1": [("M1", "1"), ("M2", "1"), ("R11", "1")],
    "ACDRV1": [("R11", "2"), ("U3", "11")],
    "VBUS": [("M2", "3"), ("M4", "3"), ("U3", "2"), ("U3", "3"), ("C6", "1"), ("C7", "1"), ("C8", "1"), ("#FLG3", "1"), ("R23", "1")],
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
    "REGN": [("U3", "5"), ("C5", "1"), ("R15", "1"), ("R17", "1"), ("R19", "1"), ("R20", "1"), ("R21", "1")],
    "BTST1": [("U3", "4"), ("C3", "1")],
    "SW1": [("U3", "28"), ("C3", "2"), ("L1", "1")],
    "BTST2": [("U3", "19"), ("C4", "1")],
    "SW2": [("U3", "26"), ("C4", "2"), ("L1", "2")],
    "PMID": [("U3", "29"), ("C9", "1"), ("C10", "1"), ("C11", "1"), ("C12", "1"), ("R23", "2")],
    "SYS": [("U3", "25"), ("C13", "1"), ("C14", "1"), ("C15", "1"), ("C16", "1"), ("C17", "1"), ("C18", "1"),
            ("U2", "10"), ("U2", "1"), ("C40", "1"), ("R43", "1"), ("Q42", "2"), ("TP2", "1")],
    "BAT_CON": [("J6", "1"), ("F1", "1")],
    "BAT_PACK": [("U3", "22"), ("U3", "23"), ("R13", "1"), ("F1", "2"), ("R60", "1")],
    "BAT_N": [("J6", "2"), ("U6", "6"), ("C60", "2"), ("M60", "3"), ("#FLG14", "1"), ("TH1", "2")],
    "HY_VDD": [("R60", "2"), ("C60", "1"), ("U6", "5"), ("#FLG13", "1")],
    "OD": [("U6", "1"), ("M60", "1")],
    "OC": [("U6", "3"), ("M61", "1")],
    "PB_MID": [("M60", "2"), ("M61", "2")],
    "HY_CS": [("U6", "2"), ("R61", "1")],
    "BATP": [("U3", "18"), ("R13", "2"), ("C19", "1"), ("C20", "1")],
    "SDRV": [("U3", "24"), ("C21", "1")],
    "PROG": [("U3", "20"), ("R14", "1")],
    "ILIM": [("U3", "17"), ("R15", "2"), ("R16", "1")],
    "TS": [("U3", "16"), ("R17", "2"), ("R18", "1"), ("TH1", "1")],
    "STAT": [("U3", "1"), ("D2", "1")],
    "LED_A": [("R19", "2"), ("D2", "2")],
    "CHG_CE": [("U3", "13"), ("R20", "2"), ("U1", "17")],
    "QON": [("U3", "12"), ("R21", "2")],
    "CHG_INT": [("U3", "21"), ("R22", "1"), ("U1", "18")],
    "I2C_SDA": [("U3", "15"), ("U1", "4"), ("J2", "3"), ("J3", "3"), ("J4", "3"), ("R50", "1"), ("U5", "1"), ("U5", "6")],
    "I2C_SCL": [("U3", "14"), ("U1", "5"), ("J2", "4"), ("J3", "4"), ("J4", "4"), ("R51", "1"), ("U5", "3"), ("U5", "4")],
    # MCU sheet
    "EN": [("U1", "3"), ("R30", "2"), ("C33", "1"), ("SW10", "1")],
    "IO0": [("U1", "27"), ("R31", "2"), ("SW11", "1")],
    "ESP_DP": [("R32", "2"), ("U1", "14")],
    "ESP_DN": [("R33", "2"), ("U1", "13")],
    "TXD0": [("U1", "37"), ("J7", "2")],
    "RXD0": [("U1", "36"), ("J7", "3")],
    "SENSOR_EN": [("U1", "19"), ("R41", "1")],
    "GAS_EN": [("U1", "20"), ("R44", "1")],
    "GAS_TXD": [("U1", "10"), ("J8", "4")],
    "GAS_RXD": [("U1", "11"), ("J8", "3")],
    # Rails sheet
    "3V3_SW": [("Q40", "3"), ("C42", "1"), ("C43", "1"), ("J2", "1"), ("J3", "2"), ("J4", "2"), ("U5", "5"), ("#FLG10", "1")],
    "SEN_G": [("Q40", "1"), ("R40", "2"), ("Q41", "3")],
    "SEN_EN_G": [("Q41", "1"), ("R41", "2"), ("R42", "1")],
    "GAS_G": [("Q42", "1"), ("R43", "2"), ("Q43", "3")],
    "GAS_EN_G": [("Q43", "1"), ("R44", "2"), ("R45", "1")],
    "GAS_VCC": [("Q42", "3"), ("C44", "1"), ("J8", "1"), ("#FLG11", "1")],
    # Power symbols
    "+3V3": [("U1", "2"), ("C30", "1"), ("C31", "1"), ("C32", "1"), ("R30", "1"), ("R31", "1"), ("J7", "1"), ("R22", "2"),
             ("R50", "2"), ("R51", "2"), ("TP1", "1"), ("U2", "6"), ("C41", "1"), ("Q40", "2"), ("R40", "1"), ("R52", "1")],
    "BUCK_L1": [("U2", "9"), ("L4", "1")],
    "BUCK_L2": [("U2", "7"), ("L4", "2")],
    "FB": [("U2", "4"), ("R52", "2"), ("R53", "1")],
    "GND": [("J1", "A1"), ("J1", "A12"), ("J1", "B1"), ("J1", "B12"), ("J1", "SH"), ("U4", "2"), ("R9", "2"), ("R10", "2"),
            ("C1", "2"), ("C2", "2"), ("L3", "3"), ("M61", "3"), ("R61", "2"), ("R53", "2"), ("U2", "2"), ("U2", "3"), ("U2", "8"),
            ("U3", "27"), ("C5", "2"), ("C6", "2"), ("C7", "2"), ("C8", "2"),
            ("C9", "2"), ("C10", "2"), ("C11", "2"), ("C12", "2"), ("C13", "2"), ("C14", "2"), ("C15", "2"), ("C16", "2"),
            ("C17", "2"), ("C18", "2"), ("C19", "2"), ("C20", "2"), ("C21", "2"), ("R14", "2"), ("R16", "2"), ("R18", "2"),
            ("U1", "1"), ("U1", "40"), ("U1", "41"), ("C30", "2"), ("C31", "2"), ("C32", "2"),
            ("C33", "2"), ("SW10", "2"), ("SW11", "2"), ("J7", "4"), ("C40", "2"), ("C41", "2"), ("Q41", "2"),
            ("R42", "2"), ("C42", "2"), ("C43", "2"), ("Q43", "2"), ("R45", "2"), ("C44", "2"), ("J2", "2"), ("J3", "1"),
            ("J4", "1"), ("U5", "2"), ("J8", "2"), ("#FLG12", "1")],
}
POWER_SYMBOLS = ("GND", "+3V3")


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


def draw(name: str, pos: dict, used: set[tuple[str, str]]) -> Sheet:
    s = Sheet(name, SHEET_FILES[name], PARTS, "A3", SHEET_NOTE[name])
    refs = [r for r, v in PARTS.items() if v[4] == name]
    for ref in refs:
        x, y, rot = pos[ref]
        s.part(ref, x, y, rot)
    for net, pins in NETS.items():
        for ref, pin in pins:
            if PARTS[ref][4] != name:
                continue
            x, y = s.at(ref, pin)
            deg = int(pin_direction(s, ref, pin))
            ex = round(x + 3 * 2.54 * math.cos(math.radians(deg)), 2)
            ey = round(y - 3 * 2.54 * math.sin(math.radians(deg)), 2)
            s.segs.append(((x, y), (ex, ey)))
            cx, cy = ex / 2.54, ey / 2.54
            if net in POWER_SYMBOLS:
                s.power(net, cx, cy)
            else:
                kind = "global" if len(sheets_of(net)) > 1 else "local"
                s.label(net, cx, cy, deg, kind)
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
    return pin_away(s.sch, ref, pin)


def build(out: Path) -> Path:
    out.mkdir(parents=True, exist_ok=True)
    Sheet.pwr_count = 0
    used = {p for pins in NETS.values() for p in pins}
    pos = dict(FIXED)
    for name in SHEET_FILES:
        free = [r for r, v in PARTS.items() if v[4] == name and r not in FIXED and not r.startswith("#")]
        for i, r in enumerate(free):
            col, row = divmod(i, 8)  # columns 30 cells apart, rows 14 cells apart (pin stubs and labels must not meet)
            assert col < 6, f"{name}: too many small parts for the grid"
            pos[r] = (6 + 30 * col, 8 + 14 * row, 0)
        flags = [r for r, v in PARTS.items() if v[4] == name and r.startswith("#")]
        for i, r in enumerate(flags):
            pos[r] = (150, 112 - 8 * i, 0)
    sheets = [draw(n, pos, used) for n in SHEET_FILES]
    root_uuid = str(uuid.uuid5(uuid.NAMESPACE_URL, "root"))
    sd = []
    blocks = {"Input": (6, 18, 44, 36), "Charger": (60, 18, 48, 52), "MCU": (118, 18, 36, 30),
              "Rails": (118, 58, 36, 24), "Sensors": (6, 64, 44, 30)}
    for i, n in enumerate(SHEET_FILES):
        x, y, w, h = blocks[n]
        sd.append(dict(name=n, file=SHEET_FILES[n], x=x, y=y, w=w, h=h, page=str(i + 2),
                       uuid=str(uuid.uuid5(uuid.NAMESPACE_URL, "sheet/" + n)), pins=[]))
    texts = [(6, 6, "#weatherstation v1 (esp32-weatherstation). Charger: BQ25798 for USB-C and PV (both inputs)."),
             (6, 10, "Connections are net labels: global labels cross sheets, local labels stay on the sheet. GND and +3V3 are power symbols."),
             (60, 72, "Battery: BQ25798 buck-boost (SYS 4.0 V min via VSYSMIN). TS: 5.23k/30.1k/NTC (JEITA)."),
             (118, 86, "3.3 V: TPS63802 buck-boost from SYS (L4). 3V3_SW is switched (Q40), GAS_VCC is switched (Q42)."),
             (6, 97, "Open: ZE25-O3 pinout, Isat of L1, ACDRV polarity (Table 7-7), FET values, fp names.")]
    path, _ = root_sheet(out, "root", sd, texts, [], [])
    for sh in sheets:
        sh.save(out, root_uuid, str(uuid.uuid5(uuid.NAMESPACE_URL, "sheet/" + sh.name)))
    return path


# JLCPCB class (Basic / Extended) and stock from hardware/tools/jlcparts.py, snapshot 2026-10-31.
JLC_CLASS = {"C165948": "Extended", "C7519": "Extended", "C23186": "Basic", "C15127": "Basic", "C23025": "Basic",
             "C14663": "Basic", "C87268": "Extended", "C2876593": "Extended", "C88211": "Extended", "C113811": "Extended",
             "C19666": "Basic", "C15850": "Basic", "C53084481": "Extended", "C22775": "Basic", "C4211": "Basic",
             "C22869": "Extended", "C25803": "Basic", "C23068": "Extended", "C23000": "Extended", "C13564": "Extended",
             "C4190": "Basic", "C2286": "Basic", "C25804": "Basic", "C2913198": "Extended", "C45783": "Basic",
             "C15849": "Basic", "C318884": "Basic", "C23345": "Basic", "C51118": "Extended", "C19702": "Basic",
             "C8545": "Basic", "C21190": "Basic", "C133065": "Extended", "C160404": "Extended",
             "C2903462": "Extended", "C963748": "Extended", "C21004": "Extended",
             "C2845237": "Extended", "C97009": "Extended", "C227946": "Extended", "C23265": "Extended",
             "C168764": "Extended", "C20917": "Basic", "C177639": "Extended"}
HAND_SOLDER = {"J5", "J6", "J7", "J8"}  # JST PH and pin header: hand-soldered, not in the assembly BOM


def write_bom(path: Path) -> None:
    """bom.csv from PARTS: one row per (value, footprint, LCSC), designators sorted. Power symbols and flags excluded."""
    groups: dict[tuple, list[str]] = {}
    for ref, (sym, value, fp, lcsc, _sheet) in PARTS.items():
        if ref.startswith("#") or ref.startswith("TP"):
            continue
        groups.setdefault((value, fp or "", lcsc or ""), []).append(ref)
    cols = ["Comment", "Designator", "Footprint", "Quantity", "LCSC Part #", "Class", "Status", "Function / notes"]
    rows = []
    for (value, fp, lcsc), refs in groups.items():
        refs = sorted(refs, key=lambda r: (r[0], int("".join(ch for ch in r if ch.isdigit()) or 0)))
        if lcsc:
            cls, status = JLC_CLASS[lcsc], "VERIFIED LCSC part (class and stock 2026-10-31; datasheet values open)"
        else:
            cls = "n/a"
            status = "HAND-SOLDER" if all(r in HAND_SOLDER for r in refs) else "NOT ASSEMBLED"
        rows.append([value, ",".join(refs), fp, str(len(refs)), lcsc or "n/a", cls, status, ""])
    tp = [r for r, v in PARTS.items() if r.startswith("TP")]
    if tp:
        rows.append(["Test points", ",".join(sorted(tp)), TP, str(len(tp)), "n/a", "n/a", "PCB pads only", "GND/3V3 test pads"])
    lines = [",".join(cols)] + [",".join(f'"{c}"' if "," in c or " " in c else c for c in r) for r in rows]
    path.write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("hardware/weatherstation-v1")
    path = build(out)
    write_bom(out / "bom.csv")
    errors = check_nets(path, NETS)
    print("\n".join(errors) or f"{path}: nets OK; bom.csv written")
    sys.exit(1 if errors else 0)
