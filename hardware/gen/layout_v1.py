"""Hand-placed block layout for the weatherstation-v1 sheets (units: 2.54 mm cells).

Every part must sit inside exactly one block; weatherstation_v1.build() asserts this. A block is a dashed
frame with a title and a one-line function note. Parts flow left to right: connectors and inputs left,
the regulator or charger in the middle, outputs and connectors right. Decoupling and bias parts sit next to
the pins they serve. Part tuples are (x, y, rotation); Device:R, Device:C and Device:L are vertical at rot 0.
"""

# sheet -> list of blocks: (title, note, (x, y, w, h), {ref: (x, y, rot)})
BLOCKS = {
    "Input": [
        ("USB-C input", "USB-C sink: CC 5.1k pull-downs, ESD on D+/D-; ACFET1/RBFET1 back-to-back (sources joined, gates driven by BQ25798 ACDRV1) into VBUS",
         (4, 10, 74, 40), {
             "J1": (12, 30, 0), "U4": (34, 32, 0), "R9": (22, 42, 0), "R10": (26, 42, 0),
             "M1": (50, 24, 90), "M2": (58, 24, 90, "m"), "R11": (54, 34, 0), "C1": (68, 36, 0),
             "#FLG1": (72, 16, 0), "#FLG12": (14, 46, 0)}),
        ("PV input", "6 V / 10 W panel (Voc about 8 V cold, up to 1.7 A): JST PH J5; SMBJ10A D1 across the pair (clamp 17 V < 30 V abs max); CM choke L3 3 A; ACFET2/RBFET2 into VBUS (ACDRV2)",
         (4, 58, 74, 40), {
             "J5": (10, 76, 0, "m"), "D1": (18, 77.5, 270), "L3": (28, 77, 0), "C2": (36, 79.5, 0),
             "M3": (54, 70, 90), "M4": (62, 70, 90, "m"), "R12": (58, 80, 0),
             "#FLG2": (44, 69, 0)}),
    ],
    "Charger": [
        ("BQ25798 charger", "Buck-boost charger, 1S. Caps per datasheet table 5-1: VBUS 2x10u+0.1u, PMID 3x10u+0.1u, BTST 47n, REGN 4.7u",
         (4, 10, 94, 52), {
             "U3": (46, 34, 0), "L1": (63, 29, 90), "C3": (60, 25, 90), "C4": (60, 33, 90), "C5": (70, 46, 0),
             "C6": (10, 22, 0), "C7": (15, 22, 0), "C8": (20, 22, 0),
             "C9": (36, 56, 0), "C10": (42, 56, 0), "C11": (48, 56, 0), "C12": (54, 56, 0),
             "#FLG3": (88, 14, 0)}),
        ("SYS and battery side", "SYS: 5x10u + 0.1u; BAT: 2x10u (table 5-1). BATP: battery sense through 100 ohm. SDRV: 1 nF (no ship FET)",
         (100, 10, 56, 52), {
             "C13": (106, 22, 0), "C14": (111, 22, 0), "C15": (116, 22, 0), "C16": (121, 22, 0),
             "C17": (126, 22, 0), "C18": (131, 22, 0),
             "R13": (106, 42, 0), "C19": (114, 44, 0), "C20": (120, 44, 0), "C21": (130, 44, 0)}),
        ("Programming, thermal and status", "PROG 3.0k = 1S, 1.5 MHz (table 7-1). ILIM 120k/100k = 1.59 A. TS 5.1k/30k + NTC (Battery sheet). CE pulled to +3V3 = charge off until firmware writes VREG. STAT LED and INT; QON open (internal pull-up). Charger I2C (IO4/IO5) pull-ups R54/R55 to +3V3",
         (4, 66, 140, 28), {
             "R14": (12, 78, 0), "R15": (26, 78, 0), "R16": (26, 88, 0), "R17": (40, 78, 0), "R18": (40, 88, 0),
             "R19": (58, 76, 0), "D2": (58, 86, 90), "R20": (74, 78, 0), "R22": (102, 78, 180),
             "R54": (122, 78, 180), "R55": (128, 78, 180)}),
    ],
    "Battery": [
        ("Cell, PTC, NTC and HY2112 protection", "J6 cell (JST PH), F1 PTC 3 A hold, TH1 NTC for BQ25798 TS. HY2112-CB: OVP 3.75 V, ODP 2.10 V; R60/C60/R61 per datasheet section 10; M60 (discharge) and M61 (charge) common-drain in the pack negative, as section 10",
         (4, 10, 90, 50), {
             "J6": (10, 30, 0, "m"), "F1": (18, 30, 90), "TH1": (26, 42, 0), "#FLG14": (16, 36, 0),
             "R60": (36, 19.5, 0), "C60": (50, 22.5, 0), "U6": (46, 30, 270, "m"), "R61": (52, 39, 90),
             "M60": (42, 48, 270), "M61": (60, 48, 270, "m"), "#FLG13": (43.5, 21, 0)}),
    ],
    "MCU": [
        ("ESP32-S3-WROOM-1-N8", "N8: 8 MB flash, no PSRAM. Strapping: IO0 (BOOT), EN (RESET). Native USB on IO19/IO20 with 22 ohm series resistors",
         (4, 10, 76, 58), {
             "U1": (40, 36, 0), "C30": (10, 22, 0), "C31": (15, 22, 0), "C32": (20, 22, 0),
             "R33": (62, 29, 270), "R32": (62, 35, 270)}),
        ("Reset and boot", "EN: RC delay 10k / 1 uF and RESET switch. IO0: 10k pull-up and BOOT switch (hold BOOT, press RESET = download mode)",
         (86, 10, 40, 30), {
             "R30": (92, 22, 0), "C33": (98, 32, 0), "SW10": (104, 32, 270), "R31": (112, 22, 0), "SW11": (118, 32, 270)}),
        ("Debug UART", "UART0 header J7: 1 +3V3, 2 TXD0 (IO43), 3 RXD0 (IO44), 4 GND",
         (86, 46, 40, 30), {
             "J7": (110, 60, 0)}),
    ],
    "Rails": [
        ("3.3 V buck-boost", "TPS63802DLA from SYS (VIN = EN = SYS, MODE = GND: power save). FB 220k / 39k: 0.5 V x (1 + 220/39) = 3.32 V. L4 0.47 uH; 10 uF in, 22 uF out",
         (4, 10, 90, 40), {
             "U2": (30, 26, 0), "L4": (42, 25, 0), "C40": (14, 26, 0), "R52": (50, 30, 0), "R53": (50, 38, 0), "C41": (58, 26, 0),
             "TP1": (72, 30, 0), "TP2": (78, 30, 0), "#FLG10": (86, 16, 0)}),
        ("3V3_SW sensor rail", "Q40 P-FET switches +3V3 to the sensors. R40 holds it off; Q41 pulls the gate low when SENSOR_EN (IO11) is high; R42 keeps Q41 off during reset",
         (4, 56, 62, 36), {
             "Q40": (30, 71, 0), "R40": (22, 66, 0), "Q41": (21, 81, 0), "R41": (12, 81, 90), "R42": (16, 88, 0),
             "C42": (44, 68, 0), "C43": (49, 68, 0)}),
        ("GAS_VCC 5 V boost", "TPS61023: SYS -> 5.06 V for the ZE25-O3. EN = GAS_EN (IO12); R45 = off by default; off = output disconnected, 0.1 uA. FB 0.595 V x (1 + 510k/68k)",
         (72, 56, 56, 36), {
             "C44": (76, 76, 0), "L5": (92, 66, 90), "U7": (92, 74, 0), "R45": (82, 84, 0),
             "R43": (108, 76, 0), "R44": (108, 85, 0), "C45": (116, 77, 0), "C46": (121, 77, 0)}),
    ],
    "Sensors": [
        ("Sensor connectors", "J2 SEN66 (GH 6-pin: 1 VDD, 2 GND, 3 SDA, 4 SCL, 5/6 NC). J3 SHT45 outdoor cable and J4 spare (Qwiic order: GND, VDD, SDA, SCL). All on 3V3_SW",
         (4, 10, 70, 46), {
             "J2": (40, 24, 0), "J3": (40, 36, 0), "J4": (40, 46, 0)}),
        ("I2C pull-ups and cable ESD", "Sensor I2C bus (IO13/IO14): pull-ups 10k to 3V3_SW; USBLC6 (U5, VBUS on 3V3_SW) on the outdoor cable lines. Charger bus is separate (Charger sheet)",
         (4, 60, 62, 30), {
             "R50": (12, 72, 180), "R51": (17, 72, 180), "U5": (38, 72, 0)}),
        ("ZE25-O3 gas connector", "J8 (hand-solder): 1 GAS_VCC, 2 GND, 3 TXD (sensor out), 4 RXD (sensor in). Pinout to confirm against the module",
         (72, 60, 36, 30), {
             "J8": (90, 74, 0)}),
    ],
}

