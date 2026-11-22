"""main-board hand-drawn copper (plain Python: no pcbnew). gen/main_pcb.py draws the result, locked, after placement.

Routing order of the engineer (main-board/BOARD.md "Routing"): the fast and sensitive copper is drawn here from the
placed pad centres (never hard-coded board coordinates; the orientations relied on are asserted), the router
(tools/route_main.sh) only adds the low-speed signals and the rail branches.

  usb()        USB 2.0 pair J1 -> U4 (USBLC6 flow-through) -> R33/R32 (22 ohm) -> U1 pins 13/14, one F.Cu pair 0.27/0.15
               (90 ohm, calc/impedance.py), BC1.2 stubs on B.Cu to J10 pins 7/8, CC resistors, U4 VBUS/GND, GND stitching
  vbus()       USB_VBUS trunk J1 -> J10 pins 19/20 (1.6 A charge input)
  sys()        SYS trunk J10 pins 1/2 -> TPS63802 input cap and TPS61023 input
  buckboost()  TPS63802 U2 power stage (SLVSEU9D 12.1/12.2, figure 12-1)
  boost()      TPS61023 U7 power stage (SLVSF14B 10.1/10.2, figure 10-1)
  mcu()        ESP32 module decoupling at pin 2 with a GND via per cap
  bmp()        BMP580 decoupling and pin escapes (nothing under the body except its own pad entries)
  gate()       Q40 gate network (R40, R76, C48) and the 3V3_SW output caps

Item formats: ("T", net, layer "F"/"B", width, [(x, y), ...]), ("V", net, x, y, diameter, drill).
"""

import json
import math
from pathlib import Path

VIA = (0.45, 0.25)       # signal via (v1 hand copper)
PVIA = (0.6, 0.3)        # power / GND via
USB_W, USB_GAP = 0.27, 0.15
HALF = (USB_W + USB_GAP) / 2   # pair centre to line centre
FLAT = 0.6               # flat run of the pair before the split at the resistors (mm)
STUB_SKEW = 0.23        # DP stub minus DN stub (mm): splits the fan-out difference so stubs and nets both match
MEANDER_N, MEANDER_S = 4, 0.8   # DP stub meander: bumps, leg pitch (mm; 3.3 x the width)


def offset(pts, d):
    """Polyline offset by d to the LEFT of the travel direction (y down, so left of east is north), mitred joins."""
    def unit(a, b):
        dx, dy = b[0] - a[0], b[1] - a[1]
        n = math.hypot(dx, dy)
        return dx / n, dy / n

    out = []
    for i, p in enumerate(pts):
        if i == 0:
            t = unit(pts[0], pts[1])
            nx, ny = t[1], -t[0]
            out.append((p[0] + nx * d, p[1] + ny * d))
            continue
        if i == len(pts) - 1:
            t = unit(pts[-2], pts[-1])
            nx, ny = t[1], -t[0]
            out.append((p[0] + nx * d, p[1] + ny * d))
            continue
        t1, t2 = unit(pts[i - 1], p), unit(p, pts[i + 1])
        n1, n2 = (t1[1], -t1[0]), (t2[1], -t2[0])
        mx, my = n1[0] + n2[0], n1[1] + n2[1]
        m = math.hypot(mx, my)
        mx, my = mx / m, my / m
        k = d / (mx * n1[0] + my * n1[1])
        out.append((p[0] + mx * k, p[1] + my * k))
    return [(round(x, 4), round(y, 4)) for x, y in out]


def meander(x, y, side, a, n, s, ch=0.2):
    """Vertical run going south from (x, y) with n rectangular bumps of amplitude a to `side` (-1 west), legs s apart,
    corners chamfered at 45 degrees (ch)."""
    pts = [(x, y)]
    for _ in range(n):
        xo = x + side * a
        pts += [(x + side * ch, y + ch), (xo - side * ch, y + ch), (xo, y + 2 * ch),
                (xo, y + s - ch), (xo - side * ch, y + s), (x + side * ch, y + s), (x, y + s + ch), (x, y + 2 * s)]
        y += 2 * s
    return pts


def length(pts):
    return sum(math.dist(a, b) for a, b in zip(pts, pts[1:]))


class Copper:
    def __init__(self, P):
        self.P = P          # P(ref, pad) -> (x, y) pad centre, board mm from the top-left corner
        self.items = []

    def t(self, net, layer, w, pts):
        self.items.append(("T", net, layer, w, [(round(x, 4), round(y, 4)) for x, y in pts]))

    def v(self, net, x, y, size=VIA):
        self.items.append(("V", net, round(x, 4), round(y, 4), *size))


DP, DN = "/USB_DP", "/USB_DN"


