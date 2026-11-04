"""weatherstation-v1 board: outline, placement, GND planes, keepouts (run with $KICAD_PYTHON, Python 3.9).

Builds hardware/weatherstation-v1/weatherstation-v1.kicad_pcb from the schematic netlist. Positions in mm from the
board's top-left corner. Big parts are placed by hand (FIXED, from the floorplan in BOARD.md); every other part is
placed by `place_near`: the free spot (courtyards never overlap) where its named pads are closest to the pins they
serve (NEAR, in priority order: critical blocks first). Routing is a separate step (tools/route_krt.sh).
Usage: pcb_v1.py design.net board.kicad_pcb classes.json   (classes.json = board.yaml net_classes, see tools/build_pcb.sh)
"""

import json
import math
import os
import shutil
import sys
from pathlib import Path

import pcbnew

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "tools"))
from pcb_from_netlist import parse  # noqa: E402
from write_project import write  # noqa: E402

W0 = H0 = 50.0  # floorplan drawn for 50 x 50; PCB_W/PCB_H grow it (extra width right of x 28, extra height below y 20)
W, H = float(os.environ.get("PCB_W", W0)), float(os.environ.get("PCB_H", H0))
OX, OY = 100.0, 100.0  # board origin on the page
mm = pcbnew.FromMM
LIBS = {"weatherstation": HERE / "lib" / "weatherstation.pretty"}

# Floorplan (REQUIREMENTS 4, 4a, 4b): module top centre with the antenna over the top edge (its keepout lies off the
# board); battery block top-left (J6, TH1 at the cell connector, protection); debug corner top-right (J7, RESET, BOOT);
# heat corner bottom-left (USB-C and PV inputs, BQ25798, TPS63802, TPS61023); sensors bottom-right (J2, J3, J8,
# SCD41), opposite the heat corner. M3 holes in the four corners.
UX, UY = 25.0, 6.75   # module centre: antenna keepout (local y < -6.75) ends at the top edge
FIXED = {  # ref: (x, y, rotation[, "B"]); hand-soldered THT connectors sit on the back (decision 2026-11-01)
    "U1": (UX, UY, 0),
    "H1": (3.5, 3.5, 0), "H2": (W - 3.5, 3.5, 0), "H3": (3.5, H - 3.5, 0), "H4": (W - 3.5, H - 3.5, 0),
    # battery: cell connector on the left edge, NTC beside it
    "J6": (3.3, 14.0, 270, "B"), "U6": (8.8, 14.0, 0),
    # pinned 2026-11-03 at their NEAR positions (the BAT_PACK trunk lands next to F1.2 and M60)
    "F1": (7.55, 10.25, 0), "M60": (12.688, 10.55, 0), "C60": (11.438, 14.5, -90), "R60": (8.688, 16.25, 0),
    # debug corner
    "J7": (48.0, 16.5, 0, "B"), "JP1": (40.5, 10.3, 0), "JP2": (40.5, 12.8, 0),  # tweezer pads
    # inputs: USB-C opening out of the left edge, PV connector on the bottom edge
    "J1": (3.4, 28.5, 270), "J5": (3.3, 40.5, 270, "B"),
    # charger (its power stage is CHARGER below); buck-boost right of it, boost below, each with room for its loop
    "U3": (16.5, 35.5, 0),
    "U2": (28.3, 41.5, 0), "U7": (23.0, 46.2, 0), "M1": (7.4, 20.012, 90), "R11": (4.425, 21.175, -90), "R12": (23.675, 23.655, -90), "R20": (23.31, 21.25, 180), "R49": (14.25, 7.84, 180), "R48": (14.25, 6.05, 180),
    # sensors
    # J2's front pads sit in the free column between the charger and U8, not inside the charger block
    "U8": (40.0, 30.0, 0), "J8": (47.4, 37.0, 270, "B"), "J2": (32.2, 29.5, 0, "B"),
    "J3": (38.6, 46.65, 0),  # mounting pads 0.3 mm inside the bottom edge
    # charger STAT LED (debug only) in the free strip below the REGN cap; by rule it landed at the far left edge
    "D2": (11.0, 39.0, 0), "R19": (11.6, 40.55, 180),
}

FIXED = {r: (p[0] + (W - W0 if p[0] > 28 else 0), p[1] + (H - H0 if p[1] > 20 else 0), *p[2:])
         if not r.startswith("H") and r != "U1" else p for r, p in FIXED.items()}

# BQ25798 power stage drawn by hand (SLUSDV2C 8.4.1/8.4.2, priority order): 0402 PMID and SYS caps on top of the
# PMID-SW1-GND-SW2-SYS pin row sharing the GND pin; SW1/SW2 drop through vias under the IC to B.Cu and come back up at
# the inductor above the caps; bulk caps in a column beside each, joined by F.Cu pours. Offsets from U3's centre (mm).
CHARGER = {
    "C9": (-0.95, -3.0, 0), "C13": (0.95, -3.0, 180), "L1": (0.0, -5.6, 0),
    "C10": (-3.6, -3.55, 180), "C11": (-3.6, -5.55, 180), "C12": (-3.6, -7.55, 180),
    "C14": (3.6, -3.55, 0), "C15": (3.6, -5.55, 0), "C16": (3.6, -7.55, 0), "C17": (3.6, -10.05, 0), "C20": (8.1, -4.1, 0),
    "C18": (3.6, -12.55, 0),
    # small parts, one ring around the pins in pin order so every pin fans out without crossing (items 3-5, 7):
    # right: BAT cap beside the BAT pins, then PROG, BTST2, ILIM, TS rows; BATP sense and SDRV cap further out
    "C19": (5.6, -1.35, 0), "C21": (8.3, -1.35, 0), "R14": (4.7, 0.6, 0), "R13": (7.2, 0.45, 0),
    "C4": (4.7, 2.15, 0), "R16": (4.6, 3.45, 0), "R15": (7.05, 3.7, 180), "R18": (4.9, 5.3, 0), "R17": (7.5, 5.3, 180),
    # left: VBUS 100 nF at the VBUS pins, BTST1 cap, REGN cap (2 GND vias to the plane, item 3)
    "C6": (-3.45, -1.15, 180), "C3": (-4.4, 0.1, 180), "C5": (-4.4, 1.75, 180),
    # ACFET1/RBFET1 output FET M2: its VBUS pin at the top of the hand-drawn VBUS channel
    "M2": (-1.4, -11.05, -90),
    # PV input cap C2 at the end of the VAC2 sense line below the escape band
    "C2": (-0.38, 6.7, 180),
}
_U3 = FIXED["U3"]
FIXED.update({r: (_U3[0] + dx, _U3[1] + dy, deg) for r, (dx, dy, deg) in CHARGER.items()})
# TPS63802 (SLVSEU9D 12.1/Figure 12-1): input cap across both VIN pins above, inductor right of the L1/L2 pins, output
# cap at VOUT/GND, FB divider at the FB pin on the far side from the switch pins. Offsets from U2's centre (mm).
BUCKBOOST = {"C40": (-1.0, -2.6, 180), "L4": (2.75, 0.0, -90), "C41": (0.45, 2.82, 0),
             "R53": (-3.05, 0.5, 180), "R52": (-3.05, 2.1, 0)}
