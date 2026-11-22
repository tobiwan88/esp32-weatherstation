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
import main_copper  # noqa: E402
import pcbkit  # noqa: E402
from stack import HOLES, J10_AT, W, H  # noqa: E402,F401  (shared stack geometry: holes and J10 on both boards)

REGIONS = "mcu=14,0,50,24 rails=22,20,50,38 sensors=0,0,24,30 bottom=0,30,50,50 usb=5,7,31,21 fanout=6,7.5,17,16.5 stubs=27,14,38,38"
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
    # USB fan-out (routing 2026-11-22, BOARD.md "Routing"): U4 turned so both lines flow straight through it
    # (DN top row, DP bottom row, as they leave J1); CC resistors on their own side of the pair; C35 above U4
    "U4": (13.0, 12.0, 180), "R9": (9.7, 10.3, 0), "R10": (9.7, 13.75, 0), "C35": (12.6, 9.4, 0),
    # moved off the pair's 45-degree descent to the resistors (0.6 mm copper to the pair): C48 above Q40's gate/drain,
    # the 3V3_SW caps C42/C43 stacked lower
    "C48": (21.5, 13.75, 0), "C42": (25.0, 18.9, 0), "C43": (25.0, 21.1, 0),
    # 22 ohm series resistors at U1 pins 13/14 (their placement-pass positions, pinned: the pair ends on them)
    "R33": (29.25, 16.73, 0), "R32": (29.25, 18.0, 0),
    # Q40 gate network and the BMP580 decoupling: drawn by hand in gen/main_copper.py, so pinned
    "R40": (18.06, 15.05, 0), "R76": (18.06, 13.55, 180), "C90": (12.75, 19.74, 0), "C91": (15.13, 22.51, 270),
    "Q41": (14.802, 15.66, 0), "D11": (28.74, 20.59, -90), "D10": (41.24, 22.86, 180),
    # wind/rain/vane block between J12, J8 and J10, in cable order so the three inputs fan out without crossing: VANE
    # (J12.4) straight right into U11, WIND (J12.3) and RAIN (J12.2) one level higher each into U10; pull-ups and RC
    # filters in rows above U10 (routing 2026-11-22: the NEAR placement crossed the three lines and left 5 of them open)
    "U11": (20.6, 47.6, 0), "U10": (20.6, 43.9, 0),
    "R72": (18.8, 38.45, 0), "R73": (21.9, 38.45, 0), "C70": (18.8, 39.5, 0), "C71": (21.9, 39.5, 0),
    "R75": (18.8, 40.55, 0), "C72": (21.9, 40.55, 0), "R70": (18.8, 41.6, 0), "R71": (21.9, 41.6, 0),
    "R74": (17.05, 41.3, 90),
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
            (None, (7.0, 8.4, 15.6, 15.4)),      # J1/U4 fan-out (hand copper, gen/main_copper.py)
            (None, (14.3, 10.4, 22.8, 13.6)),    # USB pair lane from U4 ...
            (None, (28.2, 15.3, 29.3, 16.4)), (None, (28.2, 18.4, 29.3, 19.4))]   # BC1.2 tap vias
