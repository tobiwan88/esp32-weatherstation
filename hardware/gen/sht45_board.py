"""SHT45 outdoor T/RH board (sensor option A, 2026-11-01): a small PCB in the radiation shield, cable to J3 of the main board.

Circuit = Sensirion SHT4x datasheet v7.3 figure 1: 100 nF on VDD; the 10k I2C pull-ups sit on the main board (R50/R51 on
3V3_SW). Connector order = Qwiic / main board J3: 1 GND, 2 VDD, 3 SDA, 4 SCL. SHT4x pins (datasheet 5.4): 1 SDA, 2 SCL,
3 VDD, 4 VSS; die pad not connected and not soldered (footprint without central pad).
Run: source scripts/kicad-env.sh && uv run --package weatherstation-hardware python hardware/gen/sht45_board.py
"""

import csv
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import weatherstation_v1  # noqa: E402,F401  (registers the symbol libraries with kicad_sch_api)
from schkit import Sheet, check_nets, root_sheet  # noqa: E402

PROJECT, TITLE = "sht45-board", "SHT45 outdoor T/RH board"
OUT = Path(__file__).resolve().parents[1] / "sht45-board"

PARTS = {  # ref: (symbol, value, footprint, LCSC, class)
    # SHT45-AD1F: with PTFE membrane (filter cap) against dust and water, for outdoor use and conformal coating
    "U1": ("Sensor_Humidity:SHT4x", "SHT45-AD1F-R2", "Sensor_Humidity:Sensirion_DFN-4_1.5x1.5mm_P0.8mm_SHT4x_NoCentralPad",
           "C5360602", "Extended"),
    "C1": ("Device:C", "100n", "Capacitor_SMD:C_0603_1608Metric", "C14663", "Basic"),
    "J1": ("Connector_Generic:Conn_01x04", "CABLE (Qwiic order)",
           "Connector_JST:JST_SH_SM04B-SRSS-TB_1x04-1MP_P1.00mm_Horizontal", "C160404", "Extended"),
    "#FLG1": ("power:PWR_FLAG", "PWR_FLAG", None, None, None),
    "#FLG2": ("power:PWR_FLAG", "PWR_FLAG", None, None, None),
}
NETS = {
    "SDA": [("J1", "3"), ("U1", "1")],
    "SCL": [("J1", "4"), ("U1", "2")],
    "VDD": [("J1", "2"), ("U1", "3"), ("C1", "1"), ("#FLG1", "1")],
    "GND": [("J1", "1"), ("U1", "4"), ("C1", "2"), ("#FLG2", "1")],
}


def build(out: Path) -> Path:
    out.mkdir(parents=True, exist_ok=True)
    s = Sheet("SHT45", "sht45.kicad_sch", PARTS, "A4", "SHT45 sensor, 100 nF, cable connector", project=PROJECT, title=TITLE)
    s.frame(10, 18, 56, 40, "SHT45 outdoor sensor", (20, 120, 120), (195, 238, 238))
    s.text(10.5, 20.4, "Sensirion SHT4x datasheet v7.3 figure 1: 100 nF on VDD; I2C pull-ups 10k on the main board (R50/R51). "
                       "J1 = Qwiic order like main-board J3. Address 0x44", 1.1)
    s.part("J1", 16, 31, 180)            # pins right: 4 SCL (y 29), 3 SDA (30), 2 VDD (31), 1 GND (32)
    s.tag("J1", reference=(-1.5, -6.4), value=(-1.5, 6.4), just="center")
    s.part("U1", 40, 30, 0)              # 2 SCL (37, 29), 1 SDA (37, 31), 3 VDD top (41, 27), 4 VSS bottom (41, 33)
    s.part("C1", 46, 30, 0)              # 1 top (46, 28.5), 2 bottom (46, 31.5)
    s.wire(("J1", "4"), ("U1", "2"))
    s.wire(("J1", "3"), (34, 30), (34, 31), ("U1", "1"))
    s.wire(("U1", "3"), (41, 25), (46, 25), ("C1", "1"))
    s.wire(("U1", "4"), (41, 35), (46, 35), ("C1", "2"))
    s.power("VDD", 41, 25, lib="power:VCC")
    s.power("GND", 41, 35)
    s.wire(("J1", "2"), (20, 31))
    s.wire(("J1", "1"), (20, 32))
    s.power("VDD", 20, 31, lib="power:VCC", rot=270)
    s.power("GND", 20, 32, rot=90)
    s.part("#FLG1", 46, 25, 0)
    s.part("#FLG2", 46, 35, 180)
    s.label("SDA", 26, 30, 0)
    s.label("SCL", 26, 29, 0)
    s.text(10, 3, f"{TITLE}: SHT45-AD1F (membrane) in the radiation shield, cable to main-board J3", 1.5, bold=True)
    root_uuid = str(uuid.uuid5(uuid.NAMESPACE_URL, "root/" + PROJECT))
    sheet_uuid = str(uuid.uuid5(uuid.NAMESPACE_URL, PROJECT + "/sheet/SHT45"))
    s.save(out, root_uuid, sheet_uuid)
    sd = [dict(name="SHT45", file="sht45.kicad_sch", x=10, y=10, w=30, h=12, page="2", uuid=sheet_uuid, pins=[],
               stroke=(20, 120, 120), fill=(195, 238, 238))]
    texts = [(10.5, 12, "Outdoor T/RH sensor board. One sheet; see BOARD.md for the layout rules (slits, no copper near the sensor)")]
    path, _ = root_sheet(out, "root", sd, texts, [], [], project=PROJECT, title=TITLE)
    return path


def write_bom(path: Path) -> None:
    rows = [["Comment", "Designator", "Footprint", "Quantity", "LCSC Part #", "Class"]]
    for ref, (sym, value, fp, lcsc, cls) in PARTS.items():
        if not ref.startswith("#"):
            rows.append([value, ref, fp, "1", lcsc, cls])
    with path.open("w", newline="") as f:
        csv.writer(f, lineterminator="\n").writerows(rows)


if __name__ == "__main__":
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else OUT
    p = build(out)
    write_bom(out / "bom.csv")
    errors = check_nets(p, NETS)
    print("\n".join(errors) or f"{p}: nets OK; bom.csv written")
    sys.exit(1 if errors else 0)
