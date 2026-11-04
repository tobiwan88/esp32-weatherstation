"""Qwiic add-on PCBs (run with $KICAD_PYTHON): outline, placement, all copper by hand, pours, DRC-ready.

Base = the SHT45 head's base (gen/sht45_pcb.py), unchanged: J1 IN and J2 OUT on the bottom edge (cables leave downward),
J2's VDD/SDA/SCL on three B.Cu rows to vias on J1's lines, the M3 hole at the same place. Every board of the chain has
the same connector and hole pattern, so one bracket fits all. Above the base: one sensor and its 100 nF.
Board 17 x 21.5 mm, 2 layers, GND pour on both sides.
- bmp585: SDA and SCL come up J1's lines, VDD up the right side from J2's VDD via; SDA crosses SCL once on B.Cu.
  Bosch 9.3.3: no traces or vias under the sensor (rule area between the lands, no pour under the body), no solder
  mask under it (mask opening in the footprint).
- veml6030: rotated 90 degrees so the bottom row is ADDR, SCL, VDD and the top row INT, SDA, GND; one layer for the
  signals. The sensor faces up; the connectors (about 2.9 mm tall) sit 13 mm away at the other end.
Usage: addon_pcb.py <bmp585|veml6030> board.net board.kicad_pcb
"""

import os
import sys
from pathlib import Path

import pcbnew

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "tools"))
from pcb_from_netlist import parse  # noqa: E402
from write_project import write  # noqa: E402

mm = pcbnew.FromMM
OX, OY = 100.0, 100.0
W, Y0, H = 17.0, 14.5, 36.0          # same x / y frame as the SHT45 head: the base is y 17..36 there
LIBS = {"weatherstation": HERE / "lib" / "weatherstation.pretty"}
CLASSES = {"Default": {"track_mm": 0.2, "clearance_mm": 0.15, "via_mm": 0.6, "drill_mm": 0.3, "nets": []}}

BASE_PLACE = {"J1": (4.2, 32.8, 0), "J2": (12.8, 32.8, 0), "H1": (12.8, 23.0, 0)}
BASE_TRACKS = [  # (net, layer, width, points), as in sht45_pcb.py
    ("GND", "F", 0.3, [(2.7, 30.8), (2.7, 32.3)]), ("GND", "F", 0.3, [(11.3, 30.8), (11.3, 32.3)]),
    ("VDD", "F", 0.3, [(3.7, 30.8), (3.7, 29.5)]),
    ("VDD", "F", 0.3, [(12.3, 30.8), (12.3, 29.5)]), ("VDD", "B", 0.3, [(12.3, 29.5), (3.7, 29.5)]),
    ("SDA", "F", 0.2, [(13.3, 30.8), (13.3, 28.7)]), ("SDA", "B", 0.2, [(13.3, 28.7), (4.7, 28.7)]),
    ("SCL", "F", 0.2, [(14.3, 30.8), (14.3, 27.9)]), ("SCL", "B", 0.2, [(14.3, 27.9), (5.7, 27.9)]),
]
BASE_VIAS = [("GND", 2.7, 32.3), ("GND", 11.3, 32.3), ("VDD", 12.3, 29.5), ("VDD", 3.7, 29.5),
             ("SDA", 13.3, 28.7), ("SDA", 4.7, 28.7), ("SCL", 14.3, 27.9), ("SCL", 5.7, 27.9)]
CONN = {("J1" if j < 4 else "J2", str(j % 4 + 1)): (x, 30.8, n) for j, (x, n) in enumerate(
    [(2.7, "GND"), (3.7, "VDD"), (4.7, "SDA"), (5.7, "SCL"), (11.3, "GND"), (12.3, "VDD"), (13.3, "SDA"), (14.3, "SCL")])}

