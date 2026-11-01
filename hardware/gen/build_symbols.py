"""Writes the project symbol library hardware/gen/lib/weatherstation.kicad_sym (parts missing from the KiCad libraries).

Pin numbers and names come from the datasheets (TPS63802 DLA: TI SLVSEU9D table 7-1; HY2112-CB: HYCON DS-HY2112 V08 table 2;
TPS61023 DRL: TI SLVSF14B section 5).
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
    "TPS63802DLA", "TPS63802DLA", "weatherstation:TPS63802_DLA_VSON-HR-10_2x3mm",
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

TPS61023 = symbol(  # TI SLVSF14B section 5 (DRL, SOT563): 1 FB, 2 EN, 3 VIN, 4 GND, 5 SW, 6 VOUT
    "TPS61023DRL", "TPS61023DRLR", "Package_TO_SOT_SMD:SOT-563",
    "https://www.ti.com/lit/ds/symlink/tps61023.pdf",
    {"L": [("power_in", "VIN", "3"), ("input", "EN", "2"), ("power_in", "GND", "4")],
     "R": [("passive", "SW", "5"), ("power_out", "VOUT", "6"), ("input", "FB", "1")]},
    5.08)

def cmc(name, value, footprint, datasheet):
    """2-line common-mode choke: both windings left to right, inputs 1 (top) and 4 (bottom) on the left, outputs 2 and 3
    on the right (EMTEK CMF4532F: winding A 1 -> 2, winding B 4 -> 3). Coils bulge outward from a two-line core."""
    arcs = []
    for y, s in ((2.54, 1), (-2.54, -1)):
        for k in range(4):
            x0 = -2.54 + 1.27 * k
            arcs.append(f'\t\t(arc (start {x0 + 1.27:.3f} {y:.3f}) (mid {x0 + 0.635:.3f} {y + s * 0.635:.3f}) (end {x0:.3f} {y:.3f})\n'
                        '\t\t\t(stroke (width 0.254) (type default)) (fill (type none)))')
    core = [f'\t\t(polyline (pts (xy -2.54 {y}) (xy 2.54 {y})) (stroke (width 0.254) (type default)) (fill (type none)))'
            for y in (0.508, -0.508)]
    dots = [f'\t\t(circle (center -2.286 {y}) (radius 0.254) (stroke (width 0) (type default)) (fill (type outline)))'
            for y in (3.81, -1.27)]
    def p(num, pname, x, y, ang):
        return (f'\t\t(pin passive line (at {x} {y} {ang}) (length 2.54)\n'
                f'\t\t\t(name "{pname}" (effects (font (size 1.016 1.016))))\n'
                f'\t\t\t(number "{num}" (effects (font (size 1.016 1.016)))))')
    pins = [p("1", "1", -5.08, 2.54, 0), p("4", "4", -5.08, -2.54, 0), p("2", "2", 5.08, 2.54, 180), p("3", "3", 5.08, -2.54, 180)]
    prop = lambda k, v, y, hide="": (f'\t\t(property "{k}" "{v}" (at 0 {y} 0)\n'
                                     f'\t\t\t(effects (font (size 1.27 1.27)){hide}))')
    return "\n".join([
        f'\t(symbol "{name}" (pin_names hide) (in_bom yes) (on_board yes)',
        prop("Reference", "L", 5.5), prop("Value", value, -5.5),
        prop("Footprint", footprint, 0, " (hide yes)"), prop("Datasheet", datasheet, 0, " (hide yes)"),
        f'\t\t(symbol "{name}_0_1"', *arcs, *core, *dots, "\t\t)",
        f'\t\t(symbol "{name}_1_1"', *pins, "\t\t)", "\t)"])


CMC = cmc("CMC_2line", "CMC", "weatherstation:CMF4532F_4P", "")

LIB = ('(kicad_symbol_lib (version 20231120) (generator "weatherstation_build_symbols") (generator_version "1.0")\n'
       + "\n".join([TPS63802, HY2112, TPS61023, CMC]) + "\n)\n")

if __name__ == "__main__":
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(LIB)
    print("wrote", OUT)
