"""Stack check: the main board and the power board fit on top of each other (plain Python, no KiCad; runs in the gate).

Reads both .kicad_pcb files and gen/stack.py and checks, in top view with the boards' outlines on top of each other
(stack.OFFSET):
  - outlines: same size, within stack.W x stack.H
  - holes H1..H4: at stack.HOLES on both boards, the pattern has no mirror or 180-degree symmetry (a flipped or turned
    board cannot be screwed on)
  - J10: both footprints on F.Cu and not mirrored, every one of the 20 pads at the same position on both boards, the
    same pad numbers, pin 3 present as a pad on neither net (key), and the same net on each pin (sheet prefix dropped)
  - heat through the gap: power-board heat sources (U3, L1) at least 15 mm (3D, gap stack.GAP_MM) from the main
    board's BMP580 U9, and no power-board footprint beyond the main board's top edge (antenna overhang)
Usage: python3 -I hardware/tools/stack_check.py [--selftest]
"""

import math
import sys
from pathlib import Path

HW = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HW / "calc"))
sys.path.insert(0, str(HW / "gen"))
import stack  # noqa: E402
from pcb import child, children, parse, xy  # noqa: E402

MAIN = HW / "main-board" / "main-board.kicad_pcb"
POWER = HW / "power-board" / "power-board.kicad_pcb"
TOL = 0.01
HEAT = {"U3": 15.0, "L1": 15.0}  # power-board source -> minimum 3D distance to the main board's U9 (mm)


def read(path: Path) -> dict:
    root = parse(path.read_text())
    edges = []
    for g in children(root, "gr_line") + children(root, "gr_rect"):
        if child(g, "layer")[1] == "Edge.Cuts":
            edges += [xy(child(g, "start"))[:2], xy(child(g, "end"))[:2]]
    x0, y0 = min(p[0] for p in edges), min(p[1] for p in edges)
    x1, y1 = max(p[0] for p in edges), max(p[1] for p in edges)
    fps, pads = {}, {}
    for fp in children(root, "footprint"):
        props = {p[1]: p[2] for p in children(fp, "property")}
        ref = props["Reference"]
        fx, fy, frot = xy(child(fp, "at"))
        layer = child(fp, "layer")[1]
        fps[ref] = (round(fx - x0, 3), round(fy - y0, 3), frot, layer)
        a = math.radians(frot)
        for pad in children(fp, "pad"):
            px, py, _ = xy(child(pad, "at"))
            n = child(pad, "net")
            pads[(ref, pad[1])] = (round(fx - x0 + px * math.cos(a) + py * math.sin(a), 3),
                                   round(fy - y0 - px * math.sin(a) + py * math.cos(a), 3), n[-1] if n else "")
    return {"size": (round(x1 - x0, 3), round(y1 - y0, 3)), "fps": fps, "pads": pads}


def symmetric(holes: list[tuple[float, float]], w: float, h: float) -> list[str]:
    """Names of the symmetries under which the hole pattern maps onto itself."""
    s = {tuple(round(c, 2) for c in p) for p in holes}
    maps = {"mirror left-right": lambda x, y: (w - x, y), "mirror top-bottom": lambda x, y: (x, h - y),
            "turned 180 degrees": lambda x, y: (w - x, h - y)}
    return [name for name, f in maps.items() if {tuple(round(c, 2) for c in f(*p)) for p in s} == s]


def base(net: str) -> str:
    return net.rsplit("/", 1)[-1]


