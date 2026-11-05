"""Dump the placed parts of a board as JSON for the fab package (run with KiCad's Python: pcbnew).

Per footprint: reference, footprint name, LCSC field, value, side, KiCad position (board mm, y down) and orientation,
attributes (DNP, exclude from BOM / position file, through-hole) and the board coordinates of every pad centre with
its number. fab_package.py (plain python3 -I) does the rest, so this script never reads downloaded files.
Usage: $KICAD_PYTHON hardware/tools/pcb_parts.py board.kicad_pcb out.json
"""

import json
import sys

import pcbnew

MM = 1e-6


def main() -> None:
    board = pcbnew.LoadBoard(sys.argv[1])
    parts = []
    for fp in board.GetFootprints():
        lcsc = fp.GetFieldText("LCSC") if fp.HasField("LCSC") else ""
        pos = fp.GetPosition()
        parts.append({
            "ref": fp.GetReference(),
            "value": fp.GetValue(),
            "footprint": fp.GetFPIDAsString(),
            "lcsc": lcsc.strip(),
            "side": "Bottom" if fp.IsFlipped() else "Top",
            "x": pos.x * MM, "y": pos.y * MM,
            "rot": fp.GetOrientationDegrees(),
            "dnp": fp.IsDNP(),
            "exclude_bom": fp.IsExcludedFromBOM(),
            "exclude_pos": fp.IsExcludedFromPosFiles(),
            "through_hole": bool(fp.GetAttributes() & pcbnew.FP_THROUGH_HOLE),
            "pads": [{"num": p.GetNumber(), "x": p.GetPosition().x * MM, "y": p.GetPosition().y * MM,
                      "smd": p.GetAttribute() == pcbnew.PAD_ATTRIB_SMD}
                     for p in fp.Pads() if p.GetAttribute() != pcbnew.PAD_ATTRIB_NPTH],
        })
    with open(sys.argv[2], "w") as f:
        json.dump(sorted(parts, key=lambda p: p["ref"]), f, indent=1)


if __name__ == "__main__":
    main()
