"""Hand-drawn, locked copper of the power board (run with $KICAD_PYTHON; called by gen/power_pcb.py after placement).

Board-local post-step: the shared engine gen/pcbkit.py places parts and planes only, so this module loads the placed
board, draws the critical copper (engineer's routing order, power-board/BOARD.md "Routing") and saves it again. All
copper here is locked: the autorouter (tools/route_power.sh) keeps it and routes the rest around it.

What is drawn (sources in BOARD.md "Routing"):
  1. BQ25798 power stage as weatherstation-v1 (SLUSDV2C 8.4.1 items 1-7, figure 8-21): PMID/SYS 0402 caps on the
     pin row with F.Cu pours, SW1/SW2 through vias under the IC to L1 beyond the caps, GND pin pour with two plane
     vias, bulk caps joined by pours, BTST/REGN/PROG/ILIM/BATP/SDRV/INT fan-out on the right and left pin columns.
  2. Input paths: VBUS node (M4, C7/C8, C6, M2) with the v1 B.Cu lane, ACFET1/RBFET1 pair M1/M2, PV entry
     J5 -> D1 -> L3 -> M3 -> M4, USB_VBUS trunk J10.19/20 -> M1 on B.Cu.
  3. Battery path: J6 -> F1 -> BAT_PACK trunk (F.Cu, north edge) -> C20/C19 -> BAT pins; BAT_N to U6/M60, PB_MID,
     M61 source to the GND planes; SYS from the SYS bulk caps on B.Cu to J10.1/2.
  4. BC1.2 stub pair J10.7/8 -> U3.6/7 on B.Cu (one via each under U3, length matched), GND stitching beside it.
  5. U3 bottom row south band (CE, SCL, SDA to J10, escape vias for VAC1/ACDRV1/ACDRV2/QON) and TS.
  6. GND stitching vias along the board edge (layout.stitch_pitch_mm, at most 5 mm) outside the hole keepouts.
Coordinates: U3-relative offsets for the charger block (it moves with U3), pad centres read from the placed board
for every other end point; orientations the geometry relies on are asserted.
"""

import math
import sys

import pcbnew

mm = pcbnew.FromMM
OX, OY = 100.0, 100.0
CH = 0.65            # Charge class width (board.yaml, calc/track_width.py: 1.7 A)
CHW = 0.8            # charge trunks where they fit
BIG = (0.6, 0.3)     # power via (Charge class via size)
SIG = (0.45, 0.25)   # signal via


class Copper:
    def __init__(self, board):
        self.b = board
        self.fp = {f.GetReference(): f for f in board.GetFootprints()}
        self.tracks, self.vias, self.pours = [], [], []

    def pad(self, ref, num):
        q = next(p for p in self.fp[ref].Pads() if p.GetNumber() == str(num))
        c = q.GetPosition()
        return round(pcbnew.ToMM(c.x) - OX, 4), round(pcbnew.ToMM(c.y) - OY, 4)

    def rot(self, ref):
        return self.fp[ref].GetOrientationDegrees() % 360

    def t(self, net, layer, w, pts):
        self.tracks.append((net, layer, w, [tuple(p) for p in pts]))

    def v(self, net, x, y, size=SIG):
        self.vias.append((net, x, y, size))

    def z(self, net, layer, pts):
        self.pours.append((net, layer, pts))

    def commit(self):
        b = self.b
        layer = {"F": pcbnew.F_Cu, "B": pcbnew.B_Cu}
        for net, side, pts in self.pours:
            z = pcbnew.ZONE(b)
            z.SetLayer(layer[side])
            z.SetNet(b.FindNet(net))
            z.SetLocalClearance(mm(0.15))
            z.SetMinThickness(mm(0.15))
            z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
            z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
            z.SetAssignedPriority(10)
            o = z.Outline()
            o.NewOutline()
            for x, y in pts:
                o.Append(mm(OX + x), mm(OY + y))
            z.SetLocked(True)
            b.Add(z)
        for net, side, w, pts in self.tracks:
            n = b.FindNet(net)
            assert n is not None and n.GetNetCode() > 0, f"unknown net {net}"
            for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
                if abs(x1 - x2) < 1e-6 and abs(y1 - y2) < 1e-6:
                    continue
                t = pcbnew.PCB_TRACK(b)
                t.SetStart(pcbnew.VECTOR2I(mm(OX + x1), mm(OY + y1)))
                t.SetEnd(pcbnew.VECTOR2I(mm(OX + x2), mm(OY + y2)))
                t.SetWidth(mm(w))
                t.SetLayer(layer[side])
                t.SetNet(n)
                t.SetLocked(True)
                b.Add(t)
        for net, x, y, (d, drill) in self.vias:
            t = pcbnew.PCB_VIA(b)
            t.SetPosition(pcbnew.VECTOR2I(mm(OX + x), mm(OY + y)))
            t.SetWidth(mm(d))
            t.SetDrill(mm(drill))
            t.SetNet(b.FindNet(net))
            t.SetLocked(True)
            b.Add(t)


def mirror(pts):
    return [(-x, y) for x, y in pts]


