"""main-board layout: outline, placement, GND planes, keepouts (run with $KICAD_PYTHON). Placement only, no routing.

Builds hardware/main-board/main-board.kicad_pcb from the schematic netlist through the shared engine gen/pcbkit.py
(adapted from gen/pcb_v1.py). Positions in mm from the board's top-left corner, top view. Floorplan, stack geometry
and sources: main-board/BOARD.md "Layout". The board sits ON TOP of the power board (same 50 x 50 outline, same holes,
J10 at the same top-view position); tools/stack_check.py proves the alignment.
Usage: main_pcb.py design.net board.kicad_pcb classes.json   (tools/build_board.sh main-board)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pcbkit  # noqa: E402
from stack import HOLES, J10_AT, W, H  # noqa: E402,F401  (shared stack geometry: holes and J10 on both boards)

REGIONS = "mcu=14,0,50,24 rails=22,20,50,38 sensors=0,0,24,30 bottom=0,30,50,50"
TITLE, TITLE_AT, DRU = "weatherstation main board", (25.0, 30.0), "main-board.kicad_dru"

# Floorplan (BOARD.md "Layout"):
#  - ESP32-S3-WROOM-1 in the top-right corner, antenna up and fully off the board (HW design guidelines 1.4.7 figure 24,
#    position 3; module datasheet 11.2): module origin 6.75 mm below the top edge puts the antenna keepout (local
#    y < -6.75) outside the outline, as on weatherstation-v1. The power board below has the same outline, so nothing
#    of it lies under the antenna either.
#  - cool left half: I2C connectors (J3 SHT cable on the top edge, J4 Qwiic and J11 on the left edge), BMP580 U9 in the
#    interior (BST-BMP5xy-HS000-00 7.1: not near an edge, a hole, the MCU or fast-heating parts), SCD41 U8 lower left
#  - USB-C J1 on the left edge level with the module's USB pins (IO19/IO20 = pins 13/14), so the pair runs straight
#  - warm right half: TPS63802 U2 and TPS61023 U7 between the module and J10, next to J10 pin 1/2 (SYS)
#  - outdoor cables on the bottom edge: J12 wind/rain/vane (ESD U10/U11 above it), J8 ZE25-O3; PMS7003 J2 on the
#    right edge between H2 and H4; debug UART J7 in the strip under J10
# Connector bodies on the FRONT: this board's back faces the power board across the 11 mm gap (stack.py).
UX, UY = 40.0, 6.75  # module centre
FIXED = {
    "U1": (UX, UY, 0),
    "J10": J10_AT,                                 # 2x10 male header, pin 3 pulled (key), F.Cu, unmirrored
    "J1": (3.4, 12.0, 270),                        # receptacle face 0.3 mm past the left edge (v1 J1, ORDER.md rails)
    "J3": (12.8, 3.4, 180),                        # SH horizontal, opening up; MP pads 0.6 mm inside the top edge
    "J4": (3.4, 23.5, 270),                        # SH horizontal, opening left
    "J11": (3.3, 30.6, 0),                         # 2.54 mm 1x4 vertical, pins along the left edge
    "U9": (13.0, 22.0, 0),                         # BMP580: interior, cool side
    "U8": (11.0, 37.0, 0),                         # SCD41 (DNP option)
    "U2": (38.5, 26.5, 0), "U7": (29.5, 26.5, 0),
    "J2": (45.5, 29.5, 0),                         # PMS7003 2x5 1.27 mm, right edge
    "J12": (9.2, 46.5, 0), "J8": (26.0, 46.5, 0),  # JST PH vertical on the bottom edge (courtyard 0.37 mm inside)
    "J7": (32.5, 40.6, 90),                        # debug UART, pins along x under J10
    "Q40": (21.5, 16.0, 0),                        # 3V3_SW P-FET between the rail and the sensor side (left)
}
# TPS63802 (SLVSEU9D 12.1/12.2, figure 12-1) and TPS61023 (SLVSF14B 10.1/10.2, figure 10-1) blocks, offsets from the IC
# centre as on weatherstation-v1 (routed, DRC clean): input cap across VIN/GND, inductor at the switch pins, output cap at
# VOUT/GND, FB divider on the side away from the switch node.
BUCKBOOST = {"C40": (-1.0, -2.75, 180), "L4": (2.75, 0.0, -90), "C41": (0.45, 2.82, 0),
             "R53": (-3.05, 0.5, 180), "R52": (-3.05, 2.1, 0)}
BOOST = {"L5": (0.25, 2.45, 0), "C45": (2.863, 0.0, -90), "C44": (-2.8, 0.5, 180),
         "R43": (-0.65, -2.55, -90), "R44": (-2.2, -2.55, 90), "R45": (-2.713, 2.25, 180)}
BLOCKS = [("U2", BUCKBOOST), ("U7", BOOST)]
COURTYARD = {"U1": (-9.74, -6.75, 9.74, 13.45)}  # the footprint's courtyard includes the off-board antenna keepout
RESERVED = [(None, (24.0, 0.0, 30.5, 1.2)),     # antenna-side strip beside the module (no parts, no vias)
            (None, (14.3, 10.3, 28.2, 12.7))]    # USB pair lane from U4 to the series resistors at the module

NEAR = [
    # ESP32 supply and strapping (module datasheet figure "peripheral schematic", HW guidelines 1.2/1.3): 22u + 100n +
    # 1u at the 3V3 pin, EN RC at the EN pin, IO0 pull-up
    ("C31", [("1", "U1", "2"), ("2", "U1", "1")]), ("C32", [("1", "U1", "2"), ("2", "U1", "1")]),
    ("C30", [("1", "U1", "2"), ("2", "U1", "1")]),
    ("C33", [("1", "U1", "3")]),
    ("R48", [("1", "U1", "4")]), ("R49", [("1", "U1", "6")]), ("R46", [("1", "U1", "10")]),  # UART series R at the driving pin
    ("R30", [("2", "U1", "3")]), ("JP1", [("1", "U1", "3")]),
    ("R31", [("2", "U1", "27")]), ("JP2", [("1", "U1", "27")]),
    # USB: ESD at the receptacle, CC resistors at their pins, series resistors at the module (HW guidelines 1.4.8)
    ("U4", [("1", "J1", "A6"), ("3", "J1", "A7"), ("5", "J1", "A4")]), ("C35", [("1", "U4", "5"), ("2", "U4", "2")]),
    ("R9", [("1", "J1", "A5")]), ("R10", [("1", "J1", "B5")]),
    ("R32", [("2", "U1", "14")]), ("R33", [("2", "U1", "13")]),
    # rails: output caps of U2, 3V3_SW switch and its caps, test points
    ("R40", [("2", "Q40", "1")]), ("C48", [("1", "Q40", "1"), ("2", "Q40", "3")]),
    ("R76", [("1", "Q40", "1")]), ("Q41", [("3", "R76", "2")]), ("R41", [("2", "Q41", "1")]), ("R42", [("1", "Q41", "1")]),
    ("C42", [("1", "Q40", "3")]), ("C43", [("1", "C42", "1"), ("2", "C42", "2")]), ("C47", [("1", "C43", "1")]),
    ("R78", [("1", "C43", "1")]),
    ("C46", [("1", "C45", "1"), ("2", "C45", "2")]),
    ("TP1", [("1", "C41", "1")]), ("TP2", [("1", "J10", "1")]),
    # sensor bus: ESD and the cable's series resistor at J3, pull-ups, BMP580 and SCD41 decoupling at their pins
    ("U5", [("1", "J3", "3"), ("3", "J3", "4")]), ("R77", [("2", "J3", "2")]),
    ("R50", [("1", "U5", "1")]), ("R51", [("1", "U5", "3")]),
    ("C90", [("1", "U9", "10"), ("2", "U9", "9")]), ("C91", [("1", "U9", "6"), ("2", "U9", "5")]),
    # charger host side at J10: CE, INT and I2C pull-ups
    ("R20", [("2", "J10", "16")]), ("R22", [("1", "J10", "15")]), ("R54", [("1", "J10", "11")]), ("R55", [("1", "J10", "12")]),
    # PMS7003 and ZE25-O3 UART series resistors at the driving ESP32 pin (critical.yaml series_termination, as v1),
    # the ZE25 RX divider's lower leg at the connector
    ("R47", [("1", "J8", "5")]),
    # wind/rain/vane: ESD at J12, then the pull-ups and RC filters
    ("U10", [("1", "J12", "2"), ("3", "J12", "3")]), ("U11", [("1", "J12", "4")]),
    ("R70", [("1", "J12", "2")]), ("R71", [("1", "J12", "3")]), ("R74", [("1", "J12", "4")]),
    ("R72", [("1", "R70", "1")]), ("R73", [("1", "R71", "1")]), ("R75", [("1", "R74", "1")]),
    ("C70", [("1", "R72", "2")]), ("C71", [("1", "R73", "2")]), ("C72", [("1", "R75", "2")]),
    # status LEDs
    ("R34", [("1", "U1", "34")]), ("D10", [("2", "R34", "2")]), ("R35", [("1", "U1", "35")]), ("D11", [("2", "R35", "2")]),
]
TIGHT = {"C30", "C31", "C32", "C33", "C35", "R46", "R48", "R49", "C42", "C43", "C46", "R32", "R33"}
HALO = 0.35

# connector names: front where there is room, else on the back (readable before the boards are stacked)
SILK = [("SHT", 12.8, 8.2, 0.8, "F"), ("QWIIC", 8.4, 23.5, 0.8, "F"),
        ("WIND RAIN VANE", 12.2, 43.0, 0.8, "B"), ("O3", 32.0, 43.6, 0.8, "B"), ("PM", 45.5, 37.2, 0.8, "B")]


def j10_marks():
    x, y = J10_AT[:2]
    return [("KEY 3", x - 2.54, y - 2.6, 0.8, "F"), ("SYS", x, y + 4.75, 0.8, "F")]


SILK += j10_marks()


def KEEPOUTS(put, ctx):
    import pcbnew
    rect, box = ctx["rect"], ctx["box"]
    # antenna side: no copper pours or vias on any layer in the 1.2 mm strip below the antenna edge (v1 ANTENNA_STRIP,
    # HW guidelines 1.4.7: keep the area next to the antenna free of metal)
    put("antenna_strip", ctx["COPPER"], rect((UX - 16, 0.0, W, 1.2)), vias=True, pours=True)
    # J1's metal shell: no signal copper on F.Cu under it (custom rule "no signal copper under the J1 shell")
    put("j1_shell", [pcbnew.F_Cu], rect(pcbnew_box(ctx, "J1", (-4.52, -3.7, 4.52, 3.7))), tracks=True, vias=True,
        pours=False)
    # BMP580: no traces or vias under the body on the outer layers, no copper pour (BST-BMP581-DS004-13 8.2,
    # BST-BMP5xy-HS000-00 3.2); its own pads only
    put("bmp580_body", [pcbnew.F_Cu, pcbnew.B_Cu], rect(box("U9")), tracks=True, vias=True, pours=True)
    # no tracks or vias on B.Cu under the inductors (REQUIREMENTS E3, as on v1)
    for ref in ("L4", "L5"):
        put("under_" + ref, [pcbnew.B_Cu], rect(box(ref)), tracks=True, vias=True, pours=False)


def pcbnew_box(ctx, ref, local):
    return pcbkit.box_at(local, *ctx["placed"][ref])


if __name__ == "__main__":
    pcbkit.build(sys.modules[__name__])
