"""Thin layer over kicad-sch-api: correct pin positions and a net-intent check.

kicad-sch-api 0.5.x rotates pins clockwise; KiCad rotates symbols counter-clockwise in a
y-up library frame, drawn in a y-down sheet frame. We compute pin positions ourselves and
verify every generated schematic against the exported netlist (`check_nets`).
"""

import math
import uuid
import re
import subprocess
from pathlib import Path

import kicad_sch_api as ksa


def pin_pos(sch: ksa.Schematic, ref: str, number: str, mirror: str | None = None) -> tuple[float, float]:
    """Pin end in sheet mm. KiCad rotates first, then mirrors in sheet coordinates:
    mirror 'y' flips left-right about the symbol origin, mirror 'x' flips top-bottom (checked against ERC pin positions)."""
    comp = sch.components.get(ref)
    sym = ksa.get_symbol_info(comp.lib_id)
    pin = next(p for p in sym.pins if p.number == number)
    r = math.radians(comp.rotation or 0)
    x = pin.position.x * math.cos(r) - pin.position.y * math.sin(r)
    y = pin.position.x * math.sin(r) + pin.position.y * math.cos(r)
    if mirror == "y":
        x = -x
    elif mirror == "x":
        y = -y
    return (round(comp.position.x + x, 2), round(comp.position.y - y, 2))


def pin_away(sch: ksa.Schematic, ref: str, number: str, mirror: str | None = None) -> int:
    """Direction (degrees, CCW) pointing from the pin's end away from the symbol body (mirror as in pin_pos)."""
    comp = sch.components.get(ref)
    pin = next(p for p in ksa.get_symbol_info(comp.lib_id).pins if p.number == number)
    a = (pin.rotation + (comp.rotation or 0) + 180) % 360
    if mirror == "y":
        a = 180 - a
    elif mirror == "x":
        a = -a
    return int(a) % 360


CELL = 2.54  # drawing grid: sheet coordinates are given in cells of 2.54 mm (fractions of 0.5 are on the 1.27 grid)
_uid = [0]


def uid() -> str:
    _uid[0] += 1
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"weatherstation-v1/{_uid[0]}"))


def mm(cell: float) -> float:
    return round(cell * CELL, 2)


def q(text: str) -> str:
    return text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