# Hand-drawn wires for nets an engineer draws a fixed way (the router would loop them). sheet -> net -> polylines;
# a point is a (ref, pin) or (x, y) in cells. The net counts as wired; other routes avoid these wires.
# Charger power stage as in the BQ25798 typical application: BTST caps beside the pins, L1 between the two switch nodes.
HAND_ROUTES = {
    "Charger": {
        "BTST1": [[("U3", "4"), ("C3", "1")]],
        "SW1": [[("U3", "28"), (61.5, 27)], [("C3", "2"), ("L1", "1")]],
        "SW2": [[("L1", "2"), (64.5, 31), ("U3", "26")], [("C4", "2"), (61.5, 31)]],
        "BTST2": [[("U3", "19"), ("C4", "1")]],
    },
    # PV entry: connector -> TVS across the pair -> common-mode choke -> PV_IN (C2, ACFET2)
    "Input": {
        "PV_RAW": [[("J5", "1"), ("D1", "1")], [("D1", "1"), ("L3", "1")]],
        "PV_N_RAW": [[("J5", "2"), (14, 77), (14, 79), ("D1", "2")], [("D1", "2"), (24, 79), (24, 78), ("L3", "4")]],
        "PV_IN": [[("L3", "2"), (36, 76), (36, 69), (44, 69)], [(44, 69), ("M3", "3")], [(36, 76), ("C2", "1")]],
    },
    # HY2112 section 10: R60/C60 supply filter above the IC, OD/OC down to the gates of M60/M61, CS through R61 to PB-
    "Battery": {
        "HY_VDD": [[("R60", "2"), (43.5, 21)], [(43.5, 21), (45.5, 21)], [(45.5, 21), ("U6", "5")], [(45.5, 21), ("C60", "1")]],
        "OD": [[("U6", "1"), (44.5, 36), (42, 36), ("M60", "1")]],
        "OC": [[("U6", "3"), (46.5, 36), (60, 36), ("M61", "1")]],
        "HY_CS": [[("U6", "2"), (45.5, 39), ("R61", "1")]],
        "PB_MID": [[("M60", "3"), ("M61", "3")]],
        "BAT_CON": [[("J6", "1"), ("F1", "1")]],
    },
    # sensor I2C bus: one vertical line per signal left of the connectors (SDA x 26, SCL x 24; SCL crosses SDA, no dot)
    "Sensors": {
        "SEN_SDA": [[("J2", "3"), (26, 24), (26, 37)], [(26, 37), (26, 47)], [(26, 47), ("J4", "3")], [("J3", "3"), (26, 37)],
                    [(26, 47), (26, 51)]],
        "SEN_SCL": [[("J2", "4"), (24, 25), (24, 38)], [(24, 38), (24, 48)], [(24, 48), ("J4", "4")], [("J3", "4"), (24, 38)],
                    [(24, 48), (24, 51)]],
    },
}
# name label of a hand-drawn net at a fixed wire end (x, y cells, text angle): sheet -> net
HAND_LABELS = {"Sensors": {"SEN_SDA": (26, 51, 270), "SEN_SCL": (24, 51, 270)}}

