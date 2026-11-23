"""Merge the board's fab rules and net classes into <board>.kicad_pro (KiCad keeps both in the project file).

The schematic sections of an existing project (meta, schematic, sheets, libraries) are kept; `board` and
`net_settings` are rewritten. Fab floors come from rules/jlc-4layer.json, net classes from board.yaml.
"""

from __future__ import annotations

import json
from pathlib import Path

BASE = {"line_style": 0, "pcb_color": "rgba(0, 0, 0, 0.000)", "schematic_color": "rgba(0, 0, 0, 0.000)",
        "wire_width": 6, "bus_width": 12, "microvia_diameter": 0.3, "microvia_drill": 0.1, "diff_pair_via_gap": 0.25}


def write(pro: Path, rules_file: Path, classes: dict[str, dict]) -> None:
    """classes: board.yaml net_classes (track_mm, clearance_mm, via_mm, drill_mm, gap_mm, nets)."""
    fab = json.loads(rules_file.read_text())
    d = classes["Default"]
    out = []
    for i, (name, c) in enumerate(classes.items()):
        out.append({**BASE, "name": name,
                    "track_width": c["track_mm"], "clearance": c.get("clearance_mm", d["clearance_mm"]),
                    "via_diameter": c.get("via_mm", d["via_mm"]), "via_drill": c.get("drill_mm", d["drill_mm"]),
                    "diff_pair_width": c["track_mm"] if "gap_mm" in c else d["track_mm"],
                    "diff_pair_gap": c.get("gap_mm", 0.15),
                    "priority": 2147483647 if name == "Default" else i})
    doc = json.loads(pro.read_text()) if pro.exists() else {"meta": {"filename": pro.name, "version": 3}}
    doc["board"] = {"design_settings": {"rules": fab["rules"], "defaults": {}, "diff_pair_dimensions": [],
                                        "drc_exclusions": [], "track_widths": [], "via_dimensions": []}}
    doc.setdefault("boards", [])
    doc.setdefault("libraries", {"pinned_footprint_libs": [], "pinned_symbol_libs": []})
    doc["net_settings"] = {"classes": out, "meta": {"version": 4},
                           "netclass_patterns": [{"netclass": n, "pattern": p}
                                                 for n, c in classes.items() for p in c.get("nets", [])]}
    doc["pcbnew"] = {"page_layout_descr_file": ""}
    # worst-case width (7 chars + -dirty) so DRC silk checks gate the version text; the fab package plots the real SHA
    doc.setdefault("text_variables", {})["GIT_SHA"] = "0000000-dirty"
    pro.write_text(json.dumps(doc, indent=2) + "\n")
