"""Check a board's critical blocks (critical.yaml) on its routed .kicad_pcb.

One function per constraint type; each returns (status, name, detail) rows. `known:` on an entry turns FAIL into WARN.
--placement: the board is placed but not routed. Placement rows (pad distances, footprint distances) are checked as
usual; rows that need copper (FB trace length, diff-pair skew and vias) print SKIP "not routed" instead of failing.
Usage: python3 hardware/calc/critical.py hardware/<board> [--placement] [--json]
"""

import argparse
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from pcb import Board, load, report  # noqa: E402


def pin(s: str) -> tuple[str, str]:
    ref, pad = s.split(".", 1)
    return ref, pad


def row(ok: bool, name: str, detail: str, entry: dict) -> tuple[str, str, str]:
    if ok:
        return "OK", name, detail
    if entry.get("known"):
        return "WARN", name, f"{detail} (known: {entry['known']})"
    return "FAIL", name, detail


def near(b: Board, e: dict, a: str, c: str, limit: float, label: str):
    d = b.dist(pin(a), pin(c))
    return row(d <= limit, label, f"{a} to {c} {d:.2f} mm (max {limit})", e)


def switcher_loop(b: Board, e: dict):
    cin = e["cin"]
    yield near(b, e, e["vin"], f"{cin}.1", e["max_mm"], f"{e['name']}: input cap at VIN")
    yield near(b, e, e["gnd"], f"{cin}.2", e["max_mm"], f"{e['name']}: input cap at GND")
    yield near(b, e, e["sw"], e["inductor"], e["sw_max_mm"], f"{e['name']}: inductor at SW")


PLACEMENT = False  # set by --placement: copper-only rows report SKIP


def not_routed(name: str, what: str):
    return "SKIP", name, f"not routed ({what} needs copper; placement-only board)"


def feedback(b: Board, e: dict):
    for r in e["divider"]:
        yield near(b, e, e["pin"], r, e["max_mm"], f"{e['name']}: divider at FB")
    if PLACEMENT:
        yield not_routed(f"{e['name']}: FB trace length", f"{e['net']} length")
        return
    n = b.length.get(e["net"], 0.0)
    yield row(n <= e["max_len_mm"], f"{e['name']}: FB trace length", f"{n:.2f} mm (max {e['max_len_mm']})", e)


def decoupling(b: Board, e: dict):
    yield near(b, e, e["pin"], e["cap"], e["max_mm"], f"decoupling {e['cap'].split('.')[0]}")


def series_termination(b: Board, e: dict):
    yield near(b, e, e["source"], e["part"], e["max_mm"], f"series R {e['part'].split('.')[0]} at source")


def diff_pair(b: Board, e: dict):
    if PLACEMENT:
        yield not_routed(f"{e['name']}: skew and vias", f"{e['p']}/{e['n']} skew and via count")
        return
    lp, ln = b.length.get(e["p"], 0.0), b.length.get(e["n"], 0.0)
    if not lp or not ln:
        yield row(False, f"{e['name']}: routed", f"{e['p']} {lp:.1f} mm, {e['n']} {ln:.1f} mm (unrouted?)", e)
        return
    yield row(abs(lp - ln) <= e["max_skew_mm"], f"{e['name']}: skew", f"{abs(lp - ln):.2f} mm (max {e['max_skew_mm']})", e)
    v = b.vias.get(e["p"], 0) + b.vias.get(e["n"], 0)
    yield row(v <= e["max_vias"], f"{e['name']}: vias", f"{v} (max {e['max_vias']})", e)


def thermal_distance(b: Board, e: dict):
    d = math.dist(b.footprints[e["source"]], b.footprints[e["sensor"]])
    yield row(d >= e["min_mm"], f"heat {e['source']} to {e['sensor']}", f"{d:.1f} mm (min {e['min_mm']})", e)


CHECKS = {f.__name__: f for f in (switcher_loop, feedback, decoupling, series_termination, diff_pair, thermal_distance)}


def run(board_dir: Path) -> list[tuple[str, str, str]]:
    prof, b = load(board_dir)
    rows = []
    for kind, entries in prof["critical"].items():
        if kind not in CHECKS:
            rows.append(("FAIL", kind, "unknown constraint type (add a check function or fix the name)"))
            continue
        for e in entries:
            try:
                rows += list(CHECKS[kind](b, e))
            except KeyError as err:
                rows.append(("FAIL", kind, f"{err} in {e}"))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("board_dir", type=Path)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--placement", action="store_true", help="placed, not routed: copper-only rows report SKIP")
    a = ap.parse_args()
    global PLACEMENT
    PLACEMENT = a.placement
    rows = run(a.board_dir)
    if a.json:
        json.dump([dict(zip(("status", "check", "detail"), r)) for r in rows], sys.stdout, indent=1)
        sys.exit(any(r[0] == "FAIL" for r in rows))
    fails = report(rows, f"critical blocks: {a.board_dir}" + (" (placement only)" if a.placement else ""))
    print("critical:", "FAILED" if fails else "OK")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
