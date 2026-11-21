"""Power-board routing checks: the shared calc/emi_check.py rows (settings: <board>/emi.yaml, else critical.yaml
emi:) plus the charger-specific numbers of BOARD.md
"Routing review" (plain Python, no pcbnew; zones must be filled, as route_power.sh / build_board.sh leave them).

  emi         every calc/emi_check.py row (critical.yaml emi:), run with a tie-safe shortest path (see below)
  hot loops   BQ25798 PMID and SYS input loops (critical.yaml switcher_loop): plan area of the pad-centre polygon
              cap VIN pad -> VIN pin -> GND pin 27 -> cap GND pad, and its perimeter
  SW copper   SW1/SW2 copper area, tracks plus pads (U3 pin, L1 pad, bootstrap cap pad) per outer layer
  current     widest path (max-min width) along each power path pad to pad (tracks; filled pours count as 5 mm,
              vias as their diameter): bottleneck width, the length of copper at that width, via count. Limit: the
              0.3 mm neck floor of rules/power-board.kicad_dru everywhere, and copper under the 0.65 mm class width
              (calc/track_width.py) at most 3 mm per path (short pin necks spread heat)
  SW spacing  closest copper of every other net (except GND) to SW1/SW2 on the same layer (brief: >= 0.6 mm and
              3x width for I2C/USB; reported for all nets, the five closest listed)
  via in pad  vias whose drill centre sits inside an SMD pad (rules forbid it; listed if any)
emi known: [{row: <row name>, known: <reason>}] turns that row's FAIL into WARN (as critical.py known:).
emi_check.shortest pushes (distance, node) pairs; equal distances then compare a pad node (str tuple) with a track
node (coordinate tuple) and raise TypeError on this board. The wrapper below adds a counter as a tie-breaker; the
fix belongs in emi_check.py itself (owned by the main-board work).
Usage: python3 hardware/calc/power_route_check.py hardware/power-board
"""

import argparse
import heapq
import itertools
import math
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent))
import emi_check as E  # noqa: E402
from pcb import child, children, load_profile, parse, report  # noqa: E402

POUR_W = 5.0
NECK_FLOOR = 0.3
CLASS_W = 0.65
NECK_MAX_MM = 3.0
SW = ("/Charger/SW1", "/Charger/SW2")
# power paths (net, from pad, to pad): every high-current branch of BOARD.md "Power paths"
PATHS = [
    ("USB_VBUS", "J10.19", "M1.3"), ("/Inputs/ACF1_MID", "M1.2", "M2.2"), ("VBUS", "M2.3", "C7.1"),
    ("/Inputs/PV_RAW", "J5.1", "L3.1"), ("/Inputs/PV_N_RAW", "J5.2", "L3.4"), ("/Charger/PV_IN", "L3.2", "M3.3"),
    ("/Inputs/ACF2_MID", "M3.2", "M4.2"), ("VBUS", "M4.3", "C7.1"), ("VBUS", "C7.1", "U3.2"),
    ("VBUS", "C7.1", "U3.3"), ("PMID", "U3.29", "C10.1"), ("SYS", "U3.25", "J10.1"), ("SYS", "U3.25", "J10.2"),
    ("/Charger/SW1", "U3.28", "L1.1"), ("/Charger/SW2", "U3.26", "L1.2"), ("BAT_PACK", "U3.22", "C20.1"),
    ("BAT_PACK", "C20.1", "F1.2"), ("/Battery/BAT_CON", "J6.1", "F1.1"), ("/Battery/BAT_N", "J6.2", "M60.2"),
    ("/Battery/PB_MID", "M60.3", "M61.3"),
]


def shortest(adj, src, dst):
    """emi_check.shortest with a counter between distance and node (no node comparison on ties)."""
    best, tie, todo = {src: 0.0}, itertools.count(), [(0.0, 0, src)]
    while todo:
        d, _, u = heapq.heappop(todo)
        if u == dst:
            return d
        if d > best.get(u, math.inf):
            continue
        for v, w in adj.get(u, []):
            if d + w < best.get(v, math.inf):
                best[v] = d + w
                heapq.heappush(todo, (d + w, next(tie), v))
    return None