# +3V3 output: VOUT pin to the output cap, output cap to the top of the FB divider (the router left them an island)
RAILS_COPPER = {"pours": [], "tracks": [
    ("+3V3", "F", 0.4, [(0.75, 1.0), (0.0, 1.75), (-0.5, 2.25), (-0.5, 2.5)]),
    ("+3V3", "F", 0.3, [(-0.5, 2.93), (-3.88, 2.93), (-3.88, 2.4)]),
    # TPS61023 FB node (U7.1 to the divider) and EN pull-down: local links the router kept losing to the power runs
    ("/Rails/GAS_FB", "F", 0.2, [(-5.95, 4.2), (-5.95, 2.975)]), ("/Rails/GAS_FB", "F", 0.2, [(-7.5, 2.975), (-5.95, 2.975)]),
    # EN leaves through a via between FB and the input cap, B.Cu down to the pull-down R45 (frees VIN for C44)
    ("/MCU/BOOST_EN", "F", 0.2, [(-6.015, 4.7), (-6.475, 4.7), (-6.775, 4.225)]), ("/MCU/BOOST_EN", "B", 0.2, [(-6.775, 4.225), (-6.975, 4.425), (-6.975, 6.225)]),
    ("/MCU/BOOST_EN", "F", 0.2, [(-6.975, 6.225), (-7.5, 6.95)]),
    # boost input: C44 (SYS pad toward the IC) to VIN, VIN straight down to L5
    ("SYS", "F", 0.35, [(-7.1, 5.2), (-6.1, 5.2)]), ("SYS", "F", 0.4, [(-6.015, 5.4), (-6.015, 6.2)]),
    # buck-boost VIN pins 1 and 10 joined above the GND/L1 pins, C40 dropped into the link
    # buck-boost FB pin straight to the divider tap R53/R52 (TI: short FB node)
    ("/Rails/FB", "F", 0.2, [(-1.0, 0.5), (-2.2, 0.5), (-2.2, 2.1)]),
    ("SYS", "F", 0.3, [(-0.9, -1.0), (0.75, -1.0)]), ("SYS", "F", 0.4, [(-0.225, -2.6), (-0.225, -1.0)])],
    "vias": [("/MCU/BOOST_EN", -6.775, 4.225),
             ("/MCU/BOOST_EN", -6.975, 6.225)]}
_U2 = FIXED["U2"]
FIXED.update({r: (_U2[0] + dx, _U2[1] + dy, deg) for r, (dx, dy, deg) in BUCKBOOST.items()})
# TPS61023 (SLVSF14B 10.2/Figure 10-1): inductor below the IC from the VIN pin to the SW pin, output cap at VOUT/GND,
# input cap left of VIN, FB divider above the FB pin. Offsets from U7's centre (mm).
BOOST = {"L5": (0.25, 2.3, 0), "C45": (2.863, 0.0, -90), "C44": (-2.8, 0.5, 180),
         "R43": (-0.65, -2.55, -90), "R44": (-2.2, -2.55, 90), "R45": (-2.713, 2.25, 180)}
_U7 = FIXED["U7"]
FIXED.update({r: (_U7[0] + dx, _U7[1] + dy, deg) for r, (dx, dy, deg) in BOOST.items()})
# USB 2.0 pair drawn by hand: J1 row B7 A6 A7 B6 = DN DP DN DP. DN joins on F.Cu, DP drops through two vias and
# crosses under it on B.Cu to a via beside U4 (rotated so DN/DP sit left/right on both rows, flow-through), then
# straight up to the series resistors at U1. CC1 is enclosed by the pair: via to B.Cu just outside the shell keepout,
# R9 below R10. C1's GND pad faces U4's GND pin. The diff-pair router finds no launch room here (2026-11-02).
FIXED.update({r: (x, y + (H - H0 if y > 20 else 0), d) for r, (x, y, d) in {
    "U4": (10.945, 24.5, 270), "C1": (10.945, 21.115, 270), "R10": (9.695, 30.75, 270), "R9": (9.695, 32.875, 270),
    "R33": (14.25, 16.73, 0), "R32": (14.25, 18.0, 0)}.items()})
