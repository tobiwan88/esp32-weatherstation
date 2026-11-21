"""Hand-placed block layout of the main-board sheets (units: 2.54 mm cells). Format as layout_v1.py.

MCU, Rails and Sensors keep the weatherstation-v1 drawing (layout_v1.py, reviewed 2026-11-01). USB keeps the USB-C part
of the old Input sheet (the ACFET pair moved to the power board). Header is new: J10 and the charger host pull-ups.
Every part sits inside exactly one block; boardgen asserts this. Part tuples are (x, y, rotation[, mirror]).
"""

from boards_common import HEADER_NOTE

# sheet -> list of blocks: (title, note, (x, y, w, h), {ref: (x, y, rot[, "m"])})
BLOCKS = {
    "USB": [
        ("USB-C receptacle", "USB-C sink (programming, USB-JTAG debug, charging): CC1/CC2 5.1k pull-downs (Rd); USBLC6 ESD on D+/D- with VBUS reference. USB_VBUS and D+/D- continue to J10 (power board)",
         (4, 10, 60, 40), {
             "J1": (12, 30, 0), "U4": (34, 35, 0), "R9": (26, 42, 0), "R10": (22, 42, 0), "#FLG12": (16, 40, 0), "#FLG22": (44, 24, 0)}),
    ],
    "Header": [
        ("Board-to-board header J10 (J_PWR) and charger host pull-ups", "J10 mating side (pin map: hardware/ARCHITECTURE.md). +3V3 lives here: CE pull-up R20 100k (charge off until firmware writes VREG), INT R22 10k, charger I2C R54/R55 10k (BQ25798 table 5-1)",
         (4, 10, 70, 46), {
             "J10": (30, 30, 0), "R54": (16, 26, 180), "R22": (10, 26, 180), "R55": (46, 26, 180), "R20": (52, 26, 0),
             "#FLG21": (64, 40, 0)}),
    ],
    "MCU": [
        ("ESP32-S3-WROOM-1-N8", "N8: 8 MB flash, no PSRAM. Strapping: IO0 (BOOT), EN (RESET). Native USB on IO19/IO20 with 22 ohm series resistors",
         (4, 10, 76, 58), {
             "U1": (40, 36, 0), "C30": (10, 22, 0), "C31": (15, 22, 0), "C32": (20, 22, 0),
             "R33": (62, 29, 270), "R32": (62, 35, 270)}),
        ("Reset and boot", "EN: RC delay 10k / 1 uF, RESET tweezer pads JP1. IO0: 10k pull-up, BOOT pads JP2 (short BOOT, then RESET = download mode)",
         (86, 10, 40, 30), {
             "R30": (92, 22, 0), "C33": (98, 32, 0), "JP1": (104, 32, 270), "R31": (112, 22, 0), "JP2": (118, 32, 270)}),
        ("Debug UART", "UART0 header J7: 1 +3V3, 2 TXD0 (IO43), 3 RXD0 (IO44), 4 GND",
         (86, 46, 40, 30), {
             "J7": (110, 60, 0)}),
        ("Status LEDs", "Active high: IO41 -> 1k -> LED1, IO42 -> 1k -> LED2 (red 0603, about 1.3 mA)",
         (4, 74, 50, 28), {
             "R34": (16, 82, 0), "D10": (16, 92, 90), "R35": (36, 82, 0), "D11": (36, 92, 90)}),
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
        ("5V_SW 5 V boost", "TPS61023: SYS -> 5.06 V for the PMS7003 and the ZE25-O3. EN = BOOST_EN (IO12); R45 = off by default; off = output disconnected, 0.1 uA. FB 0.595 V x (1 + 510k/68k)",
         (72, 56, 56, 36), {
             "C44": (76, 76, 0), "L5": (92, 66, 90), "U7": (92, 74, 0), "R45": (82, 84, 0),
             "R43": (108, 76, 0), "R44": (108, 85, 0), "C45": (116, 77, 0), "C46": (121, 77, 0)}),
    ],
    "Sensors": [
        ("I2C sensor connector", "J3 SHT45 board in the radiation shield (outdoor cable, Qwiic order: GND, VDD, SDA, SCL), on 3V3_SW",
         (4, 10, 70, 46), {
             "J3": (40, 36, 0)}),
        ("PM sensor PMS7003", "J2 (hand-solder, 2x5 1.27 mm, manual V2.5): 1/2 5V_SW, 3/4 GND, 7 RX <- IO4 via R48, 9 TX -> IO5, 10 SET <- IO6 via R49 (low = sleep); 5 RESET, 6, 8 open. Data 3.3 V TTL",
         (78, 10, 80, 46), {
             "J2": (120, 30, 0), "R48": (100, 31, 90), "R49": (100, 35, 90)}),
        ("CO2 SCD41 (DNP)", "Footprint only; VDD = VDDH at the sensor, 3V3_SW",
         (126, 60, 32, 30), {
             "U8": (146, 76, 0), "C47": (134, 76, 0)}),
        ("I2C pull-ups and cable ESD", "Sensor I2C bus (IO13/IO14): pull-ups 10k to 3V3_SW; USBLC6 (U5, VBUS on 3V3_SW) on the outdoor cable lines. Charger bus is separate (Header sheet)",
         (4, 60, 62, 30), {
             "R50": (12, 72, 180), "R51": (17, 72, 180), "U5": (38, 72, 0)}),
        ("ZE25-O3 gas connector", "J8 (hand-solder, 1:1 to the module): 2 DAC -> IO7, 3 GND, 4 5V_SW, 5 RXD (3.0 V via R46/R47), 6 TXD -> IO18; 1, 7 reserved",
         (70, 60, 54, 30), {
             "J8": (100, 74, 0), "R46": (84, 72, 90), "R47": (88, 80, 0)}),
    ],
    "Ports": [
        ("BMP580 pressure (BMP581 datasheet BST-BMP581-DS004-13, same package)", "I2C: CSB = VDDIO (6.2.3), SDO low = 0x46 (5.6), INT unused to GND (6.2), 100 nF at VDD and VDDIO (figure 26)",
         (4, 10, 56, 40), {
             "U9": (32, 30, 0), "C90": (12, 26, 0), "C91": (18, 26, 0)}),
        ("Qwiic port 2 and I2C header", "Same bus as J3, order GND, 3V3_SW, SDA, SCL. Module pull-ups: one 2.2k pair at most",
         (64, 10, 50, 40), {
             "J4": (90, 22, 0), "J11": (90, 34, 0)}),
        ("Rain, wind and vane port J12", "Contacts to GND, 1M to +3V3 (3.3 uA closed); 1k + 4.7 nF at IO15/IO16. Vane: 10k from 3V3_SW to IO8",
         (4, 54, 60, 44), {
             "J12": (10, 74, 0, "m"), "U10": (24, 74, 0), "U11": (24, 90, 0),
             "R70": (36, 66.5, 180), "R72": (44, 68, 90), "C70": (50, 69.5, 0),
             "R71": (36, 76.5, 180), "R73": (44, 78, 90), "C71": (50, 79.5, 0),
             "R74": (36, 88.5, 180), "R75": (44, 90, 90), "C72": (50, 91.5, 0)}),
    ],
}