def usb(c):
    P = c.P
    # J1 (HRO TYPE-C-31-M-12, rotated 270, pads in one column): top to bottom B7 A6 A7 B6 = DN DP DN DP
    b7, a6, a7, b6 = P("J1", "B7"), P("J1", "A6"), P("J1", "A7"), P("J1", "B6")
    x0 = a6[0]
    assert all(abs(p[0] - x0) < 1e-3 for p in (b7, a7, b6)), "J1 pads must form one column"
    assert b7[1] < a6[1] < a7[1] < b6[1], "J1 order B7 A6 A7 B6 (top to bottom) assumed"
    # U4 USBLC6 rotated 180: DN flows pin 4 (left) -> pin 3 (right) on the top row, DP pin 6 -> pin 1 on the bottom row
    u4, u3, u6, u1, u5, u2 = (P("U4", n) for n in "436152")
    assert u4[0] < u3[0] and abs(u4[1] - u3[1]) < 1e-3 and u6[0] < u1[0] and u4[1] < u5[1] < u6[1], "U4 rotation 180"
    # R33 (DN) above R32 (DP), pad 1 on the connector side (left), module pins 13 (DN) / 14 (DP) right of them
    r33, r32 = P("R33", "1"), P("R32", "1")
    assert abs(r33[0] - r32[0]) < 1e-3 and r33[1] < r32[1] and P("R33", "2")[0] > r33[0], "R33 over R32, pad 1 left"

    # --- connector fan-out (narrow 0.2 mm between the 0.5 mm pitch pads) ---
    xu = x0 + 1.66                      # DP U-link column: joins A6 and B6 around A7
    c.t(DP, "F", 0.2, [a6, (xu, a6[1]), (xu, b6[1]), b6])
    # A7 drops inside the U-link, crosses under it on B.Cu and comes up on the DN line (the only 2 vias of the path)
    va7 = (x0 + 1.185, a7[1])
    vdn = (x0 + 2.21, b7[1])
    c.t(DN, "F", 0.2, [a7, va7])
    # the B.Cu jumper takes a short detour: A-side DN path = A-side DP path (the U-link adds 1.0 mm to A6's branch)
    c.t(DN, "B", 0.2, [va7, (vdn[0] - 0.15, a7[1]), (vdn[0], a7[1] - 0.15), vdn])
    c.v(DN, *va7)
    c.v(DN, *vdn)
    # J1 to U4: DN straight along B7's row, DP from the U-link corner; both jog onto the U4 rows
    jx = u4[0] - 1.45
    c.t(DN, "F", 0.2, [b7, (vdn[0], b7[1])])
    c.t(DN, "F", USB_W, [(vdn[0], b7[1]), (jx, b7[1]), (jx + abs(u4[1] - b7[1]), u4[1]), u4])
    c.t(DP, "F", USB_W, [(xu, b6[1]), (jx, b6[1]), (jx + abs(u6[1] - b6[1]), u6[1]), u6])
    # flow-through: each line runs under U4 from pin to pin (separate pads in KiCad)
    c.t(DN, "F", USB_W, [u4, u3])
    c.t(DP, "F", USB_W, [u6, u1])

    # --- main run: pair centreline from U4's exit to the resistors, 45-degree bends only ---
    yc = (u3[1] + u1[1]) / 2
    conv = (u1[1] - u3[1]) / 2 - HALF   # each line converges by this much (symmetric)
    xs = u3[0] + 1.0                    # leave the pads straight (room for the GND via at pin 2), then 45 degrees in
    ym = (r33[1] + r32[1]) / 2          # pair centre at the resistor split
    split = (r32[1] - r33[1]) / 2 - HALF
    x_end = r33[0] - 0.55               # last bend before the pads (0.27 mm pad entry)
    x_flat = x_end - split              # end of the flat run at ym (then each line splits at 45 degrees)
    x_diag = x_flat - FLAT - (ym - yc)  # start of the 45-degree descent
    centre = [(xs + conv, yc), (x_diag, yc), (x_flat - FLAT, ym), (x_flat, ym)]
    dn_run = offset(centre, HALF)       # north line
    dp_run = offset(centre, -HALF)
    c.t(DN, "F", USB_W, [u3, (xs, u3[1])] + dn_run + [(x_end, r33[1]), r33])
    c.t(DP, "F", USB_W, [u1, (xs, u1[1])] + dp_run + [(x_end, r32[1]), r32])
    # GND stitching vias beside the pair (0.6 mm via, >= 0.6 mm copper to the pair), about every 4-5 mm, both sides
    d = HALF + USB_W / 2 + 0.6 + 0.3 + 0.05
    # the B.Cu crossing window (main_pcb.py) lies between; the north via sits further east, clear of the VANE via
    for xn, xs_ in ((0.5, 0.5), (5.1, 4.2)):
        c.v("GND", centre[0][0] + xn, yc - d, PVIA)
        c.v("GND", centre[0][0] + xs_, yc + d, PVIA)
    (dx0, dy0), (dx1, dy1) = centre[1], centre[2]
    for f in (0.42, 0.86):
        px, py = dx0 + f * (dx1 - dx0), dy0 + f * (dy1 - dy0)
        k = d / math.sqrt(2)
        c.v("GND", px + k, py - k, PVIA)
        c.v("GND", px - k, py + k, PVIA)
    # resistors to the module pins (ESP side, 1.27 mm apart: the pins' own pitch)
    c.t("/MCU/ESP_DN", "F", USB_W, [P("R33", "2"), P("U1", "13")])
    c.t("/MCU/ESP_DP", "F", USB_W, [P("R32", "2"), P("U1", "14")])

    # --- BC1.2 stubs to J10 pins 7 (DP) / 8 (DN): T-taps at the resistors (the pair end nearest J10), on B.Cu ---
    # DN taps above R33, DP below R32 (no crossing of the pair); both run east, then one coupled 45-degree pair (DP on
    # the south-west side, offset 0.42 mm) down to J10. DP goes straight into pin 7, DN passes pin 7 on its east side.
    j7, j8 = P("J10", "7"), P("J10", "8")
    assert abs(j7[0] - j8[0]) < 1e-3 and j7[1] < j8[1], "J10 pin 7 above pin 8"
    vt_dn = (r33[0], r33[1] - 0.88)
    vt_dp = (r32[0], r32[1] + 0.9)
    c.t(DN, "F", 0.2, [r33, vt_dn])
    c.t(DP, "F", 0.2, [r32, vt_dp])
    c.v(DN, *vt_dn)
    c.v(DP, *vt_dp)
    pitch = 2 * HALF
    xn = vt_dn[0] + 1.26
    xp = xn + (vt_dp[1] - vt_dn[1]) - pitch * math.sqrt(2)
    xv, xvn = j7[0], j7[0] + pitch
    dn_y = vt_dn[1] + (xvn - xn)
    dp_y = vt_dp[1] + (xv - xp)
    xr = j7[0] + 1.27                   # DN passes pin 7 at 1.27 mm (0.285 mm to the pad)
    yj = j7[1] - 2.9
    dn = [vt_dn, (xn, vt_dn[1]), (xvn, dn_y), (xvn, yj), (xr, yj + xr - xvn), (xr, j8[1] - (xr - j8[0])), j8]
    target = length(dn) + 0.88 + STUB_SKEW - 0.9   # DP stub (incl. its F.Cu drop) = DN stub + STUB_SKEW
    base = [vt_dp, (xp, vt_dp[1]), (xv, dp_y)]

    def dp_path(a):
        return base + meander(xv, dp_y + 0.8, -1, a, MEANDER_N, MEANDER_S) + [j7]

    lo, hi = 0.3, 1.6                   # meander amplitude by bisection on the stub length
    for _ in range(40):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if length(dp_path(mid)) < target else (lo, mid)
    c.t(DP, "B", USB_W, dp_path(lo))
    c.t(DN, "B", USB_W, dn)
    for dx, dy in ((1.05, 1.5), (1.5, 9.6)):   # GND stitching east of the stub pair
        c.v("GND", xvn + dx, dn_y + dy, PVIA)

    # --- CC pull-downs, U4 supply, ESD ground ---
    a5, b5 = P("J1", "A5"), P("J1", "B5")
    c.t("/USB/CC1", "F", 0.2, [a5, (P("R9", "1")[0] - 0.45, a5[1]), P("R9", "1")])
    c.t("/USB/CC2", "F", 0.2, [b5, P("R10", "1")])
    for ref, dx, dy in (("R9", 0.75, 0.0), ("R10", 0.0, 0.8)):
        g = P(ref, "2")
        c.t("GND", "F", 0.3, [g, (g[0] + dx, g[1] + dy)])
        c.v("GND", g[0] + dx, g[1] + dy)
    c.t("GND", "F", 0.3, [u2, (u2[0] + 1.06, u2[1])])        # ESD return: via right at the GND pin, between the lines
    c.v("GND", u2[0] + 1.06, u2[1])
    vb = (u5[0] - 1.2, u5[1])                                # VBUS pin 5 sits between the lines: via beside it
    c.t("USB_VBUS", "F", 0.3, [u5, vb])
    c.v("USB_VBUS", *vb)
    c35v, c35g = P("C35", "1"), P("C35", "2")
    assert c35v[0] < c35g[0], "C35 VBUS pad left"
    vc = (c35v[0], c35v[1] + 0.75)
    c.t("USB_VBUS", "F", 0.3, [c35v, vc])
    c.v("USB_VBUS", *vc)
    c.t("GND", "F", 0.3, [c35g, (c35g[0] + 0.75, c35g[1])])
    c.v("GND", c35g[0] + 0.75, c35g[1])
    # J1 A4/B9 (upper VBUS pair) to C35, then B.Cu C35 -> U4 pin 5 -> the trunk below the pair
    a4 = P("J1", "A4")
    c.t("USB_VBUS", "F", 0.4, [a4, (vc[0] - 1.7, a4[1]), (c35v[0] - 0.5, c35v[1]), c35v])
    c.t("USB_VBUS", "B", 0.4, [vc, vb])
    return {"dn_run": dn_run, "dp_run": dp_run, "centre": centre, "xs": xs, "d": d}