_DN, _DP, _CC1, _VB = "/USB_DN", "/USB_DP", "/Input/CC1", "USB_VBUS"
USB_COPPER = {  # absolute board mm (the J1 block does not move with PCB_W/PCB_H)
    "pours": [],
    "tracks": [
        (_DN, "F", 0.2, [(7.9, 27.745), (9.175, 27.745)]), (_DN, "F", 0.2, [(7.9, 28.745), (9.175, 28.745)]),
        (_DN, "F", 0.2, [(9.175, 27.745), (9.175, 28.745)]),
        (_DN, "F", 0.2, [(9.175, 27.745), (9.175, 26.875), (9.995, 26.055)]),
        (_DN, "F", 0.27, [(9.995, 23.365), (9.995, 19.975), (13.245, 16.725), (13.745, 16.725)]),
        (_DP, "F", 0.2, [(7.9, 28.245), (8.625, 28.245)]), (_DP, "F", 0.2, [(7.9, 29.245), (8.625, 29.245)]),
        (_DP, "B", 0.2, [(8.625, 29.245), (8.625, 28.245), (10.0, 28.245), (12.15, 26.095), (12.525, 26.475)]),
        (_DP, "F", 0.2, [(12.525, 26.475), (12.075, 26.025)]),
        (_DP, "F", 0.27, [(11.895, 23.365), (11.895, 19.575), (13.475, 17.995), (13.745, 17.995)]),
        # USBLC6 flow-through: each line runs under U4 from pin to pin (pads 3/4 and 1/6 are separate pads in KiCad)
        (_DN, "F", 0.27, [(9.995, 23.365), (9.995, 26.055)]), (_DP, "F", 0.27, [(11.895, 23.365), (11.895, 26.025)]),
        ("/MCU/ESP_DN", "F", 0.27, [(14.765, 16.725), (16.2, 16.725)]),
        ("/MCU/ESP_DP", "F", 0.27, [(14.765, 17.995), (16.2, 17.995)]),
        (_CC1, "F", 0.2, [(7.9, 27.245), (8.625, 27.175)]),
        (_CC1, "B", 0.2, [(8.625, 27.175), (7.875, 27.925), (7.875, 31.415), (8.825, 32.365)]),
        (_CC1, "F", 0.2, [(8.825, 32.365), (9.695, 32.365)]),
        ("/Input/CC2", "F", 0.2, [(7.9, 30.25), (9.5, 30.25)]),  # B5 straight to R10 (left open by the router)
        (_VB, "F", 0.3, [(10.945, 20.635), (10.945, 19.925)]),
        ("GND", "F", 0.3, [(10.945, 21.595), (10.945, 23.365)]),
        # BC1.2 detection stubs to U3 pins 6/7: vias under U3's body (clear of the SW1 vias), B.Cu to the pair
        (_DP, "F", 0.2, [(14.6, 35.9), (15.3, 35.85)]), (_DN, "F", 0.2, [(14.6, 36.3), (15.0, 36.3), (15.3, 36.6)]),
        (_DP, "B", 0.2, [(12.525, 26.475), (12.9, 26.85), (12.9, 34.8), (13.95, 35.85), (15.3, 35.85)]),
        (_DN, "F", 0.2, [(9.175, 28.745), (9.25, 28.745)]),
        (_DN, "B", 0.2, [(9.25, 28.745), (9.6, 29.095), (9.6, 33.9), (12.3, 36.6), (15.3, 36.6)]),
    ],
    "vias": [(_DP, 8.625, 28.245), (_DP, 8.625, 29.245), (_DP, 12.525, 26.475), (_CC1, 8.625, 27.175),
             (_CC1, 8.825, 32.365), (_VB, 10.945, 19.925), ("GND", 10.945, 22.275),
             (_DP, 15.3, 35.85), (_DN, 15.3, 36.6), (_DN, 9.25, 28.745)],
}
# Charge trunks at class width, absolute board mm (the autorouter necks these down to 0.2 mm in the crowded middle):
# BAT_PACK from the bulk cap C20 on B.Cu diagonally under U1's pin column to two 0.6/0.3 vias, up to the fuse F1;
# USB_VBUS from J1's A4/B9 pad right of the shell keepout, between M1 and U4, to M1's source.
TRUNKS = {"pours": [], "tracks": [
    ("BAT_PACK", "F", 0.5, [(23.275, 30.125), (24.075, 30.125)]), ("BAT_PACK", "F", 0.65, [(23.655, 30.125), (23.655, 30.9)]),
    ("BAT_PACK", "B", 0.65, [(23.275, 30.125), (24.075, 30.125)]),
    ("BAT_PACK", "B", 0.65, [(23.675, 30.125), (23.675, 23.475), (12.475, 12.275), (10.775, 12.275)]),
    ("BAT_PACK", "F", 0.5, [(10.775, 12.275), (9.875, 11.575)]),
    ("USB_VBUS", "F", 0.5, [(7.9, 26.05), (8.85, 26.05), (9.175, 25.725)]),
    ("USB_VBUS", "F", 0.65, [(9.175, 25.725), (9.175, 20.0)]),
    ("USB_VBUS", "F", 0.5, [(9.175, 20.0), (7.4, 19.1)]),
    # U3 bottom row (0.4 mm pitch), pre-routed as one nested B.Cu bundle (the router left these open in every
    # trial). ACDRV1 drops to B.Cu and runs west, up the left edge under J1 (B.Cu, screened) to R11. ACDRV2, CE, SDA,
    # SCL drop through staggered vias and run east on B.Cu at y 38.35/38.95/39.6/40.25, then turn north at x
    # 26.0/26.6/27.2/27.8 (inner lane turns first, so nothing crosses): ACDRV2 to R12, CE to R20 between R12 and R20,
    # SDA/SCL under U1 to vias beside its IO pins.
    ("/Charger/ACDRV1", "F", 0.2, [(15.9, 37.6), (15.9, 39.6)]),
    ("/Charger/ACDRV1", "B", 0.2, [(15.9, 39.6), (14.95, 39.6), (12.65, 37.3), (1.3, 37.3), (0.9, 36.9), (0.9, 23.4),
                                   (1.3, 23.0), (4.43, 23.0)]),
    ("/Charger/ACDRV1", "F", 0.2, [(4.43, 23.0), (4.43, 22.1)]),
    ("/Charger/ACDRV2", "F", 0.2, [(15.5, 37.6), (15.5, 38.0), (15.15, 38.35)]),
    ("/Charger/ACDRV2", "B", 0.2, [(15.15, 38.35), (26.0, 38.35), (26.0, 25.95), (24.65, 25.3)]),
    ("/Charger/ACDRV2", "F", 0.2, [(24.65, 25.3), (24.0, 24.65)]),
    ("/Charger/CHG_CE", "F", 0.2, [(16.7, 37.6), (16.7, 37.85), (16.4, 38.15), (16.4, 38.95)]),
    ("/Charger/CHG_CE", "B", 0.2, [(16.4, 38.95), (26.6, 38.95), (26.6, 22.45), (25.9, 21.75), (24.9, 21.75)]),
    ("/Charger/CHG_CE", "F", 0.2, [(24.9, 21.75), (24.6, 22.0), (22.8, 22.0), (22.8, 21.3)]),
    ("/Charger/CHG_SDA", "F", 0.2, [(17.5, 37.6), (17.5, 39.6)]),
    ("/Charger/CHG_SDA", "B", 0.2, [(17.5, 39.6), (27.2, 39.6), (27.2, 2.76), (32.3, 2.76)]),
    ("/Charger/CHG_SDA", "F", 0.2, [(32.3, 2.76), (33.3, 2.76)]),
    ("/Charger/CHG_SCL", "F", 0.2, [(17.1, 37.6), (17.1, 38.35), (16.95, 38.5), (16.95, 40.25)]),
    ("/Charger/CHG_SCL", "B", 0.2, [(16.95, 40.25), (27.8, 40.25), (27.8, 4.03), (32.3, 4.03)]),
    ("/Charger/CHG_SCL", "F", 0.2, [(32.3, 4.03), (33.3, 4.03)]),
    # REGN: C5 down past D2 to R19 (flipped, REGN pad toward C5), B.Cu lane east below the bundle to R17/R15
    ("REGN", "F", 0.25, [(12.75, 37.5), (12.75, 40.55), (12.85, 41.0)]), ("REGN", "F", 0.25, [(12.75, 40.55), (12.2, 40.55)]),
    ("REGN", "B", 0.25, [(12.85, 41.0), (13.25, 41.4), (24.85, 41.4), (25.25, 41.0)]),
    ("REGN", "F", 0.25, [(25.25, 41.0), (24.6, 40.8)]), ("REGN", "F", 0.25, [(24.5, 40.6), (24.45, 39.4)]),
    ("/Charger/LED_A", "F", 0.2, [(11.6, 39.3), (11.1, 40.35)]),
    # TS divider: R18 (to GND) and R17 (to REGN) joined above R18's GND pad, below the R15/R16 row
    ("/Battery/TS", "F", 0.2, [(20.6, 40.45), (21.05, 40.0), (23.45, 40.0), (23.49, 40.55)]),
    # GND of the BAT bulk cap C20 and the SDRV cap C21: one plane via between them (B.Cu lanes boxed them in)
    ("GND", "F", 0.3, [(25.55, 32.0), (25.45, 33.0), (25.3, 34.0)]),
    # PM_SETIN leaves R49 through a via between the R48 and R49 rows (the router dropped its via into the pad)
    ("/Sensors/PM_SETIN", "F", 0.2, [(13.74, 7.84), (13.74, 7.03)]),
    ("/Sensors/PM_RXIN", "F", 0.2, [(13.74, 6.05), (12.95, 6.05)]),  # same for R48, via to its left
], "vias": [("BAT_PACK", 23.275, 30.125, 0.6, 0.3), ("BAT_PACK", 24.075, 30.125, 0.6, 0.3),
            ("BAT_PACK", 10.775, 12.275, 0.6, 0.3), ("/Charger/ACDRV1", 15.9, 39.6), ("/Charger/ACDRV1", 4.43, 23.0),
            ("/Charger/ACDRV2", 15.15, 38.35), ("/Charger/ACDRV2", 24.65, 25.3), ("REGN", 12.85, 41.0),
            ("REGN", 25.25, 41.0), ("/Charger/CHG_CE", 16.4, 38.95), ("/Charger/CHG_CE", 24.9, 21.75),
            ("/Charger/CHG_SDA", 17.5, 39.6), ("/Charger/CHG_SDA", 32.3, 2.76),
            ("/Charger/CHG_SCL", 16.95, 40.25), ("/Charger/CHG_SCL", 32.3, 4.03), ("GND", 25.45, 33.0), ("/Sensors/PM_SETIN", 13.74, 7.03),
            ("/Sensors/PM_RXIN", 12.95, 6.05)]}
