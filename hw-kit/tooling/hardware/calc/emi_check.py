"""EMI and routing best-practice checks on a routed board (plain Python + calc/pcb.py; no pcbnew).

Reads <board>/board.yaml, critical.yaml, <board>/emi.yaml (else critical.yaml emi:) and the .kicad_pcb (zones filled). Prints OK/WARN/FAIL rows with numbers:
  diff pair   per critical.yaml diff_pair: layers of the main run, per-path length and skew (legs: pad-to-pad paths per
              plug orientation, series resistor bodies count equally), stub lengths and skew, vias, spacing of every
              other net's tracks/vias to the pair (outside rule area `fanout_area`), other copper crossing under/over
              the main run (plan view, any layer), the pair's stub round trip against the edge time
  edge        GND via fence along the board edge: largest gap between neighbouring vias (exempt spans: hole and antenna
              rule areas and critical.yaml emi.edge_exempt rectangles), limit emi.edge_pitch_mm (REQUIREMENTS E2)
  antenna     tracks or vias inside the antenna rule area (emi.antenna_area), copper above the top edge
  planes      signal tracks over a void of their reference plane (F.Cu -> In1, B.Cu -> In2): longest continuous run
  loops       switcher_loop entries: copper path VIN cap -> VIN pin and GND pin -> cap GND (or via-to-via through the
              plane), loop length; SW node copper area (tracks)
  parallel    emi.parallel: victim nets vs aggressor nets, longest same-layer run closer than gap_mm
Usage: python3 hardware/calc/emi_check.py hardware/<board> [--selftest]
"""

import argparse
import heapq
import itertools
import math
import sys
from fnmatch import fnmatch
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import yaml  # noqa: E402
from pcb import child, children, load_profile, parse, report  # noqa: E402

BARREL_MM = 1.53       # F.Cu -> B.Cu via barrel on a 1.6 mm board (copper excluded), counted separately
V_MM_PER_NS = 160.0    # microstrip, er_eff about 3.4 (FR4 7628): 0.3/sqrt(3.4) m/ns = 163 mm/ns


# ---------------------------------------------------------------- geometry
def seg_dist(p, a, b):
    ax, ay = a
    dx, dy = b[0] - ax, b[1] - ay
    n = dx * dx + dy * dy
    t = 0.0 if n == 0 else max(0.0, min(1.0, ((p[0] - ax) * dx + (p[1] - ay) * dy) / n))
    return math.dist(p, (ax + t * dx, ay + t * dy))


def seg_seg(a, b, c, d):
    if crosses(a, b, c, d):
        return 0.0
    return min(seg_dist(a, c, d), seg_dist(b, c, d), seg_dist(c, a, b), seg_dist(d, a, b))


def crosses(a, b, c, d):
    def o(p, q, r):
        v = (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])
        return (v > 1e-9) - (v < -1e-9)
    return o(a, b, c) * o(a, b, d) < 0 and o(c, d, a) * o(c, d, b) < 0


def inside(p, poly):
    x, y = p
    c = False
    for (x1, y1), (x2, y2) in zip(poly, poly[1:] + poly[:1]):
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            c = not c
    return c


def parallel_run(a, b, c, d, gap):
    """Length of segment a-b that runs within `gap` of segment c-d with less than 15 degrees between them."""
    va, vc = (b[0] - a[0], b[1] - a[1]), (d[0] - c[0], d[1] - c[1])
    la, lc = math.hypot(*va), math.hypot(*vc)
    if la < 1e-6 or lc < 1e-6:
        return 0.0
    if abs(va[0] * vc[1] - va[1] * vc[0]) / (la * lc) > math.sin(math.radians(15)):
        return 0.0
    n = max(2, int(la / 0.1))
    pts = [(a[0] + va[0] * i / n, a[1] + va[1] * i / n) for i in range(n + 1)]
    def beside(p):  # projection falls on c-d (not past its ends) and close enough
        t = ((p[0] - c[0]) * vc[0] + (p[1] - c[1]) * vc[1]) / (lc * lc)
        return 0.0 <= t <= 1.0 and seg_dist(p, c, d) < gap
    return sum(la / n for p in pts[1:] if beside(p))


