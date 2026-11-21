"""Hand-placed block layout of the main-board sheets (units: 2.54 mm cells). Format as layout_v1.py.

Five sheets since 2026-11-21 (review partition): USB (USB-C and J10 with the charger host pull-ups), MCU, Rails, I2C (the
sensor bus on 3V3_SW) and Sensors (UART, analog and pulse sensors). MCU and Rails keep the weatherstation-v1 drawing.
Every part sits inside exactly one block; boardgen asserts this. Part tuples are (x, y, rotation[, mirror]).
"""

from boards_common import HEADER_NOTE

# sheet -> list of blocks: (title, note, (x, y, w, h), {ref: (x, y, rot[, "m"])})
BLOCKS = {
    "USB": [
        ("USB-C receptacle", "USB-C sink (programming, USB-JTAG debug, charging): CC1/CC2 5.1k pull-downs (Rd); USBLC6 ESD on D+/D- with VBUS reference. USB_VBUS and D+/D- continue to J10 (power board)",
         (4, 10, 60, 40), {
             "J1": (12, 30, 0), "U4": (34, 35, 0), "R9": (26, 42, 0), "R10": (22, 42, 0), "#FLG12": (16, 40, 0), "#FLG22": (44, 30, 180), "C35": (50, 30, 0)}),
        ("Board-to-board header J10 (J_PWR) and charger host pull-ups", "J10 mating side (pin map: hardware/ARCHITECTURE.md). +3V3 lives here: CE pull-up R20 1M (charge off until firmware writes VREG; the power board has its own 1M), INT R22 10k, charger I2C R54/R55 10k (BQ25798 table 5-1)",
         (70, 10, 70, 46), {
             "J10": (96, 30, 0), "R54": (82, 26, 180), "R22": (76, 26, 180), "R55": (112, 26, 180), "R20": (118, 26, 0),
             "#FLG21": (130, 46, 180)}),
    ],
    "MCU": [
        ("ESP32-S3-WROOM-1-N8", "N8: 8 MB flash, no PSRAM. Strapping: IO0 (BOOT), EN (RESET). Native USB on IO19/IO20 with 22 ohm series resistors. Open pins (no-connect flags): IO3, IO45, IO46 are strapping pins left at their defaults; IO35-IO37 stay free (octal PSRAM on N8R8 modules); IO21, IO38-IO40, IO47, IO48 spare",
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
        ("3.3 V buck-boost", "TPS63802DLA from SYS (VIN = EN = SYS, MODE = GND: power save). FB 220k / 39k: 0.5 V x (1 + 220/39) = 3.32 V. L4 0.47 uH; 22 uF in (C40 0805), 22 uF out",
         (4, 10, 90, 40), {
             "U2": (30, 26, 0), "L4": (42, 25, 0), "C40": (14, 26, 0), "R52": (50, 30, 0), "R53": (50, 38, 0), "C41": (58, 26, 0),
             "TP1": (72, 34, 180), "TP2": (78, 34, 180), "#FLG10": (86, 22, 180)}),
        ("3V3_SW sensor rail", "Q40 switches +3V3 to the sensors: R40 holds it off, Q41 (SENSOR_EN, IO11) pulls the gate via R76, C48 ramps 3V3_SW (0.3-0.4 ms, calc/rail_switch.py)",
         (4, 56, 62, 36), {
             "Q40": (30, 70, 180, "m"), "R40": (22, 65, 0), "R76": (22, 75, 0), "C48": (26, 76, 0),
             "Q41": (21, 82, 0), "R41": (12, 82, 90), "R42": (16, 88, 0),
             "C42": (44, 80, 0), "C43": (49, 80, 0)}),
        ("5V_SW 5 V boost", "TPS61023: SYS -> 5.06 V for the PMS7003 and the ZE25-O3. EN = BOOST_EN (IO12); R45 = off by default; off = output disconnected, 0.1 uA. FB 0.595 V x (1 + 510k/68k)",
         (72, 56, 56, 36), {
             "C44": (75, 76, 0), "L5": (92, 66, 90), "U7": (92, 74, 0), "R45": (80, 84, 0),
             "R43": (108, 76, 0), "R44": (108, 85, 0), "C45": (116, 77, 0), "C46": (121, 77, 0)}),
    ],
    "I2C": [
        ("Outdoor cable J3 (SHT head)", "J3 in the radiation shield (Qwiic order: GND, VDD, SDA, SCL). VDD from 3V3_SW through R77 100 ohm (a cable short draws 33 mA, +3V3 stays up). USBLC6 U5 sits between J3 and the bus (VBUS pin on 3V3_SW)",
         (4, 10, 80, 46), {
             "R77": (60, 30, 0), "U5": (50, 37, 0), "J3": (70, 36, 0)}),
        ("Qwiic port 2 and I2C header", "Same bus as J3, order GND, 3V3_SW, SDA, SCL. Module pull-ups: one 2.2k pair at most",
         (88, 10, 50, 40), {
             "J4": (114, 22, 0), "J11": (114, 34, 0)}),
        ("Bus pull-ups", "Sensor I2C bus (IO13/IO14): 2.2k to 3V3_SW (2 m cable, calc/i2c_bus.py). The charger bus is separate (USB sheet, J10)",
         (4, 60, 28, 30), {
             "R50": (12, 72, 180), "R51": (17, 72, 180)}),
        ("BMP580 pressure (BMP581 datasheet BST-BMP581-DS004-13, same package)", "I2C: CSB = VDDIO (6.2.3), SDO low = 0x46 (5.6), INT unused to GND (6.2), 100 nF at VDD and VDDIO (figure 26)",
         (36, 60, 56, 40), {
             "U9": (64, 80, 0), "C90": (44, 76, 0), "C91": (50, 76, 0)}),
        ("CO2 SCD41 (DNP)", "Footprint only; VDD = VDDH at the sensor, 3V3_SW",
         (96, 60, 32, 30), {
             "U8": (116, 76, 0), "C47": (104, 76, 0)}),
    ],
    "Sensors": [
        ("PM sensor PMS7003", "J2 (hand-solder, 2x5 1.27 mm, manual V2.5): 1/2 5V_SW, 3/4 GND, 7 RX <- IO4 via R48, 9 TX -> IO5, 10 SET <- IO6 via R49 (low = sleep); 5 RESET, 6, 8 open. Data 3.3 V TTL",
         (4, 10, 80, 46), {
             "J2": (46, 30, 0), "R48": (26, 31, 90), "R49": (26, 35, 90)}),
        ("ZE25-O3 gas connector", "J8 (hand-solder, 1:1 to the module): 2 DAC -> IO7, 3 GND, 4 5V_SW, 5 RXD (3.0 V via R46/R47), 6 TXD -> IO18; 1, 7 reserved",
         (88, 10, 54, 40), {
             "J8": (118, 24, 0), "R46": (102, 22, 90), "R47": (106, 30, 0)}),
        ("Rain, wind and vane port J12", "Contacts to GND, 1M to +3V3 (3.3 uA closed); 1k + 4.7 nF at IO15/IO16. Vane: 10k from 3V3_SW to IO8",
         (4, 60, 60, 44), {
             "J12": (10, 80, 0, "m"), "U10": (24, 80, 0), "U11": (24, 96, 0),
             "R70": (36, 72.5, 180), "R72": (44, 74, 90), "C70": (50, 75.5, 0),
             "R71": (36, 82.5, 180), "R73": (44, 84, 90), "C71": (50, 85.5, 0),
             "R74": (36, 94.5, 180), "R75": (44, 96, 90), "C72": (50, 97.5, 0)}),
    ],
}

HAND_ROUTES = {
    "USB": {
        # CC1/CC2 straight down to their 5.1k (they cross the data lines without a junction)
        "CC1": [[("J1", "A5"), (26, 26), ("R9", "1")]],
        "CC2": [[("J1", "B5"), (22, 27), ("R10", "1")]],
        # charger host pull-ups: each signal leaves J10 sideways and turns up into its pull-up (rail on top)
        "CHG_SDA": [[("J10", "11"), (82, 31), ("R54", "1")]],
        "CHG_INT": [[("J10", "15"), (76, 33), ("R22", "1")]],
        "CHG_SCL": [[("J10", "12"), (112, 31), ("R55", "1")]],
        "CHG_CE": [[("J10", "16"), (118, 33), ("R20", "2")]],
    },
    # Q40 switch drawn source up (+3V3 on top): gate node from R40 across to the gate, R76 down to the Q41 drain, C48 from
    # the gate wire down to the drain wire, which runs on to the bulk caps C42/C43 (one 3V3_SW symbol)
    "Rails": {
        "SEN_G": [[("R40", "2"), (22, 70)], [(22, 70), (26, 70)], [(26, 70), ("Q40", "1")], [("R76", "1"), (22, 70)],
                  [("C48", "1"), (26, 70)]],
        "SEN_PULL": [[("R76", "2"), ("Q41", "3")]],
        "3V3_SW": [[("Q40", "3"), (31, 78.5)], [("C48", "2"), (26, 78.5), (31, 78.5)], [(31, 78.5), ("C42", "1")],
                   [("C42", "1"), ("C43", "1")]],
    },
    # outdoor cable: J3 -> USBLC6 U5 (6 -> 1, 4 -> 3) -> bus lines down to their labels; second Qwiic port and the 2.54 mm
    # header share one vertical line per signal (SDA x 106, SCL x 104)
    "I2C": {
        "3V3_CABLE": [[("R77", "2"), (60, 36)], [(60, 36), ("J3", "2")]],
        "SEN_SDA": [[("J3", "3"), ("U5", "6")], [("U5", "1"), (44, 37)], [(44, 37), (44, 54)],
                    [("J4", "3"), (106, 23)], [(106, 23), (106, 44)], [("J11", "3"), (106, 35)]],
        "SEN_SCL": [[("J3", "4"), ("U5", "4")], [("U5", "3"), (42, 38)], [(42, 38), (42, 54)],
                    [("J4", "4"), (104, 24)], [(104, 24), (104, 44)], [("J11", "4"), (104, 36)]],
    },
    # pulse port: J12 straight through the USBLC6 lines (1 -> 6, 3 -> 4), then each signal on its own row:
    # pull-up above the row, series R in the row, C below, label at the end (rows y 74 / 84 / 96)
    "Sensors": {
        "RAIN_IN": [[("J12", "2"), ("U10", "1")], [("U10", "6"), (30, 80)], [(30, 80), (30, 74)], [(30, 74), (36, 74)],
                    [(36, 74), ("R72", "1")]],
        "WIND_IN": [[("J12", "3"), ("U10", "3")], [("U10", "4"), (28, 81)], [(28, 81), (28, 84)], [(28, 84), (36, 84)],
                    [(36, 84), ("R73", "1")]],
        "VANE_IN": [[("J12", "4"), (16, 82)], [(16, 82), (16, 96)], [(16, 96), ("U11", "1")], [("U11", "6"), (36, 96)],
                    [(36, 96), ("R75", "1")]],
        "RAIN": [[("R72", "2"), (50, 74)], [(50, 74), (56, 74)]],
        "WIND": [[("R73", "2"), (50, 84)], [(50, 84), (56, 84)]],
        "VANE": [[("R75", "2"), (50, 96)], [(50, 96), (56, 96)]],
    },
}
HAND_LABELS = {"I2C": {"SEN_SDA": [(44, 54, 270), (106, 44, 270), (56, 37, 0, "above")],
                       "SEN_SCL": [(42, 54, 270), (104, 44, 270), (56, 38, 0, "above")], "3V3_CABLE": (61, 36, 0, "above")},
               "Sensors": {"RAIN": (56, 74, 0), "WIND": (56, 84, 0), "VANE": (56, 96, 0)},
               "Rails": {"SEN_G": (22.5, 70, 0, "above"), "SEN_PULL": (22, 80, 90, "above")},
               "USB": {"CHG_SDA": (82, 31, 180), "CHG_INT": (76, 33, 180), "CHG_SCL": (112, 31, 0), "CHG_CE": (118, 33, 0)}}
SHEET_DX = 2  # every block 2 cells right of the sheet border
SHEET_TEXTS = {"USB": [(74, 39, HEADER_NOTE)]}

TAGS_BELOW: set = set()
# hierarchical label shapes (signal direction seen from the sheet): J10 signals on the USB sheet and their sources
LABEL_SHAPE = {"USB": {"CHG_CE": "input", "CHG_SCL": "input", "CHG_INT": "output", "CHG_SDA": "bidirectional"},
               "MCU": {"CHG_CE": "output", "CHG_SCL": "output", "CHG_INT": "input", "SENSOR_EN": "output", "BOOST_EN": "output"},
               "Rails": {"SENSOR_EN": "input", "BOOST_EN": "input"}}

# reference/value spots that keep the texts off their symbol bodies (review_checks: "overlaps its symbol body")
TAG_POS = {"J10": ((0, -15.8, "center"), (0, 15.8, "center")), "Q40": ((5.5, -1.0, "right"), (5.5, 1.0, "right")),
           **{j: ((0, 8.0, "center"), (0, -5.3, "center")) for j in ("J3", "J4", "J7", "J11", "J12")},
           **{u: ((3.2, 7.0, "left"), (3.2, 8.8, "left")) for u in ("U4", "U5", "U10", "U11")},
           **{jp: ((2.2, -1.3, "left"), (2.2, 1.3, "left")) for jp in ("JP1", "JP2")}}

SHEET_NOTES = {
    "USB": "USB-C receptacle and J10 to the power board: USB_VBUS and D+/D- out, SYS in, charger I2C/INT/CE with their pull-ups",
    "MCU": "ESP32-S3-WROOM-1-N8: decoupling, reset and boot, USB data series resistors, UART debug, status LEDs",
    "Rails": "SYS to 3.3 V (TPS63802), switched 3V3_SW sensor rail and the 5V_SW 5 V boost (TPS61023, enable from IO12)",
    "I2C": "Sensor I2C bus on 3V3_SW: outdoor cable J3 (R77 feed, USBLC6 ESD), pull-ups, BMP580, Qwiic 2 and I2C header, SCD41 (DNP)",
    "Sensors": "UART, analog and pulse sensors: PMS7003 (5V_SW), ZE25-O3 gas connector, rain/wind/vane port J12",
}

ROOT_BOX = {
    "USB": (6, 22, 34, 40), "MCU": (58, 18, 40, 76),
    "Rails": (116, 14, 40, 24), "I2C": (116, 41, 40, 21), "Sensors": (116, 64, 40, 34),
}

# labelled bus pins on the root: the I2C sheet takes the sensor bus on its left side (facing the MCU), not on top
ROOT_SIDE = {("SEN_SDA", "I2C"): "left", ("SEN_SCL", "I2C"): "left"}

SHEET_COLOR = {
    "USB": ((30, 90, 170), (190, 215, 250)),
    "MCU": ((100, 50, 160), (225, 210, 248)),
    "Rails": ((40, 120, 60), (205, 238, 205)),
    "I2C": ((150, 110, 20), (245, 232, 190)),
    "Sensors": ((20, 120, 120), (195, 238, 238)),
}

SHEET_PURPOSE = {
    "USB": "USB-C receptacle (programming, USB-JTAG debug, charging input) and J10 (J_PWR) to the power board: USB_VBUS and D+/D- out, SYS in, charger I2C, INT and CE with their +3V3 pull-ups (CE high = charge off).",
    "MCU": "ESP32-S3 module: runs the firmware, USB data, reset and boot, debug UART, status LEDs. Controls the charger over I2C and switches the sensor rails.",
    "Rails": "SYS to 3.3 V buck-boost (TPS63802). Switched 3V3_SW (slow ramp) for the sensor bus; TPS61023 5 V boost (5V_SW) for the PMS7003 and the O3 module, enabled by the ESP32.",
    "I2C": "Sensor I2C bus (IO13/IO14, 2.2k): outdoor SHT cable J3 (feed + ESD), BMP580 (0x46), Qwiic 2, I2C header, SCD41 (DNP).",
    "Sensors": "UART, analog and pulse sensors: PMS7003 PM (5 V, UART), ZE25-O3 gas (UART + DAC), rain/wind/vane contacts (J12, ESD, RC filters).",
}