def charger(c):
    """BQ25798 power stage and pin fan-out, offsets from U3 (weatherstation-v1 CHARGER_COPPER, routed and DRC clean
    there; the ring parts sit at the same offsets on this board, C6/C5 moved by -0.35/+0.25 since review C)."""
    ux, uy = c.pad("U3", "27")[0], c.pad("U3", "5")[1]   # body centre: GND pin x, middle left pin y
    assert c.rot("U3") == 0, "power stage drawn for U3 at rotation 0"
    assert c.rot("L1") == 0 and c.pad("L1", "1")[0] < c.pad("L1", "2")[0], "L1 SW1 pad left"
    r = lambda pts: [(ux + x, uy + y) for x, y in pts]  # noqa: E731

    # pours: PMID (left) and SYS (right) over the 0402 cap and bulk cap pads; GND pin pour between C9/C13 to 2 vias
    pmid = [(-1.0, -1.3), (-0.8, -1.3), (-0.8, -2.45), (-1.1, -2.45), (-1.1, -3.5), (-1.6, -3.5), (-1.6, -8.4),
            (-3.25, -8.4), (-3.25, -2.8), (-1.75, -2.8), (-1.75, -2.3), (-1.0, -2.3)]
    c.z("PMID", "F", r(pmid))
    c.z("SYS", "F", r(mirror(pmid)))
    c.z("GND", "F", r([(-0.1, -1.3), (0.1, -1.3), (0.1, -2.6), (0.8, -2.6), (0.8, -3.4), (0.3, -3.4), (0.3, -4.95),
                       (-0.3, -4.95), (-0.3, -3.4), (-0.8, -3.4), (-0.8, -2.6), (-0.1, -2.6)]))
    for y in (-3.85, -4.65):
        c.v("GND", ux, uy + y)
    # SW1/SW2: pin stub into the body, two vias, B.Cu 0.65 mm up under the cap row, two vias up beside L1's pad
    # (via pairs 0.75 / 1.1 mm apart: separate plane antipads, the lane end stays over In2)
    sw_b = [(-0.45, 0.05), (-0.45, -0.7), (-1.0, -1.25), (-1.0, -8.15)]
    for net, s in (("/Charger/SW1", 1), ("/Charger/SW2", -1)):
        m = (lambda p: p) if s == 1 else mirror
        c.t(net, "F", 0.3, r(m([(-0.45, -1.25), (-0.45, 0.05)])))
        c.t(net, "B", CH, r(m(sw_b)))
        c.t(net, "F", CH, r(m([(-1.0, -8.15), (-1.0, -7.05), (-0.95, -6.0)])))
        for x, y in ((-0.45, -0.7), (-0.45, 0.05), (-1.0, -7.05), (-1.0, -8.15)):
            c.v(net, ux + (x if s == 1 else -x), uy + y)
    # bulk caps: GND pads to their own plane via (item 3: each cap to the plane at its pad)
    for sx in (-1, 1):
        for y in (-3.55, -5.55, -7.55):
            c.t("GND", "F", 0.4, r([(sx * 4.55, y), (sx * 5.45, y)]))
            c.v("GND", ux + sx * 5.45, uy + y)
    for y in (-10.05, -12.55):
        c.t("GND", "F", 0.4, r([(4.55, y), (5.45, y)]))
        c.v("GND", ux + 5.45, uy + y)
    # SYS bulk caps above the pour joined to it at class width
    c.t("SYS", "F", CH, r([(2.655, -7.55), (2.655, -12.55)]))

    # left column: VBUS pins to C6 and a 0.6/0.3 via beside it (v1 VBUS lane on B.Cu), BTST1 to C3, REGN to C5,
    # USB D+/D- into the body to their vias (pair, see bc12()), PV_IN (VAC2) left and down to C2
    c6 = c.pad("C6", "1")
    c.t("VBUS", "F", 0.3, [c.pad("U3", "2"), (ux - 1.9, uy - 1.0), c.pad("U3", "3")])
    c.t("VBUS", "F", 0.3, [c6, (ux - 1.9, uy - 1.0)])
    c.t("VBUS", "F", CH, [(c6[0], c6[1]), (c6[0], c6[1] - 0.75)])
    c.v("VBUS", c6[0], c6[1] - 0.8, BIG)
    c.t("/Charger/BTST1", "F", 0.2, [c.pad("U3", "4"), (ux - 2.9, uy - 0.4), (ux - 3.3, uy), c.pad("C3", "1")])
    c5 = c.pad("C5", "1")
    c.t("REGN", "F", 0.2, [c.pad("U3", "5"), (ux - 2.55, uy), (ux - 2.85, uy + 0.3), (ux - 2.85, uy + 1.05),
                            (c5[0] + 0.2, c5[1] - 0.55)])
    c2 = c.pad("C2", "1")
    assert c.rot("C2") % 180 == 90 and c2[1] < c.pad("C2", "2")[1], "C2 vertical, PV_IN pad on top"
    c.t("/Charger/PV_IN", "F", 0.3, [c.pad("U3", "8"), (c2[0] + 0.17, uy + 1.2), (c2[0] + 0.02, uy + 1.35),
                                     (c2[0] + 0.02, c2[1] - 0.1), c2])

    # STAT (top-left corner pin) out through the corner notch, west in the channel under the PMID pour, to a via in
    # the pocket between C7, C10 and C6 (the router continues on B.Cu to the debug LED D2)
    stat_v = (ux - 5.0, uy - 2.1)
    c.t("/Charger/STAT", "F", 0.15, [(ux - 1.38, uy - 1.9), (ux - 2.0, uy - 1.9), (ux - 2.64, uy - 2.54),
                                     (ux - 4.6, uy - 2.54), stat_v])
    c.v("/Charger/STAT", *stat_v)
    # GND pin 27 and the C9/C13 GND pads tied to the two pour vias by a track too (the pour is the main path)
    g9, g13 = c.pad("C9", "2"), c.pad("C13", "2")
    c.t("GND", "F", 0.2, [g9, (ux, g9[1])])
    c.t("GND", "F", 0.2, [g13, (g13[0], g13[1] + 0.1), (ux, g13[1] + 0.1)])
    # C9/C13 VIN pads to their pins by a track as well (inside the pours; gives calc/emi_check.py its loop path)
    for cap, pin, sx in (("C9", "29", 1), ("C13", "25", -1)):
        cp, pp = c.pad(cap, "1"), c.pad("U3", pin)
        c.t("PMID" if sx == 1 else "SYS", "F", 0.3, [(cp[0], cp[1] + 0.1), (pp[0], cp[1] + 0.63), (pp[0], pp[1] - 0.35)])
    c.t("GND", "F", 0.2, [(ux, uy - 1.9), (ux, uy - 4.65)])
    # REGN local links: C5 to the LED resistor R19 between C2 and TP3; R15 to R17 (ILIM and TS dividers' top)
    r19 = c.pad("R19", "1")
    xr = (c.pad("C2", "2")[0] - 0.31 + c.pad("TP3", "1")[0] + 0.75) / 2
    c.t("REGN", "F", 0.25, [(c5[0], c5[1] + 0.4), (xr, c5[1] + 1.0), (xr, r19[1] - 0.3), (r19[0] - 0.3, r19[1])])
    c.t("REGN", "F", 0.25, [c.pad("R15", "1"), (c.pad("R17", "1")[0], c.pad("R15", "1")[1] + 0.5),
                            c.pad("R17", "1")])

    # right column in pin order (no crossings): SDRV via to C21, BAT pins to C19, INT to its via, PROG to R14,
    # BTST2 to C4, BATP under the body and B.Cu to R13 (sense trace away from SW2, item 6), ILIM to R16, TS to R18
    c.t("/Charger/SDRV", "F", 0.2, [(ux + 1.35, uy - 1.9), (ux + 2.2, uy - 1.9), (ux + 2.775, uy - 2.325)])
    c.v("/Charger/SDRV", ux + 2.775, uy - 2.325)
    c21 = c.pad("C21", "1")
    c.t("/Charger/SDRV", "B", 0.2, [(ux + 2.775, uy - 2.325), (c21[0] - 0.05, uy - 2.175)])
    c.v("/Charger/SDRV", c21[0] - 0.05, uy - 2.175)
    c.t("/Charger/SDRV", "F", 0.2, [(c21[0] - 0.05, uy - 2.175), c21])
    c19 = c.pad("C19", "1")
    c.t("BAT_PACK", "F", 0.4, [(ux + 1.9, uy - 1.1), (c19[0] - 0.25, uy - 1.1)])
    c.t("BAT_PACK", "F", 0.3, [(ux + 1.95, uy - 1.2), (ux + 1.95, uy - 0.85)])
    r13 = c.pad("R13", "1")
    c.t("BAT_PACK", "F", 0.3, [r13, (r13[0], uy - 0.3), (c19[0], uy - 0.3), (c19[0], uy - 0.8)])
    c20 = c.pad("C20", "1")
    c.t("BAT_PACK", "F", CH, [(c19[0] + 0.275, c19[1] - 0.475), (c19[0] + 1.175, c19[1] - 1.375),
                              (c20[0] - 0.075, c20[1] + 0.475)])
    c.t("/Charger/CHG_INT", "F", 0.2, [c.pad("U3", "21"), (ux + 3.05, uy - 0.5)])
    c.v("/Charger/CHG_INT", ux + 3.05, uy - 0.5)
    c.t("/Charger/PROG", "F", 0.2, [c.pad("U3", "20"), (ux + 3.0, uy), (ux + 3.25, uy + 0.25),
                                     (c.pad("R14", "1")[0] - 0.375, uy + 0.25)])
    c.t("/Charger/BTST2", "F", 0.2, [c.pad("U3", "19"), (ux + 2.7, uy + 0.4), (ux + 3.1, uy + 0.8), (ux + 3.1, uy + 1.7),
                                      (c.pad("C4", "1")[0] - 0.475, c.pad("C4", "1")[1] - 0.1)])
    r13b = c.pad("R13", "2")
    c.t("/Charger/BATP", "F", 0.2, [c.pad("U3", "18"), (ux + 1.25, uy + 0.8), (ux + 1.1, uy + 0.65)])
    c.v("/Charger/BATP", ux + 1.1, uy + 0.65)
    yb = uy + 1.45                               # BATP lane 0.6 mm from the SW2 bootstrap lane (item 6)
    c.t("/Charger/BATP", "B", 0.2, [(ux + 1.1, uy + 0.65), (ux + 1.9, yb), (r13b[0] + 0.09, yb)])
    c.v("/Charger/BATP", r13b[0] + 0.09, yb)
    c.t("/Charger/BATP", "F", 0.2, [(r13b[0] + 0.09, yb), r13b])
    # bootstrap caps to their switch node (item 7): C3.2 by B.Cu from the SW1 lane under C6/C7, C4.2 by B.Cu from
    # the SW2 lane east between INT and BATP to a via in the gap between R14's pads, straight down into C4.2
    c32 = c.pad("C3", "2")
    v3 = (c32[0], c32[1] - 1.0)
    c.t("/Charger/SW1", "B", 0.4, [v3, (ux - 1.0, v3[1])])
    c.v("/Charger/SW1", *v3)
    c.t("/Charger/SW1", "F", 0.4, [v3, c32])
    c42 = c.pad("C4", "2")
    r14a, r14b = c.pad("R14", "1"), c.pad("R14", "2")
    assert r14a[0] < c42[0] - 0.3 < r14b[0] and r14a[1] < c42[1], "C4.2 below the gap between R14's pads"
    v4 = ((r14a[0] + r14b[0]) / 2, uy + 0.55)
    c.t("/Charger/SW2", "B", 0.4, [(ux + 1.0, uy - 1.25), (ux + 2.1, uy + 0.55), v4])
    c.v("/Charger/SW2", *v4)
    c.t("/Charger/SW2", "F", 0.3, [v4, (v4[0], c42[1] - 0.65), (c42[0] - 0.22, c42[1] - 0.2)])
    r16 = c.pad("R16", "1")
    c.t("/Charger/ILIM", "F", 0.2, [c.pad("U3", "17"), (ux + 2.5, uy + 1.2), (ux + 2.5, r16[1] - 0.75),
                                     (ux + 3.25, r16[1]), r16])
    r18 = c.pad("R18", "1")
    ts_turn = (ux + 1.4, r18[1] - 1.5)
    c.t("/Battery/TS", "F", 0.2, [(ux + 1.4, uy + 2.0), ts_turn, (ux + 2.9, r18[1]), r18])
    r172 = c.pad("R17", "2")
    yt = (c.pad("R15", "2")[1] + 0.475 + r18[1] - 0.475) / 2
    c.t("/Battery/TS", "F", 0.2, [r172, (r172[0], yt), (r18[0], yt), r18])
    # TS divider bottom (R18) and the VAC2 cap C2 each get their own GND via beside the pad (item 2, cap-pin-via)
    g = c.pad("R18", "2")
    c.t("GND", "F", 0.3, [g, (g[0], g[1] + 0.95)])
    c.v("GND", g[0], g[1] + 0.95)
    g = c.pad("C2", "2")
    c.t("GND", "F", 0.3, [g, (g[0] + 0.8, g[1] + 0.3)])
    c.v("GND", g[0] + 0.8, g[1] + 0.3)
    return ux, uy