def shortest(adj, src, dst):
    tie = itertools.count()   # pad nodes (str tuples) and track nodes (coordinate tuples) never get compared
    best, todo = {src: 0.0}, [(0.0, next(tie), src)]
    while todo:
        d, _, u = heapq.heappop(todo)
        if u == dst:
            return d
        if d > best.get(u, 1e18):
            continue
        for v, w in adj.get(u, ()):
            if d + w < best.get(v, 1e18):
                best[v] = d + w
                heapq.heappush(todo, (d + w, next(tie), v))
    return None


# ---------------------------------------------------------------- board model
class Pcb:
    def __init__(self, path):
        root = parse(Path(path).read_text())
        self.seg, self.via, self.pads, self.areas, self.fill = [], [], {}, {}, {}
        for fp in children(root, "footprint"):
            fx, fy = float(child(fp, "at")[1]), float(child(fp, "at")[2])
            fr = float(child(fp, "at")[3]) if len(child(fp, "at")) > 3 else 0.0
            ref = {p[1]: p[2] for p in children(fp, "property")}["Reference"]
            a = math.radians(fr)
            for pad in children(fp, "pad"):
                px, py = float(child(pad, "at")[1]), float(child(pad, "at")[2])
                c = (fx + px * math.cos(a) + py * math.sin(a), fy - px * math.sin(a) + py * math.cos(a))
                size = child(pad, "size")
                r = max(float(size[1]), float(size[2])) / 2
                n = child(pad, "net")
                self.pads.setdefault((ref, pad[1]), (c, r, n[-1] if n else ""))
        for t in children(root, "segment"):
            self.seg.append(((float(child(t, "start")[1]), float(child(t, "start")[2])),
                             (float(child(t, "end")[1]), float(child(t, "end")[2])),
                             float(child(t, "width")[1]), child(t, "layer")[1], child(t, "net")[-1]))
        for v in children(root, "via"):
            self.via.append(((float(child(v, "at")[1]), float(child(v, "at")[2])), float(child(v, "size")[1]),
                             child(v, "net")[-1]))
        for z in children(root, "zone"):
            name = child(z, "name")
            poly = child(z, "polygon")
            if name and poly:
                self.areas[name[1]] = [(float(p[1]), float(p[2])) for p in children(child(poly, "pts"), "xy")]
            net = child(z, "net")
            for f in children(z, "filled_polygon"):
                layer = child(f, "layer")[1]
                pts = [(float(p[1]), float(p[2])) for p in children(child(f, "pts"), "xy")]
                self.fill.setdefault((layer, net[-1] if net else ""), []).append(pts)
        edges = [s for s in children(root, "gr_line") + children(root, "gr_rect") if child(s, "layer")[1] == "Edge.Cuts"]
        xs = [float(child(s, k)[1]) for s in edges for k in ("start", "end")]
        ys = [float(child(s, k)[2]) for s in edges for k in ("start", "end")]
        self.box = (min(xs), min(ys), max(xs), max(ys))

    def graph(self, net, barrel=False):
        adj = {}

        def link(u, v, w):
            adj.setdefault(u, []).append((v, w))
            adj.setdefault(v, []).append((u, w))
        r = lambda p: (round(p[0], 3), round(p[1], 3))  # noqa: E731
        ends = []
        for a, b, w, layer, n in self.seg:
            if n == net:
                link((r(a), layer), (r(b), layer), math.dist(a, b))
                ends += [(r(a), layer), (r(b), layer)]
        for p, d, n in self.via:
            if n == net:
                link((r(p), "F.Cu"), (r(p), "B.Cu"), BARREL_MM if barrel else 0.0)
                ends += [(r(p), "F.Cu"), (r(p), "B.Cu")]
        for (ref, num), (c, rad, n) in self.pads.items():
            if n != net:
                continue
            for e in ends:
                if math.dist(e[0], c) <= rad + 1e-3:
                    link(("pad", ref, num), e, math.dist(e[0], c))
        # track ends landing on another track of the net (T-junctions)
        segs = [(r(a), r(b), layer) for a, b, w, layer, n in self.seg if n == net]
        for e in ends:
            for a, b, layer in segs:
                if layer == e[1] and e[0] not in (a, b) and seg_dist(e[0], a, b) < 1e-3:
                    link(e, (a, layer), math.dist(e[0], a))
                    link(e, (b, layer), math.dist(e[0], b))
        return adj

    def path(self, net, a, b, barrel=False):
        ra, pa = a.split(".", 1)
        rb, pb = b.split(".", 1)
        return shortest(self.graph(net, barrel), ("pad", ra, pa), ("pad", rb, pb))


