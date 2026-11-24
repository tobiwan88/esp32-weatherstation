"""Indicator LED current and brightness from the board profile (board.yaml `design.leds`), one row per LED group.

I = (V_drive - Vf) / R, evaluated at the lowest Vf (forward-voltage curve at the operating current: highest current)
and at the highest Vf (datasheet maximum, specified at the test current: lowest current). FAIL above the LED's DC
maximum or the GPIO's drive limit; WARN below `i_min_ma` (too dim to be useful). Luminous intensity scales linearly
with current below the test current (datasheet relative-intensity curve, profile `source`): printed for the typical
and the minimum bin.
Usage: python3 hardware/calc/led_current.py hardware/<board> [--selftest]
"""

import sys
from pathlib import Path

import yaml

KEYS = ("v_drive", "r_ohm", "vf_low_v", "vf_max_v", "if_test_ma", "if_max_ma", "gpio_max_ma", "i_min_ma", "iv_typ_mcd", "iv_min_mcd")


def run(leds: dict) -> list:
    rows = []
    for name, g in leds.items():
        v = {}
        for k in KEYS:
            item = g.get(k) or {}
            if item.get("value") is None:
                rows.append(("MISSING", f"{name}.{k}", "value is null in board.yaml"))
            elif not item.get("source"):
                rows.append(("WARN", f"{name}.{k}", f"{item['value']} has no source"))
            v[k] = item.get("value")
        if any(x is None for x in v.values()):
            continue
        hi = (v["v_drive"] - v["vf_low_v"]) / v["r_ohm"] * 1000
        lo = (v["v_drive"] - v["vf_max_v"]) / v["r_ohm"] * 1000
        lim = min(v["if_max_ma"], v["gpio_max_ma"])
        st = "FAIL" if hi > lim else ("WARN" if lo < v["i_min_ma"] else "OK")
        k = 1 / v["if_test_ma"]
        rows.append((st, f"{name} current", f"{lo:.2f}-{hi:.2f} mA through {v['r_ohm']:g} ohm from {v['v_drive']} V "
                     f"(Vf {v['vf_max_v']}-{v['vf_low_v']} V); limit {lim} mA, useful above {v['i_min_ma']} mA; "
                     f"{', '.join(g.get('refs', []))}"))
        rows.append(("OK", f"{name} brightness", f"about {v['iv_typ_mcd'] * lo * k:.1f}-{v['iv_typ_mcd'] * hi * k:.1f} mcd typical, "
                     f"{v['iv_min_mcd'] * lo * k:.1f} mcd for the lowest bin (linear from {v['iv_typ_mcd']}/{v['iv_min_mcd']} mcd at "
                     f"{v['if_test_ma']} mA)"))
    return rows


def selftest() -> bool:
    g = {k: {"value": x, "source": "x"} for k, x in dict(v_drive=3.3, r_ohm=1000, vf_low_v=1.8, vf_max_v=2.4, if_test_ma=20,
                                                      if_max_ma=30, gpio_max_ma=20, i_min_ma=0.5, iv_typ_mcd=54,
                                                      iv_min_mcd=18).items()}
    r = {x[1]: x for x in run({"led": g})}
    # (3.3 - 2.4) / 1k = 0.90 mA, (3.3 - 1.8) / 1k = 1.50 mA; 54 x 0.9 / 20 = 2.43 mcd, 54 x 1.5 / 20 = 4.05 mcd (prints 4.0)
    return r["led current"][0] == "OK" and "0.90-1.50 mA" in r["led current"][2] and "2.4-4.0 mcd" in r["led brightness"][2]


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        print("led_current selftest:", "OK" if selftest() else "FAILED")
        sys.exit(0 if selftest() else 1)
    board = Path(sys.argv[1])
    rows = run(yaml.safe_load((board / "board.yaml").read_text()).get("design", {}).get("leds", {}))
    bad = False
    for st, name, detail in rows:
        bad |= st == "FAIL"
        print(f"{st:8} {name}: {detail}")
    print("led_current:", "FAILED" if bad else "OK")
    sys.exit(1 if bad else 0)