def vbus(c):
    P = c.P
    a9 = P("J1", "A9")
    x = a9[0] + 1.41
    j19, j20 = P("J10", "19"), P("J10", "20")
    c.t("USB_VBUS", "F", 0.5, [a9, (x - 0.25, a9[1] + 0.05), (x, a9[1] + 0.3)])
    yb = j19[1] - 2.95
    c.t("USB_VBUS", "F", 0.9, [(x, a9[1] + 0.3), (x, yb - 3.55), (x + 3.55, yb), (j19[0] - 1.55, yb), (j19[0], yb + 1.55), j19, j20])
    vb = P("U4", "5")
    # B.Cu link from U4 pin 5's via down to a via on the trunk (joins both VBUS pad pairs)
    c.v("USB_VBUS", x, a9[1] + 1.4, PVIA)
    c.t("USB_VBUS", "B", 0.4, [(vb[0] - 1.2, vb[1]), (x, a9[1] + 1.4)])


def sys_(c):
    P = c.P
    j1, j2 = P("J10", "1"), P("J10", "2")
    c40 = P("C40", "1")
    xr = j1[0] + 0.7
    y = c40[1] + 0.65
    c.t("SYS", "F", 0.65, [j1, (xr, j1[1] - 0.7), (xr, y + 0.35), (xr - 0.35, y), (c40[0], y)])
    c.t("SYS", "F", 0.9, [j1, j2])
    # branch to the boost: under C41, above the J10 row, up to L5's VIN pad
    l51 = P("L5", "1")
    yb = j1[1] - 1.9
    c.t("SYS", "F", 0.65, [j1, (j1[0] - 0.6, yb), (l51[0] + 0.55, yb), (l51[0], yb - 0.55), (l51[0], l51[1])])