# ---------------------------------------------------------------- checks
def row(ok, name, detail, warn=False):
    return ("OK" if ok else ("WARN" if warn else "FAIL"), name, detail)


def check_pair(b, e, emi):
    rows = []
    p, n = e["p"], e["n"]
    main = emi.get("pair_main_layer", e.get("layer", "F.Cu"))
    fan = b.areas.get(emi.get("fanout_area", ""), [])
    for leg_name, leg in e.get("legs", {}).items():
        for barrel in (False, True):
            lp = sum(b.path(net, *ends, barrel=barrel) or float("nan") for net, ends in leg["p"])
            ln = sum(b.path(net, *ends, barrel=barrel) or float("nan") for net, ends in leg["n"])
            tag = "copper+via barrels" if barrel else "copper"
            ok = abs(lp - ln) <= e["max_skew_mm"]
            rows.append(row(ok, f"{e['name']} path {leg_name} skew ({tag})",
                            f"P {lp:.2f} mm, N {ln:.2f} mm, skew {abs(lp - ln):.2f} (max {e['max_skew_mm']})", warn=barrel))
    st = e.get("stubs")
    if st:
        sp, sn = b.path(p, *st["p"]), b.path(n, *st["n"])
        rows.append(row(abs(sp - sn) <= e["max_skew_mm"], f"{e['name']} stub skew",
                        f"P {sp:.2f} mm, N {sn:.2f} mm, skew {abs(sp - sn):.2f} (max {e['max_skew_mm']})"))
        rt = 2 * max(sp, sn) / V_MM_PER_NS
        edge = st.get("edge_ns", 4.0)
        rows.append(row(rt <= edge / 10, f"{e['name']} stub round trip",
                        f"{rt * 1000:.0f} ps vs edge {edge} ns ({rt / edge:.1%}; lumped below 10 %)"))
    tot_p = sum(math.dist(a, c) for a, c, w, l, nn in b.seg if nn == p)
    tot_n = sum(math.dist(a, c) for a, c, w, l, nn in b.seg if nn == n)
    rows.append(row(abs(tot_p - tot_n) <= e["max_skew_mm"], f"{e['name']} net copper skew",
                    f"P {tot_p:.2f} mm, N {tot_n:.2f} mm, diff {abs(tot_p - tot_n):.2f} (critical.py metric)"))
    nv = sum(1 for _, _, nn in b.via if nn in (p, n))
    rows.append(row(nv <= e["max_vias"], f"{e['name']} vias", f"{nv} (max {e['max_vias']})"))
    usb = [s for s in b.seg if s[4] in (p, n)]
    per = {}
    for s in usb:
        if not (fan and (inside(s[0], fan) or inside(s[1], fan))):
            per[s[3]] = per.get(s[3], 0.0) + math.dist(s[0], s[1])
    allowed = {main, emi.get("stub_layer", main)}
    rows.append(row(set(per) <= allowed, f"{e['name']} layers",
                    "outside the fan-out: " + ", ".join(f"{k} {v:.1f} mm" for k, v in sorted(per.items()))
                    + f" (main run {main}, stubs {emi.get('stub_layer', main)})"))
    mins = 1e9
    where = None
    need = emi.get("pair_spacing_mm", 0.6)
    for a, c, w, layer, nn in b.seg:
        if nn in (p, n):
            continue
        for ua, uc, uw, ul, un in usb:
            if ul != layer or (fan and (inside(ua, fan) or inside(uc, fan))):
                continue
            g = seg_seg(a, c, ua, uc) - w / 2 - uw / 2
            if g < mins:
                mins, where = g, (nn, layer, ua)
    for pos, d, nn in b.via:
        if nn in (p, n):
            continue
        for ua, uc, uw, ul, un in usb:
            if fan and (inside(ua, fan) or inside(uc, fan)):
                continue
            g = seg_dist(pos, ua, uc) - d / 2 - uw / 2
            if g < mins:
                mins, where = g, (nn, "via", ua)
    rows.append(row(mins >= need - 1e-3, f"{e['name']} spacing to other nets",
                    f"min {mins:.2f} mm (need {need}) at {where[0]} {where[1]} near ({where[2][0] - b.box[0]:.1f}, "
                    f"{where[2][1] - b.box[1]:.1f})" if where else "no other copper"))
    run = [s for s in usb if s[3] == main and not (fan and (inside(s[0], fan) or inside(s[1], fan)))]
    xs = [(nn, layer) for a, c, w, layer, nn in b.seg if nn not in (p, n)
          for ua, uc, uw, ul, un in run if crosses(a, c, ua, uc)]
    rows.append(row(not xs, f"{e['name']} crossings of the main run",
                    f"{len(xs)} other-net segments cross it in plan view" + (f": {sorted(set(xs))[:6]}" if xs else "")))
    stub = [s for s in usb if s[3] != main]
    xs2 = {nn for a, c, w, layer, nn in b.seg if nn not in (p, n) and layer != stub[0][3]
           for ua, uc, uw, ul, un in stub if crosses(a, c, ua, uc)} if stub else set()
    rows.append(row(True, f"{e['name']} stub crossings (info)",
                    f"{len(xs2)} nets cross the {stub[0][3] if stub else '-'} stubs on another layer (screened by the "
                    f"GND planes between): {sorted(xs2)[:8]}"))
    return rows


