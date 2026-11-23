"""Track width per net class from its current (IPC-2221 curve fit, outer layer).

Reads board.yaml: `stackup.copper_mm`, `net_classes.<name>.track_mm` and `current_a`, `layout.temp_rise_c`.
A class without `current_a` is skipped (signal classes). Exit 1 if a class is narrower than the curve asks for.
IPC-2221 (section 6.2, figure 6-4 curve fit): I = k * dT^0.44 * A^0.725, A in square mils, k = 0.048 outer layers.
Usage: python3 hardware/calc/track_width.py hardware/<board> [--selftest]
"""

import sys
from pathlib import Path

import yaml

K_OUTER = 0.048
MIL = 0.0254  # mm


def min_width_mm(current_a: float, copper_mm: float, rise_c: float) -> float:
    area_mil2 = (current_a / (K_OUTER * rise_c**0.44)) ** (1 / 0.725)
    return area_mil2 / (copper_mm / MIL) * MIL


def check(prof: dict) -> list[tuple[str, str, str]]:
    cu = prof["stackup"]["copper_mm"]
    rise = prof["layout"]["temp_rise_c"]
    rows = []
    for name, c in prof["net_classes"].items():
        if "current_a" not in c:
            continue
        need = min_width_mm(c["current_a"], cu, rise)
        ok = c["track_mm"] >= need
        rows.append(("OK" if ok else "FAIL", f"net class {name}",
                     f"{c['track_mm']} mm for {c['current_a']} A (IPC-2221 outer, {rise} C rise: min {need:.2f} mm)"))
    return rows


def selftest() -> None:
    # 1 A, 1 oz (0.035 mm), 10 C rise: about 0.30 mm (IPC-2221 calculators give 11.8 mil = 0.30 mm)
    w = min_width_mm(1.0, 0.035, 10)
    assert 0.28 < w < 0.32, w
    print("track_width selftest OK")


def main() -> None:
    if "--selftest" in sys.argv:
        selftest()
        return
    board = Path(sys.argv[1])
    prof = yaml.safe_load((board / "board.yaml").read_text())
    rows = check(prof)
    for r in rows:
        print(*r, sep="  ")
    fail = any(r[0] == "FAIL" for r in rows)
    print("track widths:", "FAILED" if fail else "OK")
    sys.exit(1 if fail else 0)


if __name__ == "__main__":
    main()
