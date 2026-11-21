"""main-board schematic: ESP32-S3-WROOM-1, USB-C (programming, debug, VBUS to the power board), TPS63802 3.3 V buck-boost
from SYS, switched 3V3_SW sensor rail, TPS61023 5 V boost (5V_SW), sensor ports, status LEDs, debug UART, and the mating
side of the board-to-board header J10 (J_PWR). Split from weatherstation-v1 (2026-11-21).

Phase A rule: every part keeps its weatherstation-v1 reference, value, footprint and LCSC number, and its nets are the
same as in hardware/gen/weatherstation_v1.py. Nets that leave this board go through J10 under the same name on both
boards (boards_common.HEADER_PINS; hardware/ARCHITECTURE.md). hardware/tools/split_check.py proves both.
Moved here from the old Charger sheet: the charger host pull-ups R20 (CE), R22 (INT), R54/R55 (I2C), because +3V3 lives
on this board and the power board has no logic rail.

PARTS and NETS are the source of truth; check_nets() compares them with KiCad's netlist. Drawing engine: boardgen.py.
Run: source scripts/kicad-env.sh && uv run --package weatherstation-hardware python hardware/gen/main_board.py [out_dir]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import boardgen  # noqa: E402  (registers the project symbol library)
from boards_common import C0402, C0603, C0805, JST_SH4, R0402, R0603, SOT23, TP, add_header, header_part  # noqa: E402
from main_layout import (BLOCKS, HAND_LABELS, HAND_ROUTES, ROOT_BOX, SHEET_COLOR, SHEET_DX, SHEET_NOTES,  # noqa: E402,F401
                         SHEET_PURPOSE, SHEET_TEXTS, TAG_POS, TAGS_BELOW)

PROJECT, TITLE, SHEET_PREFIX = "main-board", "weatherstation main board", "main board"
SHEET_FILES = {"USB": "usb.kicad_sch", "Header": "header.kicad_sch", "MCU": "mcu.kicad_sch",
               "Rails": "rails.kicad_sch", "Sensors": "sensors.kicad_sch", "Ports": "ports.kicad_sch"}

# ref: (symbol, value, footprint, LCSC or None, sheet)
PARTS = {
    # --- USB-C: programming, debug (native USB-JTAG) and VBUS to the power board ---------------------------------------
    "J1": ("Connector:USB_C_Receptacle_USB2.0_16P", "USB-C", "Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12", "C165948", "USB"),
    "U4": ("Power_Protection:USBLC6-2SC6", "USBLC6-2SC6 (USB)", "Package_TO_SOT_SMD:SOT-23-6", "C7519", "USB"),
    "R9": ("Device:R", "5.1k", R0402, "C25905", "USB"),
    "R10": ("Device:R", "5.1k", R0402, "C25905", "USB"),
    "#FLG12": ("power:PWR_FLAG", "PWR_FLAG", None, None, "USB"),
    "#FLG22": ("power:PWR_FLAG", "PWR_FLAG", None, None, "USB"),  # USB_VBUS: J1 and U4 pins are passive / power input
    # --- Header: J10 and the charger host pull-ups (moved from the old Charger sheet) ----------------------------------
    "J10": header_part("Header", "main"),
    # CE pull-up to +3V3 (not REGN: CE is also an ESP32 GPIO, 3.3 V I/O; v1 PARTS-REVIEW A7): charge off until firmware
    # has written VREG 3.65 V and drives CE low.
    "R20": ("Device:R", "100k", R0402, "C25741", "Header"),
    "R22": ("Device:R", "10k", R0402, "C25744", "Header"),
    # Charger I2C bus (IO1 SDA / IO2 SCL: the RTC I2C pins of the ULP RISC-V driver): own 10k pull-ups to +3V3, readable
    # while the sensor rail is off (v1 PARTS-REVIEW A4).
    "R54": ("Device:R", "10k", R0402, "C25744", "Header"),
    "R55": ("Device:R", "10k", R0402, "C25744", "Header"),
    "#FLG21": ("power:PWR_FLAG", "PWR_FLAG", None, None, "Header"),  # SYS arrives through J10 (passive pins)
    # --- MCU ---------------------------------------------------------------------------------------------------------
    "U1": ("RF_Module:ESP32-S3-WROOM-1", "ESP32-S3-WROOM-1-N8", "RF_Module:ESP32-S3-WROOM-1", "C2913198", "MCU"),
    "C30": ("Device:C", "22u", C0805, "C45783", "MCU"),
    "C31": ("Device:C", "100n", C0402, "C307331", "MCU"),
    "C32": ("Device:C", "1u", C0402, "C52923", "MCU"),
    "R30": ("Device:R", "10k", R0402, "C25744", "MCU"),
    "C33": ("Device:C", "1u", C0402, "C52923", "MCU"),
    # RESET and BOOT as tweezer pads (engineer 2026-11-03). Not assembled. Normal flashing needs neither (esptool resets
    # the S3 over USB-JTAG); the pads recover a board whose firmware sleeps or disables USB (short BOOT, then RESET).
    "JP1": ("Jumper:SolderJumper_2_Open", "RESET", "Jumper:SolderJumper-2_P1.3mm_Open_RoundedPad1.0x1.5mm", None, "MCU"),
    "R31": ("Device:R", "10k", R0402, "C25744", "MCU"),
    "JP2": ("Jumper:SolderJumper_2_Open", "BOOT", "Jumper:SolderJumper-2_P1.3mm_Open_RoundedPad1.0x1.5mm", None, "MCU"),
    "R32": ("Device:R", "22", R0402, "C25092", "MCU"),
    "R33": ("Device:R", "22", R0402, "C25092", "MCU"),
    # two status LEDs (engineer 2026-11-03), active high on IO41/IO42 (module pins 34/35). Red 0603 (Basic), 1k: ~1.3 mA.
    "R34": ("Device:R", "1k", R0402, "C11702", "MCU"),
    "D10": ("Device:LED", "LED1 red", "LED_SMD:LED_0603_1608Metric", "C2286", "MCU"),
    "R35": ("Device:R", "1k", R0402, "C11702", "MCU"),
    "D11": ("Device:LED", "LED2 red", "LED_SMD:LED_0603_1608Metric", "C2286", "MCU"),
    "J7": ("Connector_Generic:Conn_01x04", "DEBUG UART", "Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical", None, "MCU"),
    # --- Rails -------------------------------------------------------------------------------------------------------
    # 3.3 V buck-boost from SYS (TI SLVSEU9D). Symbol from table 7-1, footprint from the DLA0010A example board layout.
    "U2": ("weatherstation:TPS63802DLA", "TPS63802DLA 3.3 V buck-boost", "weatherstation:TPS63802_DLA_VSON-HR-10_2x3mm", "C2845237", "Rails"),
    "L4": ("Device:L", "0.47uH (Sunlord WPN201610HR47MT: Isat 4.0 A max, Irms 2.7 A)", "weatherstation:L_Sunlord_WPN201610H", "C97009", "Rails"),
    "R52": ("Device:R", "220k 1% (FB top: 0.5 V x (1 + 220k/39k) = 3.32 V)", R0603, "C22961", "Rails"),
    "R53": ("Device:R", "39k 1% (FB bottom, datasheet max 100k)", R0603, "C23153", "Rails"),
    "C40": ("Device:C", "10u", C0603, "C19702", "Rails"),
    "C41": ("Device:C", "22u (TPS63802 output: 22 uF per table 10-1)", C0805, "C45783", "Rails"),
    "Q40": ("Transistor_FET:AO3401A", "AO3401A 3V3_SW switch", SOT23, "C15127", "Rails"),
    "R40": ("Device:R", "100k", R0402, "C25741", "Rails"),
    "Q41": ("Transistor_FET:2N7002", "2N7002 (sensor enable)", SOT23, "C8545", "Rails"),
    "R41": ("Device:R", "1k", R0402, "C11702", "Rails"),
    "R42": ("Device:R", "100k", R0402, "C25741", "Rails"),
    "C42": ("Device:C", "22u", C0805, "C45783", "Rails"),
    "C43": ("Device:C", "22u", C0805, "C45783", "Rails"),
    # 5V_SW boost (TI SLVSF14B): VIN 0.5-5.5 V (start 1.8 V), true disconnect, 0.1 uA off. EN = BOOST_EN (IO12), R45 pulls
    # EN low = off by default. Figure 8-1: 1 uH, 10 uF in, 2 x 22 uF out. FB 0.595 V x (1 + 510k/68k) = 5.06 V.
    "U7": ("weatherstation:TPS61023DRL", "TPS61023DRLR 5 V boost", "Package_TO_SOT_SMD:SOT-563", "C919459", "Rails"),
    "L5": ("Device:L", "1uH (VLS252010HBX-1R0M-1, same as L1)", "weatherstation:L_TDK_VLS252010", "C88211", "Rails"),
    "R43": ("Device:R", "510k 1% (boost FB top: 0.595 V x (1 + 510k/68k) = 5.06 V)", R0603, "C23192", "Rails"),
    "R44": ("Device:R", "68k 1% (boost FB bottom)", R0603, "C23231", "Rails"),
    "R45": ("Device:R", "100k (EN pull-down: boost off by default)", R0402, "C25741", "Rails"),
    "C44": ("Device:C", "10u (boost input)", C0603, "C19702", "Rails"),
    "C45": ("Device:C", "22u (boost output)", C0805, "C45783", "Rails"),
    "C46": ("Device:C", "22u (boost output)", C0805, "C45783", "Rails"),
    "TP1": ("Connector:TestPoint", "+3V3", TP, None, "Rails"),
    "TP2": ("Connector:TestPoint", "SYS", TP, None, "Rails"),
    "#FLG10": ("power:PWR_FLAG", "PWR_FLAG", None, None, "Rails"),
    # --- Sensors -----------------------------------------------------------------------------------------------------
    # PMS7003 on its 2x5 1.27 mm cable (manual V2.5): 1/2 VCC 5 V, 3/4 GND, 5 RESET (open), 6/8 NC, 7 RX, 9 TX, 10 SET
    # (low = sleep); data 3.3 V TTL. R48/R49 1k limit current into an unpowered module.
    "J2": ("Connector_Generic:Conn_02x05_Odd_Even", "PMS7003 (2x5 1.27 mm)", "Connector_PinHeader_1.27mm:PinHeader_2x05_P1.27mm_Vertical", None, "Sensors"),
    "R48": ("Device:R", "1k (PM RX series)", R0402, "C11702", "Sensors"),
    "R49": ("Device:R", "1k (PM SET series)", R0402, "C11702", "Sensors"),
    # optional CO2: Sensirion SCD41-D-R2 (LCSC C3659294), footprint only (DNP). VDD and VDDH tied at the sensor.
    "U8": ("Sensor_Gas:SCD41-D-R2", "SCD41 DNP (C3659294)", "Sensor:Sensirion_SCD4x-1EP_10.1x10.1mm_P1.25mm_EP4.8x4.8mm", None, "Sensors"),
    "C47": ("Device:C", "10u (SCD41 VDD)", C0603, "C19702", "Sensors"),
    "J3": ("Connector_Generic:Conn_01x04", "SHT45 cable", JST_SH4, "C160404", "Sensors"),
    "U5": ("Power_Protection:USBLC6-2SC6", "USBLC6-2SC6 (I2C)", "Package_TO_SOT_SMD:SOT-23-6", "C7519", "Sensors"),
    # Sensor I2C bus (IO13/IO14): pull-ups and U5 VBUS on 3V3_SW, so nothing back-powers the sensors when the rail is off.
    # 2.2k since phase B: 2 m outdoor cable + up to 7 devices = about 280 pF; 10k gave 2.3 us rise (calc/i2c_bus.py)
    "R50": ("Device:R", "2.2k", R0402, "C25879", "Sensors"),
    "R51": ("Device:R", "2.2k", R0402, "C25879", "Sensors"),
    # ZE25-O3 7-pin (Winsen table 2): 1 reserved, 2 DAC, 3 GND, 4 Vin 3.7-5.5 V, 5 RXD (0-3.0 V in), 6 TXD, 7 reserved.
    "J8": ("Connector_Generic:Conn_01x07", "ZE25-O3 (cable pitch to confirm)", "Connector_JST:JST_PH_B7B-PH-K_1x07_P2.00mm_Vertical", None, "Sensors"),
    "R46": ("Device:R", "1k (GAS RXD level: 3.3 V x 10/11 = 3.0 V)", R0402, "C11702", "Sensors"),
    "R47": ("Device:R", "10k", R0402, "C25744", "Sensors"),
    # --- Ports (phase B): BMP585 on the sensor bus, second Qwiic port, 2.54 mm I2C header ---------------------------------
    # BMP585 as hardware/gen/addon_boards.py bmp585 (Bosch BST-BMP585-DS003-02 rev 1.2): CSB = VDDIO (I2C, 6.2.3),
    # SDO low = 0x46 (5.6), 100 nF at VDD and VDDIO (figure 25), INT open.
    "U9": ("weatherstation:BMP585", "BMP585 (0x46)", "weatherstation:BMP585_LGA-8_3.25x3.25mm", "C18184976", "Ports"),
    "C90": ("Device:C", "100n", C0603, "C14663", "Ports"),
    "C91": ("Device:C", "100n", C0603, "C14663", "Ports"),
    "J4": ("Connector_Generic:Conn_01x04", "Qwiic 2", JST_SH4, "C160404", "Ports"),
    "J11": ("Connector_Generic:Conn_01x04", "I2C 2.54 (GND 3V3_SW SDA SCL)", "Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical", None, "Ports"),
}

# Parts that are not in weatherstation-v1 (tools/split_check.py) and v1 parts changed on purpose after the split.
ADDED = {
    "U9": "phase B: BMP585 pressure on the sensor bus (REQUIREMENTS-system.md 9: BMP585 on main)",
    "C90": "phase B: BMP585 VDD 100 nF", "C91": "phase B: BMP585 VDDIO 100 nF",
    "J4": "phase B: second Qwiic port (REQUIREMENTS-system.md 5 ports)",
    "J11": "phase B: 4-pin 2.54 mm I2C header (GND, 3V3_SW, SDA, SCL)",
}
CHANGED = {
    "R50": "phase B: 10k -> 2.2k, I2C rise time with 2 m cable (calc/i2c_bus.py, PARTS-REVIEW.md B5)",
    "R51": "phase B: 10k -> 2.2k, as R50",
}

NETS = add_header({
    # USB-C
    "USB_VBUS": [("J1", "A4"), ("J1", "A9"), ("J1", "B4"), ("J1", "B9"), ("U4", "5"), ("#FLG22", "1")],
    "CC1": [("J1", "A5"), ("R9", "1")],
    "CC2": [("J1", "B5"), ("R10", "1")],
    "USB_DP": [("J1", "A6"), ("J1", "B6"), ("U4", "1"), ("U4", "6"), ("R32", "1")],
    "USB_DN": [("J1", "A7"), ("J1", "B7"), ("U4", "3"), ("U4", "4"), ("R33", "1")],
    # SYS from the power board (or a bench supply on J10 pins 1/2): buck-boost, boost and test point
    "SYS": [("U2", "10"), ("U2", "1"), ("C40", "1"), ("U7", "3"), ("L5", "1"), ("C44", "1"), ("TP2", "1"), ("#FLG21", "1")],
    # Charger host pins: two I2C buses (charger on IO1/IO2, RTC I2C for the ULP core; sensors on IO13/IO14)
    "CHG_CE": [("R20", "2"), ("U1", "17")],
    "CHG_INT": [("R22", "1"), ("U1", "18")],
    "CHG_SDA": [("U1", "39"), ("R54", "1")],
    "CHG_SCL": [("U1", "38"), ("R55", "1")],
    "SEN_SDA": [("U1", "21"), ("U8", "10"), ("J3", "3"), ("R50", "1"), ("U5", "1"), ("U5", "6"),
                ("U9", "2"), ("J4", "3"), ("J11", "3")],
    "SEN_SCL": [("U1", "22"), ("U8", "9"), ("J3", "4"), ("R51", "1"), ("U5", "3"), ("U5", "4"),
                ("U9", "1"), ("J4", "4"), ("J11", "4")],
    # MCU
    "EN": [("U1", "3"), ("R30", "2"), ("C33", "1"), ("JP1", "1")],
    "IO0": [("U1", "27"), ("R31", "2"), ("JP2", "1")],
    "LED1": [("U1", "34"), ("R34", "1")],
    "LED1_A": [("R34", "2"), ("D10", "2")],
    "LED2": [("U1", "35"), ("R35", "1")],
    "LED2_A": [("R35", "2"), ("D11", "2")],
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
    # Rails
    "3V3_SW": [("Q40", "3"), ("C42", "1"), ("C43", "1"), ("U8", "7"), ("U8", "19"), ("C47", "1"), ("J3", "2"), ("U5", "5"),
               ("R50", "2"), ("R51", "2"), ("#FLG10", "1"),
               ("U9", "8"), ("U9", "4"), ("U9", "7"), ("C90", "1"), ("C91", "1"), ("J4", "2"), ("J11", "2")],
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
    "+3V3": [("R20", "1"), ("U1", "2"), ("C30", "1"), ("C31", "1"), ("C32", "1"), ("R30", "1"), ("R31", "1"), ("J7", "1"),
             ("R22", "2"), ("R54", "2"), ("R55", "2"), ("TP1", "1"), ("U2", "6"), ("C41", "1"), ("Q40", "2"), ("R40", "1"),
             ("R52", "1")],
    "BUCK_L1": [("U2", "9"), ("L4", "1")],
    "BUCK_L2": [("U2", "7"), ("L4", "2")],
    "FB": [("U2", "4"), ("R52", "2"), ("R53", "1")],
    "GND": [("J1", "A1"), ("J1", "A12"), ("J1", "B1"), ("J1", "B12"), ("J1", "SH"), ("U4", "2"), ("R9", "2"), ("R10", "2"),
            ("R53", "2"), ("U2", "2"), ("U2", "3"), ("U2", "8"), ("U1", "1"), ("U1", "40"), ("U1", "41"), ("C30", "2"),
            ("C31", "2"), ("C32", "2"), ("C33", "2"), ("JP1", "2"), ("JP2", "2"), ("D10", "1"), ("D11", "1"), ("J7", "4"),
            ("C40", "2"), ("C41", "2"), ("Q41", "2"), ("R42", "2"), ("C42", "2"), ("C43", "2"), ("U7", "4"), ("R44", "2"),
            ("R45", "2"), ("C44", "2"), ("C45", "2"), ("C46", "2"), ("J2", "3"), ("J2", "4"), ("U8", "6"), ("U8", "20"),
            ("U8", "21"), ("C47", "2"), ("J3", "1"), ("U5", "2"), ("J8", "3"), ("R47", "2"), ("#FLG12", "1"),
            ("U9", "3"), ("U9", "6"), ("C90", "2"), ("C91", "2"), ("J4", "1"), ("J11", "1")],
})
POWER_SYMBOLS = ("GND", "+3V3", "3V3_SW", "SYS", "USB_VBUS", "5V_SW")
RAIL_LIB = {"GND": "power:GND", "+3V3": "power:+3V3"}  # others: power:VCC with the net as value

SHEET_VALUE = {"U4": "USBLC6-2SC6", "U5": "USBLC6-2SC6", "L4": "0.47uH", "U2": "TPS63802", "Q40": "AO3401A",
               "Q41": "2N7002", "U7": "TPS61023", "L5": "1uH", "J10": "J_PWR 2x9", "U9": "BMP585", "J4": "QWIIC 2",
               "J11": "I2C 2.54"}
HAND_SOLDER = {"J2", "J7", "J8", "J10", "J11"}  # pin headers and JST PH: hand-soldered, not in the assembly BOM
TP_NOTE = "SYS/3V3 test pads"
# D+/D- join three sheets (USB, MCU, Header), the sensor bus three (MCU, Sensors, Ports): no crossing-free route on the
# root, so these keep labels there
ROOT_LABELLED = ("USB_DP", "USB_DN", "SEN_SDA", "SEN_SCL")
ROOT_TEXTS = [
    (6, 6, "#weatherstation main board: block diagram"),
    (6, 10, "Each box is a sheet. Wires join the sheet pins (hierarchical labels). Rails (GND, +3V3, 3V3_SW, SYS, USB_VBUS, 5V_SW) are power symbols."),
    (6, 94, "Power path: SYS (J10, from the power board or a bench supply) -> Rails: TPS63802 -> +3V3 -> Q40 -> 3V3_SW; TPS61023 -> 5V_SW (EN = IO12)."),
    (6, 96, "USB-C: data to the ESP32 (USB-JTAG), USB_VBUS and D+/D- to J10 (charger input and BC1.2 detection on the power board)."),
    (6, 98, "Header J10 (J_PWR) pin map: hardware/ARCHITECTURE.md. Open decisions: hardware/main-board/PARTS-REVIEW.md."),
]

if __name__ == "__main__":
    sys.exit(boardgen.main(sys.modules[__name__], Path(__file__).resolve().parents[1] / "main-board"))