HAND_ROUTES = {
    "USB": {
        # CC1/CC2 straight down to their 5.1k (they cross the data lines without a junction)
        "CC1": [[("J1", "A5"), (26, 26), ("R9", "1")]],
        "CC2": [[("J1", "B5"), (22, 27), ("R10", "1")]],
    },
    # charger host pull-ups: each signal leaves J10 sideways and turns up into its pull-up (rail on top)
    "Header": {
        "CHG_SDA": [[("J10", "11"), (16, 31), ("R54", "1")]],
        "CHG_INT": [[("J10", "15"), (10, 33), ("R22", "1")]],
        "CHG_SCL": [[("J10", "12"), (46, 31), ("R55", "1")]],
        "CHG_CE": [[("J10", "16"), (52, 33), ("R20", "2")]],
    },
    # second Qwiic port and the 2.54 mm header share one vertical line per signal (SDA x 82, SCL x 80)
    "Ports": {
        "SEN_SDA": [[("J4", "3"), (82, 23)], [(82, 23), (82, 44)], [("J11", "3"), (82, 35)]],
        "SEN_SCL": [[("J4", "4"), (80, 24)], [(80, 24), (80, 44)], [("J11", "4"), (80, 36)]],
        "RAIN_IN": [[("J12", "2"), ("U10", "1")], [("U10", "6"), (30, 74)], [(30, 74), (30, 68)], [(30, 68), (36, 68)],
                    [(36, 68), ("R72", "1")]],
        "WIND_IN": [[("J12", "3"), ("U10", "3")], [("U10", "4"), (28, 75)], [(28, 75), (28, 78)], [(28, 78), (36, 78)],
                    [(36, 78), ("R73", "1")]],
        "VANE_IN": [[("J12", "4"), (16, 76)], [(16, 76), (16, 90)], [(16, 90), ("U11", "1")], [("U11", "6"), (36, 90)],
                    [(36, 90), ("R75", "1")]],
        "RAIN": [[("R72", "2"), (50, 68)], [(50, 68), (56, 68)]],
        "WIND": [[("R73", "2"), (50, 78)], [(50, 78), (56, 78)]],
        "VANE": [[("R75", "2"), (50, 90)], [(50, 90), (56, 90)]],
    },
    # pulse port: J12 straight through the USBLC6 lines (1 -> 6, 3 -> 4), then each signal on its own row:
    # pull-up above the row, series R in the row, C below, label at the end (Ports sheet, rows y 68 / 78 / 90)
    # sensor I2C bus: one vertical line per signal left of the connectors (SDA x 26, SCL x 24; SCL crosses SDA, no dot)
    "Sensors": {
        "SEN_SDA": [[("J3", "3"), (26, 37)], [(26, 37), (26, 51)]],
        "SEN_SCL": [[("J3", "4"), (24, 38)], [(24, 38), (24, 51)]],
    },
}
HAND_LABELS = {"Sensors": {"SEN_SDA": (26, 51, 270), "SEN_SCL": (24, 51, 270)},
               "Ports": {"SEN_SDA": (82, 44, 270), "SEN_SCL": (80, 44, 270),
                         "RAIN": (56, 68, 0), "WIND": (56, 78, 0), "VANE": (56, 90, 0)},
               "Header": {"CHG_SDA": (16, 31, 180), "CHG_INT": (10, 33, 180), "CHG_SCL": (46, 31, 0), "CHG_CE": (52, 33, 0)}}