def buckboost(c):
    P = c.P
    p = {n: P("U2", str(n)) for n in range(1, 11)}
    assert p[1][0] < p[10][0] and abs(p[1][1] - p[10][1]) < 1e-3 and p[1][1] < p[2][1], "U2 rotation 0 assumed"
    c40v, c40g = P("C40", "1"), P("C40", "2")
    assert c40g[0] < c40v[0], "C40 GND pad left"
    # VIN pins 1 and 10 joined across the top row, C40 dropped onto the link (input loop: C40 -> VIN -> GND 2/3 -> C40)
    c.t("SYS", "F", 0.3, [p[1], p[10]])
    c.t("SYS", "F", 0.4, [c40v, (c40v[0], p[1][1])])
    c.t("SYS", "F", 0.3, [(p[10][0], c40v[1] + 0.65), p[10]])
    # GND pins 2, 3 and the centre pad 8 joined; via left of pins 2/3; C40's GND pad and R53's GND to that node
    gv = (p[2][0] - 0.75, p[2][1])
    c.t("GND", "F", 0.25, [p[2], p[3]])
    c.t("GND", "F", 0.25, [p[3], p[8]])
    c.t("GND", "F", 0.3, [(p[2][0], gv[1]), gv])
    c.v("GND", *gv)
    cg = (c40g[0], c40g[1] + 1.2)
    c.v("GND", *cg, PVIA)
    c.t("GND", "F", 0.3, [c40g, cg, (gv[0], cg[1] + gv[0] - cg[0]), gv])
    r53g = P("R53", "2")
    c.t("GND", "F", 0.25, [r53g, (r53g[0], gv[1]), gv])
    # switch nodes: pins 9/7 straight to the inductor pads (0.38 mm keeps 0.16 mm to the VIN link and pin 8)
    c.t("/Rails/BUCK_L1", "F", 0.38, [p[9], (P("L4", "1")[0] - 0.25, p[9][1])])
    c.t("/Rails/BUCK_L2", "F", 0.38, [p[7], (P("L4", "2")[0] - 0.25, p[7][1])])
    # VOUT pin 6 to C41, C41 to the top of the FB divider
    c41v, c41g = P("C41", "1"), P("C41", "2")
    c.t("+3V3", "F", 0.25, [p[6], (p[6][0] - 0.35, p[6][1])])     # pad-height neck (0.165 mm to the L2 track)
    c.t("+3V3", "F", 0.4, [(p[6][0] - 0.35, p[6][1] + 0.1), (c41v[0] + 0.3, c41v[1] - 0.87), (c41v[0], c41v[1] - 0.3)])
    r52t = P("R52", "1")
    c.t("+3V3", "F", 0.3, [(c41v[0], c41v[1] + 0.28), (r52t[0] + 0.38, c41v[1] + 0.28), (r52t[0], c41v[1] - 0.1), r52t])
    for dy in (-0.47, 0.48):
        c.v("GND", c41g[0] + 0.95, c41g[1] + dy, PVIA)
        c.t("GND", "F", 0.4, [c41g, (c41g[0] + 0.95, c41g[1] + dy)])
    # FB: pin 4 straight to the divider tap, tap down to R52 (away from the switch pins on the right)
    r53f, r52f = P("R53", "1"), P("R52", "2")
    c.t("/Rails/FB", "F", 0.2, [p[4], r53f, r52f])


def boost(c):
    P = c.P
    p = {n: P("U7", str(n)) for n in range(1, 7)}
    assert p[1][0] < p[6][0] and p[1][1] < p[3][1] and abs(p[3][1] - p[4][1]) < 1e-3, "U7 rotation 0 assumed"
    l51, l52 = P("L5", "1"), P("L5", "2")
    c44v, c44g = P("C44", "1"), P("C44", "2")
    c45v, c45g = P("C45", "1"), P("C45", "2")
    # input: C44 -> VIN pin 3 -> L5 pin 1
    c.t("SYS", "F", 0.3, [c44v, p[3]])
    c.t("SYS", "F", 0.35, [p[3], (l51[0], p[3][1]), l51])
    c.v("GND", c44g[0], c44g[1] + 0.95, PVIA)
    c.v("GND", c44g[0] - 0.92, c44g[1], PVIA)
    c.t("GND", "F", 0.4, [c44g, (c44g[0], c44g[1] + 0.95)])
    c.t("GND", "F", 0.4, [c44g, (c44g[0] - 0.92, c44g[1])])
    # switch node: pin 5 out to the right, down to L5 pin 2 (smallest SW copper; keeps 0.2 mm to GND pin 4)
    xs = p[5][0] + 0.69
    c.t("/Rails/BOOST_SW", "F", 0.3, [p[5], (xs, p[5][1]), (xs, p[4][1] + 0.45)])
    c.t("/Rails/BOOST_SW", "F", 0.5, [(xs, p[4][1] + 0.45), (xs, l52[1] - 0.6), (l52[0], l52[1] - 0.3)])
    # VOUT pin 6 to C45 (output loop), C45 up to C46 and the FB divider top R43
    c.t("5V_SW", "F", 0.3, [p[6], (xs, p[6][1]), (xs + 0.4, p[6][1] - 0.4)])
    c.t("5V_SW", "F", 0.5, [(xs + 0.4, p[6][1] - 0.4), (xs + 0.4, c45v[1]), c45v])
    c46v, c46g = P("C46", "1"), P("C46", "2")
    r43t = P("R43", "1")
    xa = c45v[0] - 0.15
    c.t("5V_SW", "F", 0.5, [c45v, (xa, c45v[1]), (xa, c46v[1] + 0.55), (c46v[0] + 0.5, c46v[1] + 0.35), (c46v[0], c46v[1] + 0.35)])
    c.t("5V_SW", "F", 0.3, [(c46v[0] - 0.4, c46v[1] + 0.35), (r43t[0] + 0.65, c46v[1] + 0.35), (r43t[0], r43t[1] - 0.3), r43t])
    # GND pin 4: under the IC between the pin columns to a via above it (v1 pattern); output cap GND by vias
    xg = (p[1][0] + p[6][0]) / 2
    gv = (xg + 0.22, p[6][1] - 0.67)
    c.t("GND", "F", 0.2, [p[4], (xg, p[4][1]), (xg, gv[1] + 0.27), gv])
    c.v("GND", *gv)
    for dx in (-0.45, 0.4):
        c.v("GND", c45g[0] + dx, c45g[1] + 0.95, PVIA)
        c.t("GND", "F", 0.5, [c45g, (c45g[0] + dx, c45g[1] + 0.95)])
    c.v("GND", c46g[0], c46g[1] + 0.95, PVIA)
    c.t("GND", "F", 0.4, [c46g, (c46g[0], c46g[1] + 0.95)])
    # FB: pin 1 up to the divider tap R43.2, tap to R44.1; R44's GND by its own via
    r43f, r44f, r44g = P("R43", "2"), P("R44", "1"), P("R44", "2")
    c.t("/Rails/BOOST_FB", "F", 0.2, [p[1], (p[1][0], r43f[1]), r43f])
    c.t("/Rails/BOOST_FB", "F", 0.2, [r43f, r44f])
    c.v("GND", r44g[0] - 0.95, r44g[1])
    c.t("GND", "F", 0.3, [r44g, (r44g[0] - 0.95, r44g[1])])
    # EN escapes to a via left of FB (pin 2 is boxed in by FB, VIN and C44); the router takes it from there
    ev = (p[2][0] - 0.76, p[1][1] + 0.03)
    c.t("/MCU/BOOST_EN", "F", 0.2, [p[2], (p[2][0] - 0.49, p[2][1]), ev])
    c.v("/MCU/BOOST_EN", *ev)


