"""Shared hierarchical-schematic generator: one board module (PARTS, NETS, layout) in, KiCad project + bom.csv out.

Factored out of weatherstation_v1.py (2026-11-21) so the power board and the main board use the same drawing engine
instead of a copy. A board module defines, as module attributes:

  PARTS          {ref: (symbol, value, footprint, LCSC or None, sheet)}
  NETS           {net: [(ref, pin), ...]}            the net intent; check_nets() compares it with KiCad's netlist
  POWER_SYMBOLS  rails drawn as power symbols on every pin (never wires, never hierarchical labels)
  RAIL_LIB       {rail: library symbol}; other rails use power:VCC with the net name as value
  SHEET_FILES    {sheet: file name}, in root-page order
  SHEET_VALUE    {ref: short value on the sheet}
  HAND_SOLDER    refs without an LCSC number that are hand-soldered (BOM status)
  PROJECT, TITLE project name (file stem) and title block text; SHEET_PREFIX starts each sheet title line
  ROOT_TEXTS     [(x, y, text)] notes on the root page (cells; a leading '#' = heading)
and from its layout module: BLOCKS, HAND_ROUTES, HAND_LABELS, TAG_POS, TAGS_BELOW, SHEET_NOTES, ROOT_BOX, SHEET_COLOR,
SHEET_PURPOSE (see layout_v1.py for the format).

Drawing rules (kicad-schematic skill): rails are power symbols, wires inside a block, labels between blocks, one label
per wired cluster, hand routes for circuits drawn the datasheet way, passives anchored on a pin only when they terminate it.
"""

import csv
import io
import math
import re
import sys
import textwrap
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kicad_sch_api as ksa  # noqa: E402

# Project symbols (TPS63802 DLA, HY2112-CB, BMP585, ...) are not in the KiCad libraries: written by build_symbols.py.
ksa.get_symbol_cache().add_library_path(Path(__file__).resolve().parent / "lib" / "weatherstation.kicad_sym")  # idempotent

from schkit import Router, Sheet, check_nets, part_boxes, pin_away, root_sheet  # noqa: E402,F401
from review_checks import _box, _hits_box, _label_box  # noqa: E402

TP_FOOTPRINT = "TestPoint:TestPoint_Pad_D1.5mm"
PASSIVE_LIBS = {"Device:R", "Device:C", "Device:L", "Device:Fuse", "Device:Polyfuse", "Device:Thermistor_NTC", "Device:LED"}

# JLCPCB class (Basic / Extended) per LCSC number, from hardware/tools/jlcparts.py. Snapshot 2026-10-31 (v1 BOM), Basic
# swaps 2026-11-01, 0402 Basic swaps 2026-11-02; C14663 and C18184976 from the add-on boards (2026-11-04).
JLC_CLASS = {"C165948": "Extended", "C7519": "Extended", "C23186": "Basic", "C15127": "Basic", "C23025": "Basic",
             "C14663": "Basic", "C2876593": "Extended", "C88211": "Extended", "C113811": "Extended",
             "C19666": "Basic", "C15850": "Basic", "C53084481": "Extended", "C22775": "Basic", "C4211": "Basic",
             "C22869": "Extended", "C25803": "Basic", "C23068": "Extended", "C23000": "Extended", "C13564": "Extended",
             "C4190": "Basic", "C2286": "Basic", "C25804": "Basic", "C2913198": "Extended", "C45783": "Basic",
             "C15849": "Basic", "C318884": "Basic", "C23345": "Basic", "C51118": "Extended", "C19702": "Basic",
             "C8545": "Basic", "C21190": "Basic", "C133065": "Extended", "C160404": "Extended",
             "C21004": "Extended",
             "C2845237": "Extended", "C151250": "Extended", "C963746": "Extended", "C97009": "Extended", "C227946": "Extended",
             "C23265": "Extended",
             "C168764": "Extended", "C20917": "Basic", "C177639": "Extended",
             "C919459": "Extended", "C23231": "Basic",
             "C1622": "Basic", "C1588": "Basic", "C25808": "Basic", "C22984": "Basic", "C22975": "Basic",
             "C22961": "Basic", "C23153": "Basic", "C23192": "Basic",
             "C307331": "Basic",
             "C25905": "Basic", "C25076": "Basic", "C25741": "Basic", "C25879": "Basic", "C25744": "Basic", "C25768": "Basic",
             "C4109": "Basic", "C25092": "Basic", "C11702": "Basic", "C1523": "Basic", "C52923": "Basic",
             "C18184976": "Extended", "C26083": "Basic", "C1538": "Basic",
             "C22391138": "Extended", "C1532": "Basic", "C17901": "Basic", "C1779": "Basic"}


def _on_seg(p, seg) -> bool:
    (ax, ay), (bx, by) = seg
    return (ax == bx == p[0] and min(ay, by) <= p[1] <= max(ay, by)) or (ay == by == p[1] and min(ax, bx) <= p[0] <= max(ax, bx))


def _text_box(x_cell: float, y_cell: float, text: str, size: float, rot: int = 0):
    """Estimated text box of a label or note at a sheet point given in cells (returns mm)."""
    return _box(x_cell * 2.54, y_cell * 2.54, rot % 360, text, size)


