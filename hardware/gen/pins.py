"""Print pin positions (in 2.54 mm cells) and stub directions of one sheet, for writing HAND_ROUTES and placing parts.

Usage: source scripts/kicad-env.sh && uv run --package weatherstation-hardware python hardware/gen/pins.py [--board MODULE] <Sheet> [ref|net ...]
MODULE: weatherstation_v1 (default), power_board, main_board.
Example: ... pins.py --board power_board Battery BAT_N U6
"""

import importlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from boardgen import Generator, pin_direction  # noqa: E402


def main(board: str, sheet: str, want: list[str]) -> None:
    m = importlib.import_module(board)
    g = Generator(m)
    used = {p for pins in m.NETS.values() for p in pins}
    s = g.draw(sheet, g.layout_positions(), used)
    for net, pins in m.NETS.items():
        for ref, pin in pins:
            if m.PARTS[ref][4] == sheet and (not want or ref in want or net in want):
                x, y = s.at(ref, pin)
                print(f"{net:12s} {ref}.{pin:5s} cell ({x / 2.54:.2f}, {y / 2.54:.2f}) dir {int(pin_direction(s, ref, pin))}")


if __name__ == "__main__":
    args = sys.argv[1:]
    board = "weatherstation_v1"
    if args[:1] == ["--board"]:
        board, args = args[1], args[2:]
    if not args:
        sys.exit(__doc__)
    main(board, args[0], args[1:])
