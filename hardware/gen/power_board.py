"""power-board schematic: BQ25798 charger for USB VBUS (from the main board over J10) and a PV panel, the 1S cell with
PTC, NTC and HY2112-CB protection, and the board-to-board header J10 (J_PWR). Split from weatherstation-v1 (2026-11-21).

Phase A rule: every part keeps its weatherstation-v1 reference, value, footprint and LCSC number, and its nets are the
same as in hardware/gen/weatherstation_v1.py. Nets that leave this board go through J10 under the same name on both
boards (pin map: boards_common.HEADER_PINS, table and reasons: hardware/ARCHITECTURE.md). hardware/tools/split_check.py
proves both. Moved to the main board (they need +3V3): CE pull-up R20, INT pull-up R22, charger I2C pull-ups R54/R55.
USB-C itself (J1, U4 ESD, CC resistors) is on the main board.

PARTS and NETS are the source of truth; check_nets() compares them with KiCad's netlist. Drawing engine: boardgen.py.
Values marked "candidate" are still open (hardware/power-board/PARTS-REVIEW.md).
Run: source scripts/kicad-env.sh && uv run --package weatherstation-hardware python hardware/gen/power_board.py [out_dir]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import boardgen  # noqa: E402  (registers the project symbol library)
from boards_common import C0402, C0603, C0805, JST_PH2, R0402, R0603, SOT23, TP, add_header, header_part  # noqa: E402
from power_layout import (BLOCKS, HAND_LABELS, HAND_ROUTES, ROOT_BOX, SHEET_COLOR, SHEET_DX, SHEET_NOTES,  # noqa: E402,F401
                          SHEET_PURPOSE, SHEET_TEXTS, TAG_POS, TAGS_BELOW)

DATE = "2026-11-21"  # title block: date of the last schematic change
PROJECT, TITLE, SHEET_PREFIX = "power-board", "weatherstation power board", "power board"
SHEET_FILES = {"Inputs": "inputs.kicad_sch", "Charger": "charger.kicad_sch", "Battery": "battery.kicad_sch",
               "Header": "header.kicad_sch"}

# ref: (symbol, value, footprint, LCSC or None, sheet)
PARTS = {
    # --- Inputs: USB VBUS (from J10) and PV into the charger's two input FET pairs ------------------------------------
    "M1": ("Transistor_FET:AO3400A", "AO3400A ACFET1 (N-channel, BQ25798 back-to-back)", SOT23, "C20917", "Inputs"),
    "M2": ("Transistor_FET:AO3400A", "AO3400A RBFET1 (N-channel, BQ25798 back-to-back)", SOT23, "C20917", "Inputs"),
    "M3": ("Transistor_FET:AO3400A", "AO3400A ACFET2 (N-channel, BQ25798 back-to-back)", SOT23, "C20917", "Inputs"),
    "M4": ("Transistor_FET:AO3400A", "AO3400A RBFET2 (N-channel, BQ25798 back-to-back)", SOT23, "C20917", "Inputs"),
    "R11": ("Device:R", "300 (candidate; figure 294)", R0603, "C23025", "Inputs"),
    "R12": ("Device:R", "300 (candidate; figure 294)", R0603, "C23025", "Inputs"),
    "C1": ("Device:C", "0.1u", C0402, "C307331", "Inputs"),
    "C2": ("Device:C", "0.1u", C0402, "C307331", "Inputs"),
    # 6 V class PV panel (Voc about 8 V cold): SMBJ10A standoff 10 V, clamp 17 V, below the 30 V abs max of VAC2/AO3400A
    # (v1 PARTS-REVIEW A6, decided 2026-11-01). Littelfuse part.
    # unidirectional TVS (review A6): Zener-shape symbol, pin 1 = K on PV_RAW, pin 2 = A on PV_N_RAW
    "D1": ("Device:D_Zener", "SMBJ10A (PV surge, standoff 10 V, clamp 17 V)", "Diode_SMD:D_SMB", "C151250", "Inputs"),
    # 2-line common-mode choke on the PV pair: winding A = 1 -> 2, winding B = 4 -> 3 (EMTEK T-0602-102D equivalent circuit;
    # LCSC maker HongyeX). 3 A, 70 mohm DCR, 90 ohm at 100 MHz. Footprint weatherstation:CMF4532F_4P (fixed 2026-11-05).
    "L3": ("weatherstation:CMC_2line", "CM choke 90 ohm 3 A (CMF4532F-900-2P-T; datasheet page to confirm)", "weatherstation:CMF4532F_4P", "C963746", "Inputs"),
    "J5": ("Connector_Generic:Conn_01x02", "PV IN (1 +, 2 -)", JST_PH2, None, "Inputs"),
    "#FLG1": ("power:PWR_FLAG", "PWR_FLAG", None, None, "Inputs"),
    "#FLG2": ("power:PWR_FLAG", "PWR_FLAG", None, None, "Inputs"),
    # --- Charger ------------------------------------------------------------------------------------------------------
    "U3": ("Battery_Management:BQ25798", "BQ25798RQMR", "Package_DFN_QFN:Texas_RQM0029A_VQFN-29_4x4mm_P0.4mm", "C2876593", "Charger"),
    "L1": ("Device:L", "1uH (TDK VLS252010HBX-1R0M-1: Isat 3.22 A, Itemp 2.55 A, 65 mohm max)", "weatherstation:L_TDK_VLS252010", "C88211", "Charger"),
    "C3": ("Device:C", "47n", C0603, "C1622", "Charger"),
    "C4": ("Device:C", "47n", C0603, "C1622", "Charger"),
    # REGN 4.7 uF (table 5-1) in 0805 25 V (review C): a 0603 10 V part keeps only about 2.5 uF at 5 V
    "C5": ("Device:C", "4.7u 25V", C0805, "C1779", "Charger"),
    "TP3": ("Connector:TestPoint", "QON", TP, None, "Charger"),
    "C6": ("Device:C", "0.1u", C0402, "C307331", "Charger"),
    "C7": ("Device:C", "10u", C0805, "C15850", "Charger"),
    "C8": ("Device:C", "10u", C0805, "C15850", "Charger"),
    "C9": ("Device:C", "0.1u", C0402, "C307331", "Charger"),  # 0402 on the pin row (SLUSDV2C 8.4.1 item 1), 50 V
    "C10": ("Device:C", "10u", C0805, "C15850", "Charger"),
    "C11": ("Device:C", "10u", C0805, "C15850", "Charger"),
    "C12": ("Device:C", "10u", C0805, "C15850", "Charger"),
    "C13": ("Device:C", "0.1u", C0402, "C307331", "Charger"),
    "C14": ("Device:C", "10u", C0805, "C15850", "Charger"),
    "C15": ("Device:C", "10u", C0805, "C15850", "Charger"),
    "C16": ("Device:C", "10u", C0805, "C15850", "Charger"),
    "C17": ("Device:C", "10u", C0805, "C15850", "Charger"),
    "C18": ("Device:C", "10u", C0805, "C15850", "Charger"),
    "C19": ("Device:C", "10u", C0805, "C15850", "Charger"),
    "C20": ("Device:C", "10u", C0805, "C15850", "Charger"),
    "C21": ("Device:C", "1n", C0402, "C1523", "Charger"),
    "R13": ("Device:R", "100", R0402, "C25076", "Charger"),
    "R14": ("Device:R", "3.0k (PROG: 1S, 1.5 MHz)", R0603, "C4211", "Charger"),
    "R15": ("Device:R", "120k (ILIM: REGN 5 V x 100/220 = 2.27 V -> 1.59 A clamp)", R0603, "C25808", "Charger"),
    "R16": ("Device:R", "100k", R0402, "C25741", "Charger"),
    "R17": ("Device:R", "5.1k (TS top; thresholds about +0.9 C vs 5.24k/30.31k)", R0402, "C25905", "Charger"),
    "R18": ("Device:R", "30k (TS bottom)", R0603, "C22984", "Charger"),
    "R19": ("Device:R", "2.2k", R0402, "C25879", "Charger"),
    "D2": ("Device:LED", "STAT red", "LED_SMD:LED_0603_1608Metric", "C2286", "Charger"),
    "#FLG3": ("power:PWR_FLAG", "PWR_FLAG", None, None, "Charger"),
    # CE pull-up on this board (review A1, 2026-11-21): 1M to BAT_PACK keeps CE high (charge off) when the main board is
    # absent. BQ25798 SLUSDV2C 6.5: VIH_CE 1.3 V, leakage 1 uA max; 6.1: CE abs max 6 V (BAT_PACK <= 3.75 V for LFP).
    # With the main board R20 1M to +3V3 in parallel; the ESP32 GPIO overrides both.
    "R23": ("Device:R", "1M (CE pull-up to BAT_PACK)", R0402, "C26083", "Charger"),
    # --- Battery ------------------------------------------------------------------------------------------------------
    # Cell overcurrent backup: PTC hold 3 A, trip 5 A, 8 V. Backup to the HY2112 overcurrent cut.
    "F1": ("Device:Fuse", "PTC 3 A hold (SMD1812P300TF)", "Fuse:Fuse_1812_4532Metric", "C21004", "Battery"),
    # Cell connector (hand-soldered): 1 BAT+, 2 BAT-. TH1 on the board next to J6; bottom on GND like R18 (figure 8-1).
    "J6": ("Connector_Generic:Conn_01x02", "CELL (1 +, 2 -)", JST_PH2, None, "Battery"),
    "TH1": ("Device:Thermistor_NTC", "10k NTC NCP18XH103F03RB (TS, next to J6)", R0603, "C13564", "Battery"),
    "#FLG13": ("power:PWR_FLAG", "PWR_FLAG", None, None, "Battery"),
    "#FLG14": ("power:PWR_FLAG", "PWR_FLAG", None, None, "Battery"),
    # HY2112-CB (LiFePO4 1-cell protection, OVP 3.75 V / release 3.60 V, ODP 2.10 V / release 2.30 V, discharge OC 200 mV,
    # charge OC -200 mV). Pack negative = two common-drain N-FETs: M60 (OD, discharge, source on cell -), M61 (OC, charge,
    # source on PB- = system GND). HY2112 datasheet section 10: VDD via R60 100 ohm + C60 0.1 uF, CS via R61 2 kohm to PB-.
    "U6": ("weatherstation:HY2112-CB", "HY2112-CB LiFePO4 protection", "Package_TO_SOT_SMD:SOT-23-6", "C168764", "Battery"),
    "M60": ("Transistor_FET:AO3400A", "AO3400A discharge FET (OD)", SOT23, "C20917", "Battery"),
    "M61": ("Transistor_FET:AO3400A", "AO3400A charge FET (OC)", SOT23, "C20917", "Battery"),
    "R60": ("Device:R", "100 (HY2112 VDD)", R0402, "C25076", "Battery"),
    "C60": ("Device:C", "0.1u (HY2112 VDD)", C0402, "C307331", "Battery"),
    "R61": ("Device:R", "2k (HY2112 CS)", R0402, "C4109", "Battery"),
    # --- Header -------------------------------------------------------------------------------------------------------
    "J10": header_part("Header", "power"),
    "#FLG20": ("power:PWR_FLAG", "PWR_FLAG", None, None, "Header"),  # GND: on this board only passive pins drive it
}

# Parts that are not in weatherstation-v1 (tools/split_check.py)
ADDED = {"R23": "2026-11-21 review A1: CE pull-up 1M to BAT_PACK on the power board",
         "TP3": "2026-11-21 review C: QON test pad (ship-mode exit / system reset at bring-up)"}
CHANGED = {
    "D1": "2026-11-21 review A6: unidirectional symbol (D_Zener) for the SMBJ10A, same pins",
    "J5": "2026-11-21 review B19: polarity in the value", "J6": "2026-11-21 review B20: polarity in the value",
    "C5": "2026-11-21 review C: REGN cap 0603 10 V -> 0805 25 V (C1779 Basic)",
}

NETS = add_header({
    # Inputs: USB VBUS (from J10) -> ACFET1/RBFET1 -> VBUS; PV J5 -> TVS -> CM choke -> ACFET2/RBFET2 -> VBUS
    "USB_VBUS": [("M1", "3"), ("C1", "1"), ("U3", "9"), ("#FLG1", "1")],
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
    # BC1.2 detection on the USB data lines (carried over J10 from the main board's USB-C, ARCHITECTURE.md decision)
    "USB_DP": [("U3", "6")],
    "USB_DN": [("U3", "7")],
    # Charger
    "REGN": [("U3", "5"), ("C5", "1"), ("R15", "1"), ("R17", "1"), ("R19", "1")],
    "BTST1": [("U3", "4"), ("C3", "1")],
    "SW1": [("U3", "28"), ("C3", "2"), ("L1", "1")],
    "BTST2": [("U3", "19"), ("C4", "1")],
    "SW2": [("U3", "26"), ("C4", "2"), ("L1", "2")],
    "PMID": [("U3", "29"), ("C9", "1"), ("C10", "1"), ("C11", "1"), ("C12", "1")],
    "SYS": [("U3", "25"), ("C13", "1"), ("C14", "1"), ("C15", "1"), ("C16", "1"), ("C17", "1"), ("C18", "1")],
    "BATP": [("U3", "18"), ("R13", "2")],
    "SDRV": [("U3", "24"), ("C21", "1")],
    "PROG": [("U3", "20"), ("R14", "1")],
    "ILIM": [("U3", "17"), ("R15", "2"), ("R16", "1")],
    "TS": [("U3", "16"), ("R17", "2"), ("R18", "1"), ("TH1", "1")],
    "STAT": [("U3", "1"), ("D2", "1")],
    "LED_A": [("R19", "2"), ("D2", "2")],
    # QON (pin 12) left open: internal pull-up (v1 PARTS-REVIEW C, R21 removed 2026-11-01); no-connect marker.
    # Host pins: pull-ups R20 (CE), R22 (INT), R54/R55 (I2C) to +3V3 are on the main board (no 3.3 V here).
    "CHG_CE": [("U3", "13"), ("R23", "1")],
    "QON": [("U3", "12"), ("TP3", "1")],
    "CHG_INT": [("U3", "21")],
    "CHG_SDA": [("U3", "15")],
    "CHG_SCL": [("U3", "14")],
    # Battery: BAT caps C19/C20 on BAT (table 5-1); BATP only senses through R13 100 ohm
    "BAT_CON": [("J6", "1"), ("F1", "1")],
    "BAT_PACK": [("U3", "22"), ("U3", "23"), ("R13", "1"), ("R23", "2"), ("F1", "2"), ("R60", "1"), ("C19", "1"), ("C20", "1")],
    "BAT_N": [("J6", "2"), ("U6", "6"), ("C60", "2"), ("M60", "2"), ("#FLG14", "1")],
    "HY_VDD": [("R60", "2"), ("C60", "1"), ("U6", "5"), ("#FLG13", "1")],
    "OD": [("U6", "1"), ("M60", "1")],
    "OC": [("U6", "3"), ("M61", "1")],
    "PB_MID": [("M60", "3"), ("M61", "3")],  # common drain (HY2112 section 10)
    "HY_CS": [("U6", "2"), ("R61", "1")],
    "GND": [("C1", "2"), ("C2", "2"), ("L3", "3"), ("M61", "2"), ("R61", "2"), ("U3", "27"), ("TH1", "2"), ("C5", "2"),
            ("C6", "2"), ("C7", "2"), ("C8", "2"), ("C9", "2"), ("C10", "2"), ("C11", "2"), ("C12", "2"), ("C13", "2"),
            ("C14", "2"), ("C15", "2"), ("C16", "2"), ("C17", "2"), ("C18", "2"), ("C19", "2"), ("C20", "2"), ("C21", "2"),
            ("R14", "2"), ("R16", "2"), ("R18", "2"), ("#FLG20", "1")],
})
# Rails: a power symbol on every pin (never a wire across the sheet, no hierarchical label).
POWER_SYMBOLS = ("GND", "SYS", "VBUS", "USB_VBUS", "PMID", "REGN", "BAT_PACK")
RAIL_LIB = {"GND": "power:GND", "VBUS": "power:VBUS"}  # others: power:VCC with the net as value

SHEET_VALUE = {"J5": "PV IN 1+ 2-", "J6": "CELL 1+ 2-", "L3": "CMC 90R 3A", "F1": "PTC 3A", "TH1": "10k NTC", "U6": "HY2112-CB", "J10": "J_PWR 2x10 key 3",
               **{m: "AO3400A" for m in ("M1", "M2", "M3", "M4", "M60", "M61")}}
HAND_SOLDER = {"J5", "J6", "J10"}  # JST PH and the 2.54 mm header: hand-soldered, not in the assembly BOM
ROOT_TEXTS = [
    (6, 6, "#weatherstation power board: block diagram"),
    (6, 10, "Each box is a sheet. Wires join the sheet pins (hierarchical labels). Rails (GND, SYS, VBUS, USB_VBUS, PMID, REGN, BAT_PACK) are power symbols."),
    (6, 92, "Power path: USB_VBUS (J10, from the main board's USB-C) or PV (J5) -> Inputs (ACFET/RBFET pairs) -> VBUS -> Charger (BQ25798) -> SYS -> J10 -> main board."),
    (6, 94, "Cell: Battery (J6, PTC F1, HY2112-CB with M60/M61) <-> BAT_PACK <-> Charger. The board makes no 3.3 V: CE/INT/I2C pull-ups are on the main board."),
    (6, 96, "Header J10 (J_PWR) pin map and the D+/D- decision: hardware/ARCHITECTURE.md. Open decisions: hardware/power-board/PARTS-REVIEW.md."),
]

if __name__ == "__main__":
    sys.exit(boardgen.main(sys.modules[__name__], Path(__file__).resolve().parents[1] / "power-board"))