def _pin_offset(lib: str, number: str, rot: int) -> tuple[float, float]:
    """Pin position relative to the symbol origin in sheet mm (y down), for rotation rot (degrees)."""
    pin = next(p for p in ksa.get_symbol_info(lib).pins if p.number == number)
    r = math.radians(rot)
    x = pin.position.x * math.cos(r) - pin.position.y * math.sin(r)
    y = pin.position.x * math.sin(r) + pin.position.y * math.cos(r)
    return (x, -y)


def _passive_box(lib: str, x: float, y: float, rot: int) -> tuple:
    """Body plus reference/value text of a 2-pin passive at origin (x, y) mm: vertical parts carry the text on
    the right, horizontal ones above (see Sheet._auto_tags)."""
    pts = [_pin_offset(lib, p.number, rot) for p in ksa.get_symbol_info(lib).pins]
    xs, ys = [x + p[0] for p in pts], [y + p[1] for p in pts]
    if max(xs) - min(xs) < 0.1:  # vertical
        return (min(xs) - 1.6, min(ys), max(xs) + 7.0, max(ys))
    return (min(xs), min(ys) - 6.5, max(xs), max(ys) + 1.6)


def _boxes_overlap(a, b, gap: float = 0.6) -> bool:
    return min(a[2], b[2]) - max(a[0], b[0]) > -gap and min(a[3], b[3]) - max(a[1], b[1]) > -gap


def pin_direction(s: Sheet, ref: str, pin: str) -> float:
    return pin_away(s.sch, ref, pin, s.mirror.get(ref))