E.shortest = shortest


def shoelace(pts):
    return abs(sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(pts, pts[1:] + pts[:1]))) / 2


class Geo:
    """Pads with size/shape/layers, locked flags; reuses the emi_check.Pcb parse for tracks, vias and fills."""

    def __init__(self, path):
        self.b = E.Pcb(path)
        root = parse(Path(path).read_text())
        self.pad = {}
        for fp in children(root, "footprint"):
            at = child(fp, "at")
            fx, fy = float(at[1]), float(at[2])
            a = math.radians(float(at[3]) if len(at) > 3 else 0.0)
            ref = {p[1]: p[2] for p in children(fp, "property")}["Reference"]
            for pd in children(fp, "pad"):
                pat = child(pd, "at")
                px, py = float(pat[1]), float(pat[2])
                pr = math.radians(float(pat[3])) if len(pat) > 3 else a
                c = (fx + px * math.cos(a) + py * math.sin(a), fy - px * math.sin(a) + py * math.cos(a))
                sx, sy = float(child(pd, "size")[1]), float(child(pd, "size")[2])
                if abs(math.sin(pr)) > 0.7:  # pad at 90/270 in board space (file angle is absolute)
                    sx, sy = sy, sx
                n = child(pd, "net")
                lay = child(pd, "layers")[1:]
                self.pad.setdefault((ref, pd[1]), dict(c=c, sx=sx, sy=sy, smd=pd[2] == "smd", net=n[-1] if n else "",
                                                      layers=lay))

    def in_pad(self, p, key, grow=0.0):
        q = self.pad[key]
        return abs(p[0] - q["c"][0]) <= q["sx"] / 2 + grow and abs(p[1] - q["c"][1]) <= q["sy"] / 2 + grow