def mcu(c):
    P = c.P
    vdd, gnd = P("U1", "2"), P("U1", "1")
    c31v, c31g, c32v, c32g = P("C31", "1"), P("C31", "2"), P("C32", "1"), P("C32", "2")
    c30v, c30g = P("C30", "1"), P("C30", "2")
    assert c32v[0] < c31v[0] < vdd[0] and c31g[1] < c31v[1], "C32, C31 left of pin 2, GND pads on top"
    c.t("+3V3", "F", 0.3, [c32v, c31v, (vdd[0], c31v[1])])
    c.t("+3V3", "F", 0.3, [(c30v[0] + 0.15, c30v[1]), (c30v[0] + 0.15, c31v[1])])
    c.t("GND", "F", 0.3, [c32g, c31g, (gnd[0], gnd[1] + 0.3)])
    c.v("GND", c32g[0] - 0.8, c32g[1] + 0.06)
    c.t("GND", "F", 0.3, [c32g, (c32g[0] - 0.8, c32g[1] + 0.06)])
    c.v("GND", c30g[0], c30g[1] + 1.2, PVIA)
    c.t("GND", "F", 0.4, [c30g, (c30g[0], c30g[1] + 1.2)])
    # the rail feed (router, Rail class 0.4 mm) lands on C30's pad: the bulk cap sits first in the path
    c33g = P("C33", "2")
    c.v("GND", c33g[0], c33g[1] + 0.9)
    c.t("GND", "F", 0.3, [c33g, (c33g[0], c33g[1] + 0.9)])


def bmp(c):
    P = c.P
    u = {n: P("U9", str(n)) for n in range(1, 11)}
    assert u[1][0] < u[6][0] and u[10][1] < u[1][1] < u[2][1], "U9 rotation 0 assumed"
    c90v, c90g, c91v, c91g = P("C90", "1"), P("C90", "2"), P("C91", "1"), P("C91", "2")
    # VDDIO pin 10 from C90 straight down; pin 1 (also 3V3_SW) by a corner link
    c.t("3V3_SW", "F", 0.2, [c90v, (c90v[0], c90v[1] + 0.6), (u[10][0], c90v[1] + 0.83), u[10]])
    c.t("3V3_SW", "F", 0.15, [u[10], (u[10][0] - 0.26, u[10][1] + 0.26), u[1]])
    # GND pins 9 and 8 to C90's GND pad, which has its own via
    c.t("GND", "F", 0.2, [c90g, (c90g[0], c90g[1] + 0.6), (u[9][0], c90g[1] + 0.83), u[9]])
    c.t("GND", "F", 0.15, [u[9], u[8]])
    c.t("GND", "F", 0.15, [u[8], (u[8][0] + 0.26, u[8][1] + 0.26), u[7]])
    c.v("GND", c90g[0] + 0.0, c90g[1] - 0.8)
    c.t("GND", "F", 0.3, [c90g, (c90g[0], c90g[1] - 0.8)])
    # VDD pin 6 to C91 on the right; C91 GND by its via
    c.t("3V3_SW", "F", 0.2, [u[6], (c91v[0] - 0.85, u[6][1]), (c91v[0] - 0.63, c91v[1]), c91v])
    c.v("GND", c91g[0], c91g[1] + 0.8)
    c.t("GND", "F", 0.3, [c91g, (c91g[0], c91g[1] + 0.8)])
    # bottom row: GND pins 3/5 to vias below the body, SDA (pin 4) leaves between them
    for n, dx in ((3, -0.15), (5, 0.15)):
        g = (u[n][0] + dx, u[n][1] + 0.95)
        c.t("GND", "F", 0.2, [u[n], g])
        c.v("GND", *g)


def gate(c):
    P = c.P
    q1, q2, q3 = P("Q40", "1"), P("Q40", "2"), P("Q40", "3")
    assert q1[0] < q3[0] and q1[1] < q2[1], "Q40 rotation 0 assumed"
    r40v, r40g, r76g, r76p = P("R40", "1"), P("R40", "2"), P("R76", "1"), P("R76", "2")
    c48g, c48d = P("C48", "1"), P("C48", "2")
    c.t("/Rails/SEN_G", "F", 0.25, [r76g, r40g, q1])
    c.t("/Rails/SEN_G", "F", 0.25, [c48g, (c48g[0], q1[1])])
    c.t("3V3_SW", "F", 0.25, [c48d, (q3[0], c48d[1] + abs(q3[0] - c48d[0])), q3])
    c.t("+3V3", "F", 0.4, [r40v, (r40v[0], r40v[1] + 0.85), (r40v[0] + 1.05, q2[1]), q2])
    qp = P("Q41", "3")
    c.t("/Rails/SEN_PULL", "F", 0.25, [r76p, (qp[0] + 0.56 + 0.7, r76p[1]), (qp[0] + 0.56, r76p[1] + 0.7), (qp[0] + 0.56, qp[1])])
    # 3V3_SW output: drain to the two 22 uF caps (stacked, pads aligned), each GND pad with its own via
    c42v, c42g, c43v, c43g = P("C42", "1"), P("C42", "2"), P("C43", "1"), P("C43", "2")
    c.t("3V3_SW", "F", 0.4, [q3, (c42v[0] - 0.75, q3[1]), (c42v[0], q3[1] + 0.75), c42v, c43v])
    c.t("GND", "F", 0.4, [c42g, c43g])
    for g in (c42g, c43g):
        c.v("GND", g[0] + 0.95, g[1], PVIA)
        c.t("GND", "F", 0.4, [g, (g[0] + 0.95, g[1])])