class Generator:
    """The drawing engine bound to one board module `b` (see the module docstring for the attributes it reads)."""

    def __init__(self, b):
        self.b = b
        self.PARTS, self.NETS = b.PARTS, b.NETS
        self.POWER_SYMBOLS = b.POWER_SYMBOLS
        self.USED = {p for pins in b.NETS.values() for p in pins}
        self.BLOCK_OF = {ref: title for blocks in b.BLOCKS.values() for title, _n, _box, parts in blocks for ref in parts}
        self.dx = getattr(b, "SHEET_DX", 0)  # cells: shifts every block, part and hand route right (frames clear of the border)
        self.UNWIRED: list[str] = []
        self.HAND_KEYS: set = set()
        self.HAND_SEGS: dict = {}  # net -> hand-drawn segments of the sheet being drawn
        self._dedupe()

    # --- net bookkeeping -------------------------------------------------------------------------------------------
    def _dedupe(self) -> None:
        for name, pins in self.NETS.items():
            assert len(pins) == len(set(pins)), f"duplicate pins in net {name}"
        used: dict[tuple[str, str], str] = {}
        for name, pins in self.NETS.items():
            for p in pins:
                assert p[0] in self.PARTS, f"net {name}: unknown part {p[0]}"
                assert p not in used, f"pin {p} in both {used[p]} and {name}"
                used[p] = name

    def sheets_of(self, net: str) -> set[str]:
        return {self.PARTS[ref][4] for ref, _ in self.NETS[net]}

    def short_value(self, ref: str) -> str:
        """Sheet value: the part name without the design note (the full text stays in the BOM comment)."""
        return self.b.SHEET_VALUE.get(ref) or re.split(r" \(|;", self.PARTS[ref][1])[0].strip()

    def _is_passive(self, ref: str) -> bool:
        return self.PARTS[ref][0] in PASSIVE_LIBS

    def _net_of(self, ref: str, pin: str) -> str:
        return next(n for n, pins in self.NETS.items() if (ref, pin) in pins)

    # --- routing --------------------------------------------------------------------------------------------------
    def _route_sheet(self, s: Sheet, items: dict, refs: list[str], extra: list, hand: dict | None = None) -> tuple[set, list, list]:
        """Route every (net, block) cluster of this sheet: wires inside a block, labels between blocks.
        items: {(net, block): [pin items]}. extra: (box_mm, owner) obstacles (notes, labels, power symbols).
        Returns (wired cluster keys, route segments, stubs)."""
        boxes = [(bx, "*") for bx in part_boxes(s, refs)] + [(bx, o) for bx, o in extra]
        router = Router([bx for bx, _ in boxes], [o for _, o in boxes])
        stubs = []
        hand = hand or {}
        wired: set = set()
        segs: list = []
        hand_keys = set()  # (net, block) clusters whose pins all lie on hand-drawn wires
        for net, hsegs in hand.items():  # hand-drawn wires first: fixed, and obstacles for every other net
            for a, c in hsegs:
                router.add_stub(net, a, c)
            segs.extend(hsegs)
            hand_keys.update(k for k, its in items.items()
                             if k[0] == net and all(any(_on_seg(it["pos"], sg) for sg in hsegs) for it in its))
        wired.update(hand_keys)
        self.HAND_SEGS = {net: list(hsegs) for net, hsegs in hand.items()}
        self.HAND_KEYS.clear()
        self.HAND_KEYS.update(hand_keys)
        for key, its in items.items():
            net = key[0]
            for it in its:
                if key in hand_keys:
                    continue
                router.add_stub(net, it["pos"], it["exit"])
                stubs.append((it["pos"], it["exit"]))
        for key in sorted(items, key=lambda k: (len(items[k]), k)):
            if len(items[key]) < 2 or key[0] in self.POWER_SYMBOLS or key in hand_keys:
                continue
            found = router.connect(key[0], [it["exit"] for it in items[key]])
            if found is not None:
                wired.add(key)
                segs.extend(found)
        return wired, segs, stubs

    def _clear_item(self, net: str, its: list, segs: list, hand: bool = False) -> dict:
        """The pin (and text direction) of a wired cluster whose name label lies clear of every wire: the stub
        direction first, then across the wire (a label on a vertical wire reads horizontally). Else the first pin."""
        exits = {it["exit"] for it in its}
        # hand-routed: the label goes on a wire, never on the pin (it would cover the pin name), text beside the wire
        points = [] if hand else [(it["exit"], it["deg"]) for it in its]
        for a, c in segs:
            if a in exits or c in exits or (hand and any(_on_seg(e, (a, c)) for e in exits)):
                mid = (round((a[0] + c[0]) / 2 / 1.27) * 1.27, round((a[1] + c[1]) / 2 / 1.27) * 1.27)
                horiz = a[1] == c[1]
                points.append(((round(mid[0], 2), round(mid[1], 2)), (0 if horiz else 90) if hand else (90 if horiz else 0)))
        if hand:  # longest horizontal wire first: the name reads along the wire, away from the parts at its ends
            lengths = {}
            for a, c in segs:
                if a[1] == c[1] and any(_on_seg(e, (a, c)) for e in exits) or (a in exits or c in exits):
                    mid = (round(round((a[0] + c[0]) / 2 / 1.27) * 1.27, 2), round(round((a[1] + c[1]) / 2 / 1.27) * 1.27, 2))
                    lengths[mid] = (a[1] == c[1], abs(a[0] - c[0]) + abs(a[1] - c[1]))
            points.sort(key=lambda p: (not lengths.get(p[0], (False, 0))[0], -lengths.get(p[0], (False, 0))[1]))
        for pt, first in points:
            for deg in (first, 0, 180, 90, 270):
                box = _text_box(pt[0] / 2.54, pt[1] / 2.54, net, 1.27, deg)
                if hand:  # KiCad draws a local label beside its wire: test that box, not the wire itself
                    box = _label_box(pt[0], pt[1], deg, net, 1.27)
                if not any(_hits_box((a[0], a[1], c[0], c[1]), box) for a, c in segs):
                    return dict(its[0], exit=pt, deg=deg, above=hand)
        return its[0]

    def _hand_groups(self, net: str, its: list) -> list[list]:
        """Pin items of a hand-routed net grouped by connected wire (segments joined at end points or T-junctions)."""
        hs = self.HAND_SEGS.get(net, [])
        parent = list(range(len(hs)))

        def find(i):
            while parent[i] != i:
                parent[i] = parent[parent[i]]
                i = parent[i]
            return i
        for i, a in enumerate(hs):
            for j in range(i):
                b = hs[j]
                if any(_on_seg(pt, b) for pt in a) or any(_on_seg(pt, a) for pt in b):
                    parent[find(i)] = find(j)
        groups: dict = {}
        for it in its:
            k = next((find(i) for i, sg in enumerate(hs) if _on_seg(it["pos"], sg)), None)
            groups.setdefault(k, []).append(it)
        return list(groups.values()) or [its]

    def _labels_for(self, items: dict, wired: set, segs: list | None = None) -> list:
        """(net, anchor item): a power symbol on every rail pin; one name label per wired cluster (on a pin where the
        text is clear of wires); a label on every pin of a cluster that could not be wired. Duplicate points are dropped."""
        out, seen = [], set()
        for key, its in items.items():
            net = key[0]
            if net in self.POWER_SYMBOLS and key in self.HAND_KEYS:  # hand-drawn rail: one symbol, on a pin that points up
                anchors = [next((it for it in its if it["deg"] == 90), its[0])]
            elif key in self.HAND_KEYS and net not in self.POWER_SYMBOLS:
                # a hand-drawn net may be several wire groups (e.g. through an ESD part's flow-through pins):
                # one name label per group, so KiCad joins them by name
                anchors = [self._clear_item(net, grp, segs or [], True) for grp in self._hand_groups(net, its)]
            else:
                anchors = (its if net in self.POWER_SYMBOLS or key not in wired
                           else [self._clear_item(net, its, segs or [], key in self.HAND_KEYS)])
            for it in anchors:
                if (net, it["exit"]) not in seen:
                    seen.add((net, it["exit"]))
                    out.append((net, it))
        return out

    def _anchor_passives(self, s: Sheet, name: str, refs: list[str]) -> dict:
        """Wire passives directly: a 2-pin part whose pin shares a SIGNAL net with a host pin (IC, FET, connector)
        on this sheet is placed with that pin on the host's stub end and rotated so its body points away from the host.
        Rails are not anchors (rail pins get power symbols). An anchor that would overlap a part, another anchored
        passive or its text is skipped: the part stays at its block position and the router wires it.
        Returns {ref: (x_cell, y_cell, rot, own_pin)}. Each host pin takes at most one passive."""
        P, PS = self.PARTS, self.POWER_SYMBOLS
        out: dict = {}
        taken: set[tuple[str, str]] = set()
        placed = part_boxes(s, [r for r in refs if not self._is_passive(r) and not r.startswith("#")], margin=0.5)
        for ref in sorted(r for r in refs if self._is_passive(r)):
            lib = P[ref][0]
            for own in [p.number for p in ksa.get_symbol_info(lib).pins]:
                if ref in out:
                    break
                net = self._net_of(ref, own)
                others = [p for p in self.NETS[net] if not p[0].startswith("#")]
                other_pins = [p.number for p in ksa.get_symbol_info(lib).pins if p.number != own]
                # (a) the passive is the only other part on this net, (b) its other end is a rail (pull-up, pull-down,
                # decoupling): then it terminates the pin and reads best sitting on it
                if net in PS or len(others) != 2 or not all(self._net_of(ref, o) in PS for o in other_pins):
                    continue
                for href, hpin in others:
                    if href == ref or P[href][4] != name or href.startswith(("#", "TP")) or self._is_passive(href):
                        continue
                    if (href, hpin) in taken:
                        continue
                    hx, hy = s.at(href, hpin)
                    deg = pin_direction(s, href, hpin)
                    # (c) no other used pin of the host on the same side within 7 mm: its text would sit on that row
                    crowded = any(
                        (q != hpin and (href, q) in self.USED and pin_direction(s, href, q) == deg
                         and 0 < math.dist(s.at(href, q), (hx, hy)) < 7.0)
                        for q in [p.number for p in ksa.get_symbol_info(P[href][0]).pins])
                    if crowded:
                        continue
                    d = math.radians(deg)
                    ox, oy = math.cos(d), -math.sin(d)  # outward unit vector (sheet coordinates)
                    ex, ey = hx + 2 * 2.54 * ox, hy + 2 * 2.54 * oy
                    for rot in (0, 90, 180, 270):
                        dx, dy = _pin_offset(lib, own, rot)
                        length = math.hypot(dx, dy)
                        if length and abs(dx / length + ox) < 1e-6 and abs(dy / length + oy) < 1e-6:
                            box = _passive_box(lib, ex - dx, ey - dy, rot)
                            if any(_boxes_overlap(box, bx) for bx in placed):
                                break
                            out[ref] = (round((ex - dx) / 2.54, 4), round((ey - dy) / 2.54, 4), rot, own)
                            taken.add((href, hpin))
                            placed.append(box)
                            break
                    if ref in out:
                        break
        return out

    # --- one sheet ------------------------------------------------------------------------------------------------
    def draw(self, name: str, pos: dict, used: set[tuple[str, str]]) -> Sheet:
        b, P = self.b, self.PARTS
        s = Sheet(name, b.SHEET_FILES[name], P, "A3", b.SHEET_NOTES[name], project=b.PROJECT, title=b.TITLE,
                  date=getattr(b, "DATE", "2026-10-31"))
        refs = [r for r, v in P.items() if v[4] == name]
        edge, tint = b.SHEET_COLOR[name]
        dx = self.dx
        note_boxes = []  # frame titles and block notes are obstacles for wires
        for title, note, (x, y, w, h), _parts in b.BLOCKS[name]:
            x += dx
            s.frame(x, y, x + w, y + h, title, edge, tint)
            # wrap the note inside its frame (rendered stroke font: about 0.9 x size per character, review_checks)
            lines = textwrap.wrap(note, max(20, int((w * 2.54 - 3.0) / (1.1 * 0.9))))
            s.text(x + 0.5, y + 2.4, "\n".join(lines), 1.1)
            nx, ny = (x + 0.5) * 2.54, (y + 2.4) * 2.54
            note_boxes.append(((nx, ny, nx + max(map(len, lines)) * 1.1 * 0.9, ny + len(lines) * 1.1 * 1.6), "*"))
            note_boxes.append((_text_box(x + 0.5, y + 0.4, title, 1.5), "*"))
        for x, y, body in getattr(b, "SHEET_TEXTS", {}).get(name, []):  # free notes (pin tables), one line per entry
            x += dx
            s.text(x, y, body, 1.27)
            lines = body.split("\n")
            w = max(len(line) for line in lines) * 1.27 * 0.62
            note_boxes.append(((x * 2.54, y * 2.54, x * 2.54 + w, y * 2.54 + len(lines) * 1.27 * 1.6), "*"))
        # place the non-passive parts first, then the passives: anchored ones at their host pin, the rest at their block spot
        for ref in refs:
            if not self._is_passive(ref):
                x, y, rot, mirror = pos[ref]
                s.part(ref, x, y, rot, value=self.short_value(ref), mirror=mirror)
                if ref in b.TAG_POS:
                    s.tag(ref, reference=b.TAG_POS[ref][0][:2], value=b.TAG_POS[ref][1][:2], just=b.TAG_POS[ref][0][2])
        anchors = self._anchor_passives(s, name, refs)
        for ref in refs:
            if self._is_passive(ref):
                x, y, rot, mirror = (anchors[ref][:3] + (None,) if ref in anchors else pos[ref])
                s.part(ref, x, y, rot, value=self.short_value(ref), mirror=mirror)
                if ref in b.TAGS_BELOW:
                    s.tag(ref, reference=(0, 3.4), value=(0, 5.7), just="center")
        # 1. every pin on this sheet: position and the exit point of its stub (2 cells away from the body)
        items: dict = {}
        for net, pins in self.NETS.items():
            for ref, pin in pins:
                if P[ref][4] != name:
                    continue
                x, y = s.at(ref, pin)
                deg = int(pin_direction(s, ref, pin))
                if ref in anchors and anchors[ref][3] == pin:
                    ex, ey = x, y  # wired directly to the host pin: no stub
                else:
                    ex = round(x + 2 * 2.54 * math.cos(math.radians(deg)), 2)
                    ey = round(y - 2 * 2.54 * math.sin(math.radians(deg)), 2)
                items.setdefault((net, self.BLOCK_OF[ref]), []).append(dict(pos=(x, y), exit=(ex, ey), deg=deg))
        # 2. pass 1 decides which nets are wired and where labels go; pass 2 routes around those label boxes.
        # Power symbols sit at the stub ends of rail pins: obstacles for every wire
        for (net, _blk), its in items.items():
            if net not in self.POWER_SYMBOLS:
                continue
            for it in its:
                (px, py), (ex, ey) = it["pos"], it["exit"]
                d = math.radians(it["deg"])
                ux, uy = round(math.cos(d)), -round(math.sin(d))  # symbols point along their stub
                fx, fy = ex + 4.5 * ux, ey + 4.5 * uy
                pad_x, pad_y = (2.2, 2.2) if ux == 0 else (2.2 + 1.27 * 0.62 * len(net), 1.4)
                note_boxes.append(((min(ex, fx) - (2.2 if ux == 0 else 0.3), min(ey, fy) - pad_y,
                                    max(ex, fx) + (2.2 if ux == 0 else pad_x), max(ey, fy) + pad_y), net))
        # hand-drawn wires (HAND_ROUTES): polylines in cells; their pins get no stub
        hand: dict = {}
        for net, lines in b.HAND_ROUTES.get(name, {}).items():
            for line in lines:
                pts = [s.at(*p) if isinstance(p[0], str) else (round((p[0] + dx) * 2.54, 2), round(p[1] * 2.54, 2)) for p in line]
                for a, c in zip(pts, pts[1:]):
                    assert a[0] == c[0] or a[1] == c[1], f"hand route {net}: diagonal {a} -> {c}"
                    hand.setdefault(net, []).append((a, c))
            for key, its in items.items():
                if key[0] == net:
                    for it in its:
                        if any(_on_seg(it["pos"], sg) for sg in hand[net]):
                            it["exit"] = it["pos"]
        extra: list = list(note_boxes)
        previous = None
        for _ in range(4):
            wired, segs, stubs = self._route_sheet(s, items, refs, extra, hand)
            label_pts = frozenset((net, it["exit"]) for net, it in self._labels_for(items, wired) if net not in self.POWER_SYMBOLS)
            if label_pts == previous:
                break
            previous = label_pts
            extra = list(note_boxes) + [(_text_box(it["exit"][0] / 2.54, it["exit"][1] / 2.54, net, 1.27, it["deg"]), net)
                                        for net, it in self._labels_for(items, wired) if net not in self.POWER_SYMBOLS]
        for a, c in stubs:
            if a != c:
                s.segs.append((a, c))
        s.segs.extend(segs)
        for key in items:
            if len(items[key]) >= 2 and key not in wired and key[0] not in self.POWER_SYMBOLS:
                self.UNWIRED.append(f"{name}:{key[0]}@{key[1]}")
        # 3. labels: one name per wired net (on its wire); power symbols; every other pin labelled
        cross_nets = {n for n, _b in items if len(self.sheets_of(n)) > 1}
        # HAND_LABELS: one (x, y, deg[, "above"]) or a list of them (one per wire group of the net); each group takes
        # the nearest unused spot, a group without a spot is labelled at its own pin
        spots = {n: (list(v) if isinstance(v, list) else [v]) for n, v in b.HAND_LABELS.get(name, {}).items()}
        for net, it in self._labels_for(items, wired, s.segs):
            cx, cy = it["exit"][0] / 2.54, it["exit"][1] / 2.54
            if net in self.POWER_SYMBOLS:
                # vertical stubs: GND down / rail up, mirrored when the stub runs the other way; side stubs: turned sideways
                deg = it["deg"] % 360
                if deg in (90, 270):
                    s.power(net, cx, cy, flip=(deg == 90) if net == "GND" else (deg == 270), lib=b.RAIL_LIB.get(net, "power:VCC"))
                else:
                    rot = (deg + 90) % 360 if net == "GND" else (deg - 90) % 360
                    s.power(net, cx, cy, lib=b.RAIL_LIB.get(net, "power:VCC"), rot=rot)
            elif it.get("above") and spots.get(net):
                spot = min(spots[net], key=lambda t: (t[0] + dx - cx) ** 2 + (t[1] - cy) ** 2)
                spots[net].remove(spot)
                hx, hy, hdeg, *opt = spot  # optional 4th item "above": text beside the wire
                s.label(net, hx + dx, hy, hdeg, "hier" if net in cross_nets else "local", above="above" in opt,
                        shape=getattr(b, "LABEL_SHAPE", {}).get(name, {}).get(net, "bidirectional"))
            else:
                s.label(net, cx, cy, it["deg"], "hier" if net in cross_nets else "local", above=it.get("above", False),
                        shape=getattr(b, "LABEL_SHAPE", {}).get(name, {}).get(net, "bidirectional"))
        for ref in refs:
            if ref.startswith("#"):
                continue
            for number in [p.number for p in ksa.get_symbol_info(P[ref][0]).pins]:
                if (ref, number) not in used:
                    s.no_connect(ref, [number])
        s.text(5, getattr(b, "SHEET_TITLE_Y", 5), f"{b.SHEET_PREFIX}: {name}. {b.SHEET_NOTES[name]}", 1.5, bold=True)
        return s

    def layout_positions(self) -> dict:
        """Every part of every sheet placed once, inside its block (the hand layout of the board's layout module)."""
        pos: dict = {}
        for name in self.b.SHEET_FILES:
            for title, _note, (bx, by, bw, bh), parts in self.b.BLOCKS[name]:
                for ref, spec in parts.items():
                    x, y, rot = spec[:3]
                    assert ref in self.PARTS and self.PARTS[ref][4] == name, f"{ref} is not on sheet {name}"
                    assert ref not in pos, f"{ref} placed twice"
                    assert bx <= x <= bx + bw and by <= y <= by + bh, f"{ref} at ({x},{y}) is outside block '{title}'"
                    pos[ref] = (x + self.dx, y, rot, {"m": "y", "my": "y", "mx": "x"}.get(spec[3]) if len(spec) > 3 else None)
            missing = [r for r, v in self.PARTS.items() if v[4] == name and r not in pos]
            assert not missing, f"{name}: parts not placed in any block: {missing}"
        return pos

    # --- root page ------------------------------------------------------------------------------------------------
    def root_interfaces(self):
        """Root page: a sheet pin for every net shared by sheets, and the wires that join the pins.

        Each (net, sheet) pin sits on the box edge that faces the other sheets of that net. The wires are routed
        by the same maze router as the sheets, with the boxes as obstacles, so no two nets touch. A net that
        cannot be routed gets a root label at each pin instead (same name = same net).
        """
        b, sheets_of = self.b, self.sheets_of
        cell = 2.54
        boxes = dict(b.ROOT_BOX)
        nets = sorted(n for n in self.NETS if n not in self.POWER_SYMBOLS and len(sheets_of(n)) > 1)
        order = list(b.SHEET_FILES)

        def centre(sh):
            x, y, w, h = boxes[sh]
            return x + w / 2, y + h / 2
        pins: dict[str, list] = {n: [] for n in b.SHEET_FILES}
        anchor: dict[tuple, tuple] = {}
        for n in nets:
            for sh in sheets_of(n):
                others = [centre(o) for o in sheets_of(n) if o != sh]
                cx = sum(c[0] for c in others) / len(others)
                cy = sum(c[1] for c in others) / len(others)
                x, y, w, h = boxes[sh]
                dx, dy = cx - (x + w / 2), cy - (y + h / 2)
                side = ("right" if dx > 0 else "left") if abs(dx) >= abs(dy) else ("bottom" if dy > 0 else "top")
                side = getattr(b, "ROOT_SIDE", {}).get((n, sh), side)  # optional override per (net, sheet)
                anchor[(n, sh)] = (side, 0.0)
        # Pins of each (sheet, side), ordered by the position of the other end so wires do not cross. Smaller groups are
        # placed first (centred on the edge); a pin whose partner pin on a facing edge is already placed takes the same
        # coordinate when it can, so two-sheet nets become straight wires. Pins stay at least `step` cells apart.
        groups: dict[tuple, list] = {}
        for (n, sh), (side, _) in anchor.items():
            groups.setdefault((sh, side), []).append(n)
        point: dict[tuple, tuple] = {}
        facing = {"left": "right", "right": "left", "top": "bottom", "bottom": "top"}
        step = 2.0  # cells: a whole cell apart, on the 0.5-cell routing grid
        for (sh, side), group in sorted(groups.items(), key=lambda kv: (len(kv[1]), order.index(kv[0][0]))):
            x, y, w, h = boxes[sh]
            vertical = side in ("left", "right")
            lo, span = (y, h) if vertical else (x, w)

            def along(n, sh=sh, vertical=vertical):  # position of the other end(s) along this edge
                others = [centre(o) for o in sheets_of(n) if o != sh]
                return sum(c[1] if vertical else c[0] for c in others) / len(others)

            def desired(n, sh=sh, side=side, vertical=vertical, lo=lo, span=span):
                near = sorted(sheets_of(n), key=lambda o: (abs(centre(o)[0] - centre(sh)[0]) + abs(centre(o)[1] - centre(sh)[1]), o))
                for o in near:  # nearest placed partner on a facing edge (deterministic, not set order)
                    if o != sh and (n, o) in point and anchor[(n, o)][0] == facing[side]:
                        c = point[(n, o)][1] if vertical else point[(n, o)][0]
                        if lo + 2 <= c <= lo + span - 2:
                            return c
                return None
            ranked = sorted(group, key=lambda n: (desired(n) is None, desired(n) or along(n), along(n), n))
            pos_of, prev = {}, None
            n_free = sum(desired(n) is None for n in group)
            for n in ranked:
                d = desired(n)
                if d is None and prev is None:
                    d = lo + span / 2 - step * (n_free - 1) / 2
                pos = d if prev is None else max(d if d is not None else -1e9, prev + step)
                pos_of[n] = prev = round(pos * 2) / 2
            for n in group:
                pos = pos_of[n]
                point[(n, sh)] = {"left": (x, pos), "right": (x + w, pos), "top": (pos, y), "bottom": (pos, y + h)}[side]
                pins[sh].append((side, pos, n))
        # route each net: pins are the tree leaves; exits point out of their box
        router = Router([(bx * cell, by * cell, (bx + bw) * cell, (by + bh) * cell) for bx, by, bw, bh in boxes.values()])
        out_dir = {"left": (-1, 0), "right": (1, 0), "top": (0, -1), "bottom": (0, 1)}
        wires: list = []
        unrouted: list[tuple[str, str]] = []
        all_exits: dict[str, list] = {}
        for n in nets:  # every stub first, so no route can run over another net's pin
            exits = []
            for sh in sorted(sheets_of(n), key=order.index):
                side = anchor[(n, sh)][0]
                px, py = point[(n, sh)]
                ex, ey = px + out_dir[side][0], py + out_dir[side][1]  # one cell out of the box (cells)
                exits.append(((px * cell, py * cell), (ex * cell, ey * cell)))
            for pin, ext in exits:
                router.add_stub(n, pin, ext)
            all_exits[n] = exits
        forced = set(getattr(b, "ROOT_LABELLED", ()))  # nets that keep labels on the root (no planar route exists)
        for n in sorted(nets, key=lambda n: len(all_exits[n])):
            exits = all_exits[n]
            segs = None if n in forced else router.connect(n, [e for _, e in exits], strict=False)
            if segs is None:
                unrouted.append((n, "unrouted"))
                continue
            wires.extend(((a[0] / cell, a[1] / cell), (c[0] / cell, c[1] / cell)) for a, c in segs)
            for pin, ext in exits:  # the stub from the pin out of its box
                wires.append(((pin[0] / cell, pin[1] / cell), (ext[0] / cell, ext[1] / cell)))
        texts = list(b.ROOT_TEXTS)
        # unrouted nets: the reserved 1-cell exit stub out of the box with the label at its end, text pointing away from the box
        root_labels = []
        ang = {"left": 180, "right": 0, "top": 90, "bottom": 270}
        for n, _ in unrouted:
            for sh in sheets_of(n):
                side = anchor[(n, sh)][0]
                px, py = point[(n, sh)]
                ex, ey = px + out_dir[side][0], py + out_dir[side][1]
                wires.append(((px, py), (ex, ey)))
                root_labels.append((n, ex, ey, ang[side]))
        return pins, wires, texts, root_labels

    def build(self, out: Path) -> Path:
        b = self.b
        out.mkdir(parents=True, exist_ok=True)
        Sheet.pwr_count = 0
        self.UNWIRED.clear()
        used = {p for pins in self.NETS.values() for p in pins}
        pos = self.layout_positions()
        sheets = [self.draw(n, pos, used) for n in b.SHEET_FILES]
        sd = []
        for i, n in enumerate(b.SHEET_FILES):
            x, y, w, h = b.ROOT_BOX[n]
            stroke, fill = b.SHEET_COLOR[n]
            sd.append(dict(name=n, file=b.SHEET_FILES[n], x=x, y=y, w=w, h=h, page=str(i + 2),
                           uuid=str(uuid.uuid5(uuid.NAMESPACE_URL, "sheet/" + n)), pins=[], stroke=stroke, fill=fill))
        root_pins, root_wires, texts, root_labels = self.root_interfaces()
        for n in b.SHEET_FILES:  # what each box does, inside the box
            bx, by, bw, bh = b.ROOT_BOX[n]
            for k, line in enumerate(textwrap.wrap(b.SHEET_PURPOSE[n], getattr(b, "ROOT_WRAP", 52))):
                texts.append((bx + 1.5, by + 1.5 + 2.0 * k, line))
        for sh in sd:
            sh["pins"] = root_pins[sh["name"]]
            sh["shapes"] = getattr(b, "LABEL_SHAPE", {}).get(sh["name"], {})
        path, root_uuid = root_sheet(out, "root", sd, texts, root_wires, root_labels, project=b.PROJECT, title=b.TITLE,
                                     date=getattr(b, "DATE", "2026-10-31"))
        for sh in sheets:
            sh.save(out, root_uuid, str(uuid.uuid5(uuid.NAMESPACE_URL, "sheet/" + sh.name)))
        return path

    # --- BOM and drawing review -------------------------------------------------------------------------------------
    def write_bom(self, path: Path) -> None:
        """bom.csv from PARTS: one row per LCSC part (same part, same line, whatever the design note says); parts
        without LCSC group by value. Power symbols, flags and test points excluded (test points get one summary row)."""
        P = self.PARTS
        groups: dict[tuple, list[str]] = {}
        for ref, (sym, value, fp, lcsc, _sheet) in P.items():
            if ref.startswith("#") or ref.startswith("TP"):
                continue
            groups.setdefault((lcsc or value, fp or "", lcsc or ""), []).append(ref)
        cols = ["Comment", "Designator", "Footprint", "Quantity", "LCSC Part #", "Class", "Status", "Function / notes"]
        rows = []
        for (_key, fp, lcsc), refs in groups.items():
            refs = sorted(refs, key=lambda r: (r[0], int("".join(ch for ch in r if ch.isdigit()) or 0)))
            value = self.short_value(refs[0])  # clean part value; design notes per designator go to the notes column
            notes = "; ".join(f"{r}: {P[r][1]}" for r in refs if P[r][1] != value)
            if lcsc:
                cls, status = JLC_CLASS[lcsc], "VERIFIED LCSC part (class: boardgen.JLC_CLASS; stock: hw-check.sh --stock; datasheet values open)"
            else:
                cls = "n/a"
                status = "HAND-SOLDER" if all(r in self.b.HAND_SOLDER for r in refs) else "NOT ASSEMBLED"
            notes_st = [getattr(self.b, "STATUS_NOTE", {}).get(r) for r in refs]
            if any(notes_st):
                status = "; ".join(n for n in notes_st if n)
            rows.append([value, ",".join(refs), fp, str(len(refs)), lcsc or "n/a", cls, status, notes])
        tp = [r for r in P if r.startswith("TP")]
        if tp:
            rows.append(["Test points", ",".join(sorted(tp)), TP_FOOTPRINT, str(len(tp)), "n/a", "n/a", "PCB pads only",
                         getattr(self.b, "TP_NOTE", "test pads")])
        buf = io.StringIO()
        csv.writer(buf, lineterminator="\n").writerows([cols] + rows)  # quotes fields with commas or quotes
        path.write_text(buf.getvalue())

    def drawing_issues(self) -> list[str]:
        """Review rule a net list alone cannot show: a net with a single pin goes nowhere (dangling).
        Unused pins are not errors: draw() puts a no-connect marker on each one."""
        out = []
        for net, pins in self.NETS.items():
            if net not in self.POWER_SYMBOLS and len([p for p in pins if not p[0].startswith("#")]) < 2:
                out.append(f"dangling net {net}: {pins}")
        return out