def south_band(c, ux, uy):
    """U3 bottom row to J10 (CE, SCL, SDA all on F.Cu, nested so nothing crosses; BOARD.md "Routing"), and escape
    stubs with staggered vias for the west-bound pins (VAC1, ACDRV2, ACDRV1, QON), 0.45 mm vias 1 mm apart."""
    assert c.rot("J10") == 270, "J10 pin 1 at the right end"
    p = lambda n: c.pad("U3", str(n))  # noqa: E731
    j = lambda n: c.pad("J10", str(n))  # noqa: E731
    bot = p(13)[1] + 0.3                       # pad bottom edge of the bottom row
    # CE: straight down, south-west between R19 and D2, down the J10 column gap into pin 16; R23 (pull-up) below J10.16
    ce_y = (c.pad("R19", "2")[1] + 0.32 + c.pad("D2", "1")[1] - 0.475) / 2
    gap_x = (j(15)[0] + j(13)[0]) / 2
    ce_x = min(c.pad("D2", "1")[0] - 0.44 - 0.27, gap_x - 0.29)
    yd = ce_y - 0.95
    c.t("/Charger/CHG_CE", "F", 0.2, [p(13), (p(13)[0], yd), (p(13)[0] - 0.95, ce_y), (ce_x, ce_y),
                                       (ce_x, j(15)[1] - 1.6), (gap_x, j(15)[1] - 1.31), (gap_x, j(16)[1]), j(16)])
    r23 = c.pad("R23", "1")
    assert r23[1] > j(16)[1] + 1.0, "R23 sits below J10.16"
    c.t("/Charger/CHG_CE", "F", 0.2, [j(16), (j(16)[0], r23[1] - 0.5), (r23[0], r23[1] - 0.2), r23])
    # SCL: down beside CE, south-west parallel to it, down the gap left of J10.11, into pin 12
    scl_x = j(11)[0] - 0.85 - 0.42
    y0 = yd + 0.4
    c.t("/Charger/CHG_SCL", "F", 0.2, [p(14), (p(14)[0], y0), (scl_x, y0 + p(14)[0] - scl_x),
                                        (scl_x, j(12)[1] - 0.24), (scl_x + 0.24, j(12)[1]), j(12)])
    # SDA: straight down, into pin 11 from above
    c.t("/Charger/CHG_SDA", "F", 0.2, [p(15), (p(15)[0], j(11)[1] - 2.3), (j(11)[0] + 0.5, j(11)[1] - 1.1),
                                        (j(11)[0] + 0.5, j(11)[1] - 0.6)])
    # west-bound pins: stubs to a diagonal row of vias (each lane turns once, no crossing); the router continues
    vias = {9: (p(9)[0] - 0.45, bot + 0.6), 10: (p(10)[0] - 0.4, bot + 1.4), 11: (p(11)[0] - 0.35, bot + 2.25),
            12: (p(12)[0] - 0.25, bot + 3.1)}
    nets = {9: "USB_VBUS", 10: "/Charger/ACDRV2", 11: "/Charger/ACDRV1", 12: "/Charger/QON"}
    for n, (vx, vy) in vias.items():
        x = p(n)[0]
        start = (x, p(n)[1] + 0.25) if n == 9 else p(n)
        c.t(nets[n], "F", 0.2, [start, (x, vy - (x - vx)), (vx, vy)])
        c.v(nets[n], vx, vy)
    # QON on B.Cu below the other lanes to a via under the test pad TP3
    tp3 = c.pad("TP3", "1")
    v12 = vias[12]
    tv = (tp3[0], tp3[1] + 1.2)
    c.t("/Charger/QON", "B", 0.2, [v12, (v12[0] - 0.55, v12[1] + 0.55), (tv[0] + 0.6, v12[1] + 0.55), tv])
    c.v("/Charger/QON", *tv)
    c.t("/Charger/QON", "F", 0.3, [tv, tp3])