# reference/value text below a horizontal passive (default: above), where a wire runs just above it
TAGS_BELOW = {"C4"}
# reference and value of the FET pairs: stacked below the body on the outer side, clear of the gate wire (dx, dy mm, justify)
TAG_POS = {**{m: ((0, 5.4, "center"), (0, 7.2, "center")) for m in ("M60", "M61")},**{m: ((-3.6, 3.4, "right"), (-3.6, 5.2, "right")) for m in ("M1", "M3")},
           **{m: ((3.6, 3.4, "left"), (3.6, 5.2, "left")) for m in ("M2", "M4")}}  # mirrored: text right of the gate

SHEET_NOTES = {
    "Input": "USB-C and PV inputs into VBUS: ESD, CC pulldowns, back-to-back N-FET pairs (ACDRV1/2), PV surge TVS and common-mode choke",
    "Charger": "BQ25798RQMR: one charger for USB and PV. Power stage, SYS bulk, programming and status. Cell side on the Battery sheet",
    "Battery": "Cell connector, PTC, cell NTC, HY2112-CB overcharge/overdischarge/overcurrent protection and its pack-negative FETs",
    "MCU": "ESP32-S3-WROOM-1-N8: decoupling, reset and boot, USB data series resistors, UART debug",
    "Rails": "SYS to 3.3 V (TPS63802), switched 3V3_SW sensor rail and the GAS_VCC 5 V boost (TPS61023, enable from IO12)",
    "Sensors": "SEN66 and SHT45 connectors, spare port, I2C ESD and pull-ups, ZE25-O3 gas connector",
}