def widest(g, net, a, z):
    """Max-min width path between two pads of `net`: (bottleneck, metres at bottleneck, vias) or None."""
    b = g.b
    r = lambda p: (round(p[0], 3), round(p[1], 3))  # noqa: E731
    adj = {}

    def link(u, v, w, length):
        adj.setdefault(u, []).append((v, w, length))
        adj.setdefault(v, []).append((u, w, length))
    ends = []
    for s0, s1, w, layer, n in b.seg:
        if n == net:
            link((r(s0), layer), (r(s1), layer), w, math.dist(s0, s1))
            ends += [(r(s0), layer, w), (r(s1), layer, w)]
    for pos, d, n in b.via:
        if n == net:
            link((r(pos), "F.Cu"), (r(pos), "B.Cu"), d, 0.0)
            adj.setdefault(("via", r(pos)), [])
            ends += [(r(pos), "F.Cu", d), (r(pos), "B.Cu", d)]
    segs = [(r(s0), r(s1), layer, w) for s0, s1, w, layer, n in b.seg if n == net]
    for e in ends:   # T-junctions: a track end inside another track's copper
        for s0, s1, layer, w in segs:
            if layer == e[1] and e[0] not in (s0, s1) and E.seg_dist(e[0], s0, s1) < min(w, e[2]) / 2:
                link((e[0], e[1]), (s0, layer), w, math.dist(e[0], s0))
                link((e[0], e[1]), (s1, layer), w, math.dist(e[0], s1))
    for key, q in g.pad.items():
        if q["net"] != net:
            continue
        node = ("pad",) + key
        for e in ends:
            if g.in_pad(e[0], key, 0.01) and any(lay in (e[1], "*.Cu") for lay in q["layers"]):
                link(node, (e[0], e[1]), POUR_W, 0.0)
        for (layer, zn), polys in b.fill.items():
            if zn == net and any(lay in (layer, "*.Cu") for lay in q["layers"]) and \
                    any(E.inside(q["c"], poly) for poly in polys):
                link(node, ("pour", layer, zn), POUR_W, 0.0)
    for e in ends:
        for (layer, zn), polys in b.fill.items():
            if zn == net and layer == e[1] and any(E.inside(e[0], poly) for poly in polys):
                link((e[0], e[1]), ("pour", layer, zn), POUR_W, 0.0)
    src, dst = ("pad",) + tuple(a.split(".", 1)), ("pad",) + tuple(z.split(".", 1))
    # widest path (bottleneck Dijkstra); among equally wide paths the shortest
    best, tie, todo = {src: (math.inf, 0.0)}, itertools.count(), [(-math.inf, 0.0, 0, src, None)]
    prev = {}
    while todo:
        nw, d, _, u, p = heapq.heappop(todo)
        w = -nw
        if u in prev:
            continue
        prev[u] = p
        if u == dst:
            break
        for v, ew, length in adj.get(u, []):
            m = min(w, ew)
            k = best.get(v)
            if v not in prev and (k is None or m > k[0] + 1e-9 or (abs(m - k[0]) <= 1e-9 and d + length < k[1])):
                best[v] = (m, d + length)
                heapq.heappush(todo, (-m, d + length, next(tie), v, u))
    if dst not in prev:
        return None
    bott = best[dst][0]
    path, u = [], dst
    while u is not None:
        path.append(u)
        u = prev[u]
    neck, vias = 0.0, 0
    for u, v in zip(path, path[1:]):
        for x, ew, length in adj[u]:
            if x == v:
                if ew <= bott + 1e-6:
                    neck += length
                if u[0] == v[0] and u[1] != v[1] and u[1] in ("F.Cu", "B.Cu") and v[1] in ("F.Cu", "B.Cu"):
                    vias += 1
                break
    under = sum(length for u, v in zip(path, path[1:]) for x, ew, length in adj[u] if x == v and ew < CLASS_W - 1e-6)
    return bott, neck, under, vias


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("board_dir", type=Path)
    a = ap.parse_args()
    prof = load_profile(a.board_dir)
    crit = prof["critical"]
    ef = a.board_dir / "emi.yaml"
    emi = yaml.safe_load(ef.read_text()) if ef.exists() else crit.get("emi", {})
    g = Geo(a.board_dir / prof["pcb"])
    b = g.b
    rows = []
    for e in crit.get("diff_pair", []):
        rows += E.check_pair(b, e, emi)
    rows += E.check_edge(b, emi) + E.check_antenna(b, emi) + E.check_planes(b, emi) + E.check_loops(b, crit, emi)
    rows += E.check_parallel(b, emi)
    ox, oy = b.box[0], b.box[1]

    for e in crit.get("switcher_loop", []):
        pts = [g.pad[tuple(k.split(".", 1))]["c"] for k in (f"{e['cin']}.1", e["vin"], e["gnd"], f"{e['cin']}.2")]
        area = shoelace(pts)
        per = sum(math.dist(p, q) for p, q in zip(pts, pts[1:] + pts[:1]))
        rows.append(E.row(area <= 2.0, f"hot loop {e['name']} area",
                          f"{area:.2f} mm2 plan (pad centres {e['cin']}.1 -> {e['vin']} -> {e['gnd']} -> {e['cin']}.2), "
                          f"perimeter {per:.1f} mm, 0.21 mm above the In1 GND plane (max 2.0 mm2)"))
    for net in SW:
        tr = {L: sum(math.dist(s0, s1) * w for s0, s1, w, layer, n in b.seg if n == net and layer == L)
              for L in ("F.Cu", "B.Cu")}
        pads = [(k, q) for k, q in g.pad.items() if q["net"] == net]
        pa = sum(q["sx"] * q["sy"] for k, q in pads)
        nv = sum(1 for p, d, n in b.via if n == net)
        rows.append(E.row(True, f"SW copper {net.split('/')[-1]} (info)",
                          f"tracks F {tr['F.Cu']:.2f} + B {tr['B.Cu']:.2f} mm2, pads {pa:.2f} mm2 "
                          f"({', '.join(f'{k[0]}.{k[1]}' for k, q in pads)}), {nv} vias"))

    worst = None
    for net, s, t in PATHS:
        res = widest(g, net, s, t)
        if res is None:
            rows.append(E.row(False, f"current {net.split('/')[-1]} {s}->{t}", "no copper path"))
            continue
        bott, neck, under, vias = res
        ok = bott >= NECK_FLOOR - 1e-6 and under <= NECK_MAX_MM
        rows.append(E.row(ok, f"current {net.split('/')[-1]} {s}->{t}",
                          f"bottleneck {min(bott, POUR_W):.2f} mm over {neck:.2f} mm, {under:.2f} mm below "
                          f"{CLASS_W} (max {NECK_MAX_MM}), {vias} via hops"))
        if bott < POUR_W and (worst is None or bott < worst[0] or (bott == worst[0] and neck > worst[1])):
            worst = (bott, neck, net, s, t)
    if worst:
        rows.append(E.row(True, "weakest neck (info)", f"{worst[0]:.2f} mm over {worst[1]:.2f} mm on {worst[2]} "
                                                       f"{worst[3]}->{worst[4]}"))

    sw_seg = [s for s in b.seg if s[4] in SW]
    fan = b.areas.get(emi.get("fanout_area", ""), [])
    pin_field = {}
    gaps = {}
    for s0, s1, w, layer, n in b.seg:
        if n in SW or n == "GND":
            continue
        for a0, a1, aw, al, an in sw_seg:
            if al == layer:
                d = E.seg_seg(s0, s1, a0, a1) - w / 2 - aw / 2
                tgt = pin_field if fan and (E.inside(s0, fan) or E.inside(s1, fan)) else gaps
                if d < tgt.get(n, (9, 0))[0]:
                    tgt[n] = (d, w, layer, s0)
    for p, dia, n in b.via:
        if n in SW or n == "GND":
            continue
        for a0, a1, aw, al, an in sw_seg:
            d = E.seg_dist(p, a0, a1) - dia / 2 - aw / 2
            tgt = pin_field if fan and E.inside(p, fan) else gaps
            if d < tgt.get(n, (9, 0))[0]:
                tgt[n] = (d, dia, "via", p)
    close = sorted(gaps.items(), key=lambda kv: kv[1][0])[:5]
    sig = [(n, v) for n, v in gaps.items() if n.startswith(("/Charger/CHG_", "/Charger/USB_D"))]
    tw = lambda n: min((s[2] for s in b.seg if s[4] == n), default=0.2)  # noqa: E731  (net track width, vias too)
    bad = [(n, v) for n, v in sig if v[0] < max(0.6, 3 * tw(n)) - 1e-3]
    rows.append(E.row(not bad, "I2C/INT/CE/USB to SW spacing",
                      ", ".join(f"{n.split('/')[-1]} {v[0]:.2f}" for n, v in sorted(sig, key=lambda kv: kv[1][0])) +
                      " mm (min 0.6 and 3x width; outside the U3 pin field)"))
    pf = sorted(pin_field.items(), key=lambda kv: kv[1][0])[:4]
    rows.append(E.row(True, "inside the U3 pin field (info)",
                      "; ".join(f"{n.split('/')[-1]} {v[0]:.2f} mm {v[2]}" for n, v in pf) +
                      " (0.4 mm pin pitch, under the body; screened by In1/In2 between F and B)"))
    rows.append(E.row(True, "closest nets to SW (info)",
                      "; ".join(f"{n.split('/')[-1]} {v[0]:.2f} mm {v[2]} ({v[3][0] - ox:.1f}, {v[3][1] - oy:.1f})"
                                for n, v in close)))
    vip = [(n, k) for p, d, n in b.via for k, q in g.pad.items() if q["smd"] and g.in_pad(p, k)]
    rows.append(E.row(not vip, "via in SMD pad", f"{len(vip)}" + (f": {vip[:6]}" if vip else "")))
    known = {k["row"]: k["known"] for k in emi.get("known", [])}   # critical.py `known:` pattern: FAIL -> WARN
    rows = [("WARN", n, f"{d} (known: {known[n]})") if s == "FAIL" and n in known else (s, n, d) for s, n, d in rows]
    fails = report(rows, f"power_route_check: {a.board_dir}")
    print("power_route_check:", "FAILED" if fails else "OK")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