def bc12(c, ux, uy):
    """BC1.2 detection stubs J10.7/8 (D+/D-) to U3.6/7: F.Cu stub into the body to one via each, then a coupled
    pair on B.Cu (W 0.27, S 0.15, USB net class, 90 ohm per calc/impedance.py) over the solid In2 plane straight to
    the THT pins; D+ carries a meander so the two lengths match (D- reaches the lower J10 row). GND stitching vias
    beside the pair. Lengths and skew: calc/power_route_check.py."""
    dp, dn = "/Charger/USB_DP", "/Charger/USB_DN"
    p6, p7 = c.pad("U3", "6"), c.pad("U3", "7")
    j7, j8 = c.pad("J10", "7"), c.pad("J10", "8")
    w, pitch = 0.27, 0.42
    vp = (ux - 1.2, p6[1] - 0.05)               # vias under the body, clear of the SW1 vias and the left pins
    vn = (ux - 1.2, p7[1] + 0.3)
    c.t(dp, "F", 0.2, [p6, vp])
    c.t(dn, "F", 0.2, [p7, (p7[0] + 0.4, p7[1]), vn])
    c.v(dp, *vp)
    c.v(dn, *vn)
    # B.Cu: D+ upper/right, D- lower/left of the pair
    yp = vp[1] + 0.93                            # horizontal under the bottom pin row
    yn = yp + pitch
    xn_v = j7[0] - 0.85 - 0.42                   # D- down the gap between J10.9 and J10.7
    xp_v = xn_v + pitch
    turn_p = 30.9 - 30.0 + ux                    # D+ turns south-east here
    cp = yp - turn_p                             # D+ diagonal: y = x + cp
    cn = cp + pitch * math.sqrt(2)               # D- diagonal 0.42 mm away
    yp_v, yn_v = xp_v + cp, xn_v + cn            # where the diagonals reach the verticals
    split = j7[1] - 1.6                          # pair splits above the J10 pads
    pts_n = [vn, (vn[0] + (yn - vn[1]), yn), (yn - cn, yn), (xn_v, yn_v), (xn_v, j8[1]), j8]
    c.t(dn, "B", w, pts_n)
    pts_p = [vp, (vp[0] + (yp - vp[1]), yp), (turn_p, yp), (xp_v, yp_v)]
    tail = [(j7[0], split + (j7[0] - xp_v)), j7]
    plen = lambda pts: sum(math.dist(a, b) for a, b in zip(pts, pts[1:]))  # noqa: E731
    ln = plen([p7, (p7[0] + 0.4, p7[1]), vn]) + plen(pts_n)
    base = math.dist(p6, vp) + plen(pts_p + [(xp_v, split)] + tail)
    extra = ln - base
    # meander on D+ (outer side, east): rectangular bumps with 45-degree corners, each adds 2 h - ch (8 - 4 sqrt 2)
    mid = []
    if extra > 0.05:
        n = 2
        ch = 0.25                                # corner chamfer
        h = extra / n / 2 + ch * (4 - 2 * math.sqrt(2))
        y = yp_v + 0.8
        for _ in range(n):
            x0 = xp_v
            mid += [(x0, y), (x0 + ch, y + ch), (x0 + h - ch, y + ch), (x0 + h, y + 2 * ch), (x0 + h, y + 0.6),
                    (x0 + h - ch, y + 0.6 + ch), (x0 + ch, y + 0.6 + ch), (x0, y + 0.6 + 2 * ch)]
            y += 0.6 + 2 * ch + 0.8
        assert y < split, "meander does not fit above the J10 split"
    c.t(dp, "B", w, pts_p + mid + [(xp_v, split)] + tail)
    # GND stitching beside the pair (return path between In1/In2 next to the B.Cu pair), 0.6 mm off the pair edge
    for y in (split - 2.4, split - 0.5):
        c.v("GND", xn_v - w / 2 - 0.6 - 0.225, y)
    c.v("GND", xp_v + w / 2 + 0.6 + 0.225, split - 0.5)


