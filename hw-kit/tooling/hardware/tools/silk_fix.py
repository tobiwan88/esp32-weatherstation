"""Silkscreen cleanup after routing (run with $KICAD_PYTHON): footprint silk only, never copper, never board text.

Driven by kicad-cli DRC (all severities), repeated until no silk item is left or nothing more changes:
- silk_edge_clearance: a footprint silk segment crossing or touching the board edge (parts that overhang it on purpose:
  the USB-C shell, the module antenna) is clipped to the board outline inset by the silk clearance; to the fab
  layer if nothing is left inside.
- Footprint silk wholly outside the board goes to the fab layer (it would not be printed anyway).
- silk_overlap / silk_over_copper: the pin-1 mark (polygon) if one is involved, else the shorter outline segment, is
  moved away from the other item in STEP steps (across a segment, so parallel outlines separate), at most MAX_MOVE.
Usage: silk_fix.py board.kicad_pcb   (edits in place; the .kicad_pro/.kicad_dru must sit next to it)
"""

import json
import math
import os
import subprocess
import sys
import tempfile

import pcbnew

mm = pcbnew.FromMM
STEP, MAX_MOVE, ROUNDS = 0.02, 0.3, 40
SILK = {"silk_edge_clearance", "silk_overlap", "silk_over_copper"}
path = sys.argv[1]


def drc() -> list[dict]:
    report = os.path.join(tempfile.mkdtemp(), "drc.json")
    subprocess.run(["kicad-cli", "pcb", "drc", "--format", "json", "--severity-all", "-o", report, path],
                   capture_output=True)
    return [v for v in json.load(open(report))["violations"] if v["type"] in SILK]


def silk_clearance() -> float:
    """min_silk_clearance (mm) from the project next to the board"""
    pro = json.load(open(os.path.splitext(path)[0] + ".kicad_pro"))
    return pro["board"]["design_settings"]["rules"]["min_silk_clearance"]


def items_by_uuid(board) -> dict:
    out = {}
    for fp in board.GetFootprints():
        for g in fp.GraphicalItems():
            out[g.m_Uuid.AsString()] = g.Cast()
        for p in fp.Pads():
            out[p.m_Uuid.AsString()] = p
    for d in board.GetDrawings():
        out[d.m_Uuid.AsString()] = d
    return out


def clip(seg, box) -> bool:
    """Liang-Barsky clip of a segment to the box; False if nothing is left."""
    a, b = seg.GetStart(), seg.GetEnd()
    dx, dy = b.x - a.x, b.y - a.y
    t0, t1 = 0.0, 1.0
    for p, q in ((-dx, a.x - box.GetLeft()), (dx, box.GetRight() - a.x), (-dy, a.y - box.GetTop()), (dy, box.GetBottom() - a.y)):
        if p == 0:
            if q < 0:
                return False
            continue
        t = q / p
        if p < 0:
            t0 = max(t0, t)
        else:
            t1 = min(t1, t)
    if t1 - t0 < 1e-3:
        return False
    seg.SetStart(pcbnew.VECTOR2I(int(a.x + t0 * dx), int(a.y + t0 * dy)))
    seg.SetEnd(pcbnew.VECTOR2I(int(a.x + t1 * dx), int(a.y + t1 * dy)))
    return True


def away(target, other_pos) -> pcbnew.VECTOR2I:
    """STEP away from other_pos: across a segment (parallel outlines), straight away for a polygon."""
    c = target.GetBoundingBox().GetCenter()
    dx, dy = c.x - other_pos.x, c.y - other_pos.y
    if target.GetShape() == pcbnew.SHAPE_T_SEGMENT:
        a, b = target.GetStart(), target.GetEnd()
        nx, ny = -(b.y - a.y), b.x - a.x
        n = math.hypot(nx, ny) or 1
        nx, ny = nx / n, ny / n
        if nx * dx + ny * dy < 0:
            nx, ny = -nx, -ny
        return pcbnew.VECTOR2I(int(nx * mm(STEP)), int(ny * mm(STEP)))
    d = math.hypot(dx, dy) or 1
    return pcbnew.VECTOR2I(int(dx / d * mm(STEP)), int(dy / d * mm(STEP)))


def main() -> None:
    moved: dict[str, float] = {}
    changes = 0
    keep = []
    for _ in range(ROUNDS):
        board = pcbnew.LoadBoard(path)
        edge = board.GetBoardEdgesBoundingBox()   # includes half the edge line width
        changed = False
        keep.append(board)  # SWIG frees a board when its last Python reference goes
        outside = [(fp, g) for fp in board.GetFootprints() for g in map(lambda i: i.Cast(), fp.GraphicalItems())  # overhanging
                   if g.GetLayer() in (pcbnew.F_SilkS, pcbnew.B_SilkS) and g.GetClass() == "PCB_SHAPE"
                   and not g.GetBoundingBox().Intersects(edge)]
        for fp, g in outside:  # to the fab layer (not plotted): removing items breaks pcbnew's SWIG types here
            g.SetLayer(pcbnew.F_Fab if g.GetLayer() == pcbnew.F_SilkS else pcbnew.B_Fab)
            changed = True
            print(f"silk: {fp.GetReference()} outline outside the board moved to the fab layer")
        viol = drc() if not changed else []
        items = items_by_uuid(board)
        for v in viol:
            objs = [items.get(i["uuid"]) for i in v["items"]]
            own = [o for o in objs if o is not None and o.GetParentFootprint() is not None and o.GetLayer() in
                   (pcbnew.F_SilkS, pcbnew.B_SilkS) and o.GetClass() == "PCB_SHAPE"]
            if not own:
                continue
            if v["type"] == "silk_edge_clearance":
                g = own[0]
                if g.GetShape() != pcbnew.SHAPE_T_SEGMENT:
                    continue
                box = board.GetBoardEdgesBoundingBox()
                box.Inflate(-int(mm(silk_clearance()) + g.GetWidth() // 2 + mm(0.08)))
                if not clip(g, box):
                    g.SetLayer(pcbnew.F_Fab if g.GetLayer() == pcbnew.F_SilkS else pcbnew.B_Fab)
                changed = True
                print(f"silk: {g.GetParentFootprint().GetReference()} outline clipped at the board edge")
                continue
            # overlap / over copper: move the pin-1 mark (polygon) if there is one, else the shorter outline segment
            polys = [o for o in own if o.GetShape() == pcbnew.SHAPE_T_POLY]
            g = polys[0] if polys else min(own, key=lambda o: o.GetLength() if o.GetShape() == pcbnew.SHAPE_T_SEGMENT else 1e12)
            other = next((o for o in objs if o is not None and o is not g), None)
            if other is None:
                continue
            key = g.m_Uuid.AsString()
            if moved.get(key, 0) >= MAX_MOVE:
                continue
            g.Move(away(g, other.GetBoundingBox().GetCenter() if other.GetClass() != "PAD" else other.GetPosition()))
            moved[key] = moved.get(key, 0) + STEP
            changed = True
        if not changed:
            break
        changes += 1
        pcbnew.SaveBoard(path, board)
    left = drc()
    for v in left:
        print(f"silk: left {v['type']}: {v['description']}")
    moves = {k: round(v, 2) for k, v in moved.items()}
    print(f"silk: {changes} rounds, {len(moves)} items moved (max {max(moves.values(), default=0)} mm), {len(left)} silk items left")
    sys.exit(1 if left else 0)


if __name__ == "__main__":
    main()