class Sheet:
    """One schematic sheet: parts via kicad-sch-api, everything else written as S-expressions.

    Coordinates are in cells (2.54 mm). Wires are polylines through pins ((ref, pin)) and points (x, y).
    Junctions are derived from the wire geometry when saving.
    """

    pwr_count = 0  # power-symbol references are unique over all sheets

    def __init__(self, name: str, filename: str, parts: dict, paper: str = "A3", note: str = "",
                 project: str = "weatherstation-v1", title: str = "weatherstation v1"):
        self.name, self.filename, self.parts = name, filename, parts
        self.paper, self.note = paper, note
        self.sch = ksa.Schematic.create(project)
        self.sch.set_paper_size(paper)
        self.sch.set_title_block(title=title, date="2026-10-31", rev="v1", company="weatherstation",
                                 comments={1: f"Sheet: {name}", 2: note.split(":")[0][:60]})
        self.uuid = str(uuid.uuid5(uuid.NAMESPACE_URL, "sheet/" + name))
        self.raw: list[str] = []
        self.segs: list[tuple[tuple[float, float], tuple[float, float]]] = []
        self.pins: set[tuple[float, float]] = set()
        self.refs: list[str] = []
        self.mirror: dict[str, str] = {}
        self.specs: list = []
        self.tags: dict[str, dict[str, tuple[float, float, str]]] = {}
        self.rots: dict[str, int] = {}

    # --- parts -------------------------------------------------------------
    def part(self, ref: str, x: float, y: float, rot: int = 0, value: str | None = None, mirror: bool | str = False):
        sym, val, fp, lcsc = self.parts[ref][:4]
        rot = rot or 0
        props = {"LCSC": lcsc} if lcsc else {}
        comp = self.sch.components.add(sym, ref, value or val, (mm(x), mm(y)), fp, rotation=rot, **props)
        if not lcsc and not ref.startswith("#"):
            comp.in_bom = False
        self.refs.append(ref)
        self.rots[ref] = rot
        if mirror:
            # KiCad mirrors in the symbol frame before rotating: "y" flips the symbol's x, "x" flips its y
            self.mirror[ref] = mirror if isinstance(mirror, str) else "y"
        self._register(ref)
        return comp

    def _register(self, ref: str) -> None:
        info = ksa.get_symbol_info(self.sch.components.get(ref).lib_id)
        for p in info.pins:
            self.pins.add(self.at(ref, p.number))

    def tag(self, ref: str, reference=None, value=None, just: str = "left") -> None:
        """Place the reference/value texts at (dx, dy) mm from the symbol origin (None keeps the automatic spot)."""
        self.tags[ref] = {"Reference": reference and (*reference, just), "Value": value and (*value, just)}

    def _auto_tags(self) -> None:
        for ref in self.refs:
            if ref in self.tags or ref.startswith("#PWR"):
                continue
            lib = self.sch.components.get(ref).lib_id
            if lib in ("Device:R", "Device:C", "Device:L", "Device:Polyfuse", "Device:Fuse", "Device:Thermistor_NTC", "Device:LED", "Switch:SW_Push", "Connector:TestPoint"):
                native_h = lib in ("Device:LED", "Switch:SW_Push")
                if (self.rots.get(ref, 0) in (90, 270)) != native_h:
                    self.tags[ref] = {"Reference": (0, -5.2, "center"), "Value": (0, -2.9, "center")}
                else:
                    self.tags[ref] = {"Reference": (2.2, -1.3, "left"), "Value": (2.2, 1.3, "left")}
            elif lib == "power:PWR_FLAG":
                self.tags[ref] = {"Reference": "hide", "Value": "hide"}

    def _apply_tags(self, txt: str) -> str:
        for ref, props in self.tags.items():
            comp = self.sch.components.get(ref)
            for name, spec in props.items():
                if not spec:
                    continue
                if spec == "hide":
                    pat = re.compile(r'(\(property "%s" "[^"]*"\s*\(at [^\n]*\n\s*\(effects\s*\(font\s*\(size [\d. ]+\)\s*\))' % name)
                    blocks = txt.split("\t(symbol\n\t\t(lib_id")
                    for i, blk in enumerate(blocks[1:], 1):
                        if f'(property "Reference" "{ref}"' in blk:
                            blocks[i] = pat.sub(r"\1 (hide yes)", blk, count=1)
                    txt = "\t(symbol\n\t\t(lib_id".join(blocks)
                    continue
                dx, dy, just = spec
                pat = re.compile(r'(\(property "%s" "[^"]*"\s*\(at )[-\d.]+ [-\d.]+ [-\d.]+(\)\s*\(effects\s*\(font\s*\(size [\d. ]+\)\s*\))(\s*\(justify [a-z ]+\))?' % name)
                blocks = txt.split("\t(symbol\n\t\t(lib_id")
                for i, blk in enumerate(blocks[1:], 1):
                    if f'(property "Reference" "{ref}"' in blk:
                        j = f'(justify {just})' if just != "center" else ""
                        x, y = round(comp.position.x + dx, 2), round(comp.position.y + dy, 2)
                        ang = (-self.rots.get(ref, 0)) % 360 if self.rots.get(ref, 0) in (90, 270) else 0  # field angles add to the rotation
                        if (self.mirror.get(ref) == "y" or self.rots.get(ref, 0) == 180) and just != "center":
                            # mirrored or upside-down symbols flip the justification
                            j = f"(justify {'right' if just == 'left' else 'left'})"
                        blocks[i] = pat.sub(lambda m: f"{m.group(1)}{x} {y} {ang}{m.group(2)} {j}", blk, count=1)
                txt = "\t(symbol\n\t\t(lib_id".join(blocks)
        return txt

    def power(self, net: str, x: float, y: float, flip: bool = False, lib: str | None = None, rot: int = 0) -> None:
        """Explicit power symbol whose pin sits at (x, y); flip mirrors it (GND up, a rail down); rot turns it
        (a symbol on a side pin points sideways, along its stub, so it stays on its own row).
        lib: library symbol; default power:<net>. For a rail with no own symbol use power:VCC: the value is the net name."""
        Sheet.pwr_count += 1
        ref = f"#PWR{Sheet.pwr_count:02d}"
        self.sch.components.add(lib or f"power:{net}", ref, net, (mm(x), mm(y)), rotation=rot)
        self.refs.append(ref)
        self.pins.add((mm(x), mm(y)))
        if rot in (90, 270):
            self.rots[ref] = rot
            # value text beyond the symbol tip, on the stub line, reading left to right
            reach = 5.0 if net != "GND" else 4.0
            sign = 1 if (rot == 270) == (net != "GND") else -1
            self.tags[ref] = {"Reference": "hide", "Value": (sign * reach, 0, "left" if sign > 0 else "right")}
        if flip:
            self.mirror[ref] = "x"
            self.rots[ref] = 0
            self.tags[ref] = {"Reference": "hide", "Value": (0, 4.2, "center")}

    def flag(self, ref: str, x: float, y: float) -> None:
        self.part(ref, x, y)

    def at(self, ref: str, pin: str) -> tuple[float, float]:
        return pin_pos(self.sch, ref, pin, self.mirror.get(ref))

    # --- wires -------------------------------------------------------------
    def _pt(self, p) -> tuple[float, float]:
        if isinstance(p[0], str):
            return self.at(*p)
        return (mm(p[0]), mm(p[1]))

    def wire(self, *pts) -> None:
        self.specs.append(pts)  # resolved in resolve(): wires may name pins of parts placed later

    def resolve(self) -> None:
        for pts in self.specs:
            mmp = [self._pt(p) for p in pts]
            for a, b in zip(mmp, mmp[1:]):
                assert a[0] == b[0] or a[1] == b[1], f"{self.name}: diagonal wire {a}->{b} in {pts}"
                if a != b:
                    self.segs.append((a, b))
        self.specs = []

    # --- labels and text ----------------------------------------------------
    @staticmethod
    def _just(rot: int) -> str:
        return "right" if rot in (180, 270) else "left"

    def label(self, name: str, x: float, y: float, rot: int = 0, kind: str = "local", above: bool = False) -> None:
        """above: text beside the wire (justify bottom) instead of centred on it; for a name label in the middle of a wire."""
        px, py = mm(x), mm(y)
        eff = f'(effects (font (size 1.27 1.27)) (justify {self._just(rot)}{" bottom" if above else ""}))'
        if kind == "local":
            self.raw.append(f'(label "{q(name)}" (at {px} {py} {rot}) {eff} (uuid "{uid()}"))')
        elif kind == "global":
            self.raw.append(f'(global_label "{q(name)}" (shape bidirectional) (at {px} {py} {rot}) (fields_autoplaced yes) {eff} '
                            f'(uuid "{uid()}") (property "Intersheetrefs" "${{INTERSHEET_REFS}}" (at {px} {py} 0) '
                            f'(effects (font (size 1.27 1.27)) hide)))')
        else:
            self.raw.append(f'(hierarchical_label "{q(name)}" (shape bidirectional) (at {px} {py} {rot}) {eff} (uuid "{uid()}"))')

    def text(self, x: float, y: float, body: str, size: float = 1.27, bold: bool = False) -> None:
        b = " bold" if bold else ""
        self.raw.append(f'(text "{q(body)}" (exclude_from_sim no) (at {mm(x)} {mm(y)} 0) '
                        f'(effects (font (size {size} {size}){b}) (justify left top)) (uuid "{uid()}"))')

    def frame(self, x1: float, y1: float, x2: float, y2: float, title: str, color=(0, 0, 0), tint=(255, 255, 255)) -> None:
        """Group box with a caption (dashed rectangle, coloured outline, light tint) for one block."""
        r, g, b = color
        tr, tg, tb = tint
        self.raw.append(f'(rectangle (start {mm(x1)} {mm(y1)}) (end {mm(x2)} {mm(y2)}) '
                        f'(stroke (width 0.3) (type dash) (color {r} {g} {b} 1)) '
                        f'(fill (type color) (color {tr} {tg} {tb} 0.35)) (uuid "{uid()}"))')
        self.text(x1 + 0.5, y1 + 0.4, title, 1.5, bold=True)

    def no_connect(self, ref: str, numbers: list[str]) -> None:
        for number in numbers:
            x, y = self.at(ref, number)
            self.raw.append(f'(no_connect (at {x} {y}) (uuid "{uid()}"))')

    # --- output --------------------------------------------------------------
    @staticmethod
    def _inside(p, seg) -> bool:
        a, b = seg
        return ((a[0] == b[0] == p[0] and min(a[1], b[1]) < p[1] < max(a[1], b[1]))
                or (a[1] == b[1] == p[1] and min(a[0], b[0]) < p[0] < max(a[0], b[0])))

    def _junctions(self) -> list[tuple[float, float]]:
        self.resolve()
        cands = {p for s in self.segs for p in s} | self.pins
        out = []
        for p in sorted(cands):
            if not any(p in seg or self._inside(p, seg) for seg in self.segs):
                continue
            deg = 1 if p in self.pins else 0
            for a, b in self.segs:
                if p in (a, b):
                    deg += 1
                elif a[0] == b[0] == p[0] and min(a[1], b[1]) < p[1] < max(a[1], b[1]):
                    deg += 2
                elif a[1] == b[1] == p[1] and min(a[0], b[0]) < p[0] < max(a[0], b[0]):
                    deg += 2
            if deg >= 3:
                out.append(p)
        return out

    def warnings(self) -> list[str]:
        """Pins lying in the middle of a wire (they would connect) and wires touching foreign pins."""
        out = []
        self.resolve()
        for p in self.pins:
            for a, b in self.segs:
                if p not in (a, b) and ((a[0] == b[0] == p[0] and min(a[1], b[1]) < p[1] < max(a[1], b[1]))
                                        or (a[1] == b[1] == p[1] and min(a[0], b[0]) < p[0] < max(a[0], b[0]))):
                    out.append(f"{self.name}: pin at {p} lies on wire {a}-{b}")
        return out

    def save(self, directory: Path, parent_uuid: str, sheet_uuid: str) -> Path:
        path = directory / self.filename
        self.resolve()
        # stacked pins (USB-C VBUS, GND) give identical stubs: write each wire once
        self.segs = list(dict.fromkeys(tuple(sorted(s)) for s in self.segs if s[0] != s[1]))
        self.sch.save(path)
        txt = path.read_text()
        self._auto_tags()
        txt = self._apply_tags(txt)
        wires = [f'(wire (pts (xy {a[0]} {a[1]}) (xy {b[0]} {b[1]})) (stroke (width 0) (type default)) (uuid "{uid()}"))'
                 for a, b in self.segs]
        juncs = [f'(junction (at {x} {y}) (diameter 0) (color 0 0 0 0) (uuid "{uid()}"))' for x, y in self._junctions()]
        body = "\n\t".join(wires + juncs + self.raw)
        txt = txt.replace("\t(sheet_instances", "\t" + body + "\n\t(sheet_instances", 1)
        for ref, axis in self.mirror.items():
            blocks = txt.split("\t(symbol\n\t\t(lib_id")
            for i, blk in enumerate(blocks[1:], 1):
                if f'(property "Reference" "{ref}"' in blk:
                    blocks[i] = re.sub(r"(\(at [-\d.]+ [-\d.]+ [-\d.]+\))", r"\1\n\t\t(mirror %s)" % axis, blk, count=1)
            txt = "\t(symbol\n\t\t(lib_id".join(blocks)
        txt = re.sub(r'(\(property "LCSC" "[^"]*"\s*\(at [^\n]*\n\s*\(effects\s*\(font\s*\(size [\d. ]+\)\s*\)\s*\(justify left\))', r"\1 (hide yes)", txt)
        txt = txt.replace(f'(path "/{self.sch.uuid}"', f'(path "/{parent_uuid}/{sheet_uuid}"')
        path.write_text(txt)
        return path


