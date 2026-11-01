"""Geometric review of the generated schematic: what a human would see as unreadable.

Reads the .kicad_sch files (no KiCad needed) and checks, per sheet:
  - label on label: two net labels or hierarchical labels whose text boxes overlap
  - text under a wire: a wire runs through the text box of a label or note
  - note on label: a free text note overlaps a label
  - small text: a label or note below 1.0 mm (hard to read on a printed A3)
  - wires not horizontal/vertical, and four or more wire ends at one point (four-way junction)
Text boxes are estimates: width = characters x size x 0.62, height = size x 1.6 (KiCad's default font).
These checks find the layout problems a reviewer would hit. The rendered PNGs are still read by a person
(or an agent) before a sheet passes; see .claude/skills/kicad-schematic/SKILL.md, section Review loop.

Run: python3 -I hardware/gen/review_checks.py hardware/weatherstation-v1 [--strict]
Exit code 1 when any issue is found (with --strict) so the gate can use it.
"""

import re
import sys
from pathlib import Path

LABEL = re.compile(r'\((label|global_label|hierarchical_label) "([^"]*)"(.*?)\(at ([-\d.]+) ([-\d.]+) (-?\d+)\)(.*?)\(font \(size ([\d.]+)', re.S)
TEXT = re.compile(r'\(text "((?:[^"\\]|\\.)*)"(.*?)\(at ([-\d.]+) ([-\d.]+) (-?\d+)\)(.*?)\(font \(size ([\d.]+)', re.S)
WIRE = re.compile(r'\(wire \(pts \(xy ([-\d.]+) ([-\d.]+)\) \(xy ([-\d.]+) ([-\d.]+)\)\)')
CHAR_W, LINE_H = 0.62, 1.6


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


def check_sheet(path: Path) -> list[str]:
    txt = path.read_text()
    labels = []
    for m in LABEL.finditer(txt):
        kind, name, _mid, x, y, rot, _rest, size = m.groups()
        size = float(size)
        boxf = _label_box if "bottom" in txt[m.end():m.end() + 60].split("uuid")[0] else _box
        labels.append((kind, name, float(x), float(y), int(rot), size, boxf(float(x), float(y), int(rot) % 360, name, size)))
    notes = []
    for body, _mid, x, y, rot, _rest, size in TEXT.findall(txt):
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
    sys.exit(main(Path(sys.argv[1]) if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else Path("hardware/weatherstation-v1")))
