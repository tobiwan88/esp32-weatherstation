"""After routing weatherstation-v1: fix router leftovers, refill zones (run with $KICAD_PYTHON).

1. Router vias too close to a same-net SMD pad (rule "via to same-net SMD pad", >= 0.15 mm copper to the pad: solder
   wicks into a via beside a pad). KRT sometimes drops one into the pad edge; each such via moves to the nearest free
   spot (other copper 0.15 mm, via holes 0.5 mm apart, board edge 0.35 mm, via keepouts) and drags its track ends
   along. Locked (hand-drawn) vias are left alone.
2. Dangling tracks/vias from the router are removed one at a time; a removal is kept only if it opens nothing.
3. All zones refilled. kicad-cli DRC (scripts/hw-check.sh) has the last word.
Adapted from hardware/reference/desk_notifier/tools/finish.py (no outer pours, no sensor island).
Usage: finish_v1.py board.kicad_pcb   (edits in place; .kicad_pro/.kicad_dru must sit next to it)
"""

import json
import math
import os
import shutil
import subprocess
import sys
import tempfile

import pcbnew

mm = pcbnew.FromMM
SAME_NET_GAP, CLEAR, HOLE_GAP, EDGE = 0.15, 0.15, 0.5, 0.35
path = sys.argv[1]
board = pcbnew.LoadBoard(path)
edge = board.GetBoardEdgesBoundingBox()


def vw(v):
    return v.GetWidth(pcbnew.F_Cu)  # via diameter (KiCad 9+ wants a layer)


def too_close(v, pos):
    c = pcbnew.SHAPE_CIRCLE(pos, vw(v) // 2)
    return any(q.GetNetCode() == v.GetNetCode() and q.GetAttribute() == pcbnew.PAD_ATTRIB_SMD
               and q.GetEffectiveShape(layer).Collide(c, mm(SAME_NET_GAP) - 1)
               for f in board.GetFootprints() for q in f.Pads()
               for layer in (pcbnew.F_Cu, pcbnew.B_Cu) if q.IsOnLayer(layer))


def spot_ok(v, p):
    r = vw(v) // 2
    if not (edge.GetLeft() + mm(EDGE) + r < p.x < edge.GetRight() - mm(EDGE) - r
            and edge.GetTop() + mm(EDGE) + r < p.y < edge.GetBottom() - mm(EDGE) - r):
        return False
    if any(z.GetIsRuleArea() and z.GetDoNotAllowVias() and z.Outline().Contains(p) for z in board.Zones()):
        return False
    if too_close(v, p):
        return False
    circle = pcbnew.SHAPE_CIRCLE(p, r)
    for o in board.GetTracks():
        if o is v:
            continue
        if o.GetClass() == "PCB_VIA":
            gap = mm(HOLE_GAP) + (o.GetDrill() + v.GetDrill()) // 2
            if (o.GetPosition() - p).EuclideanNorm() < max(gap, (vw(o) + vw(v)) // 2 + mm(CLEAR)):
                return False
        elif o.GetNetCode() != v.GetNetCode() and o.GetEffectiveShape(o.GetLayer()).Collide(circle, mm(CLEAR)):
            return False
    return not any(q.GetNetCode() != v.GetNetCode() and q.GetEffectiveShape(layer).Collide(circle, mm(CLEAR))
                   for f in board.GetFootprints() for q in f.Pads()
                   for layer in (pcbnew.F_Cu, pcbnew.B_Cu) if q.IsOnLayer(layer))


for v in [t for t in board.GetTracks() if t.GetClass() == "PCB_VIA" and not t.IsLocked()]:
    old = v.GetPosition()
    if not too_close(v, old):
        continue
    spot = None
    for r in (0.1, 0.15, 0.2, 0.25, 0.3, 0.4, 0.5, 0.6, 0.8):
        cands = [pcbnew.VECTOR2I(old.x + mm(r * math.cos(k * math.pi / 12)), old.y + mm(r * math.sin(k * math.pi / 12)))
                 for k in range(24)]
        cands = [p for p in cands if spot_ok(v, p)]
        if cands:
            spot = cands[0]
            break
    if spot is None:
        print(f"finish: no spot for the {v.GetNetname()} via near a same-net pad")
        continue
    pad_hit = next((q for f in board.GetFootprints() for q in f.Pads() if q.GetNetCode() == v.GetNetCode()
                    and q.IsOnLayer(pcbnew.F_Cu) and q.HitTest(old)), None)
    for t in board.GetTracks():
        if t.GetClass() == "PCB_VIA" or t.GetNetCode() != v.GetNetCode():
            continue
        if t.GetStart() == old:
            t.SetStart(spot)
        if t.GetEnd() == old:
            t.SetEnd(spot)
    v.SetPosition(spot)
    if pad_hit is not None:  # the via sat in the pad: join pad and via with a short F.Cu track
        t = pcbnew.PCB_TRACK(board)
        t.SetStart(pad_hit.GetPosition())
        t.SetEnd(spot)
        t.SetWidth(mm(0.2))
        t.SetLayer(pcbnew.F_Cu)
        t.SetNet(v.GetNet())
        board.Add(t)
    print(f"finish: moved a {v.GetNetname()} via off a same-net pad")
pcbnew.ZONE_FILLER(board).Fill(board.Zones())
pcbnew.SaveBoard(path, board)


def drc(p):
    report = os.path.join(tempfile.mkdtemp(), "drc.json")
    subprocess.run(["kicad-cli", "pcb", "drc", "--format", "json", "--severity-all", "--refill-zones", "-o", report, p],
                   capture_output=True, check=True)
    d = json.load(open(report))
    dangling = [i["uuid"] for v in d["violations"] if v["type"] in ("via_dangling", "track_dangling") for i in v["items"]]
    return dangling, len(d["unconnected_items"])


dangling, open_before = drc(path)
tried = set()
keep = []  # SWIG frees a board/filler when its last Python reference goes: later loads then break
while dangling:
    uuid = next((u for u in dangling if u not in tried), None)
    if uuid is None:
        break
    tried.add(uuid)
    backup = path + ".bak"
    shutil.copy(path, backup)
    board = pcbnew.LoadBoard(path)
    keep.append(board)
    hit = [t for t in board.GetTracks() if t.m_Uuid.AsString() == uuid]
    # hand-drawn copper stays (e.g. a stub the router reached another way), except slivers under 0.1 mm that the
    # router splits off locked tracks
    if any(t.IsLocked() and (t.GetClass() == "PCB_VIA" or t.GetLength() > mm(0.1)) for t in hit):
        continue
    for t in hit:
        board.Remove(t)
    keep.append(pcbnew.ZONE_FILLER(board))
    keep[-1].Fill(board.Zones())
    pcbnew.SaveBoard(path, board)
    dangling, open_after = drc(path)
    if open_after > open_before:
        shutil.copy(backup, path)
        dangling, _ = drc(path)
        print(f"finish: kept {uuid}: removing it opens a connection")
if os.path.exists(path + ".bak"):
    os.remove(path + ".bak")
print("finish: done")
