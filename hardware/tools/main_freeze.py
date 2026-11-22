"""Freeze router copper of selected nets into hardware/main-board/frozen-routes.json.

gen/main_copper.py loads that file and draws the stored copper as locked hand copper, so a later route_main.sh run
keeps these nets as solved and the autorouter only has to finish the rest. Use it for nets that one router run solved
and others do not (the result depends on the order the router meets the nets in). Coordinates are board mm from the
top-left corner, the same as the hand copper.

Run with KiCad's Python:  $KICAD_PYTHON hardware/tools/main_freeze.py routed.kicad_pcb NET [NET ...] [--replace]
"""
import json
import sys
from pathlib import Path

import pcbnew

OUT = Path(__file__).resolve().parents[1] / "main-board" / "frozen-routes.json"
ORIGIN = 100.0   # page offset of the board's top-left corner


def mm(v):
    return round(pcbnew.ToMM(v) - ORIGIN, 4)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    board, nets = pcbnew.LoadBoard(args[0]), args[1:]
    data = {"nets": {}} if "--replace" in sys.argv or not OUT.exists() else json.loads(OUT.read_text())
    for net in nets:
        tracks, vias = [], []
        for t in board.GetTracks():
            if t.GetNetname() != net:
                continue
            if t.GetClass() == "PCB_VIA":
                vias.append([mm(t.GetPosition().x), mm(t.GetPosition().y), round(pcbnew.ToMM(t.GetWidth()), 3),
                             round(pcbnew.ToMM(t.GetDrillValue()), 3)])
            else:
                lay = "F" if t.GetLayer() == pcbnew.F_Cu else "B" if t.GetLayer() == pcbnew.B_Cu else None
                if lay is None:
                    sys.exit(f"{net}: inner-layer track, not frozen")
                tracks.append([lay, round(pcbnew.ToMM(t.GetWidth()), 3),
                               [[mm(t.GetStart().x), mm(t.GetStart().y)], [mm(t.GetEnd().x), mm(t.GetEnd().y)]]])
        if not tracks:
            sys.exit(f"{net}: no copper in {args[0]}")
        data["nets"][net] = {"tracks": tracks, "vias": vias}
        print(f"frozen {net}: {len(tracks)} tracks, {len(vias)} vias")
    OUT.write_text(json.dumps(data, indent=1) + "\n")


if __name__ == "__main__":
    main()
