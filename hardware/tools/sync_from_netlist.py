"""Value-only update of a routed board from its schematic netlist (no re-placement, no copper change).

For a routed board whose copper is partly router output (a full rebuild would re-route it): after a schematic change that
keeps every part's footprint and every pad's net (a resistor value, an LCSC number), this writes the new Value, the
fields (LCSC, ...) and the symbol link (footprint path) into the placed footprints, the same way gen/pcbkit.py sets them
on a fresh build. It refuses when the change is more than that: a missing or extra reference, another footprint, or a
pad on another net (rebuild and re-route instead).

The schematic generator gives the symbols new uuids on every run, so the paths are refreshed for every footprint.
Run with KiCad's Python:
  $KICAD_PYTHON hardware/tools/sync_from_netlist.py BOARD.net BOARD.kicad_pcb
then KiCad DRC with --schematic-parity (0 parity items).
"""

import sys
from pathlib import Path

import pcbnew

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pcb_from_netlist import parse  # noqa: E402


def main() -> int:
    net_file, pcb_file = sys.argv[1], sys.argv[2]
    comps, pads = parse(Path(net_file).read_text())
    board = pcbnew.LoadBoard(pcb_file)
    fps = {f.GetReference(): f for f in board.GetFootprints() if not f.GetAttributes() & pcbnew.FP_BOARD_ONLY}
    problems = [f"{r}: in the netlist, not on the board" for r in sorted(set(comps) - set(fps))]
    problems += [f"{r}: on the board, not in the netlist" for r in sorted(set(fps) - set(comps))]
    for ref in sorted(set(comps) & set(fps)):
        fp, fpid = fps[ref], comps[ref][1]
        have = f"{fp.GetFPID().GetLibNickname().wx_str()}:{fp.GetFPID().GetLibItemName().wx_str()}"
        if have != fpid:
            problems.append(f"{ref}: footprint {have} on the board, {fpid} in the netlist")
        for pad in fp.Pads():
            want = pads.get((ref, pad.GetNumber()), "")
            got = pad.GetNetname()
            if pad.GetNumber() and want and got != want:
                problems.append(f"{ref}.{pad.GetNumber()}: net {got} on the board, {want} in the netlist")
    if problems:
        print("\n".join(problems))
        print("sync_from_netlist: FAILED (not a value-only change: rebuild the board)")
        return 1
    changed = []
    for ref, (value, _fpid, uuid, fields, _no_bom) in sorted(comps.items()):
        fp = fps[ref]
        if fp.GetValue() != value:
            changed.append(f"{ref}: value {fp.GetValue()} -> {value}")
            fp.SetValue(value)
        for name, text in fields.items():
            if name in ("Datasheet", "Description"):
                continue
            old = fp.GetField(name).GetText() if fp.HasField(name) else None
            if old != text:
                changed.append(f"{ref}: {name} {old} -> {text}")
                fp.SetField(name, text)
                fp.GetField(name).SetVisible(False)
        fp.SetPath(pcbnew.KIID_PATH("/" + uuid))
    pcbnew.SaveBoard(pcb_file, board)
    print("\n".join(changed) or "no value or field change")
    print(f"sync_from_netlist: OK ({len(changed)} changes, symbol links of {len(comps)} footprints refreshed)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