def inputs(c, ux, uy):
    """VBUS node, USB and PV entry paths, ACFET/RBFET pairs (BQ25798 figure 8-2), drawn at Charge-class width."""
    assert c.rot("M1") == 90 and c.rot("M2") == 270 and c.rot("M3") == 180 and c.rot("M4") == 0
    # VBUS: M4 drain up between C8 and C7 to their VBUS pads, a via pair down to B.Cu east to the v1 VBUS lane
    m4 = c.pad("M4", "3")
    c7, c8 = c.pad("C7", "1"), c.pad("C8", "1")
    xg = (c7[0] - 0.725 + c8[0] + 0.725) / 2     # gap between the two caps
    yg = c.pad("C7", "2")[1]
    c.t("VBUS", "F", CH, [(m4[0] + 0.3, m4[1]), (xg, m4[1] - 0.3), (xg, yg + 1.0)])
    c.t("VBUS", "F", 0.5, [(xg, yg + 1.0), (xg, yg - 0.65)])           # 0.8 mm gap between the GND pads
    c.t("VBUS", "F", CH, [(xg, yg - 0.65), (xg, c7[1])])
    c.t("VBUS", "F", CH, [(c8[0], c8[1]), (c7[0], c7[1])])
    vb = (xg, c7[1] - 1.05)
    c.t("VBUS", "F", CH, [(xg, c7[1]), vb])
    # C7/C8 GND pads to their own plane vias below them (item 4: input caps to GND at the pad)
    for cap in ("C7", "C8"):
        g = c.pad(cap, "2")
        gv = (g[0] + (0.15 if cap == "C7" else 0.0), g[1] + 1.1)
        c.t("GND", "F", 0.5, [g, gv])
        c.v("GND", *gv)
    c.v("VBUS", *vb, BIG)
    c6v = (c.pad("C6", "1")[0], c.pad("C6", "1")[1] - 0.8)
    lane_x = ux - 2.4                            # v1 VBUS lane on B.Cu, between the PMID bulk caps' vias and SW1
    m2 = c.pad("M2", "3")
    top = (lane_x, m2[1] + 1.35)
    c.t("VBUS", "B", CH, [vb, (lane_x - 1.0, vb[1]), (lane_x, vb[1] + 1.0)])
    c.t("VBUS", "B", CH, [c6v, (lane_x, c6v[1] - (c6v[0] - lane_x) if c6v[0] > lane_x else c6v[1]), top])
    c.v("VBUS", *top, BIG)
    c.t("VBUS", "F", CH, [top, (top[0] + 0.3, top[1]), (m2[0], m2[1] + 0.6)])
    # ACFET1/RBFET1: common source ACF1_MID, gate ACG1 from R11 to both gates (M1.1 F.Cu, M2.1 over B.Cu)
    c.t("/Inputs/ACF1_MID", "F", CHW, [c.pad("M1", "2"), c.pad("M2", "2")])
    m11, m21 = c.pad("M1", "1"), c.pad("M2", "1")
    c.t("/Inputs/ACG1", "F", 0.3, [c.pad("R11", "1"), m11])
    g1, g2 = (m11[0], m11[1] + 1.45), (m21[0], m21[1] + 1.25)
    c.t("/Inputs/ACG1", "F", 0.25, [m11, g1])
    c.t("/Inputs/ACG1", "B", 0.25, [g1, (g2[0] - 0.3, g1[1]), g2])
    c.t("/Inputs/ACG1", "F", 0.25, [g2, m21])
    c.v("/Inputs/ACG1", *g1)
    c.v("/Inputs/ACG1", *g2)
    # USB_VBUS: J10.19/20 (THT) on B.Cu north west of the PV FETs, diagonal to two 0.6/0.3 vias at M1's drain, C1
    m13, c1 = c.pad("M1", "3"), c.pad("C1", "1")
    j19, j20 = c.pad("J10", "19"), c.pad("J10", "20")
    ua, ub = (m13[0], m13[1] - 1.22), (m13[0] - 0.8, m13[1] - 0.98)
    x_up = 17.0
    c.t("USB_VBUS", "B", CHW, [ring(j19, (x_up, j19[1] - 2.14)), (x_up, j19[1] - 2.14), (x_up, 13.0), (ub[0] - 0.4, ub[1] + 0.2), ub])
    c.t("USB_VBUS", "B", CHW, [ub, ua])
    for p in (ua, ub):
        c.v("USB_VBUS", *p, BIG)
        c.t("USB_VBUS", "F", 0.6, [p, (m13[0], m13[1] - 0.45)])
    c.t("USB_VBUS", "F", 0.4, [ua, c1])
    c.t("USB_VBUS", "F", 0.5, [ring(j19, j20), ring(j20, j19)])
    # PV entry (BQ25798 fig. 8-2 port 2): J5 -> D1 clamp right at the connector (wide, short, both pins) -> CM choke
    # L3 -> PV_IN -> ACFET2 M3 -> ACF2_MID -> RBFET2 M4 -> VBUS. PV_RAW and PV_N_RAW cross between D1 and L3:
    # PV_N_RAW (panel minus, the choke's return winding) takes B.Cu from J5.2 to two vias under L3.4.
    assert c.rot("D1") == 90 and c.pad("D1", "1")[1] > c.pad("D1", "2")[1], "D1 cathode (PV_RAW) at the bottom"
    j51, j52 = c.pad("J5", "1"), c.pad("J5", "2")
    d11, d12 = c.pad("D1", "1"), c.pad("D1", "2")
    l31, l32, l33, l34 = (c.pad("L3", n) for n in "1234")
    c.t("/Inputs/PV_RAW", "F", 1.0, [j51, (j51[0] + 1.2, j51[1]), (d11[0] - 0.8, d11[1] - 0.6), d11])
    xr = (d11[0] + 1.15 + l34[0] - 0.575) / 2 - 0.2
    c.t("/Inputs/PV_RAW", "F", CHW, [d11, (xr, d11[1]), (xr, l31[1]), l31])
    c.t("/Inputs/PV_N_RAW", "F", 1.0, [j52, (j52[0] + 1.2, j52[1]), (d12[0] - 0.8, d12[1] + 0.6), d12])
    pv_n = [(l34[0] - 0.35, l34[1] + 1.4), (l34[0] + 0.45, l34[1] + 1.4)]
    for p in pv_n:
        c.v("/Inputs/PV_N_RAW", *p, BIG)
        c.t("/Inputs/PV_N_RAW", "F", 0.6, [p, (p[0], l34[1])])
    c.t("/Inputs/PV_N_RAW", "B", CHW, [j52, (j52[0] + 2.0, j52[1]), (xr - 1.6, j52[1]),
                                       (pv_n[0][0] - 0.2, pv_n[0][1] - 0.2), pv_n[0], pv_n[1]])
    # L3.3 (GND side of the return winding) to the planes by three vias
    for dy in (0.2, 1.05):
        c.v("GND", l33[0] + 1.1, l33[1] + dy, BIG)
        c.t("GND", "F", CHW, [l33, (l33[0] + 1.1, l33[1] + dy)])
    m33 = c.pad("M3", "3")
    c.t("/Charger/PV_IN", "F", CHW, [l32, (l32[0] + 1.6, l32[1]), (m33[0] - 0.4, m33[1] - 0.45), m33])
    c.t("/Inputs/ACF2_MID", "F", CHW, [c.pad("M4", "2"), c.pad("M3", "2")])


