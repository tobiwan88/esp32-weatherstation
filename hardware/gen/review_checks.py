"""Geometric review of the generated schematic: what a human would see as unreadable.

Reads the .kicad_sch files (no KiCad needed) and checks, per sheet:
  - label on label: two net labels or hierarchical labels whose text boxes overlap
  - text under a wire: a wire runs through the text box of a label or note
  - note on label: a free text note overlaps a label
  - small text: a label or note below 1.0 mm (hard to read on a printed A3)
  - wires not horizontal/vertical, and four or more wire ends at one point (four-way junction)
  - ref/value on its own symbol: a visible Reference or Value text box overlaps the body graphics of its symbol
  - note past its frame: a free text note (all its lines) runs beyond the block rectangle that holds its anchor
  - rail pointing down: a power symbol other than GND/PWR_FLAG placed with its arrow downwards (rails point up, GND down)
Text boxes are estimates: width = characters x size x 0.62, height = size x 1.6 (KiCad's default font).
These checks find the layout problems a reviewer would hit. The rendered PNGs are still read by a person
(or an agent) before a sheet passes; see .claude/skills/kicad-schematic/SKILL.md, section Review loop.

Run: python3 -I hardware/gen/review_checks.py hardware/<board> [--strict]
Exit code 1 when any issue is found (with --strict) so the gate can use it.
"""

import re
import sys
from pathlib import Path

LABEL = re.compile(r'\((label|global_label|hierarchical_label) "([^"]*)"(.*?)\(at ([-\d.]+) ([-\d.]+) (-?\d+)\)(.*?)\(font \(size ([\d.]+)', re.S)
TEXT = re.compile(r'\(text "((?:[^"\\]|\\.)*)"(.*?)\(at ([-\d.]+) ([-\d.]+) (-?\d+)\)(.*?)\(font \(size ([\d.]+)', re.S)
WIRE = re.compile(r'\(wire \(pts \(xy ([-\d.]+) ([-\d.]+)\) \(xy ([-\d.]+) ([-\d.]+)\)\)')
CHAR_W, LINE_H = 0.62, 1.6
NOTE_CHAR_W = 0.90  # measured on a render: a 244-character note at 1.1 mm spans about 242 mm (frame rule only)


def _box(x, y, rot, text, size):
    w, h = len(text) * size * CHAR_W, size * LINE_H
    if rot == 0:
        return (x, y - h / 2, x + w, y + h / 2)
    if rot == 180:
        return (x - w, y - h / 2, x, y + h / 2)
    if rot == 90:
        return (x - h / 2, y - w, x + h / 2, y)
    return (x - h / 2, y, x + h / 2, y + w)


def _label_box(x, y, rot, text, size):
    """Label justified 'bottom': the text sits beside its anchor (above a horizontal wire, left of a vertical one)."""
    w, h = len(text) * size * CHAR_W, size * LINE_H
    return {0: (x, y - h, x + w, y), 180: (x - w, y - h, x, y),
            90: (x - h, y - w, x, y), 270: (x - h, y, x, y + w)}[rot]


def _hits_box(seg, box, margin=0.2):
    (x1, y1, x2, y2), (ax, ay, bx, by) = box, seg
    x1, y1, x2, y2 = x1 + margin, y1 + margin, x2 - margin, y2 - margin
    if x2 <= x1 or y2 <= y1:
        return False
    return min(ax, bx) < x2 and max(ax, bx) > x1 and min(ay, by) < y2 and max(ay, by) > y1


def _overlap(a, b) -> bool:
    return min(a[2], b[2]) - max(a[0], b[0]) > 0.2 and min(a[3], b[3]) - max(a[1], b[1]) > 0.2


def _sexpr(txt: str):
    """Minimal s-expression reader: lists of atoms (strings unquoted)."""
    tok = re.compile(r'\(|\)|"(?:[^"\\]|\\.)*"|[^\s()]+')
    stack: list = [[]]
    for m in tok.finditer(txt):
        t = m.group(0)
        if t == "(":
            stack.append([])
        elif t == ")":
            done = stack.pop()
            stack[-1].append(done)
        else:
            stack[-1].append(t[1:-1] if t.startswith('"') else t)
    return stack[0][0]


def _kids(node, name):
    return [c for c in node if isinstance(c, list) and c and c[0] == name]