def root_sheet(directory: Path, name: str, sheets: list[dict], texts: list[tuple[float, float, str]], wires, labels,
               project: str = "weatherstation-v1", title: str = "weatherstation v1") -> tuple[Path, str]:
    """Root page: block diagram of sheet symbols. Each entry of sheets: name, file, x, y, w, h, page, pins=[(edge, y_cell, name)]."""
    root = str(uuid.uuid5(uuid.NAMESPACE_URL, "root" if project == "weatherstation-v1" else "root/" + project))
    out = ['(kicad_sch (version 20250114) (generator "eeschema") (generator_version "9.0")', f'\t(uuid "{root}")', '\t(paper "A3")',
           f'\t(title_block (title "{title}") (date "2026-10-31") (rev "v1") (company "weatherstation") '
           '(comment 1 "Sheet: root (block diagram)"))', "\t(lib_symbols)"]
    segs_mm = [((mm(a[0]), mm(a[1])), (mm(b[0]), mm(b[1]))) for a, b in wires]
    for jx, jy in junction_points(segs_mm):
        out.append(f'\t(junction (at {jx} {jy}) (diameter 0) (color 0 0 0 0) (uuid "{uid()}"))')
    for w in wires:
        (x1, y1), (x2, y2) = w
        out.append(f'\t(wire (pts (xy {mm(x1)} {mm(y1)}) (xy {mm(x2)} {mm(y2)})) (stroke (width 0) (type default)) (uuid "{uid()}"))')
    for text, x, y, *rest in labels:  # optional angle: 0 text to the right, 180 to the left, 90 up, 270 down
        ang = rest[0] if rest else 0
        just = {0: "left bottom", 180: "right bottom", 90: "left bottom", 270: "right bottom"}[ang]
        out.append(f'\t(label "{text}" (at {mm(x)} {mm(y)} {ang}) (effects (font (size 1.27 1.27)) (justify {just})) (uuid "{uid()}"))')
    for sh in sheets:
        x, y, w, h = (mm(sh[k]) for k in ("x", "y", "w", "h"))
        s = [f'\t(sheet (at {x} {y}) (size {w} {h}) (exclude_from_sim no) (in_bom yes) (on_board yes) (dnp no) (fields_autoplaced yes)',
             f'\t\t(stroke (width 0.4) (type solid) (color {sh.get("stroke", (0, 0, 0))[0]} {sh.get("stroke", (0, 0, 0))[1]} {sh.get("stroke", (0, 0, 0))[2]} 1)) '
             f'(fill (color {sh.get("fill", (255, 255, 200))[0]} {sh.get("fill", (255, 255, 200))[1]} {sh.get("fill", (255, 255, 200))[2]} 0.6))', f'\t\t(uuid "{sh["uuid"]}")',
             f'\t\t(property "Sheetname" "{sh["name"]}" (at {x} {y - 1.0} 0) (effects (font (size 2 2) bold) (justify left bottom)))',
             f'\t\t(property "Sheetfile" "{sh["file"]}" (at {x} {y + h + 1.0} 0) (effects (font (size 1.27 1.27)) (justify left top)))']
        for edge, pos_cell, pname in sh["pins"]:
            if edge in ("left", "right"):
                px, py = (x if edge == "left" else round(x + w, 2)), mm(pos_cell)
                rot, just = (180, "left") if edge == "left" else (0, "right")
            else:
                px, py = mm(pos_cell), (y if edge == "top" else round(y + h, 2))
                rot, just = (90, "left") if edge == "top" else (270, "left")
            s.append(f'\t\t(pin "{pname}" bidirectional (at {px} {py} {rot}) (uuid "{uid()}") '
                     f'(effects (font (size 1.27 1.27)) (justify {just})))')
        s.append(f'\t\t(instances (project "{project}" (path "/{root}" (page "{sh["page"]}"))))')
        s.append("\t)")
        out.append("\n".join(s))
    for x, y, body in texts:
        size = 2.0 if body.startswith("#") else 1.5
        body = body.lstrip("#")
        out.append(f'\t(text "{q(body)}" (exclude_from_sim no) (at {mm(x)} {mm(y)} 0) '
                   f'(effects (font (size {size} {size})) (justify left top)) (uuid "{uid()}"))')
    out.append('\t(sheet_instances (path "/" (page "1")))')
    out.append("\t(embedded_fonts no)\n)")
    path = directory / f"{project}.kicad_sch"
    path.write_text("\n".join(out) + "\n")
    return path, root