def battery(c, ux, uy):
    """Cell path: J6.1 -> F1 -> BAT_PACK trunk along the north edge -> C20 -> C19/BAT pins; J6.2 BAT_N -> U6 VSS,
    C60 -> M60 -> PB_MID -> M61 -> GND planes; SYS bulk caps -> B.Cu -> J10.1/2. Widths: Charge class or wider."""
    assert c.rot("F1") == 0 and c.rot("M60") == 0 and c.rot("M61") == 180 and c.rot("J6") == 90
    j61, j62 = c.pad("J6", "1"), c.pad("J6", "2")
    f11, f12 = c.pad("F1", "1"), c.pad("F1", "2")
    # BAT_CON on B.Cu around J6.2 to two vias between TH1 and F1, F.Cu into F1.1
    bv = [(f11[0] - 1.06, f11[1] - 0.85), (f11[0] - 1.06, f11[1] + 0.35)]
    c.t("/Battery/BAT_CON", "B", CHW, [j61, (j61[0] + 1.5, j61[1] - 1.1), (j61[0] + 1.5, bv[1][1] + 0.5), bv[1], bv[0]])
    for p in bv:
        c.v("/Battery/BAT_CON", *p, BIG)
        c.t("/Battery/BAT_CON", "F", 0.6, [p, (f11[0], p[1])])
    # BAT_N: J6.2 east under F1 to M60's source, U6 VSS tapped at the cell side, C60 return
    m602, u66, c602 = c.pad("M60", "2"), c.pad("U6", "6"), c.pad("C60", "2")
    yb = 12.25
    c.t("/Battery/BAT_N", "F", CH, [j62, (j62[0] + 0.9, yb), (m602[0] - 0.9, yb), (m602[0] - 0.45, m602[1])])
    c.t("/Battery/BAT_N", "F", 0.3, [(u66[0], yb), u66])
    # C60 (HY2112 VDD cap) return: around C60's right side up to M60's source pad, not through the VDD pad
    m60x = c602[0] + 0.81
    c.t("/Battery/BAT_N", "F", 0.3, [c602, (m60x, c602[1]), (m60x, m602[1] + 0.3), (m602[0] + 0.5, m602[1])])
    # PB_MID (drain-drain) and M61 source to GND by three vias (pack minus = system GND)
    c.t("/Battery/PB_MID", "F", CHW, [c.pad("M60", "3"), c.pad("M61", "3")])
    m612 = c.pad("M61", "2")
    for dx, dy in ((1.29, 0.0), (1.29, -0.85), (0.0, -1.0)):
        c.v("GND", m612[0] + dx, m612[1] + dy, BIG)
        c.t("GND", "F", 0.6, [m612, (m612[0] + dx, m612[1] + dy)])
    # BAT_PACK trunk: F1.2 north, along y 4.5 east, down to C20 (charge current 1.5 A)
    c20 = c.pad("C20", "1")
    yt = 4.5
    c.t("BAT_PACK", "F", 1.0, [f12, (f12[0], yt + 0.6), (f12[0] + 0.6, yt), (c20[0] - 0.6, yt), (c20[0], yt + 0.6), c20])
    # SYS: four 0.6/0.3 vias between the SYS bulk caps, B.Cu east and south to J10.1/2 (THT)
    s16, s17 = c.pad("C16", "1"), c.pad("C17", "1")
    yv1, yv2 = (s16[1] + s17[1]) / 2 - 0.0, (s17[1] + c.pad("C18", "1")[1]) / 2
    sv = [(s16[0], yv1), (s16[0] + 0.85, yv1), (s16[0], yv2), (s16[0] + 0.85, yv2)]
    for p in sv:
        c.v("SYS", *p, BIG)
    c.t("SYS", "F", CH, [sv[0], sv[1]])
    c.t("SYS", "F", CH, [sv[2], sv[3]])
    j1, j2 = c.pad("J10", "1"), c.pad("J10", "2")
    xs = 40.6
    c.t("SYS", "B", 1.0, [sv[0], sv[1], (xs - 0.5, yv1), (xs, yv1 + 0.5), (xs, j1[1] - 1.4),
                          ring(j1, (xs, j1[1] - 1.4))])
    c.t("SYS", "B", CH, [sv[2], sv[3], (sv[3][0] + 0.6, yv2), (sv[3][0] + 0.6, yv1)])
    c.t("SYS", "F", 1.0, [ring(j1, j2), ring(j2, j1)])


