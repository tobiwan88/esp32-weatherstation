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

# J10 = J_PWR: keyed 2 x 10, 2.54 mm, through-hole, hand-soldered (no JLC fee). Odd pins = row A, even pins = row B.
# Pin HEADER_KEY is pulled from the main board's male header and its hole is blocked in the power board's socket; it has
# no net. Order (engineer 2026-11-21, hardware/tools/header_check.py): SYS on column 1, USB_VBUS on column 10, the key in
# column 2 and every signal in columns 4-8 with a GND pair between signal pairs. Then a 180 degree rotation, a mirror
# about either axis or a one-column offset puts a pin onto the blocked hole (cannot mate), and the remaining one-row
# offsets of an unshrouded header put SYS/USB_VBUS only onto GND or each other, never onto a signal pin.
HEADER_REF = "J10"
HEADER_COLS = 10
HEADER_KEY = 3
HEADER_SYMBOL = "Connector_Generic:Conn_02x10_Odd_Even"
HEADER_FOOTPRINT = "Connector_PinHeader_2.54mm:PinHeader_2x10_P2.54mm_Vertical"
HEADER_PINS = {
    "1": "SYS", "2": "SYS",
    "4": "GND",                      # pin 3 = key (removed, hole blocked)
    "5": "GND", "6": "GND",
    "7": "USB_DP", "8": "USB_DN",
    "9": "GND", "10": "GND",
    "11": "CHG_SDA", "12": "CHG_SCL",
    "13": "GND", "14": "GND",
    "15": "CHG_INT", "16": "CHG_CE",
    "17": "GND", "18": "GND",
    "19": "USB_VBUS", "20": "USB_VBUS",
}
HEADER_NETS = sorted(set(HEADER_PINS.values()))


def header_part(sheet: str, side: str) -> tuple:
    """PARTS entry of J10 on one board (side = 'power' or 'main'); same footprint on both so the holes line up."""
    kind = "male pins, pin 3 pulled" if side == "main" else "socket, hole 3 blocked"
    return (HEADER_SYMBOL, f"J_PWR 2x10 keyed 2.54 mm ({side} side: {kind}; hand-solder)", HEADER_FOOTPRINT, None, sheet)


def add_header(nets: dict) -> dict:
    """Append the J10 pins to the board's NETS (every header net must already exist on the board)."""
    for pin, net in HEADER_PINS.items():
        assert net in nets, f"header net {net} has no other pin on this board"
        nets[net].append((HEADER_REF, pin))
    return nets


# The pin table as a sheet note (beside J10 on both boards), one line per entry: KiCad's font is proportional, so no columns.
HEADER_NOTE = (
    "J10 pin map (hardware/ARCHITECTURE.md), keyed 2x10: pin 3 is the key (no pin, hole blocked)\n"
    "pins 1, 2: SYS, power board -> main board: system rail (cell-referred, 1.8-5.5 V), at least 1 A\n"
    "pins 4, 5, 6, 9, 10, 13, 14, 17, 18: GND (a GND pair between every signal pair)\n"
    "pins 7, 8: USB_DP, USB_DN, main -> power: BC1.2 detection only (BQ25798 D+/D-)\n"
    "pins 11, 12: CHG_SDA, CHG_SCL: charger I2C (address 0x6B), 10k pull-ups on the main board\n"
    "pin 15: CHG_INT, power -> main: open drain, 10k pull-up on the main board\n"
    "pin 16: CHG_CE, main -> power: active low, pulled high (charge off) until firmware drives it low\n"
    "pins 19, 20: USB_VBUS, main -> power: USB-C VBUS to ACFET1 drain and VAC1\n"
    "Rotated, mirrored or column-shifted plugs hit the key (tools/header_check.py). No 3.3 V on the power board.")