# the block sits below y 20, so it moves down with PCB_H like FIXED (points above y 20 stay with U1)
_sy = lambda y: y + (H - H0 if y > 20 else 0)  # noqa: E731
USB_COPPER = {"pours": [], "tracks": [(n, sd, w, [(x, _sy(y)) for x, y in pts]) for n, sd, w, pts in USB_COPPER["tracks"]],
              "vias": [(n, x, _sy(y)) for n, x, y in USB_COPPER["vias"]]}


def _mirror(pts):
    return [(-x, y) for x, y in pts]


# bottom edge raised to -2.8 left of x -1.75 (still covers the C10/C14 pads): a channel above the pin row for STAT
# (left) and SDRV (right, mirrored SYS pour)
_PMID = [(-1.0, -1.3), (-0.8, -1.3), (-0.8, -2.45), (-1.1, -2.45), (-1.1, -3.5), (-1.6, -3.5), (-1.6, -8.4),
         (-3.25, -8.4), (-3.25, -2.8), (-1.75, -2.8), (-1.75, -2.3), (-1.0, -2.3)]
_SW1_B = [(-0.45, 0.25), (-0.45, -0.55), (-1.0, -1.1), (-1.0, -7.85)]
# U3 bottom row (net, pin x, bend y, via x): ACDRV2, ACDRV1, CE, SCL, SDA, TS (pin 12 QON unused)
_FAN = [("/Charger/ACDRV2", -1.0, 2.7, -1.1), ("/Charger/ACDRV1", -0.6, 2.6, -0.3), ("/Charger/CHG_CE", 0.2, 2.6, 0.5),
        ("/Charger/CHG_SCL", 0.6, 2.5, 1.3), ("/Charger/CHG_SDA", 1.0, 2.4, 2.1), ("/Battery/TS", 1.85, 2.6, 2.9)]