def stitching(c, W, H):
    """GND vias along the board edge (pitch <= 3 mm), 0.9 mm inside the outline, outside the hole keepouts and away
    from pads; a candidate that hits copper is skipped (DRC decides; the loop only avoids obvious clashes)."""
    holes = [(3.5, 3.5), (46.5, 24.0), (3.5, 46.5), (46.5, 46.5)]
    pads = []
    for f in c.b.GetFootprints():
        for q in f.Pads():
            bb = q.GetBoundingBox()
            pads.append((pcbnew.ToMM(bb.GetLeft()) - OX, pcbnew.ToMM(bb.GetTop()) - OY,
                         pcbnew.ToMM(bb.GetRight()) - OX, pcbnew.ToMM(bb.GetBottom()) - OY))
    inset, pitch = 0.9, 3.0                    # board.yaml layout.stitch_pitch_mm [2, 3]
    pts = []
    for edge in range(4):
        n = int((W - 2 * inset) / pitch) + 1
        for k in range(n + 1):
            s = inset + k * (W - 2 * inset) / n
            pts.append([(s, inset), (W - inset, s), (s, H - inset), (inset, s)][edge])
    seen = set()
    for x, y in pts:
        key = (round(x, 2), round(y, 2))
        if key in seen:
            continue
        seen.add(key)
        if any(math.dist((x, y), h) < 4.0 for h in holes):   # keepout 3.2 + via + plane neck
            continue
        if any(b[0] - 0.6 < x < b[2] + 0.6 and b[1] - 0.6 < y < b[3] + 0.6 for b in pads):
            continue
        if any(t[0] != "GND" and any(seg_dist((x, y), a, bb) < t[2] / 2 + 0.45 for a, bb in zip(t[3], t[3][1:]))
               for t in c.tracks):
            continue
        c.v("GND", round(x, 3), round(y, 3))
    # beside each hole: the nearest legal points on the inset line (hole keepouts reach the edge; fence gap there
    # = keepout chord only)
    for hx, hy in holes:
        for horiz, line in ((True, inset), (True, H - inset), (False, inset), (False, W - inset)):
            d = abs((hy if horiz else hx) - line)
            if d >= 4.0:
                continue
            off = math.sqrt(4.0 ** 2 - d * d) + 0.01
            for sgn in (-1, 1):
                x, y = ((hx + sgn * off, line) if horiz else (line, hy + sgn * off))
                if not (inset <= x <= W - inset and inset <= y <= H - inset):
                    continue
                if any(math.dist((x, y), (v[1], v[2])) < 1.2 for v in c.vias if v[0] == "GND"):
                    continue
                if any(b[0] - 0.6 < x < b[2] + 0.6 and b[1] - 0.6 < y < b[3] + 0.6 for b in pads) or any(
                        t[0] != "GND" and any(seg_dist((x, y), a, bb) < t[2] / 2 + 0.45 for a, bb in zip(t[3], t[3][1:]))
                        for t in c.tracks):
                    continue
                c.v("GND", round(x, 3), round(y, 3))