def netlist(sch_file: Path) -> dict[str, set[tuple[str, str]]]:
    """KiCad's netlist keyed by the last path component: '/Power/CC1', '/USB_DP' and 'GND' -> 'CC1', 'USB_DP', 'GND'."""
    net_file = sch_file.with_suffix(".net")
    subprocess.run(["kicad-cli", "sch", "export", "netlist", "-o", str(net_file), str(sch_file)],
                   check=True, capture_output=True)
    text = net_file.read_text().split("(nets", 1)[1]
    out = {}
    for blk in text.split("(net\n")[1:]:
        name = re.search(r'\(name "([^"]+)"', blk).group(1).split("/")[-1]
        pins = set(re.findall(r'\(ref "([^"]+)"\)\s*\(pin "([^"]+)"', blk))
        if name in out:
            name += "!dup"
        out[name] = pins
    return out


def check_nets(sch_file: Path, nets: dict[str, list[tuple[str, str]]]) -> list[str]:
    """Differences between intended nets and KiCad's netlist (power symbols/flags ignored), also extra nets."""
    actual = netlist(sch_file)
    errors = []
    for net, pins in nets.items():
        want = {p for p in pins if not p[0].startswith("#")}
        got = actual.get(net, set())
        if want != got:
            errors.append(f"{net}: missing {sorted(want - got)} extra {sorted(got - want)}")
    for name, pins in actual.items():
        if name not in nets and not name.startswith("unconnected-") and pins:
            errors.append(f"unexpected net {name}: {sorted(pins)}")
    return errors


