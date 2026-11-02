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
    # debug corner
    "J7": (48.0, 16.5, 0, "B"), "SW10": (40.5, 10.3, 0), "SW11": (40.5, 17.0, 0),
    # inputs: USB-C opening out of the left edge, PV connector on the bottom edge
    "J1": (3.4, 28.5, 270), "J5": (3.3, 40.5, 270, "B"),
    # charger (its power stage is CHARGER below); buck-boost right of it, boost below, each with room for its loop
    "U3": (16.5, 35.5, 0),
    "U2": (26.5, 38.5, 0), "U7": (23.0, 46.8, 0),
    # sensors
    # J2's front pads sit in the free column between the charger and U8, not inside the charger block
    "U8": (40.0, 30.0, 0), "J8": (47.4, 37.0, 270, "B"), "J2": (32.2, 29.5, 0, "B"),
    "J3": (38.6, 46.65, 0),  # mounting pads 0.3 mm inside the bottom edge
}

FIXED = {r: (p[0] + (W - W0 if p[0] > 28 else 0), p[1] + (H - H0 if p[1] > 20 else 0), *p[2:])
         if not r.startswith("H") and r != "U1" else p for r, p in FIXED.items()}

# BQ25798 power stage drawn by hand (SLUSDV2C 8.4.1/8.4.2, priority order): 0402 PMID and SYS caps on top of the
# PMID-SW1-GND-SW2-SYS pin row sharing the GND pin; SW1/SW2 drop through vias under the IC to B.Cu and come back up at
# the inductor above the caps; bulk caps in a column beside each, joined by F.Cu pours. Offsets from U3's centre (mm).
CHARGER = {
    "C9": (-0.95, -3.0, 0), "C13": (0.95, -3.0, 180), "L1": (0.0, -5.6, 0),
    "C10": (-3.6, -3.55, 180), "C11": (-3.6, -5.55, 180), "C12": (-3.6, -7.55, 180),
    "C14": (3.6, -3.55, 0), "C15": (3.6, -5.55, 0), "C16": (3.6, -7.55, 0),
    # small parts, one ring around the pins in pin order so every pin fans out without crossing (items 3-5, 7):
    # right: BAT cap beside the BAT pins, then PROG, BTST2, ILIM, TS rows; BATP sense and SDRV cap further out
    "C19": (5.6, -1.35, 0), "C21": (8.3, -1.35, 0), "R14": (4.7, 0.45, 0), "R13": (7.2, 0.45, 0),
    "C4": (4.7, 2.0, 0), "R16": (4.6, 3.3, 0), "R15": (7.05, 3.55, 180), "R18": (4.9, 5.1, 0), "R17": (7.5, 5.1, 180),
    # left: VBUS 100 nF at the VBUS pins, BTST1 cap, REGN cap (2 GND vias to the plane, item 3)
    "C6": (-3.45, -1.15, 180), "C3": (-4.4, 0.1, 180), "C5": (-4.4, 1.75, 180),
}
_U3 = FIXED["U3"]
FIXED.update({r: (_U3[0] + dx, _U3[1] + dy, deg) for r, (dx, dy, deg) in CHARGER.items()})


def _mirror(pts):
    return [(-x, y) for x, y in pts]


_PMID = [(-1.0, -1.3), (-0.8, -1.3), (-0.8, -2.45), (-1.1, -2.45), (-1.1, -3.5), (-1.6, -3.5), (-1.6, -8.4),
         (-3.25, -8.4), (-3.25, -2.3), (-1.0, -2.3)]
_SW1_B = [(-0.45, 0.25), (-0.45, -0.55), (-1.0, -1.1), (-1.0, -7.85)]
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
    ] + [("GND", "F", 0.4, [(sx * 4.55, y), (sx * 5.45, y)]) for sx in (-1, 1) for y in (-3.55, -5.55, -7.55)],
    "vias": [("/Charger/SW1", -0.45, -0.55), ("/Charger/SW1", -0.45, 0.25), ("/Charger/SW1", -1.0, -7.05),
             ("/Charger/SW1", -1.0, -7.85), ("/Charger/SW2", 0.45, -0.55), ("/Charger/SW2", 0.45, 0.25),
             ("/Charger/SW2", 1.0, -7.05), ("/Charger/SW2", 1.0, -7.85), ("GND", 0.0, -3.85), ("GND", 0.0, -4.65)]
            + [("GND", sx * 5.45, y) for sx in (-1, 1) for y in (-3.55, -5.55, -7.55)],
}