def ring(pad, toward, r=0.55):
    """Point on a THT pad's copper ring towards `toward`: tracks end there, not at the drill centre, so no track
    runs over the plane antipad inside the pad (calc/emi_check.py 'track over plane void')."""
    d = math.dist(pad, toward)
    return (pad[0] + (toward[0] - pad[0]) * r / d, pad[1] + (toward[1] - pad[1]) * r / d)


def seg_dist(p, a, b):
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    L = dx * dx + dy * dy
    s = 0 if L == 0 else max(0, min(1, ((p[0] - ax) * dx + (p[1] - ay) * dy) / L))
    return math.dist(p, (ax + s * dx, ay + s * dy))


def gnd_vias(c, W, H, keys):
    """Each listed GND pad (decoupling and divider returns) its own plane via: the first spot around the pad, 0.42 mm
    beyond its edge, that clears other nets' pads (0.15 mm), hand tracks and vias, the outline and hole keepouts; a
    0.3 mm stub joins it. Pads that already have one (a hand GND via within 1.3 mm) are skipped."""
    holes = [(3.5, 3.5), (46.5, 24.0), (3.5, 46.5), (46.5, 46.5)]
    boxes = []
    for f in c.b.GetFootprints():
        for q in f.Pads():
            bb = q.GetBoundingBox()
            boxes.append((q.GetNetname(), f.GetReference() + "." + q.GetNumber(), q.GetAttribute() == pcbnew.PAD_ATTRIB_SMD,
                          pcbnew.ToMM(bb.GetLeft()) - OX, pcbnew.ToMM(bb.GetTop()) - OY,
                          pcbnew.ToMM(bb.GetRight()) - OX, pcbnew.ToMM(bb.GetBottom()) - OY))
    r = SIG[0] / 2
    for key in keys:
        ref, num = key.split(".")
        px, py = c.pad(ref, num)
        if any(v[0] == "GND" and math.dist((v[1], v[2]), (px, py)) < 1.3 for v in c.vias):
            continue
        box = next(b for b in boxes if b[1] == key)
        hx, hy = (box[5] - box[3]) / 2, (box[6] - box[4]) / 2
        cands = [(px + dx * (hx + e), py + dy * (hy + e)) for e in (0.42, 0.7)
                 for dx, dy in ((0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (1, -1), (-1, 1), (-1, -1))]

        def free(x, y):
            if not (1.0 <= x <= W - 1.0 and 1.0 <= y <= H - 1.0):
                return False
            if any(math.dist((x, y), h) < 3.2 + r + 0.1 for h in holes):
                return False
            for net, k2, smd, x0, y0, x1, y1 in boxes:
                gap = 0.15 if net != "GND" else (0.15 if smd else -1)
                if x0 - gap - r < x < x1 + gap + r and y0 - gap - r < y < y1 + gap + r:
                    return False
            for net, layer, w, pts in c.tracks:
                if net != "GND" and any(seg_dist((x, y), a, b) < w / 2 + 0.15 + r for a, b in zip(pts, pts[1:])):
                    return False
            return not any(math.dist((x, y), (v[1], v[2])) < (v[3][0] / 2 + r + 0.2) for v in c.vias)
        spot = next((p for p in cands if free(*p)), None)
        if spot is None:
            print(f"gnd_vias: no spot beside {key} (left to the planes router)")
            continue
        c.t("GND", "F", 0.3, [(px, py), spot])
        c.v("GND", round(spot[0], 3), round(spot[1], 3))


def fanout_area(board, ux, uy):
    """Named rule area 'bc12_fanout' (outer layers, no pours) over U3's 0.4 mm pin field where the BC1.2 pair leaves
    the pins: calc/emi_check.py (critical.yaml emi.fanout_area) measures pair spacing outside it only."""
    z = pcbnew.ZONE(board)
    z.SetIsRuleArea(True)
    z.SetZoneName("bc12_fanout")
    ls = pcbnew.LSET()
    ls.AddLayer(pcbnew.F_Cu)
    ls.AddLayer(pcbnew.B_Cu)
    z.SetLayerSet(ls)
    z.SetDoNotAllowZoneFills(True)
    z.SetDoNotAllowTracks(False)
    z.SetDoNotAllowVias(False)
    z.SetDoNotAllowPads(False)
    z.SetDoNotAllowFootprints(False)
    o = z.Outline()
    o.NewOutline()
    for x, y in ((ux - 2.6, uy - 0.2), (ux + 2.0, uy - 0.2), (ux + 2.0, uy + 2.9), (ux - 2.6, uy + 2.9)):
        o.Append(mm(OX + x), mm(OY + y))
    z.SetLocked(True)
    board.Add(z)


def draw(pcb_file, W, H):
    board = pcbnew.LoadBoard(pcb_file)
    c = Copper(board)
    ux, uy = charger(c)
    south_band(c, ux, uy)
    bc12(c, ux, uy)
    inputs(c, ux, uy)
    battery(c, ux, uy)
    gnd_vias(c, W, H, ["C20.2", "C21.2", "C19.2", "C1.2", "R16.2", "R14.2", "TH1.2", "C5.2", "C6.2", "R61.2"])
    stitching(c, W, H)
    c.commit()
    fanout_area(board, ux, uy)
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    if not pcbnew.SaveBoard(pcb_file, board, True):
        sys.exit("save failed")
    print(f"{pcb_file}: hand copper {sum(len(t[3]) - 1 for t in c.tracks)} segments, {len(c.vias)} vias, "
          f"{len(c.pours)} pours (locked)")
