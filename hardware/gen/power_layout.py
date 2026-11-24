"""Hand-placed block layout of the power-board sheets (units: 2.54 mm cells). Format as layout_v1.py.

Three sheets since 2026-11-21 (review partition): Inputs (J10, the USB FET pair and the PV chain), Charger, Battery. The
charger and battery sheets keep the weatherstation-v1 drawing (layout_v1.py, reviewed 2026-11-01).
Every part sits inside exactly one block; boardgen asserts this. Part tuples are (x, y, rotation[, mirror]).
"""

from boards_common import HEADER_NOTE

# sheet -> list of blocks: (title, note, (x, y, w, h), {ref: (x, y, rot[, "m"])})
BLOCKS = {
    "Inputs": [
        ("USB VBUS input FETs", "USB_VBUS from header J10 (main-board USB-C). BQ25798 figure 8-2 port 1: ACFET1 M1 / RBFET1 M2 back-to-back, sources joined, gates on ACDRV1 through R11; VAC1 senses USB_VBUS (Charger sheet). C1 0.1u at the FET input",
         (4, 10, 74, 34), {
             "#FLG1": (37, 24, 0), "C1": (40, 25.5, 0), "M1": (50, 25, 90), "M2": (58, 25, 90, "m"), "R11": (54, 35, 0)}),
        ("PV input", "5 W 6 V class panel (Voc about 8 V cold, under 1 A): JST PH J5 (1 +, 2 -); SMBJ10A D1 across the pair (clamp 17 V < 30 V abs max); CM choke L3 3 A; figure 8-2 port 2: ACFET2 M3 / RBFET2 M4 into VBUS (ACDRV2)",
         (4, 50, 74, 40), {
             "J5": (10, 68, 0, "m"), "D1": (18, 69.5, 270), "L3": (28, 69, 0), "C2": (36, 71.5, 0),
             "M3": (54, 62, 90), "M4": (62, 62, 90, "m"), "R12": (58, 72, 0),
             "#FLG2": (44, 61, 0)}),
        ("Board-to-board header J10 (J_PWR)", "Keyed 2x10 2.54 mm socket, hand-soldered, hole 3 blocked (key). SYS out (pins 1, 2, >= 1 A), USB_VBUS in (19, 20), D+/D- in (BC1.2 detection), charger I2C/INT/CE to the main board. A GND pair between signal pairs. Pin map: hardware/ARCHITECTURE.md",
         (82, 10, 74, 48), {
             "J10": (96, 30, 0), "#FLG20": (89, 38, 0)}),
    ],
    "Charger": [
        ("BQ25798 charger", "Buck-boost charger, 1S (SLUSDV2C figure 8-1/8-2). Caps per table 5-1: VBUS 2x10u+0.1u, PMID 3x10u+0.1u, BTST 47n, REGN 4.7u. D+/D- from J10 for BC1.2 detection (7.3.4.5)",
         (4, 10, 94, 52), {
             "U3": (46, 34, 0), "L1": (63, 29, 90), "C3": (60, 25, 90), "C4": (60, 33, 90), "C5": (70, 46, 0),
             "C6": (10, 22, 0), "C7": (15, 22, 0), "C8": (20, 22, 0),
             "C9": (36, 56, 0), "C10": (42, 56, 0), "C11": (48, 56, 0), "C12": (54, 56, 0), "TP3": (30, 44, 0),
             "#FLG3": (88, 20, 180)}),
        ("SYS and battery side", "SYS: 5x10u + 0.1u; BAT: 2x10u (table 5-1). BATP: battery sense through 100 ohm. SDRV: 1 nF (no ship FET)",
         (100, 10, 56, 52), {
             "C13": (106, 22, 0), "C14": (111, 22, 0), "C15": (116, 22, 0), "C16": (121, 22, 0),
             "C17": (126, 22, 0), "C18": (131, 22, 0),
             "R13": (106, 42, 0), "C19": (114, 44, 0), "C20": (120, 44, 0), "C21": (130, 44, 0)}),
        ("Programming, thermal and status", "PROG 3.0k = 1S, 1.5 MHz (table 7-1). ILIM 120k/100k = 1.59 A (eq. 1). TS 5.1k/30k + NTC TH1 (Battery sheet). STAT LED from REGN. QON open (internal pull-up). R23 330k CE to BAT_PACK (charge off alone; CE = 0.75 x BAT with the main board R20 1M and +3V3 dead); INT/I2C pull-ups on the main board",
         (4, 66, 96, 28), {
             "R14": (12, 78, 0), "R15": (26, 78, 0), "R16": (26, 88, 0), "R17": (40, 78, 0), "R18": (40, 88, 0),
             "R19": (58, 76, 0), "D2": (58, 86, 90), "R23": (72, 80, 180)}),
    ],
    "Battery": [
        ("Cell, PTC, NTC and HY2112 protection", "J6 cell (JST PH), F1 PTC 3 A hold, TH1 NTC for BQ25798 TS. HY2112-CB: OVP 3.75 V, ODP 2.10 V; R60/C60/R61 per datasheet section 10; M60 (discharge) and M61 (charge) common-drain in the pack negative, as section 10",
         (4, 10, 90, 50), {
             "J6": (10, 30, 0, "m"), "F1": (18, 30, 90), "TH1": (26, 42, 0), "#FLG14": (24, 55, 0),
             "R60": (36, 19.5, 0), "C60": (50, 22.5, 0), "U6": (46, 30, 270, "m"), "R61": (52, 39, 90),
             "M60": (42, 48, 270), "M61": (60, 48, 270, "m"), "#FLG13": (43.5, 21, 0)}),
    ],
}