BOARDS = {
    "bmp585": dict(
        place={"U1": (8.5, 18.0, 0), "C1": (12.4, 16.7, 270), "C2": (8.5, 21.4, 270)},
        pads={("U1", "1"): (7.275, 16.9, "SCL"), ("U1", "2"): (7.275, 18.0, "SDA"), ("U1", "3"): (7.275, 19.1, "GND"),
              ("U1", "4"): (8.5, 19.225, "VDD"), ("U1", "6"): (9.725, 18.0, "GND"), ("U1", "7"): (9.725, 16.9, "VDD"),
              ("U1", "8"): (8.5, 16.775, "VDD"), ("C1", "1"): (12.4, 15.925, "VDD"), ("C1", "2"): (12.4, 17.475, "GND"),
              ("C2", "1"): (8.5, 20.625, "VDD"), ("C2", "2"): (8.5, 22.175, "GND")},
        tracks=[
            ("SCL", "F", 0.2, [(5.7, 30.8), (5.7, 16.9), (7.275, 16.9)]),
            # SDA hops under SCL on B.Cu and comes up beside its land (outside the body)
            ("SDA", "F", 0.2, [(4.7, 30.8), (4.7, 21.6)]), ("SDA", "B", 0.2, [(4.7, 21.6), (6.35, 19.95), (6.35, 18.0)]),
            ("SDA", "F", 0.2, [(6.35, 18.0), (7.275, 18.0)]),
            # VDD from J2's via up the right side, over the top to VDD (8) and CSB (7); branch under to VDDIO (4)
            ("VDD", "F", 0.3, [(12.3, 29.5), (10.6, 27.8), (10.6, 20.6), (11.4, 19.8), (11.4, 15.9), (12.4, 15.9)]),
            ("VDD", "F", 0.25, [(11.4, 15.9), (8.5, 15.9), (8.5, 16.775)]), ("VDD", "F", 0.25, [(9.725, 15.9), (9.725, 16.9)]),
            ("VDD", "F", 0.25, [(10.6, 20.6), (8.5, 20.6), (8.5, 19.225)]),
            ("GND", "F", 0.25, [(9.725, 18.0), (10.55, 18.0)]), ("GND", "F", 0.25, [(7.275, 19.1), (7.275, 20.0)]),
            ("GND", "F", 0.3, [(12.4, 17.475), (12.4, 18.4)]), ("GND", "F", 0.3, [(8.5, 22.175), (8.5, 23.0)]),
        ],
        vias=[("SDA", 4.7, 21.6), ("SDA", 6.35, 18.0), ("GND", 10.55, 18.0), ("GND", 7.275, 20.0), ("GND", 12.4, 18.4),
              ("GND", 8.5, 23.0)],
        # Bosch 9.3.3: nothing between the lands; no pour under the body
        keepouts=[((8.5 - 0.85, 18.0 - 0.85, 8.5 + 0.85, 18.0 + 0.85), True),
                  ((8.5 - 1.65, 18.0 - 1.65, 8.5 + 1.65, 18.0 + 1.65), False)],
        silk=[("F", "0x46", 15.0, 17.0, 0.8), ("F", "IN", 4.2, 26.4, 1.0), ("F", "OUT", 12.8, 26.4, 1.0),
              ("B", "WS BMP585 v1", 5.6, 24.6, 0.8)]),
    "veml6030": dict(
        place={"U1": (8.5, 17.0, 90), "C1": (11.0, 17.4, 90)},
        pads={("U1", "1"): (9.15, 16.125, "GND"), ("U1", "2"): (8.5, 16.125, "SDA"), ("U1", "4"): (7.85, 17.875, "GND"),
              ("U1", "5"): (8.5, 17.875, "SCL"), ("U1", "6"): (9.15, 17.875, "VDD"),
              ("C1", "1"): (11.0, 18.175, "VDD"), ("C1", "2"): (11.0, 16.625, "GND")},
        tracks=[
            ("SDA", "F", 0.2, [(4.7, 30.8), (4.7, 15.3), (8.5, 15.3), (8.5, 16.125)]),
            ("SCL", "F", 0.2, [(5.7, 30.8), (5.7, 19.6), (8.5, 19.6), (8.5, 17.875)]),
            ("VDD", "F", 0.3, [(12.3, 29.5), (10.2, 27.4), (10.2, 18.9)]), ("VDD", "F", 0.2, [(10.2, 18.9), (9.15, 17.85), (9.15, 17.875)]), ("VDD", "F", 0.3, [(10.2, 18.9), (11.0, 18.9), (11.0, 18.175)]),
            ("GND", "F", 0.2, [(9.15, 16.125), (9.15, 15.6), (11.0, 15.6)]), ("GND", "F", 0.2, [(7.85, 17.875), (7.85, 18.75)]),
            ("GND", "F", 0.3, [(11.0, 16.625), (11.0, 15.6)]),
        ],
        vias=[("GND", 11.0, 15.6), ("GND", 7.85, 18.75)],
        keepouts=[],
        silk=[("F", "0x10", 15.0, 16.5, 0.8), ("F", "IN", 4.2, 26.4, 1.0), ("F", "OUT", 12.8, 26.4, 1.0),
              ("B", "WS VEML6030 v1", 5.6, 24.6, 0.8)]),
}


