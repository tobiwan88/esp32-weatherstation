"""power-board layout: outline, placement, GND planes, keepouts, hand-drawn critical copper (run with $KICAD_PYTHON).

Builds hardware/power-board/power-board.kicad_pcb from the schematic netlist through the shared engine gen/pcbkit.py
(adapted from gen/pcb_v1.py). Positions in mm from the board's top-left corner, top view. Floorplan, stack geometry
and sources: power-board/BOARD.md "Layout". The board sits UNDER the main board in the stack (same 50 x 50 outline,
same holes, J10 at the same top-view position); tools/stack_check.py proves the alignment.
After the shared engine has placed the parts, gen/power_copper.py draws the locked critical copper (BQ25798 power
stage, charge trunks, BC1.2 pair, U3 south band, edge stitching); tools/route_power.sh autoroutes the rest.
Usage: power_pcb.py design.net board.kicad_pcb classes.json   (tools/build_board.sh power-board)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pcbkit  # noqa: E402
import power_copper  # noqa: E402
from stack import HOLES, J10_AT, W, H  # noqa: E402,F401  (shared stack geometry: holes and J10 on both boards)

REGIONS = "charger=18,8,42,36 cell=0,0,22,36 header=12,30,46,46"
TITLE, TITLE_AT, DRU = "weatherstation power board", (25.0, 47.0), "power-board.kicad_dru"

# Floorplan (BOARD.md): cell corner top-left (J6 on the left edge, TH1 beside it, HY2112 and its FETs, F1); PV input on
# the left edge below it (J5, TVS, choke); charger U3 centre-right with L1 above it, its heat under the main board's
# warm right half; J10 socket along the bottom (pin 1 = SYS at the right end, USB_VBUS at the left end), so SYS leaves
# U3's SYS side (right) and USB_VBUS reaches the ACFET pair on the left. J5/J6 are hand-soldered THT with the bodies on
# the back (weatherstation-v1 decision 2026-11-01): the cables leave below the stack, not into the 11 mm board gap.
UX3, UY3 = 30.0, 21.5  # BQ25798 centre
FIXED = {
    "J10": J10_AT,                                 # 2x10 socket, hole 3 blocked (key), F.Cu, unmirrored
    "U3": (UX3, UY3, 0),
    # cell corner as on weatherstation-v1 (pinned there 2026-11-03 around the same H1 hole)
    "J6": (3.3, 14.0, 270, "B"), "U6": (8.8, 14.0, 0),
    "F1": (7.55, 10.05, 0), "M60": (12.688, 10.55, 0), "C60": (11.438, 14.5, -90), "R60": (8.688, 16.25, 0),
    # PV input on the left edge below the cell corner
    "J5": (3.3, 27.0, 270, "B"),
    # CE pull-up below J10.16 (routing 2026-11-22): at U3.13 it blocked the escape vias of the bottom-row pins
    "R23": (24.22, 38.4, 0),
    # QON test pad and STAT LED pinned at their placement positions (R19 0.15 mm lower, clear of C2) so the area
    # under U3's bottom row stays free for the escape vias (routing 2026-11-22)
    "TP3": (25.55, 26.15, 0), "R19": (27.8, 27.4, -90), "D2": (26.8, 29.51, 0),
}
# BQ25798 power stage and its ring of small parts, offsets from U3 (weatherstation-v1 CHARGER, SLUSDV2C 8.4.1 items 1-5,
# Figure 8-21; routed and DRC clean on v1): 0402 PMID/SYS caps on top of the PMID-SW1-GND-SW2-SYS pin row sharing the
# GND pin, L1 above them (SW1/SW2 reach it through vias under the IC), bulk caps in a column each side, REGN/BTST1/VBUS
# 100 nF on the left, BAT cap, PROG, BTST2, ILIM, TS, BATP and SDRV on the right, RBFET1 M2 at the top of the VBUS
# channel, PV_IN cap C2 at the end of the VAC2 sense line.
CHARGER = {
    "C9": (-0.95, -3.0, 0), "C13": (0.95, -3.0, 180), "L1": (0.0, -5.6, 0),
    "C10": (-3.6, -3.55, 180), "C11": (-3.6, -5.55, 180), "C12": (-3.6, -7.55, 180),
    "C14": (3.6, -3.55, 0), "C15": (3.6, -5.55, 0), "C16": (3.6, -7.55, 0), "C17": (3.6, -10.05, 0), "C20": (8.1, -4.1, 0),
    "C18": (3.6, -12.55, 0),
    "C19": (5.6, -1.35, 0), "C21": (8.3, -1.35, 0), "R14": (4.7, 0.6, 0), "R13": (7.2, 0.45, 0),
    "C4": (4.7, 2.15, 0), "R16": (4.6, 3.45, 0), "R15": (7.05, 3.7, 180), "R18": (4.9, 5.3, 0), "R17": (7.5, 5.3, 180),
    "C6": (-3.8, -1.15, 180), "C3": (-4.4, 0.1, 180), "C5": (-4.4, 2.0, 180),  # C5 0805 since review C (was 0603 at 1.75)
    "M2": (-1.4, -11.05, -90),
    # PV_IN (VAC2) cap at the pin, left of the bottom row (routing 2026-11-22: below U3 it sat in the south band)
    "C2": (-2.55, 3.95, 270),
}
BLOCKS = [("U3", CHARGER)]
# escape bands for U3's signal pins (weatherstation-v1): no part there, so every pin can fan out when it is routed;
# plus the B.Cu-free VBUS channel and the hand copper of the power stage (pours under C9-C16, drawn at routing time)
RESERVED = [("U3", (2.4, -0.55, 4.3, 2.7)), ("U3", (-2.7, 2.4, 2.7, 4.3)), ("U3", (-4.3, 0.25, -2.4, 2.7))]

NEAR = [
    # inputs first (they need the edge): PV TVS at the connector, then the choke
    ("D1", [("1", "J5", "1"), ("2", "J5", "2")]), ("L3", [("1", "D1", "1"), ("4", "D1", "2")]),
    # charger VBUS bulk caps beside the VBUS 100 nF, pads aligned
    ("C7", [("1", "C6", "1"), ("2", "C6", "2")]), ("C8", [("1", "C7", "1"), ("2", "C7", "2")]),
    # input FET pairs (BQ25798 figure 8-2): RBFET2 at the VBUS pin, ACFET2 beside it; ACFET1 beside RBFET1 M2
    ("M4", [("3", "U3", "2")]), ("M3", [("2", "M4", "2")]), ("M1", [("2", "M2", "2")]),
    ("R11", [("1", "M1", "1")]), ("R12", [("1", "M3", "1")]), ("C1", [("1", "M1", "3")]),
    # (CE pull-up R23, QON pad TP3 and the STAT LED R19/D2 are pinned in FIXED: the south band routing needs them there)
    # battery protection: NTC at the cell connector (senses the cell side), charge FET beside the discharge FET
    ("TH1", [("2", "J6", "2")]), ("M61", [("3", "M60", "3")]), ("R61", [("1", "U6", "2")]),
]
TIGHT = {"TH1", "F1", "M60", "M61", "C60", "R60", "R61", "C7", "C8"}
HALO = 0.35

SILK = [  # polarity and key marks (review B19/B20, ARCHITECTURE.md J10)
    ("CELL 1+ 2-", 7.2, 18.6, 0.8, "F"),
    ("PV 1+ 2-", 4.6, 31.0, 0.8, "B"), ("CELL 1+ 2-", 4.6, 18.3, 0.8, "B"),
]


def j10_marks():
    """KEY 3 above pin 3, SYS below pin 2: from the J10 position (rotation 270: pin 1 at the right end)."""
    x, y = J10_AT[:2]
    return [("KEY 3", x - 2.54, y - 2.6, 0.8, "F"), ("SYS", x, y + 4.75, 0.8, "F")]


SILK += j10_marks()


def KEEPOUTS(put, ctx):
    """No extra rule areas on the power board: L1 carries its own SW1/SW2 tracks and the charger GND vias under it
    (SLUSDV2C 8.4.1 item 2, engineer decision 2026-11-02 on v1); the holes get theirs from pcbkit."""


if __name__ == "__main__":
    pcbkit.build(sys.modules[__name__])
    power_copper.draw(sys.argv[2], W, H)
