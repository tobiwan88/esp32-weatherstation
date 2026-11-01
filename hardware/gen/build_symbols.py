"""Writes the project symbol library hardware/gen/lib/weatherstation.kicad_sym (parts missing from the KiCad libraries).

Pin numbers and names come from the datasheets (TPS63802 DLA: TI SLVSEU9D table 7-1; HY2112-CB: HYCON DS-HY2112 V08 table 2).
Run: python3 hardware/gen/build_symbols.py
"""

from pathlib import Path

OUT = Path(__file__).resolve().parent / "lib" / "weatherstation.kicad_sym"
PITCH, PIN_LEN, HALF_W = 2.54, 2.54, 7.62


def pin(etype, name, number, side, y):
    x, ang = (-(HALF_W + PIN_LEN), 0) if side == "L" else (HALF_W + PIN_LEN, 180)
    return (f'\t\t(pin {etype} line (at {x:.2f} {y:.2f} {ang}) (length {PIN_LEN})\n'
            f'\t\t\t(name "{name}" (effects (font (size 1.016 1.016))))\n'
            f'\t\t\t(number "{number}" (effects (font (size 1.016 1.016)))))')


def symbol(name, value, footprint, datasheet, rows, half_h):
    pins = []
    for side, items in rows.items():
        n = len(items)
        for i, (etype, pname, num) in enumerate(items):
            y = (n - 1) * PITCH / 2 - i * PITCH
            pins.append(pin(etype, pname, num, side, y))
    body = (f'\t\t(rectangle (start {-HALF_W} {half_h}) (end {HALF_W} {-half_h})\n'
            f'\t\t\t(stroke (width 0.254) (type default)) (fill (type background)))')
    prop = lambda k, v, y, hide="": (f'\t\t(property "{k}" "{v}" (at 0 {y} 0)\n'
                                     f'\t\t\t(effects (font (size 1.27 1.27)){hide}))')
    return "\n".join([
        f'\t(symbol "{name}" (pin_names (offset 1.016)) (in_bom yes) (on_board yes)',
        prop("Reference", "U", half_h + 1.5),
        prop("Value", value, -half_h - 1.5),
        prop("Footprint", footprint, 0, " (hide yes)"),
        prop("Datasheet", datasheet, 0, " (hide yes)"),
        f'\t\t(symbol "{name}_0_1"', body, "\t\t)",
        f'\t\t(symbol "{name}_1_1"', *pins, "\t\t)",
        "\t)"])


TPS63802 = symbol(
    "TPS63802DLA", "TPS63802DLA", "Package_SON:WSON-10-1EP_2x3mm_P0.5mm_EP0.84x2.4mm",
    "https://www.ti.com/lit/ds/symlink/tps63802.pdf",
    {"L": [("power_in", "VIN", "10"), ("input", "EN", "1"), ("input", "MODE", "2"),
           ("power_in", "AGND", "3"), ("power_in", "GND", "8")],
     "R": [("power_out", "VOUT", "6"), ("passive", "L1", "9"), ("passive", "L2", "7"),
           ("input", "FB", "4"), ("open_collector", "PG", "5")]},
    6.35)

HY2112 = symbol(
    "HY2112-CB", "HY2112-CB", "Package_TO_SOT_SMD:SOT-23-6",
    "https://www.hycontek.com/wp-content/uploads/DS-HY2112_EN.pdf",
    {"L": [("power_in", "VDD", "5"), ("power_in", "VSS", "6")],
     "R": [("output", "OD", "1"), ("input", "CS", "2"), ("output", "OC", "3"), ("no_connect", "NC", "4")]},
    6.35)

LIB = ('(kicad_symbol_lib (version 20231120) (generator "weatherstation_build_symbols") (generator_version "1.0")\n'
       + "\n".join([TPS63802, HY2112]) + "\n)\n")

if __name__ == "__main__":
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(LIB)
    print("wrote", OUT)