def v(x, y):
    return pcbnew.VECTOR2I(mm(OX + x), mm(OY + y))


def load_fp(fpid):
    lib, name = fpid.split(":")
    d = LIBS.get(lib, Path(os.environ["KICAD_FOOTPRINT_DIR"]) / (lib + ".pretty"))
    fp = pcbnew.FootprintLoad(str(d), name)
    if fp is None:
        sys.exit(f"footprint not found: {fpid}")
    fp.SetFPID(pcbnew.LIB_ID(lib, name))
    return fp


def rect_outline(z, x0, y0, x1, y1):
    o = z.Outline(); o.NewOutline()
    for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
        o.Append(mm(OX + x), mm(OY + y))


def main():
    key, net_file, pcb_file = sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3])
    b = BOARDS[key]
    comps, pads = parse(net_file.read_text())
    board = pcbnew.BOARD()
    ds = board.GetDesignSettings()
    ds.SetCopperLayerCount(2)
    ds.m_TrackMinWidth, ds.m_MinClearance, ds.m_ViasMinSize = mm(0.127), mm(0.127), mm(0.5)
    ds.m_MinThroughDrill, ds.m_HoleToHoleMin, ds.m_CopperEdgeClearance = mm(0.3), mm(0.5), mm(0.3)
    ds.m_SilkClearance = mm(0.15)
    d = ds.m_NetSettings.GetDefaultNetclass()
    d.SetTrackWidth(mm(0.2)); d.SetClearance(mm(0.15)); d.SetViaDiameter(mm(0.6)); d.SetViaDrill(mm(0.3))
    corners = [(0, Y0), (W, Y0), (W, H), (0, H)]
    for (x1, y1), (x2, y2) in zip(corners, corners[1:] + corners[:1]):
        s = pcbnew.PCB_SHAPE(board)
        s.SetShape(pcbnew.SHAPE_T_SEGMENT)
        s.SetStart(v(x1, y1)); s.SetEnd(v(x2, y2))
        s.SetLayer(pcbnew.Edge_Cuts); s.SetWidth(mm(0.05))
        board.Add(s)
    nets = {}
    for name in sorted(set(pads.values())):
        nets[name] = pcbnew.NETINFO_ITEM(board, name)
        board.Add(nets[name])
    place = {**BASE_PLACE, **b["place"]}
    for ref, (value, fpid, uuid, fields, no_bom) in sorted(comps.items()):
        fp = load_fp(fpid)
        fp.SetReference(ref); fp.SetValue(value)
        fp.SetPath(pcbnew.KIID_PATH("/" + uuid))
        for k, val in fields.items():
            fp.SetField(k, val)
            fp.GetField(k).SetVisible(False)  # LCSC number etc.: data, not silkscreen
        board.Add(fp)
        x, y, deg = place[ref]
        fp.SetPosition(v(x, y)); fp.SetOrientationDegrees(deg)
        for pad in fp.Pads():
            if (ref, pad.GetNumber()) in pads:
                pad.SetNet(nets[pads[(ref, pad.GetNumber())]])
        fp.Value().SetVisible(False)
        fp.Reference().SetVisible(False)  # too small for reference text; the CPL carries the designators
    fps = {f.GetReference(): f for f in board.GetFootprints()}
    nets = {name.split("/")[-1]: net for name, net in nets.items()}  # local labels: /BMP585/SDA -> SDA
    # the hand copper assumes these pad positions and nets: fail loudly if a footprint or rotation changes
    for (ref, num), (x, y, n) in {**CONN, **b["pads"]}.items():
        p = fps[ref].FindPadByNumber(num)
        got = (round(pcbnew.ToMM(p.GetPosition().x) - OX, 3), round(pcbnew.ToMM(p.GetPosition().y) - OY, 3))
        if got != (x, y) or p.GetNetname().split("/")[-1] != n:
            sys.exit(f"{ref}.{num}: at {got} on {p.GetNetname()}, copper expects ({x}, {y}) on {n}")
    layer = {"F": pcbnew.F_Cu, "B": pcbnew.B_Cu}
    for n, side, w, pts in BASE_TRACKS + b["tracks"]:
        for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
            t = pcbnew.PCB_TRACK(board)
            t.SetStart(v(x1, y1)); t.SetEnd(v(x2, y2))
            t.SetWidth(mm(w)); t.SetLayer(layer[side]); t.SetNet(nets[n])
            board.Add(t)
    for n, x, y in BASE_VIAS + b["vias"]:
        t = pcbnew.PCB_VIA(board)
        t.SetPosition(v(x, y)); t.SetWidth(mm(0.6)); t.SetDrill(mm(0.3)); t.SetNet(nets[n])
        board.Add(t)
    for (x0, y0, x1, y1), no_copper in b["keepouts"]:  # F.Cu rule areas under the sensor
        z = pcbnew.ZONE(board)
        z.SetIsRuleArea(True); z.SetLayer(pcbnew.F_Cu)
        z.SetDoNotAllowZoneFills(True)
        z.SetDoNotAllowTracks(no_copper); z.SetDoNotAllowVias(no_copper)
        z.SetDoNotAllowPads(False); z.SetDoNotAllowFootprints(False)
        rect_outline(z, x0, y0, x1, y1)
        board.Add(z)
    for side in ("F", "B"):  # GND pours over the whole board
        z = pcbnew.ZONE(board)
        z.SetLayer(layer[side]); z.SetNet(nets["GND"])
        z.SetLocalClearance(mm(0.25)); z.SetMinThickness(mm(0.2))
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
        z.SetThermalReliefGap(mm(0.25)); z.SetThermalReliefSpokeWidth(mm(0.3))
        z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
        rect_outline(z, 0, Y0, W, H)
        board.Add(z)
    for side, text, x, y, size in b["silk"]:
        t = pcbnew.PCB_TEXT(board)
        t.SetText(text); t.SetPosition(v(x, y))
        t.SetLayer(pcbnew.F_SilkS if side == "F" else pcbnew.B_SilkS)
        t.SetTextSize(pcbnew.VECTOR2I(mm(size), mm(size))); t.SetTextThickness(mm(0.15))
        if side == "B":
            t.SetMirrored(True)
        board.Add(t)
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    pcbnew.SaveBoard(str(pcb_file), board)
    write(pcb_file.with_suffix(".kicad_pro"), HERE.parent / "rules" / "jlc-2layer.json", CLASSES)
    print(f"{pcb_file}: {len(comps)} parts, {W:g} x {H - Y0:g} mm, all copper drawn")


if __name__ == "__main__":
    main()