# ref: [(pad, target ref, target pad), ...]; the part goes where these pads are closest to their targets. Order = priority.
NEAR = [
    # inputs first (they need the edge): PV TVS at the connector, then the choke; USB ESD at the connector
    ("D1", [("1", "J5", "1"), ("2", "J5", "2")]), ("L3", [("1", "D1", "1"), ("4", "D1", "2")]), ("C2", [("1", "L3", "2")]),
    ("U4", [("1", "J1", "A6"), ("3", "J1", "A7")]), ("C1", [("1", "U4", "5")]),
    ("R9", [("1", "J1", "A5")]), ("R10", [("1", "J1", "B5")]),
    # switching loops, bootstrap, FB and IC decoupling of all three converters (critical.yaml)
    # charger bulk caps: each beside the previous cap of its net, pads aligned (one short wide copper run per net)
    ("C17", [("1", "C16", "1"), ("2", "C16", "2")]),
    ("C18", [("1", "C17", "1"), ("2", "C17", "2")]),
    ("C20", [("1", "C19", "1"), ("2", "C19", "2")]),
    ("C7", [("1", "C6", "1"), ("2", "C6", "2")]), ("C8", [("1", "C7", "1"), ("2", "C7", "2")]),
    ("C40", [("1", "U2", "1"), ("2", "U2", "2")]), ("L4", [("1", "U2", "9"), ("2", "U2", "7")]),
    ("C41", [("1", "U2", "6"), ("2", "U2", "8")]), ("R53", [("1", "U2", "4")]), ("R52", [("2", "U2", "4")]),
    ("C45", [("1", "U7", "6"), ("2", "U7", "4")]), ("L5", [("2", "U7", "5")]), ("C44", [("1", "U7", "3")]),
    ("R44", [("1", "U7", "1")]), ("R43", [("2", "U7", "1")]), ("C46", [("1", "U7", "6")]), ("R45", [("1", "U7", "2")]),
    # charger input FETs (VBUS pins), gate resistors, set resistors
    ("M2", [("3", "U3", "3")]), ("M4", [("3", "U3", "2")]), ("M1", [("2", "M2", "2")]), ("M3", [("2", "M4", "2")]),
    ("R11", [("2", "U3", "11"), ("1", "M1", "1")]), ("R12", [("2", "U3", "10"), ("1", "M3", "1")]),
    ("D2", [("1", "U3", "1")]), ("R19", [("2", "D2", "2")]),
    # charger I2C/INT/CE pull-ups at the MCU end of those nets (frees U3's pin ring)
    ("R20", [("2", "U1", "17")]), ("R22", [("1", "U1", "18")]), ("R54", [("1", "U1", "39")]), ("R55", [("1", "U1", "38")]),
    # module (decoupling, EN RC, series resistors at the driving pin)
    ("C31", [("1", "U1", "2")]), ("C33", [("1", "U1", "3")]), ("C32", [("1", "U1", "2")]),
    ("R30", [("2", "U1", "3")]), ("C30", [("1", "U1", "2")]),
    ("R33", [("2", "U1", "13")]), ("R32", [("2", "U1", "14")]),
    ("R48", [("1", "U1", "4")]), ("R49", [("1", "U1", "6")]), ("R46", [("1", "U1", "10")]), ("R47", [("1", "R46", "2")]),
    ("R31", [("2", "U1", "27")]),
    # battery protection
    ("TH1", [("2", "J6", "2")]), ("F1", [("1", "J6", "1")]), ("M60", [("2", "U6", "6")]), ("M61", [("3", "M60", "3")]),
    ("C60", [("1", "U6", "5")]), ("R60", [("2", "U6", "5")]), ("R61", [("1", "U6", "2")]),
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


def draw_charger(board, origin):
    """CHARGER_COPPER at U3's position, locked (the router keeps and never rips it)."""
    ox, oy = origin
    layer = {"F": pcbnew.F_Cu, "B": pcbnew.B_Cu}
    for net, side, pts in CHARGER_COPPER["pours"]:
        zone(board, layer[side], net, [(ox + x, oy + y) for x, y in pts], clearance=0.15)
        z = board.Zones()[-1]
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
        z.SetMinThickness(mm(0.15))
        z.SetLocked(True)
    for net, side, w, pts in CHARGER_COPPER["tracks"]:
        for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
            t = pcbnew.PCB_TRACK(board)
            t.SetStart(v(ox + x1, oy + y1))
            t.SetEnd(v(ox + x2, oy + y2))
            t.SetWidth(mm(w))
            t.SetLayer(layer[side])
            t.SetNet(board.FindNet(net))
            t.SetLocked(True)
            board.Add(t)
    for net, x, y in CHARGER_COPPER["vias"]:
        t = pcbnew.PCB_VIA(board)
        t.SetPosition(v(ox + x, oy + y))
        t.SetWidth(mm(0.45))
        t.SetDrill(mm(0.25))
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

    # hand-drawn charger copper on F.Cu (vias count on both sides): no part lands on it
    ux3, uy3 = placed["U3"][:2]
    for net, side, w, pts in CHARGER_COPPER["tracks"]:
        if side == "F":
            for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
                g = w / 2 + 0.2
                taken.append((ux3 + min(x1, x2) - g, uy3 + min(y1, y2) - g, ux3 + max(x1, x2) + g, uy3 + max(y1, y2) + g))
    for net, x, y in CHARGER_COPPER["vias"]:
        taken.append((ux3 + x - 0.45, uy3 + y - 0.45, ux3 + x + 0.45, uy3 + y + 0.45))
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
                    if b[0] < 0 or b[1] < 0 or b[2] > W or b[3] > H or any(overlaps(g, t) for t in taken):
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
    # J1's metal shell sits on the board: only GND under it (rule "no signal copper under the J1 shell")
    b = box_at((-4.52, -3.7, 4.52, 3.7), *placed["J1"])
    keepout(board, [pcbnew.F_Cu, pcbnew.B_Cu], [(b[0], b[1]), (b[2], b[1]), (b[2], b[3]), (b[0], b[3])], pours=False, name="j1_shell")
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

    draw_charger(board, placed["U3"][:2])
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