RESERVED += [(None, (21.8 + t - 1.1, 12.0 + t - 1.1, 21.8 + t + 1.1, 12.0 + t + 1.1)) for t in (0.5 * k for k in range(13))]

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
    # rails: output caps of U2, 3V3_SW switch and its caps, test points

    ("R41", [("2", "Q41", "1")]), ("R42", [("1", "Q41", "1")]),
    ("C47", [("1", "C43", "1")]),
    ("R78", [("1", "C43", "1")]),
    ("C46", [("1", "C45", "1"), ("2", "C45", "2")]),
    ("TP1", [("1", "C41", "1")]), ("TP2", [("1", "J10", "1")]),
    # sensor bus: ESD and the cable's series resistor at J3, pull-ups, BMP580 and SCD41 decoupling at their pins
    ("U5", [("1", "J3", "3"), ("3", "J3", "4")]), ("R77", [("2", "J3", "2")]),
    ("R50", [("1", "U5", "1")]), ("R51", [("1", "U5", "3")]),
    # charger host side at J10: CE, INT and I2C pull-ups
    ("R20", [("2", "J10", "16")]), ("R22", [("1", "J10", "15")]), ("R54", [("1", "J10", "11")]), ("R55", [("1", "J10", "12")]),
    # PMS7003 and ZE25-O3 UART series resistors at the driving ESP32 pin (critical.yaml series_termination, as v1),
    # the ZE25 RX divider's lower leg at the connector
    ("R47", [("1", "J8", "5")]),
    # status LEDs
    ("R34", [("1", "U1", "34")]), ("R35", [("1", "U1", "35")]),
]
TIGHT = {"C30", "C31", "C32", "C33", "R46", "R48", "R49", "C46", "R32", "R33"}
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
    put("antenna_strip", ctx["COPPER"], rect((UX - 16, 0.0, W, 1.2)), tracks=True, vias=True, pours=True)
    # under the module body: no F.Cu tracks inside its pad ring (the module's underside is its exposed pad and pin
    # pads; signals cross under it on B.Cu, screened by In1/In2). A 1.1 mm band inside each pad row stays free for the
    # pin escapes to their vias (the right pin column is 0.5 mm from the board edge: it can only leave by vias).
    put("module_body", [pcbnew.F_Cu], rect((UX - 6.65, 1.2, UX + 6.65, UY + 10.65)), tracks=True, vias=False, pours=False)
    # J1's metal shell: no signal copper on F.Cu under it (custom rule "no signal copper under the J1 shell")
    put("j1_shell", [pcbnew.F_Cu], rect(pcbnew_box(ctx, "J1", (-4.52, -3.7, 4.52, 3.7))), tracks=True, vias=True,
        pours=False)
    # BMP580: no traces or vias under the body (BST-BMP581-DS004-13 8.2, BST-BMP5xy-HS000-00 3.2) except the entries
    # into its own pads: B.Cu keepout over the whole body, F.Cu keepout inside the pad ring, no pour under the body
    ux, uy = ctx["placed"]["U9"][:2]
    put("bmp580_body", [pcbnew.B_Cu], rect((ux - 1.0, uy - 1.0, ux + 1.0, uy + 1.0)), tracks=True, vias=True, pours=True)
    put("bmp580_inner", [pcbnew.F_Cu], rect((ux - 0.45, uy - 0.45, ux + 0.45, uy + 0.45)), tracks=True, vias=True,
        pours=True)
    put("bmp580_pour", [pcbnew.F_Cu], rect(box("U9")), pours=True)
    # no tracks or vias on B.Cu under the inductors (REQUIREMENTS E3, as on v1)
    for ref in ("L4", "L5"):
        put("under_" + ref, [pcbnew.B_Cu], rect(box(ref)), tracks=True, vias=True, pours=False)
    # USB: nothing on B.Cu under the main run of the pair (In1 is its reference, In2 screens B.Cu), except one 2.5 mm
    # window on the straight run between the two GND stitch-via pairs: the pair and J1 wall off the top-left pocket
    # (J3, U5, the module's left pins) on F.Cu, so the pocket's slow signals (sensor I2C, anemometer inputs) cross
    # there on B.Cu, two solid GND planes away from the pair (BOARD.md "Routing review"). Plus the named fan-out area
    # where the custom DRC rule allows connector-pitch clearances.
    info = main_copper.build(ctx["pad"])[1]
    c0, c1 = info["centre"][0], info["centre"][1]
    assert abs(c0[1] - c1[1]) < 1e-6 and c1[0] - c0[0] > 4.5, "straight run of at least 4.5 mm before the bend"
    wx0, wx1 = c0[0] + 0.95, c0[0] + 3.45
    for name, line in (("usb_under", [c0, (wx0, c0[1])]), ("usb_under2", [(wx1, c0[1])] + info["centre"][1:])):
        poly = main_copper.offset(line, 0.62) + main_copper.offset(line, -0.62)[::-1]
        put(name, [pcbnew.B_Cu], poly, tracks=True, vias=True, pours=False)
    put("usb_fanout", [pcbnew.F_Cu, pcbnew.B_Cu], rect((6.0, 8.3, info["xs"] + 0.9, 15.6)), pours=False)


def pcbnew_box(ctx, ref, local):
    return pcbkit.box_at(local, *ctx["placed"][ref])


def draw_copper(pcb_file):
    """Second pass on the placed board: hand-drawn critical copper (gen/main_copper.py) from the real pad centres,
    locked; the module's exposed-pad vias fully joined to the planes; zones refilled."""
    import pcbnew
    mm, OX, OY = pcbnew.FromMM, pcbkit.OX, pcbkit.OY
    board = pcbnew.LoadBoard(pcb_file)
    pads = {}
    for fp in board.GetFootprints():
        for q in fp.Pads():
            c = q.GetPosition()
            pads.setdefault((fp.GetReference(), q.GetNumber()), (pcbnew.ToMM(c.x) - OX, pcbnew.ToMM(c.y) - OY))
    items, _ = main_copper.build(lambda ref, num: pads[(ref, num)])
    layer = {"F": pcbnew.F_Cu, "B": pcbnew.B_Cu}
    for it in items:
        net = board.FindNet(it[1])
        if net is None:
            sys.exit(f"main_copper: unknown net {it[1]}")
        if it[0] == "T":
            _, _, side, w, pts = it
            for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
                if (x1, y1) == (x2, y2):
                    continue
                t = pcbnew.PCB_TRACK(board)
                t.SetStart(pcbkit.v(x1, y1))
                t.SetEnd(pcbkit.v(x2, y2))
                t.SetWidth(mm(w))
                t.SetLayer(layer[side])
                t.SetNet(net)
                t.SetLocked(True)
                board.Add(t)
        else:
            _, _, x, y, d, drill = it
            t = pcbnew.PCB_VIA(board)
            t.SetPosition(pcbkit.v(x, y))
            t.SetWidth(mm(d))
            t.SetDrill(mm(drill))
            t.SetNet(net)
            t.SetLocked(True)
            board.Add(t)
    # ESP32 exposed pad: its 9 footprint vias solid into both GND planes (HW guidelines 1.2: EPAD to GND, thermal)
    for q in board.FindFootprintByReference("U1").Pads():
        if q.GetNumber() == "41":
            q.SetLocalZoneConnection(pcbnew.ZONE_CONNECTION_FULL)
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    pcbnew.SaveBoard(pcb_file, board)
    print(f"{pcb_file}: hand copper {sum(i[0] == 'T' for i in items)} tracks, {sum(i[0] == 'V' for i in items)} vias")


if __name__ == "__main__":
    pcbkit.build(sys.modules[__name__])
    draw_copper(sys.argv[2])