def check_edge(b, emi):
    x0, y0, x1, y1 = b.box
    lim = emi.get("edge_pitch_mm", 5.0)
    band = emi.get("edge_band_mm", 1.6)
    per = 2 * (x1 - x0) + 2 * (y1 - y0)

    def s_of(p):
        x, y = p
        d = {"t": y - y0, "r": x1 - x, "b": y1 - y, "l": x - x0}
        side = min(d, key=d.get)
        return {"t": x - x0, "r": (x1 - x0) + (y - y0), "b": (x1 - x0) + (y1 - y0) + (x1 - x),
                "l": 2 * (x1 - x0) + (y1 - y0) + (y1 - y)}[side], d[side]

    def pt(s):
        w, h = x1 - x0, y1 - y0
        s %= per
        if s < w:
            return (x0 + s, y0 + 1.0)
        if s < w + h:
            return (x1 - 1.0, y0 + s - w)
        if s < 2 * w + h:
            return (x1 - (s - w - h), y1 - 1.0)
        return (x0 + 1.0, y1 - (s - 2 * w - h))
    ss = sorted(s for p, d, n in b.via if n == "GND" for s, dd in [s_of(p)] if dd <= band)
    if not ss:
        return [row(False, "edge GND fence", f"no GND vias within {band} mm of the edge")]
    exempt = [b.areas[k] for k in b.areas if k.startswith("hole_") or k == emi.get("antenna_area")]
    rects = emi.get("edge_exempt", [])
    worst, worst_at, gaps = 0.0, None, []
    for a, c in zip(ss, ss[1:] + [ss[0] + per]):
        g = c - a
        if g <= lim:
            continue
        # gap length outside exempt spans
        n = int(g / 0.2)
        free = sum(0.2 for i in range(n) if not any(inside(pt(a + i * 0.2), poly) for poly in exempt)
                   and not any(r["box"][0] <= pt(a + i * 0.2)[0] - x0 <= r["box"][2]
                               and r["box"][1] <= pt(a + i * 0.2)[1] - y0 <= r["box"][3] for r in rects))
        if free > lim:
            gaps.append((round(free, 1), tuple(round(v, 1) for v in (pt(a)[0] - x0, pt(a)[1] - y0))))
        if free > worst:
            worst, worst_at = free, pt(a)
    rows = [row(not gaps, "edge GND fence", f"{len(ss)} vias within {band} mm of the edge, largest unexempted gap "
                f"{worst:.1f} mm (max {lim})" + (f"; gaps (len, start): {gaps}" if gaps else ""))]
    return rows


