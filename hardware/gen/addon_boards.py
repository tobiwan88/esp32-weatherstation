"""Qwiic add-on boards for the sensor chain (2026-11-04): schematic, bom.csv and net check, one board per run.

Each board is one link of the outdoor I2C chain that starts at main-board J3 and runs through the SHT45 head: J1 = Qwiic
in, J2 = Qwiic out (wired 1:1), one sensor with its decoupling, an M3 hole. Same connector part (C160404), same base
layout and pin order as the SHT45 head (1 GND, 2 VDD, 3 SDA, 4 SCL), so the boards chain in any order. No pull-ups on the
add-ons: the 10k pull-ups on 3V3_SW are on the main board (R50/R51). Supply 3V3_SW (3.32 V), off between measurements.

Boards:
- bmp585: barometric pressure, Bosch BMP585 (BST-BMP585-DS003-02 rev 1.2). I2C mode: CSB to VDDIO (section 6.2.3),
  SDO low = address 0x46 (section 5.6, "SDO must not be floating"). VDD and VDDIO both 100 nF (figure 25). INT unused.
- veml6030: ambient light, Vishay VEML6030 (doc. 84366 rev 1.8). ADDR low = 0x10; 100 nF at VDD (figure 8, the 10R/10 uF
  filter is optional and left out). INT (open drain) unused.
Sensor-bus addresses in use: SHT45 0x44, BMP585 0x46, SCD41 0x62, VEML6030 0x10.
Run: source scripts/kicad-env.sh && uv run --package weatherstation-hardware python hardware/gen/addon_boards.py bmp585
Layout: hardware/gen/addon_pcb.py. Build both: hardware/tools/build_addons.sh
"""

import csv
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import weatherstation_v1  # noqa: E402,F401  (registers the symbol libraries with kicad_sch_api)
from schkit import CELL, Sheet, check_nets, pin_away, root_sheet  # noqa: E402

HW = Path(__file__).resolve().parents[1]
JST = ("Connector_Generic:Conn_01x04", "Connector_JST:JST_SH_SM04B-SRSS-TB_1x04-1MP_P1.00mm_Horizontal", "C160404", "Extended")
C100N = ("Device:C", "100n", "Capacitor_SMD:C_0603_1608Metric", "C14663", "Basic")

BOARDS = {
    "bmp585": dict(
        project="bmp585-board", title="BMP585 pressure add-on (Qwiic)",
        sensor=("weatherstation:BMP585", "BMP585", "weatherstation:BMP585_LGA-8_3.25x3.25mm", "C18184976", "Extended"),
        pins={"8": "VDD", "4": "VDD", "7": "VDD", "1": "SCL", "2": "SDA", "3": "GND", "6": "GND"}, nc=["5"],
        caps=["C1", "C2"], address="0x46",
        note="Bosch BST-BMP585-DS003-02 rev 1.2: I2C mode CSB = VDDIO (6.2.3), SDO low = 0x46 (5.6), 100 nF at VDD and "
             "VDDIO (figure 25). INT not used. No pull-ups here (main board R50/R51)."),
    "veml6030": dict(
        project="veml6030-board", title="VEML6030 light add-on (Qwiic)",
        sensor=("weatherstation:VEML6030", "VEML6030", "weatherstation:Vishay_VEML6030_2x2mm", "C132182", "Extended"),
        pins={"6": "VDD", "5": "SCL", "2": "SDA", "1": "GND", "4": "GND"}, nc=["3"],
        caps=["C1"], address="0x10",
        note="Vishay 84366 rev 1.8 figure 8: 100 nF at VDD (10R/10 uF filter optional, not fitted), ADDR low = 0x10. "
             "INT not used. No pull-ups here (main board R50/R51)."),
}


def parts_and_nets(b: dict) -> tuple[dict, dict]:
    parts = {"U1": b["sensor"]}
    for c in b["caps"]:
        parts[c] = C100N
    parts["J1"] = (JST[0], "CABLE IN (Qwiic order)", *JST[1:])
    parts["J2"] = (JST[0], "CHAIN OUT (Qwiic order)", *JST[1:])
    parts["H1"] = ("Mechanical:MountingHole", "M3", "MountingHole:MountingHole_3.2mm_M3", None, None)
    parts["#FLG1"] = ("power:PWR_FLAG", "PWR_FLAG", None, None, None)
    parts["#FLG2"] = ("power:PWR_FLAG", "PWR_FLAG", None, None, None)
    nets = {n: [("J1", k), ("J2", k)] for n, k in (("GND", "1"), ("VDD", "2"), ("SDA", "3"), ("SCL", "4"))}
    for pin, net in b["pins"].items():
        nets[net].append(("U1", pin))
    for c in b["caps"]:
        nets["VDD"].append((c, "1"))
        nets["GND"].append((c, "2"))
    nets["VDD"].append(("#FLG1", "1"))
    nets["GND"].append(("#FLG2", "1"))
    return parts, nets