# --- orthogonal router: draw real wires between the pins of a net instead of labels everywhere -----------
def _seg_hits_seg(a, b, c, d) -> bool:
    """Closed axis-aligned segments a-b and c-d share a point."""
    (ax, ay), (bx, by) = a, b
    (cx, cy), (dx, dy) = c, d
    return (min(ax, bx) <= max(cx, dx) and min(cx, dx) <= max(ax, bx)
            and min(ay, by) <= max(cy, dy) and min(cy, dy) <= max(ay, by))


def _seg_hits_box(a, b, box) -> bool:
    x1, y1, x2, y2 = box
    (ax, ay), (bx, by) = a, b
    return min(ax, bx) <= x2 and max(ax, bx) >= x1 and min(ay, by) <= y2 and max(ay, by) >= y1


GRID = 1.27  # routing grid (mm): half a cell, so every pin and stub end lies on it


def _u(v: float) -> int:
    return round(v / GRID)


class Router:
    """Maze router for the wires of one sheet (Dijkstra on a 1.27 mm grid, fewest bends).

    Nodes blocked: inside a part box (part bodies plus a cell of margin) or on a wire of another net.
    A net's new pin may join any node of its own tree (its exit points); other nodes of the same net are
    blocked, so a route never runs along or across the tree by accident. Stubs (pin -> exit) are registered
    first, so every other route avoids them.
    """

    STEP, TURN = 1, 2

    def __init__(self, boxes: list, owners: list | None = None):
        """boxes in mm; owner '*' (default) blocks every net, a net name blocks only the other nets."""
        owners = owners or ["*"] * len(boxes)
        self.boxes = [(_u(a), _u(b), _u(c), _u(d)) for a, b, c, d in boxes]
        self.box_nodes: dict[tuple[int, int], str] = {}
        for (x1, y1, x2, y2), owner in zip(self.boxes, owners):
            for i in range(x1, x2 + 1):
                for j in range(y1, y2 + 1):
                    prev = self.box_nodes.get((i, j))
                    self.box_nodes[(i, j)] = owner if prev in (None, owner) else "*"

        self.occ: dict[tuple[int, int], str] = {}
        self.stub_nodes: dict[tuple[str, tuple[int, int]], set[tuple[int, int]]] = {}
        self.segs: list[tuple[str, tuple[float, float], tuple[float, float]]] = []

    @staticmethod
    def _nodes_of(a, b) -> list[tuple[int, int]]:
        (ax, ay), (bx, by) = (_u(a[0]), _u(a[1])), (_u(b[0]), _u(b[1]))
        if ax == bx:
            step = 1 if by >= ay else -1
            return [(ax, j) for j in range(ay, by + step, step)]
        step = 1 if bx >= ax else -1
        return [(i, ay) for i in range(ax, bx + step, step)]

    def add_stub(self, net: str, a, b) -> None:
        self.segs.append((net, a, b))
        nodes = set(self._nodes_of(a, b))
        self.stub_nodes[(net, (_u(b[0]), _u(b[1])))] = nodes
        for n in nodes:
            self.occ[n] = net

    def _search(self, net: str, start: tuple[int, int], targets: set[tuple[int, int]]):
        import heapq
        dirs = ((1, 0), (-1, 0), (0, 1), (0, -1))
        best = {}
        parent = {}
        heap = [(0, start[0], start[1], -1)]
        xs = [t[0] for t in targets] + [start[0]]
        ys = [t[1] for t in targets] + [start[1]]
        lo_x, hi_x, lo_y, hi_y = min(xs) - 40, max(xs) + 40, min(ys) - 40, max(ys) + 40
        while heap:
            d, i, j, k = heapq.heappop(heap)
            if (i, j, k) in best:
                continue
            best[(i, j, k)] = d
            if (i, j) in targets and (i, j) != start:
                path = [(i, j)]
                state = (i, j, k)
                while state in parent:
                    state = parent[state]
                    path.append(state[:2])
                return list(reversed(path))
            for nd, (dx, dy) in enumerate(dirs):
                ni, nj = i + dx, j + dy
                if not (lo_x <= ni <= hi_x and lo_y <= nj <= hi_y):
                    continue
                node = (ni, nj)
                if node in targets:
                    pass
                else:
                    owner = self.box_nodes.get(node)
                    if (owner is not None and (owner == "*" or owner != net)) or node in self.occ:
                        continue
                cost = d + self.STEP + (self.TURN if k != -1 and k != nd else 0)
                if (ni, nj, nd) not in best:
                    parent[(ni, nj, nd)] = (i, j, k)
                    heapq.heappush(heap, (cost, ni, nj, nd))
        return None

    MAX_BENDS = 4

    @classmethod
    def _short(cls, path) -> bool:
        """A wire is drawn only when it is direct: at most 4 bends and no more than 1.5x the manhattan
        distance plus 6 cells. Longer connections keep labels (they cross blocks; the reader follows the label)."""
        length = sum(abs(a[0] - b[0]) + abs(a[1] - b[1]) for a, b in zip(path, path[1:]))
        dist = abs(path[0][0] - path[-1][0]) + abs(path[0][1] - path[-1][1])
        bends = sum(1 for a, b, c in zip(path, path[1:], path[2:])
                    if (b[0] - a[0], b[1] - a[1]) != (c[0] - b[0], c[1] - b[1]))
        return bends <= cls.MAX_BENDS and length <= 1.5 * dist + 12

    def connect(self, net: str, exits: list[tuple[float, float]], strict: bool = True):
        """Segments that join all exit points into one tree, or None when a pin cannot be reached.

        The tree starts as the first pin's stub. Each pin, nearest first, is joined to any node of the tree
        (its stub included), and its stub and route join the tree. Nothing else of this net is a target.
        """
        tree = {(_u(exits[0][0]), _u(exits[0][1]))}  # join at stub ends, never in the middle of a stub
        todo = [(_u(e[0]), _u(e[1])) for e in exits[1:]]
        added: list[tuple[str, tuple[float, float], tuple[float, float]]] = []
        occ_before = dict(self.occ)
        while todo:
            todo.sort(key=lambda p: min(abs(p[0] - t[0]) + abs(p[1] - t[1]) for t in tree))
            start = todo[0]
            if start in tree:  # two stubs end on the same point: already joined
                todo.pop(0)
                continue
            path = self._search(net, start, tree)
            if path is None or (strict and not self._short(path)):
                self.occ = occ_before
                return None
            for n in path:
                self.occ[n] = net
            tree.add(start)
            tree |= set(path)
            todo.pop(0)
            corners = [path[0]]
            for k in range(1, len(path) - 1):
                (a, b, c) = path[k - 1], path[k], path[k + 1]
                if (b[0] - a[0], b[1] - a[1]) != (c[0] - b[0], c[1] - b[1]):
                    corners.append(b)
            corners.append(path[-1])
            for p, q in zip(corners, corners[1:]):
                added.append((net, (p[0] * GRID, p[1] * GRID), (q[0] * GRID, q[1] * GRID)))
        self.segs.extend(added)
        return [(a, b) for _, a, b in added]


