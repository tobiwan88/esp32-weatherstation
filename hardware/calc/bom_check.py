"""Check a board's BOM (hardware/<board>/bom.csv): fab part numbers, library class, fee estimate, optional live stock.

Rows: OK, WARN, FAIL, MISSING (see hw-base). `--strict` (order time) turns MISSING into FAIL. `--stock` asks the
fab's parts library (hardware/tools/jlcparts.py) for stock and Basic/Extended; needs network.
Fee model: JLCPCB Economic PCBA charges a loading fee per unique Extended part (jlcpcb.com/help/article/pcb-assembly-price);
the fee comes from board.yaml `fab.extended_fee_usd`, never hard-coded here.
Usage: uv run --package weatherstation-hardware python hardware/calc/bom_check.py hardware/<board> [--strict] [--stock] [--qty N]
"""

import argparse
import csv
import re
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent.parent / "tools"))

LCSC = re.compile(r"^C\d{3,}$")
NO_FAB = {"n/a", "na", ""}   # hand-soldered, DNP or pads only: no fab part number by design


def load_rows(board: Path) -> list[dict]:
    with open(board / "bom.csv", newline="") as f:
        return list(csv.DictReader(f))


def check(rows: list[dict], profile: dict, qty: int, stock: dict | None = None):
    fee = (profile.get("fab") or {}).get("extended_fee_usd")
    out, extended = [], set()
    for r in rows:
        ref, lcsc = r["Designator"], (r["LCSC Part #"] or "").strip()
        name = f"{ref} {r['Comment']}"
        cls = (r.get("Class") or "").lower()
        if lcsc.lower() in NO_FAB:
            out.append(("OK", name, f"no fab part number by design ({r.get('Status', '')})"))
            continue
        if lcsc.upper() == "TBD":
            out.append(("MISSING", name, "LCSC number still TBD: pick it in the fab parts search"))
            continue
        if not LCSC.match(lcsc):
            out.append(("FAIL", name, f"'{lcsc}' is not an LCSC number"))
            continue
        if "extended" in cls and "?" not in cls:
            extended.add(lcsc)
        note = "" if "verified" in r.get("Status", "").lower() else " (status not VERIFIED)"
        status = "OK" if not note else "WARN"
        if "?" in cls or "check" in cls:
            status, note = "WARN", note + " (Basic/Extended class unconfirmed)"
        need = int(r["Quantity"]) * qty
        if stock and lcsc in stock:
            s = stock[lcsc]
            if s["stock"] < need:
                status, note = "FAIL", note + f" stock {s['stock']} < need {need}"
            elif s["stock"] < 2 * need:
                status, note = "WARN", note + f" LOW STOCK {s['stock']} (need {need})"
            lib = s["library"] + (" (preferred)" if s.get("preferred") else "")
            note += f" [{lib}, stock {s['stock']}]"
            if s["library"] == "Extended" and not s.get("preferred"):
                extended.add(lcsc)
            elif lcsc in extended:
                extended.discard(lcsc)
        out.append((status, name, f"{lcsc}{note}"))
    if fee is None:
        out.append(("MISSING", "extended-part fee", "board.yaml fab.extended_fee_usd is null"))
    else:
        out.append(("OK", "extended-part fee", f"{len(extended)} unique Extended parts x ${fee} = ${len(extended) * fee:.2f} (Economic PCBA)"))
    return out


def selftest() -> bool:
    rows = [
        {"Comment": "a", "Designator": "R1", "LCSC Part #": "C25804", "Quantity": "1", "Class": "Basic", "Status": "VERIFIED"},
        {"Comment": "b", "Designator": "U1", "LCSC Part #": "C2913198", "Quantity": "1", "Class": "Extended", "Status": "VERIFIED"},
        {"Comment": "c", "Designator": "U2", "LCSC Part #": "C16581", "Quantity": "1", "Class": "Extended", "Status": "VERIFIED"},
        {"Comment": "d", "Designator": "R2", "LCSC Part #": "TBD", "Quantity": "1", "Class": "?", "Status": "NOT FOUND"},
        {"Comment": "e", "Designator": "J7", "LCSC Part #": "n/a", "Quantity": "1", "Class": "n/a", "Status": "HAND-SOLDER"},
    ]
    res = check(rows, {"fab": {"extended_fee_usd": 3.0}}, 5)
    kinds = [r[0] for r in res]
    return kinds == ["OK", "OK", "OK", "MISSING", "OK", "OK"] and "2 unique Extended parts x $3.0 = $6.00" in res[-1][2]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("board", nargs="?")
    ap.add_argument("--strict", action="store_true")
    ap.add_argument("--stock", action="store_true")
    ap.add_argument("--qty", type=int, default=5)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        print("bom_check selftest:", "OK" if selftest() else "FAILED")
        return 0 if selftest() else 1
    board = Path(a.board)
    profile = yaml.safe_load((board / "board.yaml").read_text())
    rows = load_rows(board)
    stock = None
    if a.stock:
        import jlcparts
        codes = sorted({r["LCSC Part #"].strip() for r in rows if LCSC.match(r["LCSC Part #"].strip())})
        stock = {}
        for c in codes:
            hit = [p for p in jlcparts.query(c, 3) if p["lcsc"] == c]
            if hit:
                stock[c] = hit[0]
    res = check(rows, profile, a.qty, stock)
    bad = False
    for st, name, detail in res:
        if st == "MISSING" and a.strict:
            st = "FAIL"
        bad |= st == "FAIL"
        print(f"{st:8} {name}: {detail}")
    print("bom_check:", "FAILED" if bad else "OK")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
