"""SHT45 sensor head PCB (run with $KICAD_PYTHON): outline, placement, all copper by hand, pours, DRC-ready.

Shape (Sensirion SHT4x design guide v2, section 3: keep heat and copper away from the sensor): a 9 x 8 mm sensor
island on a 3.4 mm wide, 9 mm long neck that carries only four 0.2 mm traces; the base below holds the cable side.
No pour, no via and no other part on the island except the 100 nF cap at the VDD pin.
Extensible: J1 = Qwiic in (from main-board J3), J2 = Qwiic out (1:1), both on the bottom edge. Any Qwiic/STEMMA QT
board chains behind J2 on the same bus. Two same-handed connectors cannot be joined on one layer, so J2's lines run
on B.Cu (three straight rows) to vias on J1's F.Cu lines; GND is the B.Cu pour on the base.
Usage: sht45_pcb.py sht45-board.net sht45-board.kicad_pcb
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
W, H = 17.0, 36.0
ISLAND = (4.0, 13.0, 0.0, 8.0)      # x0, x1, y0, y1
NECK = (6.8, 10.2, 8.0, 17.0)
BASE_Y = 17.0
OUTLINE = [(ISLAND[0], 0), (ISLAND[1], 0), (ISLAND[1], ISLAND[3]), (NECK[1], ISLAND[3]), (NECK[1], BASE_Y), (W, BASE_Y),
           (W, H), (0, H), (0, BASE_Y), (NECK[0], BASE_Y), (NECK[0], ISLAND[3]), (ISLAND[0], ISLAND[3])]
PLACE = {"U1": (8.5, 3.0, 180), "C1": (7.175, 6.0, 0), "J1": (4.2, 32.8, 0), "J2": (12.8, 32.8, 0),
         "H1": (12.8, 23.0, 0)}  # H1: M3 hole, no copper (NPTH)
CLASSES = {"Default": {"track_mm": 0.2, "clearance_mm": 0.15, "via_mm": 0.6, "drill_mm": 0.3, "nets": []}}

# (net key, layer, width, points); net keys resolve through J1's pins (1 GND, 2 VDD, 3 SDA, 4 SCL)
TRACKS = [
    # J1 straight up the left of the base, nested turns (GND/VDD swap at the neck through the B.Cu pour), up the neck
    ("VDD", "F", 0.3, [(3.7, 30.8), (3.7, 18.0), (7.6, 18.0)]), ("VDD", "F", 0.2, [(7.6, 18.0), (7.6, 7.6), (6.4, 6.4),
                                                                                   (6.4, 6.0)]),
    ("VDD", "F", 0.2, [(6.4, 6.0), (6.4, 2.6), (7.8, 2.6)]),
    # the SHT4x footprint keeps copper off its body (rule area): every pin is entered from outside the package
    ("GND", "F", 0.2, [(8.2, 18.6), (8.2, 6.75), (7.95, 6.5), (7.95, 6.0), (7.95, 4.3), (7.4, 3.75), (7.4, 3.4),
                       (7.8, 3.4)]),
    ("SDA", "F", 0.2, [(4.7, 30.8), (4.7, 19.2), (8.8, 19.2), (8.8, 4.4), (9.7, 4.4), (9.7, 3.4), (9.2, 3.4)]),
    ("SCL", "F", 0.2, [(5.7, 30.8), (5.7, 19.8), (9.4, 19.8), (9.4, 7.5), (10.6, 6.3), (10.6, 2.6), (9.2, 2.6)]),
    # GND pins to the B.Cu pour
    ("GND", "F", 0.3, [(2.7, 30.8), (2.7, 32.3)]), ("GND", "F", 0.3, [(11.3, 30.8), (11.3, 32.3)]),
    # J2 (chain out): escape up to a via each, B.Cu rows west to J1's lines
    ("VDD", "F", 0.3, [(12.3, 30.8), (12.3, 29.5)]), ("VDD", "B", 0.3, [(12.3, 29.5), (3.7, 29.5)]),
    ("SDA", "F", 0.2, [(13.3, 30.8), (13.3, 28.7)]), ("SDA", "B", 0.2, [(13.3, 28.7), (4.7, 28.7)]),
    ("SCL", "F", 0.2, [(14.3, 30.8), (14.3, 27.9)]), ("SCL", "B", 0.2, [(14.3, 27.9), (5.7, 27.9)]),
]
VIAS = [("GND", 8.2, 18.6), ("GND", 2.7, 32.3), ("GND", 11.3, 32.3), ("VDD", 12.3, 29.5), ("VDD", 3.7, 29.5),
        ("SDA", 13.3, 28.7), ("SDA", 4.7, 28.7), ("SCL", 14.3, 27.9), ("SCL", 5.7, 27.9)]
BASE = [(0, BASE_Y), (W, BASE_Y), (W, H), (0, H)]
SILK = [("F", "IN", 4.2, 26.4, 1.0), ("F", "OUT", 12.8, 26.4, 1.0), ("B", "WS SHT45 v1", 5.0, 23.0, 0.8)]


def v(x, y):
    return pcbnew.VECTOR2I(mm(OX + x), mm(OY + y))


def load_fp(fpid):
    lib, name = fpid.split(":")
    fp = pcbnew.FootprintLoad(os.path.join(os.environ["KICAD_FOOTPRINT_DIR"], lib + ".pretty"), name)
    if fp is None:
        sys.exit(f"footprint not found: {fpid}")
    fp.SetFPID(pcbnew.LIB_ID(lib, name))
    return fp


def main():
    net_file, pcb_file = Path(sys.argv[1]), Path(sys.argv[2])
    comps, pads = parse(net_file.read_text())
    board = pcbnew.BOARD()
    ds = board.GetDesignSettings()
    ds.SetCopperLayerCount(2)
    ds.m_TrackMinWidth, ds.m_MinClearance, ds.m_ViasMinSize = mm(0.127), mm(0.127), mm(0.5)
    ds.m_MinThroughDrill, ds.m_HoleToHoleMin, ds.m_CopperEdgeClearance = mm(0.3), mm(0.5), mm(0.3)
    ds.m_SilkClearance = mm(0.15)
    d = ds.m_NetSettings.GetDefaultNetclass()
    d.SetTrackWidth(mm(0.2)); d.SetClearance(mm(0.15)); d.SetViaDiameter(mm(0.6)); d.SetViaDrill(mm(0.3))
    for (x1, y1), (x2, y2) in zip(OUTLINE, OUTLINE[1:] + OUTLINE[:1]):
        s = pcbnew.PCB_SHAPE(board)
        s.SetShape(pcbnew.SHAPE_T_SEGMENT)
        s.SetStart(v(x1, y1)); s.SetEnd(v(x2, y2))
        s.SetLayer(pcbnew.Edge_Cuts); s.SetWidth(mm(0.05))
        board.Add(s)
    nets = {}
    for name in sorted(set(pads.values())):
        nets[name] = pcbnew.NETINFO_ITEM(board, name)
        board.Add(nets[name])
    for ref, (value, fpid, uuid, fields, no_bom) in sorted(comps.items()):
        fp = load_fp(fpid)
        fp.SetReference(ref); fp.SetValue(value)
        fp.SetPath(pcbnew.KIID_PATH("/" + uuid))
        for k, val in fields.items():
            fp.SetField(k, val)
            fp.GetField(k).SetVisible(False)  # LCSC number etc.: data, not silkscreen
        board.Add(fp)
        x, y, deg = PLACE[ref]
        fp.SetPosition(v(x, y)); fp.SetOrientationDegrees(deg)
        for pad in fp.Pads():
            if (ref, pad.GetNumber()) in pads:
                pad.SetNet(nets[pads[(ref, pad.GetNumber())]])
        fp.Value().SetVisible(False)
        fp.Reference().SetVisible(False)  # too small a board for reference text; the CPL carries the designators
    key = {"GND": "1", "VDD": "2", "SDA": "3", "SCL": "4"}
    fps = {f.GetReference(): f for f in board.GetFootprints()}
    net = {k: fps["J1"].FindPadByNumber(n).GetNet() for k, n in key.items()}
    # the hand copper assumes these pad positions: fail loudly if a footprint or rotation changes
    expect = {("U1", "1"): (9.2, 3.4, "SDA"), ("U1", "2"): (9.2, 2.6, "SCL"), ("U1", "3"): (7.8, 2.6, "VDD"),
              ("U1", "4"): (7.8, 3.4, "GND"), ("C1", "1"): (6.4, 6.0, "VDD"), ("C1", "2"): (7.95, 6.0, "GND")}
    expect.update({(j, n): (PLACE[j][0] - 1.5 + i, 30.8, k) for j in ("J1", "J2") for i, (k, n) in enumerate(key.items())})
    for (ref, num), (x, y, k) in expect.items():
        p = fps[ref].FindPadByNumber(num)
        got = (round(pcbnew.ToMM(p.GetPosition().x) - OX, 3), round(pcbnew.ToMM(p.GetPosition().y) - OY, 3))
        if got != (x, y) or p.GetNetname() != net[k].GetNetname():
            sys.exit(f"{ref}.{num}: at {got} on {p.GetNetname()}, copper expects ({x}, {y}) on {net[k].GetNetname()}")
    layer = {"F": pcbnew.F_Cu, "B": pcbnew.B_Cu}
    for k, side, w, pts in TRACKS:
        for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
            t = pcbnew.PCB_TRACK(board)
            t.SetStart(v(x1, y1)); t.SetEnd(v(x2, y2))
            t.SetWidth(mm(w)); t.SetLayer(layer[side]); t.SetNet(net[k])
            board.Add(t)
    for k, x, y in VIAS:
        t = pcbnew.PCB_VIA(board)
        t.SetPosition(v(x, y)); t.SetWidth(mm(0.6)); t.SetDrill(mm(0.3)); t.SetNet(net[k])
        board.Add(t)
    for side in ("F", "B"):  # GND pours on the base only (none on the neck or the sensor island)
        z = pcbnew.ZONE(board)
        z.SetLayer(layer[side]); z.SetNet(net["GND"])
        z.SetLocalClearance(mm(0.25)); z.SetMinThickness(mm(0.2))
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
        z.SetThermalReliefGap(mm(0.25)); z.SetThermalReliefSpokeWidth(mm(0.3))
        z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
        o = z.Outline(); o.NewOutline()
        for x, y in BASE:
            o.Append(mm(OX + x), mm(OY + y))
        board.Add(z)
    for side, text, x, y, size in SILK:
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
    print(f"{pcb_file}: {len(comps)} parts + H1, {W:g} x {H:g} mm, all copper drawn")


if __name__ == "__main__":
    main()