# Hand-drawn wires (cells, or (ref, pin)); the net counts as wired and other routes avoid it.
HAND_ROUTES = {
    # Charger power stage as in the BQ25798 typical application: BTST caps beside the pins, L1 between the two switch nodes
    "Charger": {
        "BTST1": [[("U3", "4"), ("C3", "1")]],
        "SW1": [[("U3", "28"), (61.5, 27)], [("C3", "2"), ("L1", "1")]],
        "SW2": [[("L1", "2"), (64.5, 31), ("U3", "26")], [("C4", "2"), (61.5, 31)]],
        "BTST2": [[("U3", "19"), ("C4", "1")]],
    },
    "Inputs": {
        # PV entry: connector -> TVS across the pair -> common-mode choke -> PV_IN (C2, ACFET2)
        "PV_RAW": [[("J5", "1"), ("D1", "1")], [("D1", "1"), ("L3", "1")]],
        "PV_N_RAW": [[("J5", "2"), (14, 69), (14, 71), ("D1", "2")], [("D1", "2"), (24, 71), (24, 70), ("L3", "4")]],
        "PV_IN": [[("L3", "2"), (36, 68), (36, 61), (44, 61)], [(44, 61), ("M3", "3")], [(36, 68), ("C2", "1")]],
        # USB_VBUS from the header: flag and C1 on the wire into the ACFET1 drain (one rail symbol at C1)
        "USB_VBUS": [[(37, 24), (40, 24)], [(40, 24), ("M1", "3")]],
    },
    # HY2112 section 10: R60/C60 supply filter above the IC, OD/OC down to the gates of M60/M61, CS through R61 to PB-
    "Battery": {
        "HY_VDD": [[("R60", "2"), (43.5, 21)], [(43.5, 21), (45.5, 21)], [(45.5, 21), ("U6", "5")], [(45.5, 21), ("C60", "1")]],
        "OD": [[("U6", "1"), (44.5, 36), (42, 36), ("M60", "1")]],
        "OC": [[("U6", "3"), (46.5, 36), (60, 36), ("M61", "1")]],
        "HY_CS": [[("U6", "2"), (45.5, 39), ("R61", "1")]],
        "PB_MID": [[("M60", "3"), ("M61", "3")]],
        "BAT_CON": [[("J6", "1"), ("F1", "1")]],
        # cell minus: J6 pin 2 to the M60 drain and around the FETs up to HY2112 VSS and C60 (section 10)
        "BAT_N": [[("J6", "2"), (14, 31), (14, 55)], [(14, 55), (24, 55)], [(24, 55), (36, 55)], [("M60", "2"), (36, 49), (36, 55)],
                  [(36, 55), (70, 55), (70, 24), ("C60", "2")], [("U6", "6"), (46.5, 24), ("C60", "2")]],
    },
}
HAND_LABELS: dict = {}
SHEET_DX = 2  # every block 2 cells right of the sheet border

# free text on a sheet (cells): the J10 pin table, so the header reads without opening ARCHITECTURE.md
SHEET_TEXTS = {"Inputs": [(84, 43, HEADER_NOTE)]}

TAGS_BELOW = {"C4"}
# hierarchical label shapes (signal direction seen from the sheet): J10 signals
LABEL_SHAPE = {"Inputs": {"CHG_CE": "output", "CHG_SCL": "output", "CHG_INT": "input", "USB_DP": "output", "USB_DN": "output"},
               "Charger": {"CHG_CE": "input", "CHG_SCL": "input", "CHG_INT": "output", "USB_DP": "input", "USB_DN": "input"}}

TAG_POS = {**{m: ((0, 5.4, "center"), (0, 7.2, "center")) for m in ("M60", "M61")},
           **{m: ((-3.6, 3.4, "right"), (-3.6, 5.2, "right")) for m in ("M1", "M3")},
           **{m: ((3.6, 3.4, "left"), (3.6, 5.2, "left")) for m in ("M2", "M4")},
           "J10": ((0, -15.8, "center"), (0, 15.8, "center")),
           **{j: ((0, 5.4, "center"), (0, -2.8, "center")) for j in ("J5", "J6")},
           "D1": ((0, -7.6, "center"), (0, -5.6, "center"))}

SHEET_NOTES = {
    "Inputs": "J10 to the main board, USB_VBUS and PV inputs into VBUS: back-to-back N-FET pairs (ACDRV1/2), PV surge TVS and choke",
    "Charger": "BQ25798RQMR: one charger for USB and PV. Power stage, SYS bulk, programming and status. Cell side on the Battery sheet",
    "Battery": "Cell connector, PTC, cell NTC, HY2112-CB overcharge/overdischarge/overcurrent protection and its pack-negative FETs",
}

ROOT_BOX = {
    "Inputs": (6, 18, 34, 40), "Charger": (56, 18, 40, 40), "Battery": (112, 18, 40, 26),
}

SHEET_COLOR = {
    "Inputs": ((30, 90, 170), (190, 215, 250)),
    "Charger": ((190, 90, 20), (255, 222, 180)),
    "Battery": ((150, 30, 60), (250, 200, 210)),
}

SHEET_PURPOSE = {
    "Inputs": "J10 (J_PWR, keyed 2x10 socket) to the main board: SYS out, USB_VBUS and D+/D- in, charger I2C, INT and CE. Solar panel J5 with surge TVS and EMI choke; two back-to-back FET pairs select the source into VBUS.",
    "Charger": "BQ25798 charger: turns VBUS (USB or solar) into battery charge current and SYS power. Programmed over I2C by the main board: 1S, 1.5 MHz, 3.65 V, ICHG per FIRMWARE-RULES.md. BC1.2 detection on D+/D-.",
    "Battery": "Cell connection and protection: fuse (PTC), cell NTC for the charger, HY2112-CB overcharge, overdischarge and overcurrent protection with its pack-negative FETs.",
}
