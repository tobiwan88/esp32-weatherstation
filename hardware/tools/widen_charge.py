"""Widen thin Charge-class tracks after autorouting (run with $KICAD_PYTHON).

The router necks power taps down to the default width where a wide track does not fit. This pass tries each such
track at 0.65, 0.5, 0.4 and finally 0.3 mm (the "charge path neck" DRC floor) and keeps the widest width that
kicad-cli DRC accepts without a new clearance, hole or keepout violation. Tracks that fit at none stay as they are and
are listed (fix those by hand).
Usage: widen_charge.py in.kicad_pcb out.kicad_pcb   (the .kicad_pro/.kicad_dru must sit next to in.kicad_pcb)
"""

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pcbnew

LADDER = (0.65, 0.5, 0.4, 0.3)
BAD = {"clearance", "hole_clearance", "items_not_allowed", "shorting_items", "tracks_crossing", "copper_edge_clearance",
       "solder_mask_bridge"}
src, out = Path(sys.argv[1]), Path(sys.argv[2])
work = Path(tempfile.mkdtemp())
for ext in (".kicad_pro", ".kicad_dru"):
    shutil.copy(src.with_suffix(ext), work / ("w" + ext))
wb = work / "w.kicad_pcb"


def drc_bad(board):
    """uuids of tracks in a blocking DRC violation"""
    pcbnew.SaveBoard(str(wb), board)
    rep = work / "drc.json"
    subprocess.run(["kicad-cli", "pcb", "drc", "--format", "json", "--refill-zones", "-o", str(rep), str(wb)],
                   capture_output=True)
    bad = set()
    for v in json.loads(rep.read_text())["violations"]:
        if v["type"] in BAD:
            bad.update(i["uuid"] for i in v["items"])
    return bad


board = pcbnew.LoadBoard(str(src))
# Charge class members (same list as route_krt.sh CHARGE; board.yaml net classes)
cls = set("USB_VBUS VBUS PMID SYS BAT_PACK /Battery/BAT_CON /Battery/BAT_N /Battery/PB_MID /Charger/SW1 /Charger/SW2 "
          "/Charger/PV_IN /Input/PV_RAW /Input/PV_N_RAW /Input/ACF1_MID /Input/ACF2_MID".split())
thin = {t.m_Uuid.AsString(): t for t in board.GetTracks()
        if t.GetClass() == "PCB_TRACK" and str(t.GetNetname()) in cls and t.GetWidth() < pcbnew.FromMM(0.3) - 1}
orig = {u: t.GetWidth() for u, t in thin.items()}
before = drc_bad(board)
todo = dict(thin)
for w in LADDER:
    if not todo:
        break
    for t in todo.values():
        t.SetWidth(pcbnew.FromMM(w))
    while True:  # revert the violators of this step until the step is clean (reverts can clear others)
        bad = (drc_bad(board) - before) & set(todo)
        bad = {u for u in bad if todo[u].GetWidth() != orig[u]}
        if not bad:
            break
        for u in bad:
            todo[u].SetWidth(orig[u])
    todo = {u: t for u, t in todo.items() if t.GetWidth() == orig[u]}
pcbnew.SaveBoard(str(out), board)
print(f"widened {len(thin) - len(todo)} of {len(thin)} thin Charge tracks; left thin:")
for t in todo.values():
    p = t.GetStart()
    print(f"  {t.GetNetname()} {pcbnew.ToMM(t.GetLength()):.2f} mm at ({pcbnew.ToMM(p.x):.2f}, {pcbnew.ToMM(p.y):.2f})")
shutil.rmtree(work)
