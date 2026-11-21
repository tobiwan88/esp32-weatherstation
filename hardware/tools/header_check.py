"""Mating-error check of the board-to-board header J10 (J_PWR) from boards_common (HEADER_PINS, HEADER_KEY, HEADER_COLS).

Model (hardware/ARCHITECTURE.md, J10): a 2-row 2.54 mm header, both footprints identical and unmirrored on F.Cu. The
main board carries the male pins with pin HEADER_KEY pulled out; the power board carries the socket with that hole
blocked. Pin n sits in column (n + 1) // 2, row A (odd) or B (even). A mating error maps each main-board pin position
p to a power-board hole T(p):
  - orientation: as designed, rotated 180 deg, mirrored about the long axis (rows swapped), mirrored about the short
    axis (columns reversed); a mirror needs one board flipped or a mirrored footprint, checked anyway
  - offset on an unshrouded header: shifted by -1/0/+1 column and -1/0/+1 row (a pin off the grid hangs free)
Each error is BLOCKED when a present main-board pin meets the blocked hole (the plug cannot go in). Otherwise every
engaged pin pair is classified: SYS or USB_VBUS on a signal pin (ESP32 GPIO, charger pin, USB data) = FAIL; SYS or
USB_VBUS on GND or on each other = WARN (a short the charger's SYS short protection, HY2112 short detection or the USB
source limits; no signal pin sees a supply); anything else OK.
Rows OK / WARN / FAIL; last line `header_check: OK|FAILED`; exit 1 on FAIL. No KiCad needed (reads boards_common only).
Usage: python3 -I hardware/tools/header_check.py [--selftest] [-v]
"""

import importlib
import sys
from pathlib import Path

GEN = Path(__file__).resolve().parents[1] / "gen"
POWER = {"SYS", "USB_VBUS"}


def pos(n: int) -> tuple[int, int]:
    return (n + 1) // 2, (n + 1) % 2  # (column 1.., row 0 = A odd, 1 = B even)


def pin(c: int, r: int) -> int:
    return 2 * c - 1 + r


ORIENT = {
    "as designed": lambda c, r, n: (c, r),
    "rotated 180": lambda c, r, n: (n + 1 - c, 1 - r),
    "mirrored, rows swapped": lambda c, r, n: (c, 1 - r),
    "mirrored, columns reversed": lambda c, r, n: (n + 1 - c, r),
}


def mate(pins: dict, key: int, cols: int, orient: str, dc: int, dr: int) -> tuple[str, list[str]]:
    """Result of one mating error: ('BLOCKED' | 'OK' | 'WARN' | 'FAIL', details)."""
    engaged = []
    for p in range(1, 2 * cols + 1):
        if p == key:
            continue  # pulled pin on the main board
        c, r = ORIENT[orient](*pos(p), cols)
        c, r = c + dc, r + dr
        if not (1 <= c <= cols and 0 <= r <= 1):
            continue  # hangs free
        hole = pin(c, r)
        if hole == key:
            return "BLOCKED", [f"main pin {p} meets the blocked hole {key}"]
        engaged.append((p, hole))
    worst, notes = "OK", []
    for p, hole in engaged:
        a, b = pins[str(p)], pins[str(hole)]
        if a == b:
            continue
        pair = {a, b}
        if pair & POWER:
            other = (pair - POWER) or pair
            if other <= POWER | {"GND"}:
                worst = "WARN" if worst == "OK" else worst
                notes.append(f"main {p} {a} on power {hole} {b} (short)")
            else:
                worst = "FAIL"
                notes.append(f"main {p} {a} on power {hole} {b} (supply on a signal pin)")
    return worst, notes


def check(pins: dict, key: int, cols: int) -> list[tuple[str, str, str]]:
    rows = []
    assert len(pins) == 2 * cols and str(key) in pins and pins[str(key)] == "KEY", "header map: 2 x cols pins, key marked KEY"
    for orient in ORIENT:
        for dc in (-1, 0, 1):
            for dr in (-1, 0, 1):
                if orient == "as designed" and dc == dr == 0:
                    continue
                st, notes = mate(pins, key, cols, orient, dc, dr)
                name = f"{orient}, shift {dc:+d} col {dr:+d} row"
                rows.append(("OK" if st == "BLOCKED" else st, name, "; ".join(notes[:4]) if st != "OK" or notes else "engages, power-safe"))
    st, _ = mate(pins, -1, cols, "as designed", 0, 0)
    blocked = sum(1 for _, _, d in rows if "blocked hole" in d)
    rows.append(("OK" if blocked else "FAIL", "key", f"pin {key} removed, hole blocked: {blocked} of {len(rows)} mating errors cannot mate"))
    return rows


def selftest() -> bool:
    # 2 x 2: SYS on 1, key on 4. Rotation maps pin 1 to hole 4: blocked. Rows swapped: pin 3 (SIG) lands on hole 4: blocked.
    pins = {"1": "SYS", "2": "GND", "3": "SIG", "4": "KEY"}
    ok = mate(pins, 4, 2, "rotated 180", 0, 0)[0] == "BLOCKED"
    ok &= mate(pins, 4, 2, "mirrored, rows swapped", 0, 0)[0] == "BLOCKED"
    # columns reversed: pin 1 SYS -> hole 3 SIG, pin 2 GND -> hole 4 KEY: blocked anyway
    ok &= mate(pins, 4, 2, "mirrored, columns reversed", 0, 0)[0] == "BLOCKED"
    # shift one column: pin 1 SYS -> hole 3 SIG, pin 2 -> 4 blocked
    ok &= mate(pins, 4, 2, "as designed", 1, 0)[0] == "BLOCKED"
    # no key at all (key -1): rotation puts SYS (1) on hole 4 (SIG in this variant): FAIL
    ok &= mate({"1": "SYS", "2": "GND", "3": "GND", "4": "SIG"}, -1, 2, "rotated 180", 0, 0)[0] == "FAIL"
    return bool(ok)


def main() -> int:
    if "--selftest" in sys.argv:
        ok = selftest()
        print("header_check selftest:", "OK" if ok else "FAILED")
        return 0 if ok else 1
    sys.path.insert(0, str(GEN))
    common = importlib.import_module("boards_common")
    pins = dict(common.HEADER_PINS)
    if str(common.HEADER_KEY) in pins:
        print(f"FAIL     key: pin {common.HEADER_KEY} carries net {pins[str(common.HEADER_KEY)]} (the key pin has no net)")
        print("header_check: FAILED")
        return 1
    pins[str(common.HEADER_KEY)] = "KEY"
    rows = check(pins, common.HEADER_KEY, common.HEADER_COLS)
    bad = any(st == "FAIL" for st, _, _ in rows)
    for st, name, detail in rows:
        if "-v" in sys.argv or st != "OK" or name == "key":
            print(f"{st:8} {name}: {detail}")
    print("header_check:", "FAILED" if bad else "OK")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