# off by default: trial 7 (2026-11-03) closed the bottom-row nets but the via row cut the channel under U3 (10 open
# with it, 6 without); PCB_FAN=1 brings it back for experiments
_FAN = _FAN if os.environ.get("PCB_FAN", "0") == "1" else []
CHARGER_COPPER = {  # same offsets; tracks (net, layer, width, points), vias (net, x, y), pours (net, layer, polygon)
    "pours": [
        ("PMID", "F", _PMID), ("SYS", "F", _mirror(_PMID)),
        ("GND", "F", [(-0.1, -1.3), (0.1, -1.3), (0.1, -2.6), (0.8, -2.6), (0.8, -3.4), (0.3, -3.4), (0.3, -4.95),
                      (-0.3, -4.95), (-0.3, -3.4), (-0.8, -3.4), (-0.8, -2.6), (-0.1, -2.6)]),
    ],
    "tracks": [
        ("/Charger/SW1", "F", 0.3, [(-0.45, -1.25), (-0.45, 0.25)]),
        ("/Charger/SW1", "B", 0.6, _SW1_B),
        ("/Charger/SW1", "F", 0.6, [(-1.0, -7.85), (-1.0, -7.05), (-0.95, -6.0)]),
        ("/Charger/SW2", "F", 0.3, [(0.45, -1.25), (0.45, 0.25)]),
        ("/Charger/SW2", "B", 0.6, _mirror(_SW1_B)),
        ("/Charger/SW2", "F", 0.6, [(1.0, -7.85), (1.0, -7.05), (0.95, -6.0)]),
        # SYS bulk caps above the pour joined to it (the router left the pour island unconnected)
        ("SYS", "F", 0.65, [(2.655, -7.55), (2.655, -12.55)]),
        # VBUS pins + C6 were an island (the rest of VBUS is M2 above, C7/C8 left): via left of C6, B.Cu up the free
        # channel between the DP stub and SW1, one 0.6/0.3 via up to M2's VBUS pin. The via at C6 is 0.6/0.3 too
        # (input current up to the 1.59 A ILIM clamp); STAT runs 0.15 mm higher to make room for it.
        ("VBUS", "F", 0.4, [(-3.0, -1.95), (-2.97, -1.3)]), ("VBUS", "F", 0.3, [(-2.97, -1.15), (-1.9, -1.0)]),
        ("VBUS", "B", 0.65, [(-3.0, -1.95), (-2.4, -2.6)]), ("VBUS", "B", 0.65, [(-2.4, -2.6), (-2.4, -8.75)]),
        ("VBUS", "F", 0.5, [(-2.4, -8.75), (-2.1, -8.75), (-1.4, -9.45)]),  # one 0.6/0.3 via (KRT drops parallel-via links)
        # STAT (top-left corner pin) left above C6 in the pour channel, down beside C3/C5 to the debug LED D2
        # (pins 1 and 24 are L-shaped corner pads open toward the corner: the stubs leave through that notch)
        ("/Charger/STAT", "F", 0.2, [(-1.38, -1.9), (-2.0, -1.9), (-2.65, -2.55), (-4.75, -2.55), (-6.05, -1.25),
                                     (-6.05, 3.1), (-6.29, 3.5)]),
        # SDRV (top-right corner pin) right in the SYS pour channel, above C19, down to its 1 nF C21
        # left pins in one fan: BTST1 and REGN to their caps, VAC2 (PV_IN sense, uA) between pins 7 and 9 at the
        # 0.3 mm charge-class floor (0.15 mm each side), down past the REGN cap to C2
        ("/Charger/BTST1", "F", 0.2, [(-1.9, -0.4), (-2.9, -0.4), (-3.3, 0.0)]),
        ("REGN", "F", 0.2, [(-1.9, 0.0), (-2.55, 0.0), (-2.85, 0.3), (-2.85, 1.05), (-3.3, 1.5)]),
        ("/Charger/PV_IN", "F", 0.3, [(-1.9, 1.2), (-2.3, 1.2), (-2.65, 1.55), (-2.65, 3.1), (0.11, 5.86), (0.11, 6.45)]),
        # right column in pin order (no crossings): PROG into R14's upper pad half, BTST2 down to C4, BATP through a
        # via under the body (clear of the SW2 vias) and B.Cu to R13, ILIM down to R16, TS from the corner pad's
        # inner arm down to R18, INT to a via for its long run to the MCU; BAT pins to the BAT cap at 0.4 mm
        ("/Charger/PROG", "F", 0.2, [(1.9, 0.0), (3.0, 0.0), (3.25, 0.25), (3.5, 0.25)]),
        ("/Charger/BTST2", "F", 0.2, [(1.9, 0.4), (2.7, 0.4), (3.1, 0.8), (3.1, 1.7), (3.45, 2.05)]),
        ("/Charger/BATP", "F", 0.2, [(1.9, 0.8), (1.25, 0.8), (1.1, 0.65)]),
        ("/Charger/BATP", "B", 0.2, [(1.1, 0.65), (1.7, 1.25), (7.8, 1.25)]),
        ("/Charger/BATP", "F", 0.2, [(7.8, 1.25), (7.71, 0.45)]),
        ("/Charger/ILIM", "F", 0.2, [(1.9, 1.2), (2.5, 1.2), (2.5, 2.7), (3.25, 3.45), (4.0, 3.45)]),
        ("/Battery/TS", "F", 0.2, [(1.4, 2.0), (1.4, 3.8), (2.9, 5.3), (4.0, 5.3)]),
        ("/Charger/CHG_INT", "F", 0.2, [(1.9, -0.4), (3.05, -0.5)]),
        ("BAT_PACK", "F", 0.4, [(1.9, -1.1), (4.4, -1.1)]),
        ("BAT_PACK", "F", 0.3, [(1.95, -1.2), (1.95, -0.85)]),  # BAT pins 23 and 22 joined at 0.3 mm
        # BATP sense resistor R13 to the BAT cap C19, under C19's GND pad
        ("BAT_PACK", "F", 0.3, [(6.69, 0.45), (6.69, -0.3), (4.65, -0.3), (4.65, -0.8)]),
        ("/Charger/SDRV", "F", 0.2, [(1.35, -1.9), (2.2, -1.9), (2.775, -2.325)]),
        ("/Charger/SDRV", "B", 0.2, [(2.775, -2.325), (7.775, -2.175)]),
        ("/Charger/SDRV", "F", 0.2, [(7.775, -2.175), (7.8, -1.35)]),
        # BAT cap C19 to the bulk cap C20 diagonally (SDRV dropped to B.Cu to free this path)
        ("BAT_PACK", "F", 0.65, [(4.925, -1.825), (5.825, -2.725), (7.075, -3.625)]),
    ] + [("GND", "F", 0.4, [(sx * 4.55, y), (sx * 5.45, y)]) for sx in (-1, 1) for y in (-3.55, -5.55, -7.55)]
      + [("GND", "F", 0.4, [(4.55, y), (5.45, y)]) for y in (-10.05, -12.55)]
      # bottom-row escapes to a via row (0.8 mm pitch): bends staggered so the 0.4 mm pitch fan keeps 0.15 mm
      + [(n, "F", 0.2, [(px, 1.6 if n == "/Battery/TS" else 1.9), (px, by), (vx, by + abs(vx - px)), (vx, 3.9)]) for n, px, by, vx in _FAN],
    "vias": [("/Charger/SW1", -0.45, -0.55), ("/Charger/SW1", -0.45, 0.25), ("/Charger/SW1", -1.0, -7.05),
             ("/Charger/SW1", -1.0, -7.85), ("/Charger/SW2", 0.45, -0.55), ("/Charger/SW2", 0.45, 0.25),
             ("/Charger/SW2", 1.0, -7.05), ("/Charger/SW2", 1.0, -7.85), ("GND", 0.0, -3.85), ("GND", 0.0, -4.65)]
            + [("GND", sx * 5.45, y) for sx in (-1, 1) for y in (-3.55, -5.55, -7.55)]
            + [("VBUS", -3.0, -1.95, 0.6, 0.3), ("VBUS", -2.4, -8.75, 0.6, 0.3)]
            + [("/Charger/SDRV", 2.775, -2.325), ("/Charger/SDRV", 7.775, -2.175)]
            + [("/Charger/BATP", 1.1, 0.65), ("/Charger/BATP", 7.8, 1.25), ("/Charger/CHG_INT", 3.05, -0.5)]
            + [("GND", 5.45, y) for y in (-10.05, -12.55)] + [(n, vx, 3.9) for n, px, by, vx in _FAN],
}

# ref: [(pad, target ref, target pad), ...]; the part goes where these pads are closest to their targets. Order = priority.
NEAR = [
    # inputs first (they need the edge): PV TVS at the connector, then the choke; USB ESD at the connector
    ("D1", [("1", "J5", "1"), ("2", "J5", "2")]), ("L3", [("1", "D1", "1"), ("4", "D1", "2")]), 
    # switching loops, bootstrap, FB and IC decoupling of all three converters (critical.yaml)
    # charger bulk caps: each beside the previous cap of its net, pads aligned (one short wide copper run per net)
    ("C7", [("1", "C6", "1"), ("2", "C6", "2")]), ("C8", [("1", "C7", "1"), ("2", "C7", "2")]),
    ("C46", [("1", "C45", "1"), ("2", "C45", "2")]),
    # charger input FETs (VBUS pins), gate resistors, set resistors
    ("M4", [("3", "U3", "2")]), ("M3", [("2", "M4", "2")]),

    # charger I2C/INT/CE pull-ups at the MCU end of those nets (frees U3's pin ring)
    ("R22", [("1", "U1", "18")]), ("R54", [("1", "U1", "39")]), ("R55", [("1", "U1", "38")]),
    # module (decoupling, EN RC, series resistors at the driving pin)
    ("C31", [("1", "U1", "2")]), ("C33", [("1", "U1", "3")]), ("C32", [("1", "U1", "2")]),
    ("R30", [("2", "U1", "3")]), ("C30", [("1", "U1", "2")]),
    ("R46", [("1", "U1", "10")]), ("R47", [("1", "R46", "2")]),
    ("R31", [("2", "U1", "27")]),
    ("R34", [("1", "U1", "34")]), ("R35", [("1", "U1", "35")]), ("D10", [("2", "R34", "2")]), ("D11", [("2", "R35", "2")]),
    # battery protection
    ("TH1", [("2", "J6", "2")]), ("M61", [("3", "M60", "3")]),
    ("R61", [("1", "U6", "2")]),
    # sensors: I2C ESD at the cable connectors, switched rail
    ("U5", [("1", "J3", "3"), ("3", "J3", "4")]), ("R50", [("1", "U5", "1")]), ("R51", [("1", "U5", "3")]),
    ("Q40", [("3", "U5", "5")]), ("C42", [("1", "Q40", "3")]), ("C43", [("1", "Q40", "3")]), ("C47", [("1", "U8", "19")]),
    ("Q41", [("3", "Q40", "1")]), ("R40", [("2", "Q40", "1")]), ("R41", [("2", "Q41", "1")]), ("R42", [("1", "Q41", "1")]),
    ("TP1", [("1", "C30", "1")]), ("TP2", [("1", "C40", "1")]),
]
# courtyard used for placement where the footprint's own courtyard includes an off-board keepout (local mm)
COURTYARD = {"U1": (-9.74, -6.75, 9.74, 13.45)}
# gap kept free around every NEAR part's courtyard: room for a via (0.45 mm) or a 0.4 mm power track between parts
# (critical.yaml parts and the battery corner stay tight: their connections are short pad-to-pad links)
# (ref, pad, via distance from the pad centre mm, stub width mm): U5's supply pin sits between the SDA/SCL pins, every
# route to it must enter between their tracks (routing trial 9 left 3V3_SW open there)
PAD_VIAS = [("U5", "5", 1.2, 0.4)]
HALO = float(os.environ.get("PCB_HALO", "0.35"))
TIGHT = {"C40", "C41", "L4", "R52", "R53", "C45", "L5", "C44", "R43", "R44",
         "C31", "C32", "C33", "C30", "R30", "R48", "R49", "R46", "R47", "R32", "R33",
         "TH1", "F1", "M60", "M61", "C60", "R60", "R61", "TP1"}