SHEET_DX = 2  # every block 2 cells right of the sheet border
SHEET_TEXTS = {"Header": [(8, 39, HEADER_NOTE)]}

TAGS_BELOW: set = set()
TAG_POS = {"J10": ((0, -15.8, "center"), (0, 15.8, "center"))}

SHEET_NOTES = {
    "USB": "USB-C receptacle: CC pull-downs, ESD on D+/D-; USB_VBUS and D+/D- to the power board over J10",
    "Header": "J10 (J_PWR) from the power board: SYS in, USB_VBUS and D+/D- out, charger I2C/INT/CE with their pull-ups",
    "MCU": "ESP32-S3-WROOM-1-N8: decoupling, reset and boot, USB data series resistors, UART debug, status LEDs",
    "Rails": "SYS to 3.3 V (TPS63802), switched 3V3_SW sensor rail and the 5V_SW 5 V boost (TPS61023, enable from IO12)",
    "Sensors": "PMS7003 PM sensor, SHT45 cable, I2C ESD and pull-ups, optional SCD41 (DNP), ZE25-O3 gas connector",
    "Ports": "BMP580 pressure sensor, second Qwiic port, 2.54 mm I2C header and the rain/wind/vane pulse port",
}

ROOT_BOX = {
    "USB": (6, 28, 34, 22), "Header": (6, 58, 34, 28), "MCU": (58, 18, 40, 68),
    "Rails": (116, 18, 40, 18), "Sensors": (116, 40, 40, 30), "Ports": (116, 74, 40, 18),
}

# labelled bus pins on the root: Ports takes the sensor bus on its left side (facing the MCU), not on top
ROOT_SIDE = {("SEN_SDA", "Ports"): "left", ("SEN_SCL", "Ports"): "left"}

SHEET_COLOR = {
    "USB": ((30, 90, 170), (190, 215, 250)),
    "Header": ((90, 90, 90), (225, 225, 225)),
    "MCU": ((100, 50, 160), (225, 210, 248)),
    "Rails": ((40, 120, 60), (205, 238, 205)),
    "Sensors": ((20, 120, 120), (195, 238, 238)),
    "Ports": ((150, 110, 20), (245, 232, 190)),
}

SHEET_PURPOSE = {
    "USB": "USB-C receptacle: programming and USB-JTAG debug, CC pull-downs, ESD on D+/D-. VBUS and D+/D- go on to the power board (charger input, BC1.2 detection).",
    "Header": "J10 (J_PWR) to the power board: SYS in, USB_VBUS and D+/D- out, charger I2C, INT and CE with their +3V3 pull-ups (CE high = charge off).",
    "MCU": "ESP32-S3 module: runs the firmware, USB data, reset and boot, debug UART, status LEDs. Controls the charger over I2C and switches the sensor rails.",
    "Rails": "SYS to 3.3 V buck-boost (TPS63802). Switched 3V3_SW for the sensor bus; TPS61023 5 V boost (5V_SW) for the PMS7003 and the O3 module, enabled by the ESP32.",
    "Sensors": "PMS7003 PM sensor (5 V, UART), the outdoor SHT45 board, optional SCD41 CO2 (not fitted) and the ZE25-O3 gas sensor; I2C pull-ups and ESD protection.",
    "Ports": "BMP580 pressure (0x46), Qwiic port 2, I2C header, rain/wind/vane port.",
}