# root block diagram boxes (cells): sheet -> (x, y, w, h)
ROOT_BOX = {
    "Input": (6, 18, 34, 30), "Charger": (52, 18, 40, 32), "MCU": (106, 18, 50, 32),
    "Battery": (6, 60, 34, 24), "Rails": (52, 62, 40, 24), "Sensors": (106, 62, 50, 24),
}

# colour per sheet: (outline, tint). Power = warm, digital = cool, sensing = green.
SHEET_COLOR = {
    "Input": ((30, 90, 170), (190, 215, 250)),
    "Charger": ((190, 90, 20), (255, 222, 180)),
    "Battery": ((150, 30, 60), (250, 200, 210)),
    "MCU": ((100, 50, 160), (225, 210, 248)),
    "Rails": ((40, 120, 60), (205, 238, 205)),
    "Sensors": ((20, 120, 120), (195, 238, 238)),
}

# what each sheet does, in one or two sentences (shown on the sheet and in the root block diagram)
SHEET_PURPOSE = {
    "Input": "Brings in power from USB-C and from the solar panel. ESD and CC pulldowns on USB, surge TVS and EMI choke on PV, two back-to-back FET pairs select the source into VBUS.",
    "Charger": "BQ25798 charger: turns VBUS (USB or solar) into battery charge current and SYS power. Programmed over I2C by the firmware: 1S, 1.5 MHz, 3.65 V, 1.5 A.",
    "Battery": "Cell connection and protection: fuse (PTC), cell temperature sensor for the charger, HY2112-CB overcharge, overdischarge and overcurrent protection with its pack-negative FETs.",
    "MCU": "ESP32-S3 module: runs the firmware, USB data, reset and boot, debug UART. Controls the charger over I2C and switches the sensor rails.",
    "Rails": "SYS to 3.3 V buck-boost (TPS63802). Switched 3V3_SW for the SEN66 and SHT45; TPS61023 5 V boost (GAS_VCC) for the gas sensor, enabled by the ESP32. Sensors are off between measurements.",
    "Sensors": "Connectors for the SEN66 (PM, CO2, T/RH, NOx), the outdoor SHT45 and the ZE25-O3 gas sensor; I2C pull-ups and ESD protection.",
}
