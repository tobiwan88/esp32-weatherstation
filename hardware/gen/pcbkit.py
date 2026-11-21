"""Shared placement engine for the split boards (power_pcb.py, main_pcb.py); run with $KICAD_PYTHON (pcbnew).

Adapted from gen/pcb_v1.py (weatherstation-v1, routed and DRC clean), which stays untouched as the reference. A board
module describes its floorplan as data; build() turns the schematic netlist into a placed .kicad_pcb:
  W, H            outline (mm, origin top-left, y down)
  FIXED           {ref: (x, y, rotation[, "B"])}: big parts by hand ("B" = body on the back, THT pads stay on both sides)
  BLOCKS          [(anchor ref, {ref: (dx, dy, rotation)})]: critical blocks by hand, offsets from the anchor's position
  NEAR            [(ref, [(pad, target ref, target pad), ...])]: the part goes to the free spot where its named pads
                  are closest to their targets (courtyards never overlap); order = priority (critical blocks first)
  HOLES           {ref: (x, y)}: board-only M3 holes (no symbol, no BOM, no position file)
  COURTYARD       {ref: (x0, y0, x1, y1)}: placement box where the footprint courtyard includes an off-board keepout
  RESERVED        [(anchor ref or None, (x0, y0, x1, y1))]: areas no NEAR part may use (later hand copper, escape bands)
  TIGHT           refs placed without the routing halo
  KEEPOUTS(put)   callback that adds rule areas: put(name, layers, polygon, tracks, vias, pours)
  SILK            [(text, x, y, size, layer)] user silkscreen texts
  TITLE           board text on the back silkscreen
No routing, no hand copper, no outer pours: placement only (planes on In1/In2 are the only zones).
Usage (from tools/build_board.sh): $KICAD_PYTHON gen/<board>_pcb.py design.net board.kicad_pcb classes.json
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

OX, OY = 100.0, 100.0  # board origin on the page
mm = pcbnew.FromMM
LIBS = {"weatherstation": HERE / "lib" / "weatherstation.pretty"}
HOLE_FP = "MountingHole:MountingHole_3.2mm_M3_ISO7380"
HOLE_KEEPOUT = 3.2  # M3 with ISO 7380 head (5.7 mm) or a standoff: no copper within this radius
COPPER = [pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu]


def v(x, y):
    return pcbnew.VECTOR2I(mm(OX + x), mm(OY + y))


def rot(x, y, deg):
    """KiCad footprint rotation (counter-clockwise on screen, y down)."""
    a = math.radians(deg)
    return x * math.cos(a) + y * math.sin(a), -x * math.sin(a) + y * math.cos(a)


def box_at(box, x, y, deg):
    pts = [rot(px, py, deg) for px in (box[0], box[2]) for py in (box[1], box[3])]
    return (x + min(p[0] for p in pts), y + min(p[1] for p in pts), x + max(p[0] for p in pts), y + max(p[1] for p in pts))


def overlaps(a, b):
    return a[0] < b[2] - 1e-6 and b[0] < a[2] - 1e-6 and a[1] < b[3] - 1e-6 and b[1] < a[3] - 1e-6


def rect(b):
    return [(b[0], b[1]), (b[2], b[1]), (b[2], b[3]), (b[0], b[3])]


def circle(x, y, r, n=32):
    r = r / math.cos(math.pi / n)  # polygon outside the circle
    return [(x + r * math.cos(2 * math.pi * k / n), y + r * math.sin(2 * math.pi * k / n)) for k in range(n)]


def edge_poly(board, pts):
    for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]):
        seg = pcbnew.PCB_SHAPE(board)
        seg.SetShape(pcbnew.SHAPE_T_SEGMENT)
        seg.SetStart(v(x1, y1))
        seg.SetEnd(v(x2, y2))
        seg.SetLayer(pcbnew.Edge_Cuts)
        seg.SetWidth(mm(0.05))
        board.Add(seg)


def plane(board, layer, net, pts):
    z = pcbnew.ZONE(board)
    z.SetLayer(layer)
    z.SetNet(board.FindNet(net))
    z.SetLocalClearance(mm(0.25))
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
        z.SetZoneName(name)  # referenced by the board's custom DRC rules
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


def load_fp(fpid):
    lib, name = fpid.split(":")
    d = LIBS.get(lib, Path(os.environ["KICAD_FOOTPRINT_DIR"]) / (lib + ".pretty"))
    fp = pcbnew.FootprintLoad(str(d), name)
    if fp is None:
        sys.exit(f"footprint not found: {fpid}")
    fp.SetFPID(pcbnew.LIB_ID(lib, name))
    return fp


def local_box(fp, ref, override):
    """Courtyard box at rotation 0 around the footprint origin (mm)."""
    if ref in override:
        return override[ref]
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


def build(cfg):
    net_file, pcb_file, classes_file = sys.argv[1], sys.argv[2], sys.argv[3]
    W, H = cfg.W, cfg.H
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

    fixed = dict(cfg.FIXED)
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
    for ref, (hx, hy) in cfg.HOLES.items():  # board-only: no schematic symbol, no BOM, no placement file
        fp = load_fp(HOLE_FP)
        fp.SetReference(ref)
        fp.SetAttributes(pcbnew.FP_BOARD_ONLY | pcbnew.FP_EXCLUDE_FROM_BOM | pcbnew.FP_EXCLUDE_FROM_POS_FILES)
        fp.Value().SetVisible(False)
        fp.Reference().SetLayer(pcbnew.F_Fab)
        fps[ref] = fp
        fixed[ref] = (hx, hy, 0)
    for ref, fp in fps.items():
        board.Add(fp)
        boxes[ref] = local_box(fp, ref, getattr(cfg, "COURTYARD", {}))
        pad_local[ref] = {}
        for q in fp.Pads():
            p = q.GetPosition() - fp.GetPosition()
            pad_local[ref].setdefault(q.GetNumber(), (pcbnew.ToMM(p.x), pcbnew.ToMM(p.y)))

    for anchor, parts in getattr(cfg, "BLOCKS", []):
        ax, ay = fixed[anchor][:2]
        fixed.update({r: (ax + dx, ay + dy, deg) for r, (dx, dy, deg) in parts.items()})
    near_refs = {r for r, _ in cfg.NEAR}
    unknown = sorted((set(fixed) | near_refs) - set(fps))
    unplaced = sorted(set(fps) - set(fixed) - near_refs)
    twice = sorted(set(fixed) & near_refs)
    if unknown or unplaced or twice:
        sys.exit(f"placement: unknown refs {unknown}, refs without a position {unplaced}, placed twice {twice}")

    placed = {}  # ref -> (x, y, rot)
    taken = []   # F-side courtyard boxes in board mm (a back-side THT part blocks the front only with its pads)
    owners = []  # (box, ref) for the overlap report
    back = []    # back-side courtyard boxes
    real_pads = {}

    def put(ref, x, y, deg):
        placed[ref] = (x, y, deg)
        b = box_at(boxes[ref], x, y, deg)
        taken.append(b)
        owners.append((b, ref))

    def pad_at(ref, num):
        if ref in real_pads:
            return real_pads[ref][num]
        x, y, deg = placed[ref]
        px, py = rot(*pad_local[ref][num], deg)
        return x + px, y + py

    def mm_box(b, grow=0.0):
        return (pcbnew.ToMM(b.GetLeft()) - OX - grow, pcbnew.ToMM(b.GetTop()) - OY - grow,
                pcbnew.ToMM(b.GetRight()) - OX + grow, pcbnew.ToMM(b.GetBottom()) - OY + grow)

    for ref, (x, y, deg, *side) in sorted(fixed.items(), key=lambda kv: not kv[0].startswith("H")):
        fp = fps[ref]
        fp.SetPosition(v(x, y))
        fp.SetOrientationDegrees(deg)
        if side == ["B"]:
            fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_TOP_BOTTOM)
            fp.Reference().SetLayer(pcbnew.B_Fab)
            placed[ref] = (x, y, deg)
            for q in fp.Pads():
                b = mm_box(q.GetBoundingBox(), 0.25)
                taken.append(b)
                owners.append((b, ref))
            b = mm_box(fp.GetCourtyard(pcbnew.B_CrtYd).BBox())
            if any(overlaps(b, o) for o in back):
                sys.exit(f"back-side courtyard of {ref} overlaps another back-side part")
            back.append(b)
        else:
            put(ref, x, y, deg)
            if ref in cfg.HOLES:  # standoff or nut under the board: no back-side body there either
                back.append(box_at(boxes[ref], x, y, deg))
        real_pads[ref] = {}
        for q in fp.Pads():
            c = q.GetPosition()
            real_pads[ref].setdefault(q.GetNumber(), (pcbnew.ToMM(c.x) - OX, pcbnew.ToMM(c.y) - OY))
    # hand positions: report boxes that overlap by more than 0.05 mm (abutting courtyards are fine; KiCad DRC decides)
    shrink = lambda b: (b[0] + 0.05, b[1] + 0.05, b[2] - 0.05, b[3] - 0.05)  # noqa: E731
    fixed_clash = sorted({(a, b) for i, (ba, a) in enumerate(owners) for bb, b in owners[i + 1:]
                          if a != b and overlaps(shrink(ba), shrink(bb))})
    for anchor, b in getattr(cfg, "RESERVED", []):
        ax, ay = placed[anchor][:2] if anchor else (0.0, 0.0)
        taken.append((ax + b[0], ay + b[1], ax + b[2], ay + b[3]))

    halo_default = getattr(cfg, "HALO", 0.35)
    tight = getattr(cfg, "TIGHT", set())
    no_room = []

    def place_near(ref, wants):
        targets = [(num, pad_at(tr, tp)) for num, tr, tp in wants]
        cx = sum(t[1][0] for t in targets) / len(targets)
        cy = sum(t[1][1] for t in targets) / len(targets)
        best = None
        step = 0.25
        halo = 0.0 if ref in tight else halo_default
        for r in range(0, 80):  # rings of candidate centres around the targets' mean, out to 20 mm
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

    for ref, wants in cfg.NEAR:
        place_near(ref, wants)
    for ref, (x, y, deg) in placed.items():
        if ref in fixed:
            continue
        fp = fps[ref]
        fp.SetPosition(v(x, y))
        fp.SetOrientationDegrees(deg)

    full = [(0, 0), (W, 0), (W, H), (0, H)]
    plane(board, pcbnew.In1_Cu, "GND", full)
    plane(board, pcbnew.In2_Cu, "GND", full)

    def put_keepout(name, layers, pts, tracks=False, vias=False, pours=True):
        keepout(board, layers, pts, tracks=tracks, vias=vias, pours=pours, name=name)

    for ref in cfg.HOLES:
        hx, hy = placed[ref][:2]
        keepout(board, COPPER, circle(hx, hy, HOLE_KEEPOUT), tracks=True, vias=True, name="hole_" + ref)
    ctx = {"placed": placed, "boxes": boxes, "box": lambda r: box_at(boxes[r], *placed[r]), "pad": pad_at,
           "W": W, "H": H, "COPPER": COPPER, "rect": rect}
    cfg.KEEPOUTS(put_keepout, ctx)
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    for text, x, y, size, layer in getattr(cfg, "SILK", []):
        t = pcbnew.PCB_TEXT(board)
        t.SetText(text)
        t.SetPosition(v(x, y))
        t.SetLayer(pcbnew.F_SilkS if layer == "F" else pcbnew.B_SilkS)
        t.SetMirrored(layer == "B")
        t.SetTextSize(pcbnew.VECTOR2I(mm(size), mm(size)))
        t.SetTextThickness(mm(0.15))
        board.Add(t)
    t = pcbnew.PCB_TEXT(board)
    t.SetText(cfg.TITLE + " ${GIT_SHA}")
    t.SetPosition(v(*cfg.TITLE_AT))
    t.SetLayer(pcbnew.B_SilkS)
    t.SetMirrored(True)
    t.SetTextSize(pcbnew.VECTOR2I(mm(1.0), mm(1.0)))
    t.SetTextThickness(mm(0.15))
    board.Add(t)
    if not pcbnew.SaveBoard(pcb_file, board):
        sys.exit("save failed")
    write(Path(pcb_file).with_suffix(".kicad_pro"), HERE.parent / "rules" / "jlc-4layer.json", classes)
    shutil.copy(HERE.parent / "rules" / cfg.DRU, Path(pcb_file).with_suffix(".kicad_dru"))
    # area budget: front courtyards (back-side THT bodies count with their pads only), holes excluded
    front = [(box_at(boxes[r], *placed[r]) if r not in fixed or fixed[r][3:] != ("B",) else None, r) for r in placed]
    used = sum((b[2] - b[0]) * (b[3] - b[1]) for b, r in front if b and r not in cfg.HOLES and 0 <= b[0] < W + 5)
    used_b = sum((b[2] - b[0]) * (b[3] - b[1]) for b in back)
    if fixed_clash:
        print("FIXED OVERLAP: " + ", ".join(f"{a}/{b}" for a, b in fixed_clash))
    if no_room:
        print(f"PLACEMENT FAILED, no room for: {' '.join(no_room)} (parked right of the board)")
    print(f"{pcb_file}: {len(fps)} footprints, {len(nets)} nets, {W}x{H} mm, front courtyards {used / (W * H):.0%} of "
          f"the board ({used:.0f} of {W * H:.0f} mm2, holes excluded), back bodies and standoffs {used_b:.0f} mm2")
    if no_room or fixed_clash:
        sys.exit(1)