HOLE_KEEPOUT = 3.2  # M3 (ISO 7380 head 5.7 mm): no copper within this radius
ANTENNA_STRIP = [(UX - 16, 0), (UX + 16, 0), (UX + 16, 1.0), (UX - 16, 1.0)]  # no pours or vias beside the antenna


def v(x, y):
    return pcbnew.VECTOR2I(mm(OX + x), mm(OY + y))


def edge_poly(board, pts):
    for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]):
        seg = pcbnew.PCB_SHAPE(board)
        seg.SetShape(pcbnew.SHAPE_T_SEGMENT)
        seg.SetStart(v(x1, y1))
        seg.SetEnd(v(x2, y2))
        seg.SetLayer(pcbnew.Edge_Cuts)
        seg.SetWidth(mm(0.05))
        board.Add(seg)


def zone(board, layer, net, pts, clearance=0.25):
    z = pcbnew.ZONE(board)
    z.SetLayer(layer)
    z.SetNet(board.FindNet(net))
    z.SetLocalClearance(mm(clearance))
    z.SetMinThickness(mm(0.2))
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_THT_THERMAL)
    z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
    z.SetThermalReliefGap(mm(0.25))
    z.SetThermalReliefSpokeWidth(mm(0.3))
    o = z.Outline()
    o.NewOutline()
    for x, y in pts:
        o.Append(mm(OX + x), mm(OY + y))
    board.Add(z)


def keepout(board, layers, pts, tracks=False, vias=False, pours=True, name=""):
    z = pcbnew.ZONE(board)
    z.SetIsRuleArea(True)
    if name:
        z.SetZoneName(name)  # referenced by rules/weatherstation.kicad_dru
    ls = pcbnew.LSET()
    for layer in layers:
        ls.AddLayer(layer)
    z.SetLayerSet(ls)
    z.SetDoNotAllowTracks(tracks)
    z.SetDoNotAllowVias(vias)
    z.SetDoNotAllowZoneFills(pours)
    z.SetDoNotAllowPads(False)
    z.SetDoNotAllowFootprints(False)
    o = z.Outline()
    o.NewOutline()
    for x, y in pts:
        o.Append(mm(OX + x), mm(OY + y))
    board.Add(z)


def rules(board, classes):
    ds = board.GetDesignSettings()
    ds.m_TrackMinWidth = mm(0.127)
    ds.m_MinClearance = mm(0.127)
    ds.m_ViasMinSize = mm(0.45)
    ds.m_MinThroughDrill = mm(0.2)
    ds.m_HoleToHoleMin = mm(0.5)
    ds.m_CopperEdgeClearance = mm(0.3)
    ds.m_SilkClearance = mm(0.15)
    nc = ds.m_NetSettings
    d = classes["Default"]
    default = nc.GetDefaultNetclass()
    default.SetTrackWidth(mm(d["track_mm"]))
    default.SetClearance(mm(d["clearance_mm"]))
    default.SetViaDiameter(mm(d["via_mm"]))
    default.SetViaDrill(mm(d["drill_mm"]))
    for name, c in classes.items():
        if name == "Default":
            continue
        cls = pcbnew.NETCLASS(name)
        cls.SetTrackWidth(mm(c["track_mm"]))
        cls.SetClearance(mm(c.get("clearance_mm", d["clearance_mm"])))
        cls.SetViaDiameter(mm(c.get("via_mm", d["via_mm"])))
        cls.SetViaDrill(mm(c.get("drill_mm", d["drill_mm"])))
        if "gap_mm" in c:
            cls.SetDiffPairWidth(mm(c["track_mm"]))
            cls.SetDiffPairGap(mm(c["gap_mm"]))
        nc.SetNetclass(name, cls)
        for pattern in c["nets"]:
            nc.SetNetclassPatternAssignment(pattern, name)


def draw_copper(board, copper, origin=(0.0, 0.0)):
    """Hand-drawn copper (CHARGER_COPPER at U3, USB_COPPER absolute), locked (the router keeps and never rips it)."""
    ox, oy = origin
    layer = {"F": pcbnew.F_Cu, "B": pcbnew.B_Cu}
    for net, side, pts in copper["pours"]:
        zone(board, layer[side], net, [(ox + x, oy + y) for x, y in pts], clearance=0.15)
        z = board.Zones()[-1]
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
        z.SetMinThickness(mm(0.15))
        z.SetLocked(True)
    for net, side, w, pts in copper["tracks"]:
        for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
            t = pcbnew.PCB_TRACK(board)
            t.SetStart(v(ox + x1, oy + y1))
            t.SetEnd(v(ox + x2, oy + y2))
            t.SetWidth(mm(w))
            t.SetLayer(layer[side])
            t.SetNet(board.FindNet(net))
            t.SetLocked(True)
            board.Add(t)
    for net, x, y, *size in copper["vias"]:  # optional (diameter, drill), default 0.45/0.25
        d, drill = size or (0.45, 0.25)
        t = pcbnew.PCB_VIA(board)
        t.SetPosition(v(ox + x, oy + y))
        t.SetWidth(mm(d))
        t.SetDrill(mm(drill))
        t.SetNet(board.FindNet(net))
        t.SetLocked(True)
        board.Add(t)


def load_fp(fpid):
    lib, name = fpid.split(":")
    d = LIBS.get(lib, Path(os.environ["KICAD_FOOTPRINT_DIR"]) / (lib + ".pretty"))
    fp = pcbnew.FootprintLoad(str(d), name)
    if fp is None:
        sys.exit(f"footprint not found: {fpid}")
    fp.SetFPID(pcbnew.LIB_ID(lib, name))
    return fp


