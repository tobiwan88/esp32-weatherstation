"""Replace placed footprints by the current library version, in place (KiCad's "Update footprint from library").

Keeps position, orientation, side, reference, value, fields and the pad nets (by pad number); tracks are not touched,
so run DRC afterwards. For a land-pattern fix on a routed board without re-routing.
Usage: $KICAD_PYTHON hardware/tools/swap_footprint.py board.kicad_pcb lib.pretty REF [REF ...]
"""

import sys

import pcbnew

board_path, lib, refs = sys.argv[1], sys.argv[2], sys.argv[3:]
board = pcbnew.LoadBoard(board_path)
for ref in refs:
    old = board.FindFootprintByReference(ref)
    name = old.GetFPID().GetLibItemName().wx_str()
    new = pcbnew.FootprintLoad(lib, name)
    if new is None:
        sys.exit(f"{ref}: {name} not in {lib}")
    new.SetFPID(old.GetFPID())
    new.SetReference(ref)
    new.SetValue(old.GetValue())
    for f in old.GetFields():
        if not f.IsReference() and not f.IsValue():
            new.SetField(f.GetName(), f.GetText())
            nf = new.GetField(f.GetName())
            nf.SetVisible(f.IsVisible())
            nf.SetLayer(f.GetLayer())
    new.Reference().SetLayer(old.Reference().GetLayer())
    new.Reference().SetVisible(old.Reference().IsVisible())
    new.Value().SetVisible(old.Value().IsVisible())
    new.SetAttributes(old.GetAttributes())
    new.SetPath(old.GetPath())
    nets = {p.GetNumber(): p.GetNet() for p in old.Pads()}
    if old.IsFlipped():
        new.Flip(new.GetPosition(), pcbnew.FLIP_DIRECTION_TOP_BOTTOM)
    new.SetOrientation(old.GetOrientation())
    new.SetPosition(old.GetPosition())
    new.SetLocked(old.IsLocked())
    for p in new.Pads():
        p.SetNet(nets[p.GetNumber()])
    board.Remove(old)
    board.Add(new)
    print(f"swap: {ref} -> {lib}/{name}")
pcbnew.ZONE_FILLER(board).Fill(board.Zones())
pcbnew.SaveBoard(board_path, board)