def anemometer(c):
    """J12 -> ESD in cable order, planar: VANE (pin 4) straight into U11, WIND (pin 3) and RAIN (pin 2) one level higher
    each into U10; each ESD channel's two pins joined under the body, GND pins by their own via between the lines."""
    P = c.P
    j2, j3, j4 = P("J12", "2"), P("J12", "3"), P("J12", "4")
    a = {n: P("U10", str(n)) for n in range(1, 7)}
    b = {n: P("U11", str(n)) for n in range(1, 7)}
    for u in (a, b):
        assert u[1][0] < u[6][0] and u[1][1] < u[2][1] < u[3][1], "U10/U11 rotation 0 assumed"
    assert a[3][1] < b[1][1] and j2[0] < j3[0] < j4[0] < a[1][0], "U10 above U11, J12 left of both"
    c.t("/Sensors/VANE_IN", "F", 0.25, [j4, (j4[0] + 0.5, b[1][1]), b[1], b[6]])
    c.t("/Sensors/WIND_IN", "F", 0.25, [j3, (j3[0], a[3][1] + 0.4), (j3[0] + 0.4, a[3][1]), a[3], a[4]])
    c.t("/Sensors/RAIN_IN", "F", 0.25, [j2, (j2[0], a[1][1] + 0.4), (j2[0] + 0.4, a[1][1]), a[1], a[6]])
    for u in (a, b):
        g = (u[2][0] - 1.05, u[2][1])
        c.t("GND", "F", 0.3, [u[2], g])
        c.v("GND", *g)


def cluster(c, info):
    """Wind/rain/vane filter block and the three MCU lines to the module's left pins (locked, the autorouter left
    them open). Block: RAIN column (C70 / R72 / R70) and WIND column (C71 / R73 / R71) above U10, VANE column
    (C72 / R75 / R74) right of it. MCU lines: B.Cu bundle (0.5 mm pitch) west of J10, north through the window in
    the pair's B.Cu keepout (two GND planes between), RAIN and WIND on B.Cu into the pocket to vias at pins 8/9,
    VANE up to F.Cu right after the window and along the pair's north side (2 mm from its centre) to pin 12."""
    P = c.P
    W = 0.2
    a = {n: P("U10", str(n)) for n in range(1, 7)}
    b6 = P("U11", "6")
    c70, c71, c72 = P("C70", "1"), P("C71", "1"), P("C72", "1")
    r72 = (P("R72", "1"), P("R72", "2"))
    r73 = (P("R73", "1"), P("R73", "2"))
    r70, r71 = P("R70", "1"), P("R71", "1")
    r75, r74 = (P("R75", "1"), P("R75", "2")), P("R74", "1")
    assert abs(r72[1][0] - c70[0]) < 0.05 and abs(r72[0][0] - r70[0]) < 0.05, "RAIN column pads aligned"
    assert abs(r73[1][0] - c71[0]) < 0.05 and abs(r73[0][0] - r71[0]) < 0.05, "WIND column pads aligned"
    assert c72[1] < r75[1][1] < r75[0][1] < r74[1] and abs(c72[0] - r74[0]) < 0.05, "VANE column C72 / R75 / R74"
    # inputs: ESD pins to the series R and the pull-up
    c.t("/Sensors/RAIN_IN", "F", 0.25, [a[1], (r70[0], a[1][1] - 0.6), r70, r72[0]])
    c.t("/Sensors/WIND_IN", "F", 0.25, [a[4], (r71[0] + 0.54, a[4][1]), (r71[0] + 0.54, r71[1] + 0.54), r71, r73[0]])
    xv = r74[0] - 0.6
    c.t("/Sensors/VANE_IN", "F", 0.25, [b6, (xv, b6[1]), (xv, r74[1]), r74, r75[0]])
    # MCU-side nodes and their bundle vias
    vr = (r72[1][0] - 0.84, c70[1])                       # RAIN via left of C70
    c.t("/MCU/RAIN", "F", W, [r72[1], c70, vr])
    yw = c71[1] - 0.85                                    # WIND runs west above the cap row
    vw = (16.8, yw)
    c.t("/MCU/WIND", "F", W, [r73[1], c71, (c71[0], yw + 0.35), (c71[0] - 0.35, yw), vw])
    vv = (c72[0] - 0.8, (c72[1] + r75[1][1]) / 2)          # VANE via left of its column
    c.t("/MCU/VANE", "F", W, [r75[1], c72])
    c.t("/MCU/VANE", "F", W, [(c72[0], vv[1]), vv])
    for p in (vr, vw, vv):
        c.v(p == vr and "/MCU/RAIN" or p == vw and "/MCU/WIND" or "/MCU/VANE", *p)
    # bundle: RAIN is the centre line; WIND 0.5 mm west, VANE 0.5 mm east (mitred offsets keep the pitch in the jog)
    c0 = info["centre"][0]
    xr0, xr1 = vr[0], c0[0] + 3.12                        # corridor west of J10 pin 20, window in the pair keepout
    jog = [(xr0, 30.0), (xr0, 26.0), (xr1, 26.0 - (xr1 - xr0)), (xr1, 12.5)]
    wm, vm = offset(jog, 0.5), offset(jog, -0.5)
    yr, yw2 = 9.9, 9.4                                    # pocket runs: RAIN south, WIND north (RAIN turns first)
    u8, u9, u12 = P("U1", "8"), P("U1", "9"), P("U1", "12")
    pr = (u8[0] - 2.05, u8[1])                            # RAIN via, then F.Cu to pin 8 over WIND's B.Cu
    pw = (u9[0] - 1.3, u9[1])
    assert pw[0] - pr[0] > 0.7
    c.t("/MCU/RAIN", "B", W, [vr] + jog + [(xr1, yr + 0.4), (xr1 + 0.4, yr), (pr[0] - (pr[1] - yr), yr), pr])
    c.t("/MCU/WIND", "B", W, [vw, (wm[0][0], vw[1] - 0.15)] + wm + [(wm[-1][0], yw2 + 0.4), (wm[-1][0] + 0.4, yw2),
                              (pw[0] - 0.4, yw2), (pw[0], yw2 + 0.4), pw])
    yv = vw[1] - 0.4                                      # VANE runs west under the J10 pad row
    c.t("/MCU/VANE", "B", W, [vv, (vv[0], yv + 0.45), (vv[0] - 0.45, yv), (vm[0][0] + 0.3, yv), (vm[0][0], yv - 0.3)]
        + vm + [(vm[-1][0], 11.0), (vm[-1][0] + 0.45, 10.55)])
    vt = (vm[-1][0] + 0.45, 10.55)
    c.v("/MCU/VANE", *vt)
    for p, u, net in ((pr, u8, "/MCU/RAIN"), (pw, u9, "/MCU/WIND")):
        c.v(net, *p)
        c.t(net, "F", W, [p, u])
    # VANE on F.Cu: parallel to the pair's diagonal, 2.0 mm from its centre on the north side, then into pin 12
    o = offset(info["centre"][1:3], 2.0)
    assert abs((o[1][0] - o[0][0]) - (o[1][1] - o[0][1])) < 1e-6, "45-degree descent"
    yf, ye = 10.1, u12[1] - 0.56
    xs_, xe_ = o[0][0] + (yf - o[0][1]), o[0][0] + (ye - o[0][1])
    c.t("/MCU/VANE", "F", W, [vt, (vt[0] + 0.45, yf), (xs_, yf), (xe_, ye), (u12[0] - 1.3, ye),
                              (u12[0] - 0.75, u12[1]), u12])