def check(main: dict, power: dict) -> list[tuple[str, str]]:
    rows = []
    ok = lambda c, msg: rows.append(("OK" if c else "FAIL", msg))  # noqa: E731
    ox, oy = stack.OFFSET
    ok(main["size"] == power["size"] and main["size"][0] <= stack.W + TOL and main["size"][1] <= stack.H + TOL,
       f"outlines main {main['size']} power {power['size']} (max {stack.W} x {stack.H})")
    for ref, (hx, hy) in stack.HOLES.items():
        m, p = main["fps"].get(ref), power["fps"].get(ref)
        good = bool(m and p) and math.dist(m[:2], (hx, hy)) < TOL and math.dist((p[0] + ox, p[1] + oy), (hx, hy)) < TOL
        ok(good, f"hole {ref} at {hx}, {hy} on both boards (main {m and m[:2]}, power {p and p[:2]})")
    sym = symmetric(list(stack.HOLES.values()), stack.W, stack.H)
    ok(not sym, "hole pattern asymmetric" + (f" (FAILS: maps onto itself when {', '.join(sym)})" if sym else ""))
    m, p = main["fps"].get("J10"), power["fps"].get("J10")
    ok(bool(m and p) and m[3] == p[3] == "F.Cu", f"J10 on F.Cu on both boards (main {m and m[3]}, power {p and p[3]})")
    mp = {k[1]: v for k, v in main["pads"].items() if k[0] == "J10"}
    pp = {k[1]: v for k, v in power["pads"].items() if k[0] == "J10"}
    ok(sorted(mp) == sorted(pp) and len(mp) == 20, f"J10 pad numbers match ({len(mp)} main, {len(pp)} power)")
    worst = max((math.dist(mp[n][:2], (pp[n][0] + ox, pp[n][1] + oy)) for n in mp if n in pp), default=99.0)
    ok(worst < TOL, f"J10 pads aligned (worst pin offset {worst:.3f} mm)")
    p1 = mp.get("1", (0, 0))[:2]
    ok(math.dist(p1, stack.J10_AT[:2]) < TOL, f"J10 pin 1 at {stack.J10_AT[:2]} (main {p1})")
    wrong = [n for n in mp if n in pp and base(mp[n][2]) != base(pp[n][2])
             and not (mp[n][2].startswith("unconnected") and pp[n][2].startswith("unconnected"))]
    ok(not wrong, "J10 nets match pin by pin" + (f" (differ on pins {', '.join(sorted(wrong, key=int))})" if wrong else ""))
    ok(mp.get("3", (0, 0, "x"))[2].startswith("unconnected") and pp.get("3", (0, 0, "x"))[2].startswith("unconnected"),
       "J10 pin 3 (key) on no net on either board")
    u9 = main["fps"].get("U9")
    for src, dmin in HEAT.items():
        s = power["fps"].get(src)
        d = math.hypot(math.dist((s[0] + ox, s[1] + oy), u9[:2]), stack.GAP_MM) if s and u9 else 0.0
        ok(d >= dmin, f"heat power {src} to main U9 {d:.1f} mm through the {stack.GAP_MM} mm gap (min {dmin})")
    above = [r for r, f in power["fps"].items() if f[1] + oy < 0]
    ok(not above, "no power-board part beyond the main board's top edge (antenna overhang)" + (f": {above}" if above else ""))
    return rows


def selftest():
    w = h = 50.0
    assert symmetric([(3.5, 3.5), (46.5, 3.5), (3.5, 46.5), (46.5, 46.5)], w, h) == \
        ["mirror left-right", "mirror top-bottom", "turned 180 degrees"]
    assert symmetric(list(stack.HOLES.values()), w, h) == []
    assert base("/MCU/CHG_SDA") == base("/Inputs/CHG_SDA") == "CHG_SDA" and base("SYS") == "SYS"
    print("stack_check selftest: OK")


def main():
    if "--selftest" in sys.argv:
        selftest()
        return
    if not (MAIN.exists() and POWER.exists()):
        print("stack: SKIP (a board file is missing; run tools/build_board.sh)")
        return
    rows = check(read(MAIN), read(POWER))
    for status, msg in rows:
        print(f"  {status:4} {msg}")
    bad = sum(s == "FAIL" for s, _ in rows)
    print("stack:", "FAILED" if bad else "OK")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