def local_box(fp, ref):
    """Courtyard box at rotation 0 around the footprint origin (mm)."""
    if ref in COURTYARD:
        return COURTYARD[ref]
    xs, ys = [], []
    for g in fp.GraphicalItems():
        if g.GetLayer() == pcbnew.F_CrtYd:
            b = g.GetBoundingBox()
            xs += [b.GetLeft(), b.GetRight()]
            ys += [b.GetTop(), b.GetBottom()]
    if not xs:
        b = fp.GetBoundingBox(False)
        xs, ys = [b.GetLeft(), b.GetRight()], [b.GetTop(), b.GetBottom()]
    p = fp.GetPosition()
    return tuple(round(pcbnew.ToMM(a - o), 3) for a, o in ((min(xs), p.x), (min(ys), p.y), (max(xs), p.x), (max(ys), p.y)))


def rot(x, y, deg):
    """KiCad footprint rotation (counter-clockwise on screen, y down)."""
    a = math.radians(deg)
    return x * math.cos(a) + y * math.sin(a), -x * math.sin(a) + y * math.cos(a)


def box_at(box, x, y, deg):
    pts = [rot(px, py, deg) for px in (box[0], box[2]) for py in (box[1], box[3])]
    return (x + min(p[0] for p in pts), y + min(p[1] for p in pts), x + max(p[0] for p in pts), y + max(p[1] for p in pts))


def overlaps(a, b):
    return a[0] < b[2] - 1e-6 and b[0] < a[2] - 1e-6 and a[1] < b[3] - 1e-6 and b[1] < a[3] - 1e-6