def sen_trunk(c):
    """Sensor I2C from module pins 21/22 to U5 (and R51): vias in the band inside the bottom pad row, B.Cu north
    under the module (east of the EPAD vias) and west at y 4.9/4.1; SCL hops to F.Cu so the pair swaps order at U5."""
    P = c.P
    sda, scl = P("U1", "21"), P("U1", "22")
    u6, u4, r51 = P("U5", "6"), P("U5", "4"), P("R51", "1")
    assert sda[0] < scl[0] and u6[1] < u4[1] < r51[1]
    ya = sda[1] - 1.4
    vd, vc = (u6[0] + 1.16, 4.9), (u6[0] + 2.56, 4.1)
    c.t("/SEN_SDA", "F", W2, [sda, (sda[0], ya)])
    c.t("/SEN_SCL", "F", W2, [scl, (scl[0], ya)])
    c.v("/SEN_SDA", sda[0], ya)
    c.v("/SEN_SCL", scl[0], ya)
    c.t("/SEN_SDA", "B", W2, [(sda[0], ya), (sda[0], vd[1] + 0.4), (sda[0] - 0.4, vd[1]), vd])
    c.t("/SEN_SCL", "B", W2, [(scl[0], ya), (scl[0], vc[1] + 0.4), (scl[0] - 0.4, vc[1]), vc])
    c.v("/SEN_SDA", *vd)
    c.v("/SEN_SCL", *vc)
    c.t("/SEN_SDA", "F", W2, [vd, (vd[0] - 0.45, u6[1]), u6])
    c.t("/SEN_SCL", "F", W2, [vc, (vc[0], u4[1] - 0.5), (vc[0] - 0.5, u4[1]), u4])
    c.t("/SEN_SCL", "F", W2, [(r51[0], u4[1]), r51])


W2 = 0.2


def boost_en(c):
    """BOOST_EN (module pin 20) to the via beside U7: the stubs (B.Cu) and the pair (F.Cu) close off U7's side, so the
    net drops into the pad band (via like the sensor I2C), runs west on B.Cu under the module, comes up north of the
    stubs and leaves on F.Cu through the corner gap between pins 14 and 15 (pin 15 is unused), then B.Cu again west
    of the stubs. Pins 17-19 keep their own escapes straight down and in the band."""
    P = c.P
    p20, p13, p14, p15 = P("U1", "20"), P("U1", "13"), P("U1", "14"), P("U1", "15")
    net = "/MCU/BOOST_EN"
    xg = round((p14[0] + 0.75 + p15[0] - 0.45) / 2, 2)   # middle of the corner gap
    yb = round(p13[1] - 0.65, 2)                          # B.Cu row under the module, north of pin 13
    v1 = (p20[0], round(p20[1] - 1.4, 2))
    v2 = (round(xg + 0.7, 2), yb)
    v3 = (round(xg - 0.7, 2), 20.6)
    ve = (28.03, 26.03)                                   # existing via beside U7.2
    c.t(net, "F", W2, [p20, v1])
    c.v(net, *v1)
    c.t(net, "B", W2, [v1, (round(v1[0] - (v1[1] - yb), 2), yb), v2])
    c.v(net, *v2)
    c.t(net, "F", W2, [v2, (xg, round(yb + 0.7, 2)), (xg, 18.6), (v3[0], 19.3), v3])
    c.v(net, *v3)
    c.t(net, "B", W2, [v3, (v3[0], round(ve[1] - (v3[0] - ve[0]), 2)), ve])


