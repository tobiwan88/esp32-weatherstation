"""Print pin positions (in 2.54 mm cells) and stub directions of one sheet, for writing HAND_ROUTES and placing parts.

Usage: source scripts/kicad-env.sh && uv run --package weatherstation-hardware python hardware/gen/pins.py <Sheet> [ref|net ...]
Example: ... pins.py Battery BAT_N U6
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import weatherstation_v1 as w  # noqa: E402


def main(sheet: str, want: list[str]) -> None:
    used = {p for pins in w.NETS.values() for p in pins}
    s = w.draw(sheet, w.layout_positions(), used)
    for net, pins in w.NETS.items():
        for ref, pin in pins:
            if w.PARTS[ref][4] == sheet and (not want or ref in want or net in want):
                x, y = s.at(ref, pin)
                print(f"{net:12s} {ref}.{pin:5s} cell ({x / 2.54:.2f}, {y / 2.54:.2f}) dir {int(w.pin_direction(s, ref, pin))}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2:])