def check_antenna(b, emi):
    area = b.areas.get(emi.get("antenna_area", ""), [])
    t = [n for a, c, w, l, n in b.seg if area and (inside(a, area) or inside(c, area) or any(
        crosses(a, c, p, q) for p, q in zip(area, area[1:] + area[:1])))]
    v = [n for p, d, n in b.via if area and inside(p, area)]
    out = [n for a, c, w, l, n in b.seg if min(a[1], c[1]) < b.box[1]]
    return [row(not t and not v and not out, "antenna strip",
                f"{len(t)} tracks, {len(v)} vias inside '{emi.get('antenna_area')}', {len(out)} tracks past the top edge")]


def check_planes(b, emi):
    ref = emi.get("plane_ref", {"F.Cu": "In1.Cu", "B.Cu": "In2.Cu"})
    lim = emi.get("void_max_mm", 1.0)
    worst, at = 0.0, None
    for a, c, w, layer, n in b.seg:
        if layer not in ref or n == "GND":
            continue
        fills = b.fill.get((ref[layer], "GND"), [])
        own = [(pc, r + 0.45) for pc, r, nn in b.pads.values() if nn == n] + \
              [(pos, d / 2 + 0.45) for pos, d, nn in b.via if nn == n]   # its own antipads (clearance 0.25 + margin)
        L = math.dist(a, c)
        k = max(1, int(L / 0.1))
        run = 0.0
        for i in range(k + 1):
            p = (a[0] + (c[0] - a[0]) * i / k, a[1] + (c[1] - a[1]) * i / k)
            if any(inside(p, f) for f in fills) or any(math.dist(p, q) < r for q, r in own):
                run = 0.0
            else:
                run += L / k
                if run > worst:
                    worst, at = run, (n, layer, p)
    return [row(worst <= lim, "track over plane void",
                f"longest continuous run without its reference plane under it {worst:.2f} mm (max {lim}; its own "
                f"pads' and vias' antipads excluded)" + (f" at {at[0]} {at[1]} ({at[2][0] - b.box[0]:.1f}, "
                                                             f"{at[2][1] - b.box[1]:.1f})" if at else ""))]