def stub(s: Sheet, ref: str, pin: str, net: str, length: float = 2.0) -> None:
    """Short wire from the pin outward, ended by a label (signals) or a power symbol (VDD, GND) pointing the same way."""
    x, y = (v / CELL for v in s.at(ref, pin))
    a = pin_away(s.sch, ref, pin)
    dx, dy = {0: (1, 0), 180: (-1, 0), 90: (0, -1), 270: (0, 1)}[a]
    ex, ey = round(x + dx * length, 2), round(y + dy * length, 2)
    s.wire((ref, pin), (ex, ey))
    if net in ("VDD", "GND"):
        rot = {("VDD", 0): 270, ("VDD", 180): 90, ("GND", 0): 90, ("GND", 180): 270}[(net, a)]
        s.power(net, ex, ey, lib="power:VCC" if net == "VDD" else None, rot=rot)
    else:
        s.label(net, ex, ey, 0 if a == 0 else 180)


def build(key: str, out: Path) -> tuple[Path, dict, dict]:
    b = BOARDS[key]
    parts, nets = parts_and_nets(b)
    out.mkdir(parents=True, exist_ok=True)
    name = b["sensor"][1]
    s = Sheet(name, f"{key}.kicad_sch", parts, "A4", b["note"][:60], project=b["project"], title=b["title"])
    s.frame(10, 18, 70, 50, f"{name} sensor and Qwiic chain", (20, 120, 120), (195, 238, 238))
    s.text(10.5, 20.4, b["note"] + f" Address {b['address']}.", 1.1)
    # connectors (pins right: 4 SCL, 3 SDA, 2 VDD, 1 GND from the top), as on the SHT45 head
    for ref, y in (("J1", 30), ("J2", 40)):
        s.part(ref, 16, y, 180)
        s.tag(ref, reference=(-1.5, -6.4), value=(-1.5, 6.4), just="center")
        for pin, net in (("4", "SCL"), ("3", "SDA"), ("2", "VDD"), ("1", "GND")):
            stub(s, ref, pin, net)
    s.part("U1", 40, 32, 0)
    s.tag("U1", reference=(0, -9.5 if len(b["caps"]) > 1 else -7.0), value=(0, 9.5 if len(b["caps"]) > 1 else 7.0), just="center")
    for pin, net in b["pins"].items():
        stub(s, "U1", pin, net)
    s.no_connect("U1", b["nc"])
    for i, c in enumerate(b["caps"]):  # 100 nF next to the sensor: VDD up, GND down
        x = 56 + 5 * i
        s.part(c, x, 32, 0)
        s.wire((c, "1"), (x, 29))
        s.wire((c, "2"), (x, 35))
        s.power("VDD", x, 29, lib="power:VCC")
        s.power("GND", x, 35)
    fx = 56 + 5 * len(b["caps"])
    s.wire((fx - 5, 29), (fx, 29))
    s.wire((fx - 5, 35), (fx, 35))
    s.part("#FLG1", fx, 29, 0)
    s.part("#FLG2", fx, 35, 180)
    s.part("H1", 64, 45, 0)
    s.text(10, 3, f"{b['title']}: chains behind the SHT45 head on the outdoor sensor bus", 1.5, bold=True)
    root_uuid = str(uuid.uuid5(uuid.NAMESPACE_URL, "root/" + b["project"]))
    sheet_uuid = str(uuid.uuid5(uuid.NAMESPACE_URL, b["project"] + "/sheet/" + name))
    s.save(out, root_uuid, sheet_uuid)
    sd = [dict(name=name, file=f"{key}.kicad_sch", x=10, y=10, w=30, h=12, page="2", uuid=sheet_uuid, pins=[],
               stroke=(20, 120, 120), fill=(195, 238, 238))]
    texts = [(10.5, 12, f"Qwiic add-on: {name}, address {b['address']}. One sheet; layout notes in BOARD.md")]
    path, _ = root_sheet(out, "root", sd, texts, [], [], project=b["project"], title=b["title"])
    return path, parts, nets


def write_bom(path: Path, parts: dict) -> None:
    rows = [["Comment", "Designator", "Footprint", "Quantity", "LCSC Part #", "Class"]]
    for ref, (sym, value, fp, lcsc, cls) in parts.items():
        if not ref.startswith("#") and lcsc:  # H1 (hole) has no part
            rows.append([value, ref, fp, "1", lcsc, cls])
    with path.open("w", newline="") as f:
        csv.writer(f, lineterminator="\n").writerows(rows)


def write_lib_tables(out: Path) -> None:
    """Project symbol/footprint libraries (hardware/gen/lib), so KiCad finds BMP585 and VEML6030 when the board is opened."""
    (out / "sym-lib-table").write_text(
        '(sym_lib_table\n  (version 7)\n  (lib (name "weatherstation")(type "KiCad")(uri "${KIPRJMOD}/../gen/lib/weatherstation.kicad_sym")'
        '(options "")(descr "Project symbols (hardware/gen/build_symbols.py)"))\n)\n')
    (out / "fp-lib-table").write_text(
        '(fp_lib_table\n  (version 7)\n  (lib (name "weatherstation")(type "KiCad")(uri "${KIPRJMOD}/../gen/lib/weatherstation.pretty")'
        '(options "")(descr "Project footprints from maker drawings (hardware/gen/build_footprints.py)"))\n)\n')


if __name__ == "__main__":
    key = sys.argv[1]
    out = HW / BOARDS[key]["project"]
    p, parts, nets = build(key, out)
    write_bom(out / "bom.csv", parts)
    write_lib_tables(out)
    errors = check_nets(p, nets)
    print("\n".join(errors) or f"{p}: nets OK; bom.csv written")
    sys.exit(1 if errors else 0)