def write_lib_tables(out: Path) -> None:
    """Project symbol/footprint libraries (hardware/gen/lib), so KiCad finds the project parts when the board is opened."""
    (out / "sym-lib-table").write_text(
        '(sym_lib_table\n  (version 7)\n  (lib (name "weatherstation")(type "KiCad")(uri "${KIPRJMOD}/../gen/lib/weatherstation.kicad_sym")'
        '(options "")(descr "Project symbols (hardware/gen/build_symbols.py)"))\n)\n')
    (out / "fp-lib-table").write_text(
        '(fp_lib_table\n  (version 7)\n  (lib (name "weatherstation")(type "KiCad")(uri "${KIPRJMOD}/../gen/lib/weatherstation.pretty")'
        '(options "")(descr "Project footprints from maker drawings (hardware/gen/build_footprints.py)"))\n)\n')


def write_project(out: Path, project: str) -> None:
    """<project>.kicad_pro with the shared ERC rule severities (hardware/rules/kicad-erc.json, taken from the
    weatherstation-v1 project), so kicad-cli runs ERC with the same rules on every board. An existing file is kept
    except for its erc section (KiCad's GUI adds its own keys)."""
    import json
    pro = out / f"{project}.kicad_pro"
    erc = json.loads((Path(__file__).resolve().parents[1] / "rules" / "kicad-erc.json").read_text())["erc"]
    doc = json.loads(pro.read_text()) if pro.exists() else {"meta": {"filename": pro.name, "version": 3}}
    doc["erc"] = erc
    pro.write_text(json.dumps(doc, indent=2) + "\n")


def main(board_module, default_out: Path) -> int:
    """Command line of a board generator: build into argv[1] (or the profile folder), write bom.csv, run the net check."""
    g = Generator(board_module)
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else default_out
    path = g.build(out)
    g.write_bom(out / "bom.csv")
    write_lib_tables(out)
    write_project(out, board_module.PROJECT)
    errors = check_nets(path, board_module.NETS) + g.drawing_issues()
    if g.UNWIRED:
        print("labelled clusters (UNWIRED):", ", ".join(g.UNWIRED))
    print("\n".join(errors) or f"{path}: nets OK; bom.csv written")
    return 1 if errors else 0