def check_loops(b, crit, emi):
    rows = []
    for e in crit.get("switcher_loop", []):
        cin = e["cin"]
        vin_net = b.pads[tuple(e["vin"].split(".", 1))][2]
        l1 = b.path(vin_net, f"{cin}.1", e["vin"])
        l2 = b.path("GND", e["gnd"], f"{cin}.2")
        how = "copper"
        if l2 is None:  # through the plane: nearest GND via of each pad, joined in In1
            def nearest_via(pad):
                c = b.pads[tuple(pad.split(".", 1))][0]
                g = b.graph("GND")
                best = None
                for pos, d, n in b.via:
                    if n != "GND":
                        continue
                    k = shortest(g, ("pad", *pad.split(".", 1)), ((round(pos[0], 3), round(pos[1], 3)), "F.Cu"))
                    if k is not None and (best is None or k < best[0]):
                        best = (k, pos)
                return best or (math.dist(c, c), c)
            ga, gb = nearest_via(e["gnd"]), nearest_via(f"{cin}.2")
            l2 = ga[0] + gb[0] + math.dist(ga[1], gb[1]) + 2 * 0.21
            how = "via + In1 plane"
        pins = math.dist(b.pads[tuple(e["vin"].split(".", 1))][0], b.pads[tuple(e["gnd"].split(".", 1))][0])
        tot = (l1 or 0) + l2 + pins
        lim, hard = emi.get("loop_max_mm", 12.0), emi.get("loop_fail_mm", 15.0)
        st = "OK" if l1 is not None and tot <= lim else ("WARN" if l1 is not None and tot <= hard else "FAIL")
        rows.append((st, f"loop {e['name']}", f"cap->VIN {l1 or float('nan'):.1f} + VIN->GND pin {pins:.1f} + GND->cap "
                     f"{l2:.1f} ({how}) = {tot:.1f} mm (target {lim}, fail above {hard})"))
    for net in emi.get("sw_nets", []):
        area = sum(math.dist(a, c) * w for a, c, w, l, n in b.seg if n == net)
        rows.append(row(area <= emi.get("sw_area_max_mm2", 3.0), f"SW copper {net.split('/')[-1]}",
                        f"{area:.2f} mm2 of track (pads excluded; max {emi.get('sw_area_max_mm2', 3.0)})"))
    return rows


def check_parallel(b, emi):
    rows = []
    for e in emi.get("parallel", []):
        vic = [s for s in b.seg if any(fnmatch(s[4], p) for p in e["victims"])]
        agg = [s for s in b.seg if any(fnmatch(s[4], p) for p in e["aggressors"])]
        worst, at = 0.0, None
        for a, c, w, l, n in vic:
            tot = sum(parallel_run(a, c, ga, gc, e["gap_mm"] + w / 2 + gw / 2)
                      for ga, gc, gw, gl, gn in agg if gl == l and gn != n)
            if tot > worst:
                worst, at = tot, (n, l)
        rows.append(row(worst <= e["max_mm"], f"parallel {e['name']}",
                        f"longest victim segment run within {e['gap_mm']} mm of an aggressor: {worst:.2f} mm "
                        f"(max {e['max_mm']})" + (f" ({at[0]} {at[1]})" if at else "")))
    return rows


def selftest():
    assert abs(seg_dist((0, 1), (-1, 0), (1, 0)) - 1) < 1e-9
    assert crosses((0, 0), (2, 2), (0, 2), (2, 0)) and not crosses((0, 0), (1, 0), (0, 1), (1, 1))
    assert inside((0.5, 0.5), [(0, 0), (1, 0), (1, 1), (0, 1)]) and not inside((2, 0.5), [(0, 0), (1, 0), (1, 1), (0, 1)])
    assert abs(parallel_run((0, 0), (10, 0), (2, 0.3), (6, 0.3), 0.5) - 4.0) < 0.2
    assert parallel_run((0, 0), (10, 0), (0, 0.3), (0, 5), 0.5) == 0.0
    adj = {"a": [("b", 1.0), ("c", 5.0)], "b": [("c", 1.0)], "c": []}
    assert shortest(adj, "a", "c") == 2.0
    print("emi_check selftest OK")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("board_dir", type=Path, nargs="?")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        selftest()
        return
    prof = load_profile(a.board_dir)
    crit = prof["critical"]
    ef = a.board_dir / "emi.yaml"
    emi = yaml.safe_load(ef.read_text()) if ef.exists() else crit.get("emi", {})
    b = Pcb(a.board_dir / prof["pcb"])
    rows = []
    for e in crit.get("diff_pair", []):
        rows += check_pair(b, e, emi)
    rows += check_edge(b, emi) + check_antenna(b, emi) + check_planes(b, emi) + check_loops(b, crit, emi)
    rows += check_parallel(b, emi)
    fails = report(rows, f"emi_check: {a.board_dir}")
    print("emi_check:", "FAILED" if fails else "OK")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
