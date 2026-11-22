"""After routing the main board: outer GND pours and GND stitching vias (run with $KICAD_PYTHON).

1. GND pours on F.Cu and B.Cu (whole outline; rule areas keep them out of the antenna strip, the holes and the BMP580
   body; thermal reliefs from board.yaml `layout.thermal_relief`; islands removed). Clearance 0.3 mm, the USB net class
   keeps 0.6 mm (net class clearance).
2. Edge fence (REQUIREMENTS E2: every 5 mm or closer): a GND via every PITCH mm along each edge, 0.85 mm inside it, at the
   nearest free spot within +-SLIDE mm of the nominal position; gaps that stay open are printed.
3. Interior grid: a GND via at every GRID mm grid point that is free (ties both pours to In1/In2).
Free = outside via rule areas, other nets' copper at their class clearance (USB 0.6 mm), 0.5 mm between drill holes,
0.15 mm copper to same-net SMD pads (custom rule), never in a pad. Locked like the hand copper.
Usage: main_stitch.py board.kicad_pcb   (edits in place; .kicad_pro/.kicad_dru next to it)
"""

import math
import sys

import pcbnew

mm = pcbnew.FromMM
PITCH, SLIDE, INSET, GRID = 3.5, 1.4, 0.85, 4.0
VIA_D, VIA_DRILL = 0.6, 0.3
CLASS_CLEAR = {"USB": 0.6}
path = sys.argv[1]
board = pcbnew.LoadBoard(path)
gnd = board.FindNet("GND")
box = board.GetBoardEdgesBoundingBox()
X0, Y0, X1, Y1 = (pcbnew.ToMM(v) for v in (box.GetLeft(), box.GetTop(), box.GetRight(), box.GetBottom()))
# W x H in mm, board origin at (X0, Y0)

keep = [z for z in board.Zones() if z.GetIsRuleArea() and z.GetDoNotAllowVias()]
pads = [q for f in board.GetFootprints() for q in f.Pads()]
tracks = list(board.GetTracks())
added = []


def clear_of(net_item):
    nc = net_item.GetNetClassName() if hasattr(net_item, "GetNetClassName") else ""
    return max(0.15, CLASS_CLEAR.get(nc, 0.0))


def free(x, y):
    p = pcbnew.VECTOR2I(mm(x), mm(y))
    r = mm(VIA_D / 2)
    circ = pcbnew.SHAPE_CIRCLE(p, r)
    if any(z.Outline().Contains(p) or z.Outline().Collide(p, r) for z in keep):
        return False
    for q in pads:
        if q.GetBoundingBox().GetInflated(mm(1.5)).Contains(p) is False:
            continue
        for layer in (pcbnew.F_Cu, pcbnew.B_Cu, pcbnew.In1_Cu):
            if not q.IsOnLayer(layer):
                continue
            same = q.GetNetCode() == gnd.GetNetCode()
            gap = 0.15 if same else clear_of(q)
            if q.GetEffectiveShape(layer).Collide(circ, mm(gap) - 1):
                return False
        if q.HasHole() and (q.GetPosition() - p).EuclideanNorm() < mm(0.5 + VIA_DRILL / 2) + q.GetDrillSize().x // 2:
            return False
    for t in tracks + added:
        if t.GetClass() == "PCB_VIA":
            d = (t.GetPosition() - p).EuclideanNorm()
            if d < mm(0.5 + VIA_DRILL / 2) + t.GetDrill() // 2:
                return False
            if t.GetNetCode() != gnd.GetNetCode() and d < r + t.GetWidth(pcbnew.F_Cu) // 2 + mm(clear_of(t)):
                return False
        elif t.GetNetCode() != gnd.GetNetCode():
            if t.GetEffectiveShape(t.GetLayer()).Collide(circ, mm(clear_of(t)) - 1):
                return False
    return True


def put(x, y):
    v = pcbnew.PCB_VIA(board)
    v.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y)))
    v.SetWidth(mm(VIA_D))
    v.SetDrill(mm(VIA_DRILL))
    v.SetNet(gnd)
    v.SetLocked(True)
    board.Add(v)
    added.append(v)


# 1. pours
for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
    z = pcbnew.ZONE(board)
    z.SetLayer(layer)
    z.SetNet(gnd)
    z.SetLocalClearance(mm(0.3))
    z.SetMinThickness(mm(0.25))
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
    z.SetThermalReliefGap(mm(0.25))
    z.SetThermalReliefSpokeWidth(mm(0.3))
    z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
    z.SetAssignedPriority(0)
    z.SetZoneName("gnd_pour_" + ("F" if layer == pcbnew.F_Cu else "B"))
    o = z.Outline()
    o.NewOutline()
    for x, y in ((X0, Y0), (X1, Y0), (X1, Y1), (X0, Y1)):
        o.Append(mm(x), mm(y))
    board.Add(z)

# 2. edge fence
gaps = []
for (ax, ay), (bx, by), (nx, ny) in (((X0, Y0), (X1, Y0), (0, 1)), ((X1, Y0), (X1, Y1), (-1, 0)),
                                     ((X1, Y1), (X0, Y1), (0, -1)), ((X0, Y1), (X0, Y0), (1, 0))):
    L = math.dist((ax, ay), (bx, by))
    ux, uy = (bx - ax) / L, (by - ay) / L
    n = int(L // PITCH)
    last = None
    for k in range(1, n + 1):
        s0 = k * L / (n + 1)
        spot = None
        for ds in sorted({round(i * 0.1, 1) for i in range(-int(SLIDE * 10), int(SLIDE * 10) + 1)}, key=abs):
            for inset in (INSET, INSET + 0.4, INSET + 0.8):
                x, y = ax + ux * (s0 + ds) + nx * inset, ay + uy * (s0 + ds) + ny * inset
                if free(x, y):
                    spot = (x, y)
                    break
            if spot:
                break
        if spot:
            put(*spot)
        else:
            gaps.append((round(ax + ux * s0 - X0, 1), round(ay + uy * s0 - Y0, 1)))
# 3. interior grid
grid = 0
y = Y0 + GRID / 2
while y < Y1 - 2:
    x = X0 + GRID / 2
    while x < X1 - 2:
        if free(x, y):
            put(x, y)
            grid += 1
        x += GRID
    y += GRID
pcbnew.ZONE_FILLER(board).Fill(board.Zones())
pcbnew.SaveBoard(path, board)
print(f"stitch: {len(added) - grid} edge vias (pitch {PITCH} mm), {grid} grid vias, outer GND pours F.Cu/B.Cu; "
      f"edge spots without room (board mm): {gaps}")
