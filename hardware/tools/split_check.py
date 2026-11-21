"""Prove the power-board / main-board split against the single-board weatherstation-v1 generator, from PARTS and NETS.

Checks (rows OK / WARN / FAIL, last line `split_check: OK|FAILED`, exit 1 on FAIL):
  1. every v1 part is on exactly one new board, with the same symbol, value, footprint and LCSC number; a later change
     must be listed in that board's CHANGED = {ref: reason}; a part not in v1 must be listed in ADDED = {ref: reason}
     (the header J10 is the one expected addition of the split itself)
  2. every v1 net keeps its pins: the union over both boards of the net's pins (without J10 and ADDED parts) equals the
     v1 pins, and each pin sits on the board of its part
  3. a net present on both boards is a header net, and both boards carry J10 with boards_common.HEADER_PINS
  4. a new net name touches only ADDED parts, or v1 pins that were unconnected in v1 (a free GPIO)
  Declared changes after the split (each a WARN row with its reason): RENAMED = {v1 net: new name} (the pins move with
  the name), REWIRED = {(ref, pin): reason} (a v1 pin moved to another net on purpose; it is left out of checks 2 and 4).
Power flags (#FLG) and power symbols are not parts and are ignored.
Runs without KiCad and without kicad-sch-api (a stub stands in for the drawing library: only PARTS/NETS are read), so
the gate (scripts/hw-check.sh) can run it everywhere.
Usage: python3 -I hardware/tools/split_check.py
"""

import importlib
import sys
import types
from pathlib import Path

GEN = Path(__file__).resolve().parents[1] / "gen"
OLD, BOARDS = "weatherstation_v1", ("power_board", "main_board")


def _stub_kicad_sch_api() -> None:
    try:
        import kicad_sch_api  # noqa: F401
    except ImportError:
        ksa = types.ModuleType("kicad_sch_api")
        ksa.get_symbol_cache = lambda: types.SimpleNamespace(add_library_path=lambda *_a, **_k: True)
        sys.modules["kicad_sch_api"] = ksa


def load():
    sys.path.insert(0, str(GEN))
    _stub_kicad_sch_api()
    old = importlib.import_module(OLD)
    new = {b: importlib.import_module(b) for b in BOARDS}
    common = importlib.import_module("boards_common")
    return old, new, common


def real(pins):
    return {p for p in pins if not p[0].startswith("#")}


def check(old, new: dict, common) -> list[tuple[str, str, str]]:
    rows = []
    hdr = common.HEADER_REF
    # 1. parts
    where: dict[str, list[str]] = {}
    for b, m in new.items():
        for ref in m.PARTS:
            if not ref.startswith("#"):
                where.setdefault(ref, []).append(b)
    old_refs = [r for r in old.PARTS if not r.startswith("#")]
    for ref in old_refs:
        boards = where.get(ref, [])
        if len(boards) != 1:
            rows.append(("FAIL", f"part {ref}", f"on {len(boards)} boards {boards} (expected exactly one)"))
            continue
        m = new[boards[0]]
        if tuple(m.PARTS[ref][:4]) != tuple(old.PARTS[ref][:4]):
            reason = getattr(m, "CHANGED", {}).get(ref)
            diff = [f"{k}: {a!r} -> {b!r}" for k, a, b in zip(("symbol", "value", "footprint", "lcsc"), old.PARTS[ref][:4], m.PARTS[ref][:4]) if a != b]
            rows.append(("WARN" if reason else "FAIL", f"part {ref}", f"changed on {boards[0]} ({'; '.join(diff)})"
                         + (f": {reason}" if reason else ": not listed in CHANGED")))
    n_ok = sum(1 for r in old_refs if len(where.get(r, [])) == 1)
    rows.append(("OK", "v1 parts placed", f"{n_ok} of {len(old_refs)} v1 parts on exactly one board"))
    added = {b: {r for r in m.PARTS if not r.startswith("#") and r not in old.PARTS} for b, m in new.items()}
    for b, refs in added.items():
        listed = set(getattr(new[b], "ADDED", {})) | {hdr}
        for ref in sorted(refs):
            if ref in listed:
                rows.append(("OK", f"added {ref} on {b}", getattr(new[b], "ADDED", {}).get(ref, "board-to-board header J_PWR")))
            else:
                rows.append(("FAIL", f"added {ref} on {b}", "not in v1 and not listed in ADDED"))
    skip = {b: added[b] | {hdr} for b in new}
    renamed = {o: n for m in new.values() for o, n in getattr(m, "RENAMED", {}).items()}
    rewired = {p: (b, why) for b, m in new.items() for p, why in getattr(m, "REWIRED", {}).items()}
    for o, n in renamed.items():
        rows.append(("WARN", f"net {o}", f"renamed to {n} after the split"))
    for p, (b, why) in rewired.items():
        rows.append(("WARN", f"pin {p[0]}.{p[1]}", f"rewired on {b}: {why}"))
    # 2. v1 nets keep their pins
    for net, pins in old.NETS.items():
        want = {p for p in real(pins) if p not in rewired}
        got: set = set()
        for b, m in new.items():
            for p in real(m.NETS.get(renamed.get(net, net), [])):
                if p[0] in skip[b] or p in rewired:
                    continue
                if p[0] in m.PARTS and p in want:
                    got.add(p)
                elif p[0] not in old.PARTS:
                    continue
                else:
                    rows.append(("FAIL", f"net {net}", f"{p} on {b} is not on this net in v1"))
        if got != want:
            rows.append(("FAIL", f"net {net}", f"missing {sorted(want - got)}"))
    # 3. shared nets go through the header, with the same pin map on both boards
    names = {b: set(m.NETS) for b, m in new.items()}
    shared = set.intersection(*names.values())
    for net in sorted(shared):
        if net not in common.HEADER_NETS and net != "GND":
            rows.append(("FAIL", f"net {net}", "on both boards but not a header net"))
    for b, m in new.items():
        pinmap = {pin: net for net, pins in m.NETS.items() for ref, pin in pins if ref == hdr}
        if pinmap != common.HEADER_PINS:
            rows.append(("FAIL", f"header on {b}", f"J10 pins {pinmap} differ from boards_common.HEADER_PINS"))
        else:
            rows.append(("OK", f"header on {b}", f"J10 carries {', '.join(common.HEADER_NETS)}"))
    for net in common.HEADER_NETS:
        on = [b for b in new if net in new[b].NETS]
        rows.append(("OK" if len(on) == 2 else "FAIL", f"header net {net}", f"present on {on}"))
    # 4. no stray new nets: a new net may touch v1 parts only on pins that were unconnected in v1 (e.g. a free GPIO)
    old_used = {p for pins in old.NETS.values() for p in real(pins)}
    for b, m in new.items():
        for net, pins in m.NETS.items():
            if net in old.NETS or net in renamed.values():
                continue
            v1_pins = {p for p in real(pins) if p[0] not in added[b] | {hdr} and p not in rewired}
            clash = sorted(v1_pins & old_used)
            if clash:
                rows.append(("FAIL", f"new net {net} on {b}", f"uses v1 pins that were on other nets {clash}"))
            else:
                rows.append(("OK", f"new net {net} on {b}", "added parts" + (f" and free v1 pins {sorted(v1_pins)}" if v1_pins else "")))
    return rows


def main() -> int:
    old, new, common = load()
    rows = check(old, new, common)
    bad = False
    for st, name, detail in rows:
        bad |= st == "FAIL"
        print(f"{st:8} {name}: {detail}")
    print("split_check:", "FAILED" if bad else "OK")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
