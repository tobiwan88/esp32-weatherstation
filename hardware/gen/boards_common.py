"""Shared by power_board.py and main_board.py: footprints, the board-to-board header J10 (J_PWR) and its pin map.

The pin map lives here once, so both boards always agree (hardware/ARCHITECTURE.md has the table and the reasons;
hardware/tools/split_check.py proves both generators use it). Header net names are the netlist names: the contract
signal "VBUS" is the net USB_VBUS (USB-C VBUS before the charger's ACFET1/RBFET1 pair), "D+/D-" are USB_DP/USB_DN.
"""

R0603, C0603, C0805 = "Resistor_SMD:R_0603_1608Metric", "Capacitor_SMD:C_0603_1608Metric", "Capacitor_SMD:C_0805_2012Metric"
C0402, R0402 = "Capacitor_SMD:C_0402_1005Metric", "Resistor_SMD:R_0402_1005Metric"
JST_PH2 = "Connector_JST:JST_PH_B2B-PH-K_1x02_P2.00mm_Vertical"
JST_SH4 = "Connector_JST:JST_SH_SM04B-SRSS-TB_1x04-1MP_P1.00mm_Horizontal"
TP = "TestPoint:TestPoint_Pad_D1.5mm"
SOT23 = "Package_TO_SOT_SMD:SOT-23"

# J10 = J_PWR: 2 x 9, 2.54 mm, through-hole, hand-soldered (no JLC fee). Odd pins = row A, even pins = row B.
# Every signal row has a GND row on both sides; SYS (row 1) and VBUS (row 3) sit at the far end from the I2C rows.
HEADER_REF = "J10"
HEADER_SYMBOL = "Connector_Generic:Conn_02x09_Odd_Even"
HEADER_FOOTPRINT = "Connector_PinHeader_2.54mm:PinHeader_2x09_P2.54mm_Vertical"
HEADER_PINS = {
    "1": "SYS", "2": "SYS",
    "3": "GND", "4": "GND",
    "5": "USB_VBUS", "6": "USB_VBUS",
    "7": "GND", "8": "GND",
    "9": "USB_DP", "10": "USB_DN",
    "11": "GND", "12": "GND",
    "13": "CHG_SDA", "14": "CHG_SCL",
    "15": "GND", "16": "GND",
    "17": "CHG_INT", "18": "CHG_CE",
}
HEADER_NETS = sorted(set(HEADER_PINS.values()))


def header_part(sheet: str, side: str) -> tuple:
    """PARTS entry of J10 on one board (side = 'power' or 'main'); same footprint on both so the holes line up."""
    return (HEADER_SYMBOL, f"J_PWR 2x9 2.54 mm ({side} side, hand-solder)", HEADER_FOOTPRINT, None, sheet)


def add_header(nets: dict) -> dict:
    """Append the J10 pins to the board's NETS (every header net must already exist on the board)."""
    for pin, net in HEADER_PINS.items():
        assert net in nets, f"header net {net} has no other pin on this board"
        nets[net].append((HEADER_REF, pin))
    return nets


# The pin table as a sheet note (both Header sheets), one line per entry: KiCad's font is proportional, so no columns.
HEADER_NOTE = (
    "J10 pin map (hardware/ARCHITECTURE.md):\n"
    "pins 1, 2: SYS, power board -> main board: system rail (cell-referred, 1.5-5.5 V), at least 1 A\n"
    "pins 3, 4, 7, 8, 11, 12, 15, 16: GND (a GND row beside every signal row)\n"
    "pins 5, 6: USB_VBUS, main -> power: USB-C VBUS to ACFET1 drain and VAC1\n"
    "pins 9, 10: USB_DP, USB_DN, main -> power: BC1.2 detection only (BQ25798 D+/D-)\n"
    "pins 13, 14: CHG_SDA, CHG_SCL: charger I2C (address 0x6B), 10k pull-ups on the main board\n"
    "pin 17: CHG_INT, power -> main: open drain, 10k pull-up on the main board\n"
    "pin 18: CHG_CE, main -> power: active low, 100k pull-up on the main board = charge off\n"
    "The power board has no 3.3 V. A bought charger module that supplies SYS and GND can replace it.")