def part_boxes(sheet: Sheet, refs: list[str], margin: float = 2.54) -> list[tuple[float, float, float, float]]:
    """Body box per part from its pin positions, plus a margin (sheet mm)."""
    boxes = []
    for ref in refs:
        pts = [sheet.at(ref, p.number) for p in ksa.get_symbol_info(sheet.sch.components.get(ref).lib_id).pins]
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        boxes.append((min(xs) - margin, min(ys) - margin, max(xs) + margin, max(ys) + margin))
    return boxes


def junction_points(segs, pins=()) -> list[tuple[float, float]]:
    """Points where 3 or more wire ends meet (a wire end on another wire counts 2, a pin counts 1)."""
    ends: dict[tuple[float, float], int] = {}
    for a, b in segs:
        for p in (a, b):
            ends[p] = ends.get(p, 0) + 1
    for p in pins:
        ends[p] = ends.get(p, 0) + 1
    out = []
    for p in sorted(ends):
        deg = ends[p]
        for a, b in segs:
            if p in (a, b):
                continue
            if (a[0] == b[0] == p[0] and min(a[1], b[1]) < p[1] < max(a[1], b[1])) or \
               (a[1] == b[1] == p[1] and min(a[0], b[0]) < p[0] < max(a[0], b[0])):
                deg += 2
        if deg >= 3:
            out.append(p)
    return out