def gas_dac(c):
    """GAS_DAC (module pin 7, left column) cannot go south on the west side: the pair (F.Cu) and the stubs (B.Cu)
    interleave there. It drops to B.Cu next to the pin, runs under the module north of the BOOST_EN row, leaves the
    pad band between the BOOST_EN via and the SEN_SDA via and ends south of the pad row; the router takes it on to J8."""
    P = c.P
    p7, p20, p21 = P("U1", "7"), P("U1", "20"), P("U1", "21")
    net = "/MCU/GAS_DAC"
    v = (round(p7[0] + 1.35, 2), p7[1])
    xs = round((p20[0] + p21[0]) / 2, 2)                  # between the band vias of pins 20 and 21
    ye = round(P("U1", "13")[1] - 0.65 - 0.6, 2)          # 0.6 north of the BOOST_EN row
    # south on B.Cu west of L4's keepout, via south of the SYS run, F.Cu between J10 columns 3/5 over the charger
    # I2C trunk, B.Cu above J7 and west of J8 pin 3 into pin 2
    j3, j5, j7_1, j8 = P("J10", "3"), P("J10", "5"), P("J7", "1"), P("J8", "2")
    xj = round((j3[0] + j5[0]) / 2, 2)
    xv = round(xs - 0.4, 2)
    yt = round(j3[1] - 1.05, 2)                            # via between the SYS run and J10's top row
    yb = round(j7_1[1] - 1.7, 2)                           # B.Cu run above J7
    xw = round(j7_1[0] - 1.3, 2)
    rest = [(xv, round(yt - 1.55 - (xv - xj), 2)), (xj, round(yt - 1.55, 2)), (xj, yt)]
    c.t(net, "F", W2, [p7, v])
    c.v(net, *v)
    c.v(net, xj, yt)
    c.t(net, "F", W2, [(xj, yt), (xj, yb)])
    c.v(net, xj, yb)
    c.t(net, "B", W2, [(xj, yb), (xw + 0.4, yb), (xw, yb + 0.4), (xw, round(j8[1] - (xw - j8[0]), 2)), j8])
    c.t(net, "B", W2, [v, (v[0], round(ye - 3.1, 2)), (round(v[0] + 3.1, 2), ye), (round(xs - 1.4, 2), ye),
                       (xs, round(ye + 1.4, 2)), (xs, 19.5), (round(xs - 0.4, 2), 19.9)] + rest)


def chg_trunk(c):
    """Charger I2C (module pins 39/38, right column) to J10 pins 11/12: vias in the band inside the pad column, B.Cu
    south under the pads, west under the bottom pad row (pins 23-26 are unused), south through the gap between L4's
    keepout and H2, east of J10 pins 1/2, west under J10's bottom row into pins 12 (from below) and 11 (between the
    columns). IO0 (pin 27) leaves on F.Cu under the bottom row to R31."""
    P = c.P
    sda, scl, io0 = P("U1", "39"), P("U1", "38"), P("U1", "27")
    j11, j12, j1 = P("J10", "11"), P("J10", "12"), P("J10", "1")
    r31 = P("R31", "2")
    assert sda[1] < scl[1] < io0[1] and abs(j11[0] - j12[0]) < 1e-3 and j11[1] < j12[1] and j1[0] > j11[0]
    xb = sda[0] - 1.4                                    # via column in the band
    va, vb = (xb, sda[1]), (xb, scl[1])
    for net, pin, v in (("/MCU/CHG_SDA", sda, va), ("/MCU/CHG_SCL", scl, vb)):
        c.t(net, "F", W2, [pin, v])
        c.v(net, *v)
    xe_d, xe_c = sda[0] + 0.15, sda[0] - 0.35            # SDA outer (east), SCL inner, under the pad column
    yb_c, yb_d = 19.4, 19.9                              # under the bottom pad row
    xc_c = 42.6                                          # between the L4 keepout and H2
    xk_c = j1[0] + 1.3                                   # east of J10 pins 1/2
    yj = 29.0
    yr_c = j12[1] + 1.6                                 # under J10's bottom row (0.6 mm from the USB pin 8 pad)
    xm = j11[0] - 1.27                                   # between J10 columns 11/12 and 13/14
    # SCL is the reference path of the bundle south of the bottom row; SDA its mitred offset 0.5 mm east
    mid = [(xc_c, yb_c + 0.4), (xc_c, yj), (xk_c, yj + xk_c - xc_c), (xk_c, yr_c - 0.4), (xk_c - 0.4, yr_c)]
    mo = offset(mid, 0.5)        # left of southward travel = east
    c.t("/MCU/CHG_SCL", "B", W2, [vb, (xe_c, vb[1]), (xe_c, yb_c - 0.4), (xe_c - 0.4, yb_c), (xc_c + 0.4, yb_c)]
        + mid + [(j12[0] + 0.4, yr_c), (j12[0], yr_c - 0.4), j12])
    c.t("/MCU/CHG_SDA", "B", W2, [va, (xe_d, va[1]), (xe_d, yb_d - 0.4), (xe_d - 0.4, yb_d), (mo[0][0] + 0.4, yb_d),
                                   (mo[0][0], yb_d + 0.4)] + mo[1:] + [(xm + 0.4, mo[-1][1]), (xm, mo[-1][1] - 0.4),
                                                                     (xm, j11[1] + 1.27), j11])
    c.t("/MCU/IO0", "F", W2, [io0, (io0[0], 20.4), (r31[0] + 0.85, 20.4), r31])




def build(P):
    c = Copper(P)
    info = usb(c)
    vbus(c)
    sys_(c)
    buckboost(c)
    boost(c)
    mcu(c)
    bmp(c)
    gate(c)
    anemometer(c)
    cluster(c, info)
    sen_trunk(c)
    chg_trunk(c)
    boost_en(c)
    gas_dac(c)
    frozen(c)
    return c.items, info


FROZEN = Path(__file__).resolve().parents[1] / "main-board" / "frozen-routes.json"


def frozen(c):
    """Router copper frozen by tools/main_freeze.py (nets that only some router orders solve), drawn as locked copper."""
    if not FROZEN.exists():
        return
    for net, d in json.loads(FROZEN.read_text())["nets"].items():
        for lay, w, pts in d["tracks"]:
            c.t(net, lay, w, [tuple(p) for p in pts])
        for x, y, size, drill in d["vias"]:
            c.v(net, x, y, (size, drill))