def _first(node, name):
    k = _kids(node, name)
    return k[0] if k else None


def _body_points(sym) -> list:
    """Graphic points of a library symbol (all units, no pins, no text), library coordinates (y up)."""
    pts = []
    for unit in _kids(sym, "symbol"):
        for g in unit[1:]:
            if not isinstance(g, list):
                continue
            if g[0] == "rectangle":
                pts += [tuple(map(float, _first(g, k)[1:3])) for k in ("start", "end")]
            elif g[0] in ("polyline", "bezier"):
                pts += [tuple(map(float, xy[1:3])) for xy in _kids(_first(g, "pts"), "xy")]
            elif g[0] == "circle":
                cx, cy = map(float, _first(g, "center")[1:3])
                r = float(_first(g, "radius")[1])
                pts += [(cx - r, cy - r), (cx + r, cy + r)]
            elif g[0] == "arc":
                pts += [tuple(map(float, _first(g, k)[1:3])) for k in ("start", "mid", "end")]
    return pts


def _place(pt, at, rot, mirror):
    x, y = pt[0], -pt[1]  # library y up -> sheet y down
    if mirror == "x":
        y = -y
    elif mirror == "y":
        x = -x
    for _ in range((rot // 90) % 4):  # counter-clockwise on screen (sheet y down)
        x, y = y, -x
    return at[0] + x, at[1] + y


def _prop_box(prop, flip=False, sym_rot=0):
    at = _first(prop, "at")
    x, y = float(at[1]), float(at[2])
    ang = ((int(float(at[3])) if len(at) > 3 else 0) + sym_rot) % 360  # stored relative to the symbol rotation
    eff = _first(prop, "effects")
    size = float(_first(_first(eff, "font"), "size")[1])
    just = _first(eff, "justify")
    w, h = len(prop[2]) * size * CHAR_W, size * 1.0
    side = None if not just else ("left" if "left" in just else "right" if "right" in just else None)
    if side and flip:  # KiCad mirrors field justification with a symbol rotated 180 or mirrored about y
        side = "right" if side == "left" else "left"
    left = -w / 2 if side is None else (0 if side == "left" else -w)
    if ang % 180 == 0:
        return (x + left, y - h / 2, x + left + w, y + h / 2)
    return (x - h / 2, y - left - w, x + h / 2, y - left)


def check_symbols(tree, where: str) -> list[str]:
    issues = []
    lib = {s[1]: s for s in _kids(_first(tree, "lib_symbols") or [], "symbol")}
    for sym in _kids(tree, "symbol"):
        lib_id = _first(sym, "lib_id")[1]
        at = _first(sym, "at")
        pos, rot = (float(at[1]), float(at[2])), int(float(at[3])) if len(at) > 3 else 0
        mir = _first(sym, "mirror")
        mirror = mir[1] if mir else None
        props = {p[1]: p for p in _kids(sym, "property")}
        ref, value = props["Reference"][2], props["Value"][2]
        if lib_id.startswith("power:"):
            # arrow up at rotation 0; down when rotated 180 or mirrored about the x axis
            down = ((rot % 360 == 180) != (mirror == "x"))
            if down and not value.upper().startswith("GND") and lib_id != "power:PWR_FLAG" and rot % 180 == 0:
                issues.append(f"{where}: rail symbol '{value}' points down at ({pos[0]},{pos[1]})")
            continue
        pts = [_place(p, pos, rot, mirror) for p in _body_points(lib.get(lib_id, []))]
        if not pts:
            continue
        body = (min(p[0] for p in pts), min(p[1] for p in pts), max(p[0] for p in pts), max(p[1] for p in pts))
        for key in ("Reference", "Value"):
            prop = props[key]
            eff = _first(prop, "effects")
            if eff is None or any(isinstance(c, list) and c[:2] == ["hide", "yes"] for c in eff) or "hide" in eff:
                continue
            if _overlap(_prop_box(prop, (rot % 360 == 180) != (mirror == "y"), rot), body):
                issues.append(f"{where}: {key.lower()} '{prop[2]}' of {ref} overlaps its symbol body")
    return issues


def check_note_frames(tree, txt_notes, where: str) -> list[str]:
    frames = []
    for r in _kids(tree, "rectangle"):
        (x1, y1), (x2, y2) = (tuple(map(float, _first(r, k)[1:3])) for k in ("start", "end"))
        frames.append((min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)))
    issues = []
    for body, x, y, size, lines, longest in txt_notes:
        inside = [f for f in frames if f[0] <= x <= f[2] and f[1] <= y <= f[3]]
        if not inside:
            continue
        f = min(inside, key=lambda f: (f[2] - f[0]) * (f[3] - f[1]))
        right, bottom = x + longest * size * NOTE_CHAR_W, y + lines * size * LINE_H
        if right > f[2] + 0.5 or bottom > f[3] + 0.5:
            issues.append(f"{where}: note '{body}' runs past its frame (right {right:.0f} > {f[2]:.0f} mm or bottom)")
    return issues


def check_sheet(path: Path) -> list[str]:
    txt = path.read_text()
    labels = []
    for m in LABEL.finditer(txt):
        kind, name, _mid, x, y, rot, _rest, size = m.groups()
        size = float(size)
        boxf = _label_box if "bottom" in txt[m.end():m.end() + 60].split("uuid")[0] else _box
        labels.append((kind, name, float(x), float(y), int(rot), size, boxf(float(x), float(y), int(rot) % 360, name, size)))
    notes, frame_notes = [], []
    for body, _mid, x, y, rot, _rest, size in TEXT.findall(txt):
        if int(rot) % 360 == 0:
            ls = body.split("\\n")
            frame_notes.append((body[:40], float(x), float(y), float(size), len(ls), max(len(line) for line in ls)))
        body = body.replace('\\n', ' ').replace('\\"', '"')
        longest = max((len(line) for line in body.split("\\n")), default=0) or len(body)
        size = float(size)
        notes.append((body[:40], float(size), _box(float(x), float(y), int(rot) % 360, "x" * longest, size)))
    wires = [tuple(map(float, m)) for m in WIRE.findall(txt)]
    issues = []
    where = path.name
    for i, (kind, name, x, y, rot, size, box) in enumerate(labels):
        if size < 1.0:
            issues.append(f"{where}: small text {size} mm on label '{name}' at ({x},{y})")
        for kind2, name2, x2, y2, _r2, _s2, box2 in labels[i + 1:]:
            if _overlap(box, box2):
                issues.append(f"{where}: label '{name}' ({x},{y}) overlaps label '{name2}' ({x2},{y2})")
        for seg in wires:
            if _hits_box(seg, box):
                issues.append(f"{where}: wire runs through label '{name}' at ({x},{y})")
                break
    for body, size, box in notes:
        if size < 1.0:
            issues.append(f"{where}: small note text {size} mm: '{body}'")
        for kind, name, x, y, _r, _s, lbox in labels:
            if _overlap(box, lbox):
                issues.append(f"{where}: note '{body}' overlaps label '{name}' at ({x},{y})")
                break
        for seg in wires:
            if _hits_box(seg, box):
                issues.append(f"{where}: wire runs through note '{body}'")
                break
    # rules from the drawing research (scratch notes 2026-11-01): wires are horizontal or vertical only, and never more
    # than three wire ends meet at one point (a four-way junction reads like a crossing)
    ends: dict = {}
    for ax, ay, bx, by in wires:
        if ax != bx and ay != by:
            issues.append(f"{where}: diagonal wire ({ax},{ay})-({bx},{by})")
        for p in ((ax, ay), (bx, by)):
            ends[p] = ends.get(p, 0) + 1
    for p, n in ends.items():
        through = sum(1 for ax, ay, bx, by in wires if (ax == bx == p[0] and min(ay, by) < p[1] < max(ay, by))
                      or (ay == by == p[1] and min(ax, bx) < p[0] < max(ax, bx)))
        if n + 2 * through >= 4:
            issues.append(f"{where}: four-way wire junction at {p}")
    tree = _sexpr(txt)
    issues += check_symbols(tree, where)
    issues += check_note_frames(tree, frame_notes, where)
    return issues


def main(board: Path) -> int:
    issues = []
    for sch in sorted(board.glob("*.kicad_sch")):
        issues += check_sheet(sch)
    for line in issues:
        print(line)
    print(f"review checks: {len(issues)} issue(s)")
    return 1 if issues and "--strict" in sys.argv else 0


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        sys.exit("usage: review_checks.py hardware/<board> [--strict]")
    sys.exit(main(Path(args[0])))