def main():
    net_file, pcb_file, classes_file = sys.argv[1], sys.argv[2], sys.argv[3]
    classes = json.loads(Path(classes_file).read_text())
    comps, pads = parse(open(net_file).read())
    board = pcbnew.BOARD()
    board.SetCopperLayerCount(4)
    rules(board, classes)
    edge_poly(board, [(0, 0), (W, 0), (W, H), (0, H)])
    nets = {}
    for name in sorted(set(pads.values())):
        net = pcbnew.NETINFO_ITEM(board, name)
        board.Add(net)
        nets[name] = net

    fps, boxes, pad_local = {}, {}, {}
    for ref, (value, fpid, uuid, fields, no_bom) in sorted(comps.items()):
        fp = load_fp(fpid)
        fp.SetReference(ref)
        fp.SetValue(value)
        fp.SetPath(pcbnew.KIID_PATH("/" + uuid))
        for pad in fp.Pads():
            name = pads.get((ref, pad.GetNumber()))
            if name:
                pad.SetNet(nets[name])
        fp.Value().SetVisible(False)
        fp.Reference().SetLayer(pcbnew.F_Fab)  # references on the fab layer; silkscreen carries user labels only
        for name, text in fields.items():
            if name not in ("Datasheet", "Description"):
                fp.SetField(name, text)
                fp.GetField(name).SetVisible(False)
        attrs = fp.GetAttributes() & ~pcbnew.FP_EXCLUDE_FROM_BOM
        fp.SetAttributes(attrs | (pcbnew.FP_EXCLUDE_FROM_BOM if no_bom else 0))
        fps[ref] = fp
    for ref in ("H1", "H2", "H3", "H4"):  # board-only: no schematic symbol, no BOM, no placement file
        fp = load_fp("MountingHole:MountingHole_3.2mm_M3_ISO7380")
        fp.SetReference(ref)
        fp.SetAttributes(pcbnew.FP_BOARD_ONLY | pcbnew.FP_EXCLUDE_FROM_BOM | pcbnew.FP_EXCLUDE_FROM_POS_FILES)
        fp.Value().SetVisible(False)
        fp.Reference().SetLayer(pcbnew.F_Fab)
        fps[ref] = fp
    for ref, fp in fps.items():
        board.Add(fp)
        boxes[ref] = local_box(fp, ref)
        pad_local[ref] = {}
        for q in fp.Pads():
            p = q.GetPosition() - fp.GetPosition()
            pad_local[ref].setdefault(q.GetNumber(), (pcbnew.ToMM(p.x), pcbnew.ToMM(p.y)))

    unknown = sorted((set(FIXED) | {r for r, _ in NEAR}) - set(fps))
    unplaced = sorted(set(fps) - set(FIXED) - {r for r, _ in NEAR})
    if unknown or unplaced:
        sys.exit(f"placement: unknown refs {unknown}, refs without a position {unplaced}")

    placed = {}  # ref -> (x, y, rot)
    taken = []   # F-side courtyard boxes in board mm (a back-side THT part blocks the front only with its pads)
    real_pads = {}  # fixed parts: pad centres read back from pcbnew (handles the flip of back-side parts)
    back = []    # back-side courtyard boxes

    def put(ref, x, y, deg):
        placed[ref] = (x, y, deg)
        taken.append(box_at(boxes[ref], x, y, deg))

    def pad_at(ref, num):
        if ref in real_pads:
            return real_pads[ref][num]
        x, y, deg = placed[ref]
        px, py = rot(*pad_local[ref][num], deg)
        return x + px, y + py

    def mm_box(b, grow=0.0):
        return (pcbnew.ToMM(b.GetLeft()) - OX - grow, pcbnew.ToMM(b.GetTop()) - OY - grow,
                pcbnew.ToMM(b.GetRight()) - OX + grow, pcbnew.ToMM(b.GetBottom()) - OY + grow)

    for ref, (x, y, deg, *side) in sorted(FIXED.items(), key=lambda kv: not kv[0].startswith("H")):
        fp = fps[ref]
        fp.SetPosition(v(x, y))
        fp.SetOrientationDegrees(deg)
        if side == ["B"]:
            fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_TOP_BOTTOM)
            fp.Reference().SetLayer(pcbnew.B_Fab)
            placed[ref] = (x, y, deg)
            taken.extend(mm_box(q.GetBoundingBox(), 0.25) for q in fp.Pads())
            b = mm_box(fp.GetCourtyard(pcbnew.B_CrtYd).BBox())
            if any(overlaps(b, o) for o in back):
                sys.exit(f"back-side courtyard of {ref} overlaps another back-side part")
            back.append(b)
        else:
            put(ref, x, y, deg)
            if ref.startswith("H"):  # standoff or nut under the board: no back-side body there either
                back.append(box_at(boxes[ref], x, y, deg))
        real_pads[ref] = {}
        for q in fp.Pads():
            c = q.GetPosition()
            real_pads[ref].setdefault(q.GetNumber(), (pcbnew.ToMM(c.x) - OX, pcbnew.ToMM(c.y) - OY))

    # hand-drawn copper on F.Cu (vias count on both sides): no part lands on it
    ux3, uy3 = placed["U3"][:2]
    for copper, (ox, oy) in ((CHARGER_COPPER, (ux3, uy3)), (USB_COPPER, (0.0, 0.0)), (RAILS_COPPER, placed["U2"][:2]),
                                  (TRUNKS, (0.0, 0.0))):
        for net, side, w, pts in copper["tracks"]:
            if side == "F":
                for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
                    g = w / 2 + 0.2
                    taken.append((ox + min(x1, x2) - g, oy + min(y1, y2) - g, ox + max(x1, x2) + g, oy + max(y1, y2) + g))
        for net, x, y, *_ in copper["vias"]:
            taken.append((ox + x - 0.45, oy + y - 0.45, ox + x + 0.45, oy + y + 0.45))
    # escape bands for U3's signal pins (TS/ILIM/BATP/BTST2/PROG/INT on the right below BAT, the bottom row, D+/D-/
    # PV_IN on the left below REGN): no part there, so every pin can fan out before the router takes over
    for bx0, by0, bx1, by1 in ((2.4, -0.55, 4.3, 2.7), (-2.7, 2.4, 2.7, 4.3), (-4.3, 0.25, -2.4, 2.7)):
        taken.append((ux3 + bx0, uy3 + by0, ux3 + bx1, uy3 + by1))

    def place_near(ref, wants):
        targets = [(num, pad_at(tr, tp)) for num, tr, tp in wants]
        cx = sum(t[1][0] for t in targets) / len(targets)
        cy = sum(t[1][1] for t in targets) / len(targets)
        best = None
        step = 0.25
        halo = 0.0 if ref in TIGHT else HALO
        for r in range(0, 64):  # rings of candidate centres around the targets' mean, out to 16 mm
            ring = [(i, j) for i in range(-r, r + 1) for j in range(-r, r + 1) if max(abs(i), abs(j)) == r]
            for i, j in ring:
                x, y = round(cx + i * step, 3), round(cy + j * step, 3)
                for deg in (0, 90, 180, 270):
                    b = box_at(boxes[ref], x, y, deg)
                    g = (b[0] - halo, b[1] - halo, b[2] + halo, b[3] + halo)
                    e = 0.15  # courtyard to edge: keeps pads 0.3 mm from the board edge (copper edge clearance)
                    if b[0] < e or b[1] < e or b[2] > W - e or b[3] > H - e or any(overlaps(g, t) for t in taken):
                        continue
                    cost = sum(math.dist((x + rot(*pad_local[ref][n], deg)[0], y + rot(*pad_local[ref][n], deg)[1]), p)
                               for n, p in targets)
                    if best is None or cost < best[0] - 1e-9:
                        best = (cost, x, y, deg)
            if best is not None and r * step > best[0] + 1.0:
                break  # rings further out cannot beat the best cost by much
        if best is None:  # parked right of the board so the render shows what is missing; the build fails below
            no_room.append(ref)
            placed[ref] = (W + 8, 4.0 * len(no_room), 0)
            return
        put(ref, best[1], best[2], best[3])

    no_room = []
    for ref, wants in NEAR:
        place_near(ref, wants)

    for ref, (x, y, deg) in placed.items():
        if ref in FIXED:
            continue
        fp = fps[ref]
        fp.SetPosition(v(x, y))
        fp.SetOrientationDegrees(deg)

    copper = [pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu]
    full = [(0, 0), (W, 0), (W, H), (0, H)]
    zone(board, pcbnew.In1_Cu, "GND", full)
    zone(board, pcbnew.In2_Cu, "GND", full)
    keepout(board, copper, ANTENNA_STRIP, vias=True)
    # J1's metal shell sits on the top side: no signal copper on F.Cu under it (rule "no signal copper under the J1
    # shell"). B.Cu under it is screened by both GND planes and stays a routing lane (2026-11-03).
    b = box_at((-4.52, -3.7, 4.52, 3.7), *placed["J1"])
    keepout(board, [pcbnew.F_Cu], [(b[0], b[1]), (b[2], b[1]), (b[2], b[3]), (b[0], b[3])], tracks=True,
            vias=True, pours=False, name="j1_shell")  # real keepout: the router ignores the custom rule
    # no tracks or vias under the inductors on B.Cu (REQUIREMENTS E3); F.Cu under them is their own pads. L1 is
    # exempt: its own SW1/SW2 tracks and the charger GND vias run under it (TI layout, engineer decision 2026-11-02)
    for ref in ("L4", "L5"):
        b = box_at(boxes[ref], *placed[ref])
        keepout(board, [pcbnew.B_Cu], [(b[0], b[1]), (b[2], b[1]), (b[2], b[3]), (b[0], b[3])], tracks=True, vias=True,
                pours=False, name="under_" + ref)
    r_ko = HOLE_KEEPOUT / math.cos(math.pi / 32)
    for ref in ("H1", "H2", "H3", "H4"):
        hx, hy = placed[ref][:2]
        keepout(board, copper, [(hx + r_ko * math.cos(math.pi * k / 16), hy + r_ko * math.sin(math.pi * k / 16))
                                for k in range(32)], tracks=True, vias=True)

    draw_copper(board, CHARGER_COPPER, placed["U3"][:2])
    draw_copper(board, USB_COPPER)
    draw_copper(board, RAILS_COPPER, placed["U2"][:2])
    draw_copper(board, TRUNKS)
    # escape vias for pads the router finds boxed in: via `dist` mm from the pad centre, straight away from the part
    # centre, joined by a locked stub (the router starts from the via, on either layer)
    pv = {"pours": [], "tracks": [], "vias": []}
    for ref, num, dist, w in PAD_VIAS:
        fp = fps[ref]
        c = fp.GetPosition()
        q = next(p for p in fp.Pads() if p.GetNumber() == num)
        net = q.GetNetname()
        px, py = pcbnew.ToMM(q.GetPosition().x) - OX, pcbnew.ToMM(q.GetPosition().y) - OY
        dx, dy = px - (pcbnew.ToMM(c.x) - OX), py - (pcbnew.ToMM(c.y) - OY)
        n = math.hypot(dx, dy)
        vx, vy = round(px + dx / n * dist, 3), round(py + dy / n * dist, 3)
        pv["tracks"].append((net, "F", w, [(px, py), (vx, vy)]))
        pv["vias"].append((net, vx, vy))
    draw_copper(board, pv)
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    t = pcbnew.PCB_TEXT(board)
    t.SetText("weatherstation v1 ${GIT_SHA}")
    t.SetPosition(v(25.0, 22.0))
    t.SetLayer(pcbnew.B_SilkS)
    t.SetMirrored(True)
    t.SetTextSize(pcbnew.VECTOR2I(mm(1.0), mm(1.0)))
    t.SetTextThickness(mm(0.15))
    board.Add(t)
    if not pcbnew.SaveBoard(pcb_file, board):
        sys.exit("save failed")
    write(Path(pcb_file).with_suffix(".kicad_pro"), HERE.parent / "rules" / "jlc-4layer.json", classes)
    shutil.copy(HERE.parent / "rules" / "weatherstation.kicad_dru", Path(pcb_file).with_suffix(".kicad_dru"))
    used = sum((b[2] - b[0]) * (b[3] - b[1]) for b in taken)
    if no_room:
        print(f"PLACEMENT FAILED, no room for: {' '.join(no_room)} (parked right of the board)")
    print(f"{pcb_file}: {len(fps)} footprints, {len(nets)} nets, {W}x{H} mm, courtyard {used / (W * H):.0%} of the board")
    if no_room:
        sys.exit(1)


main()
