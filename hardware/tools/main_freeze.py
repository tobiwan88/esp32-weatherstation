"""Freeze router copper into hardware/main-board/frozen-routes.json.

gen/main_copper.py loads that file and draws the stored copper as locked hand copper, so a later route_main.sh run
keeps these nets as solved and the autorouter only has to finish the rest. The router result depends on the order it
meets the nets in and plateaus at a few open nets on this board; freezing a good run and drawing the last nets by hand
(gen/main_copper.py) makes the routing reproducible. Coordinates are board mm from the top-left corner.

Run with KiCad's Python:
  $KICAD_PYTHON hardware/tools/main_freeze.py ROUTED.kicad_pcb NET [NET ...] [--replace]
  $KICAD_PYTHON hardware/tools/main_freeze.py ROUTED.kicad_pcb --all --minus BASE.kicad_pcb [--replace]
--all takes every net; --minus drops copper that BASE (the board with only the hand copper) already has, so the hand
copper is not stored twice. Use the router output before stitching (route_main.sh keeps it as routed.kicad_pcb).
"""
import json
import sys
from pathlib import Path

import pcbnew

OUT = Path(__file__).resolve().parents[1] / "main-board" / "frozen-routes.json"
ORIGIN = 100.0   # page offset of the board's top-left corner


def mm(v):
    return round(pcbnew.ToMM(v) - ORIGIN, 4)


def items(board):
    """{net: {"tracks": [...], "vias": [...]}} for F.Cu/B.Cu tracks and vias."""
    out = {}
    for t in board.GetTracks():
        d = out.setdefault(t.GetNetname(), {"tracks": [], "vias": []})
        if t.GetClass() == "PCB_VIA":
            d["vias"].append([mm(t.GetPosition().x), mm(t.GetPosition().y), round(pcbnew.ToMM(t.GetWidth()), 3),
                              round(pcbnew.ToMM(t.GetDrillValue()), 3)])
        else:
            lay = {pcbnew.F_Cu: "F", pcbnew.B_Cu: "B"}.get(t.GetLayer())
            if lay is None:
                sys.exit(f"{t.GetNetname()}: inner-layer track, not frozen")
            d["tracks"].append([lay, round(pcbnew.ToMM(t.GetWidth()), 3),
                                [[mm(t.GetStart().x), mm(t.GetStart().y)], [mm(t.GetEnd().x), mm(t.GetEnd().y)]]])
    return out


def key_t(t):
    a, b = (tuple(round(v, 2) for v in p) for p in t[2])
    return (t[0], min(a, b), max(a, b))


def key_v(v):
    return (round(v[0], 2), round(v[1], 2))


def main():
    argv = sys.argv[1:]
    minus = argv[argv.index("--minus") + 1] if "--minus" in argv else None
    args = [a for a in argv if not a.startswith("--") and a != minus]
    routed = items(pcbnew.LoadBoard(args[0]))
    nets = sorted(n for n in routed if n) if "--all" in argv else args[1:]
    base = items(pcbnew.LoadBoard(minus)) if minus else {}
    data = {"nets": {}} if "--replace" in argv or not OUT.exists() else json.loads(OUT.read_text())
    for net in nets:
        if net not in routed:
            sys.exit(f"{net}: no copper in {args[0]}")
        b = base.get(net, {"tracks": [], "vias": []})
        bt, bv = {key_t(t) for t in b["tracks"]}, {key_v(v) for v in b["vias"]}
        tracks = [t for t in routed[net]["tracks"] if key_t(t) not in bt]
        vias = [v for v in routed[net]["vias"] if key_v(v) not in bv]
        if tracks or vias:
            data["nets"][net] = {"tracks": tracks, "vias": vias}
            print(f"frozen {net}: {len(tracks)} tracks, {len(vias)} vias")
    OUT.write_text(json.dumps(data, indent=1) + "\n")


if __name__ == "__main__":
    main()
