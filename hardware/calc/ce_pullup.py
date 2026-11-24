"""Charger CE pull-up check across a two-board split: one pull-up to the cell (charger board), one to the host's 3.3 V
rail (host board), the host GPIO on the same net. Inputs: board.yaml `design.ce_pullup` of the charger board.

Cases (each row: OK / WARN / FAIL with the numbers used):
  1. charger board alone: CE = BAT - I_leak x R_bat; lowest BAT that still reads high (VIH) with the maximum CE leakage
  2. both boards, host rail up, GPIO released: CE = (V3V3/R_host + BAT/R_bat) / (1/R_host + 1/R_bat), at the highest
     regulated BAT (FAIL above the GPIO abs max, WARN within 50 mV) and at the protection trip (printed); the current
     back into the GPIO when it drives high is printed
  3. both boards, host rail dead (0 V), GPIO unpowered: CE = BAT x R_host / (R_host + R_bat) - I_leak x (R_host || R_bat);
     lowest BAT that reads high, against the protection IC's overdischarge level (FAIL if CE is undefined above it).
     Not modelled: the host GPIO's ESD diode to its dead supply rail (WARN row; a bench check)
  4. CE held low by the GPIO in sleep: V/R through each pull-up (power_budget.py sleep loads must match)
Sources: VIH and leakage from the charger datasheet (profile `source`), the GPIO abs max from the MCU datasheet.
Usage: python3 hardware/calc/ce_pullup.py hardware/<board> [--selftest]
"""

import sys
from pathlib import Path

import yaml


def run(c: dict) -> list:
    rows = []
    v = {}
    for k in ("r_bat_ohm", "r_host_ohm", "v_host", "vih_v", "leak_ua", "bat_min_v", "bat_max_v", "bat_ovp_v", "bat_sleep_v",
              "gpio_abs_max_v", "protect_v"):
        item = c.get(k) or {}
        if item.get("value") is None:
            rows.append(("MISSING", k, "value is null in board.yaml"))
        elif not item.get("source"):
            rows.append(("WARN", k, f"{item['value']} has no source"))
        v[k] = item.get("value")
    if any(x is None for x in v.values()):
        return rows
    rb, rh, vh, vih, il = v["r_bat_ohm"], v["r_host_ohm"], v["v_host"], v["vih_v"], v["leak_ua"] * 1e-6
    # 1: charger board alone
    b1 = vih + il * rb
    rows.append(("OK" if b1 <= v["protect_v"] else "WARN", "charger board alone",
                 f"CE = BAT - {il * 1e6:.1f} uA x {rb / 1e3:.0f}k: high (>= VIH {vih} V) for BAT >= {b1:.2f} V "
                 f"(no leakage: {vih:.2f} V); protection floor {v['protect_v']} V"))
    # 2: both boards, host rail up, GPIO released
    g = 1 / rh + 1 / rb
    ce_hi = (vh / rh + v["bat_max_v"] / rb) / g
    ce_lo = (vh / rh + v["bat_min_v"] / rb) / g - il / g
    ce_ovp = (vh / rh + v["bat_ovp_v"] / rb) / g
    st = "OK" if ce_hi <= v["gpio_abs_max_v"] - 0.05 else ("WARN" if ce_hi <= v["gpio_abs_max_v"] else "FAIL")
    rows.append((st, "both boards, host rail up, GPIO released",
                 f"CE {ce_lo:.2f} V (BAT {v['bat_min_v']} V, leakage) to {ce_hi:.2f} V (BAT {v['bat_max_v']} V, highest regulated), "
                 f"{ce_ovp:.2f} V at the protection trip (BAT {v['bat_ovp_v']} V); GPIO abs max {v['gpio_abs_max_v']} V "
                 f"(open-circuit values: the pad clamp takes at most {(v['bat_ovp_v'] - vh) / rb * 1e6:.1f} uA); "
                 f"GPIO driving high instead: CE = {vh} V, {(v['bat_max_v'] - vh) / rb * 1e6:.1f} uA from BAT into the pin"))
    # 3: both boards, host rail dead
    k = rh / (rh + rb)
    rpar = 1 / g
    b3 = vih / k
    b3l = (vih + il * rpar) / k
    st = "OK" if b3l <= v["protect_v"] else ("WARN" if b3 <= v["protect_v"] else "FAIL")
    rows.append((st, "both boards, host rail dead",
                 f"CE = {k:.3f} x BAT: high for BAT >= {b3:.2f} V, {b3l:.2f} V with {il * 1e6:.1f} uA leakage through "
                 f"{rpar / 1e3:.0f}k; protection floor {v['protect_v']} V"))
    rows.append(("WARN", "host GPIO clamp (not modelled)",
                 f"an unpowered MCU pad clamps CE through its ESD diode to the dead rail; up to {v['bat_max_v'] / rb * 1e6:.1f} uA "
                 "flows into that rail and CE may sit near the rail voltage + one diode: measure CE with +3V3 off"))
    # 4: CE held low in sleep
    rows.append(("OK", "CE held low (sleep)", f"host pull-up {vh / rh * 1e6:.1f} uA on the 3.3 V rail, charger pull-up "
                 f"{v['bat_sleep_v'] / rb * 1e6:.2f} uA at the cell (BAT {v['bat_sleep_v']} V; {v['bat_max_v'] / rb * 1e6:.1f} uA at "
                 f"{v['bat_max_v']} V)"))
    return rows


def selftest() -> bool:
    s = {k: {"value": x, "source": "x"} for k, x in dict(r_bat_ohm=330e3, r_host_ohm=1e6, v_host=3.3, vih_v=1.3, leak_ua=1,
                                                      bat_min_v=2.1, bat_max_v=3.685, bat_ovp_v=3.75, bat_sleep_v=3.2, gpio_abs_max_v=3.6,
                                                      protect_v=2.1).items()}
    r = {x[1]: x for x in run(s)}
    # 330k / (1M + 330k) -> CE = 0.752 x BAT; 1.3 / 0.752 = 1.73 V; with 1 uA x 248k: 1.548 / 0.752 = 2.06 V
    ok3 = "BAT >= 1.73 V" in r["both boards, host rail dead"][2] and "2.06 V" in r["both boards, host rail dead"][2]
    # (3.3/1M + 3.685/330k) / (1/1M + 1/330k) = 3.590 V: within 0.05 V of 3.6 -> WARN; at 3.75 V: 3.638 V
    row2 = r["both boards, host rail up, GPIO released"]
    ok2 = row2[0] == "WARN" and "3.59 V" in row2[2] and "3.64 V" in row2[2]
    return ok2 and ok3


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        print("ce_pullup selftest:", "OK" if selftest() else "FAILED")
        sys.exit(0 if selftest() else 1)
    board = Path(sys.argv[1])
    rows = run(yaml.safe_load((board / "board.yaml").read_text()).get("design", {}).get("ce_pullup", {}))
    bad = False
    for st, name, detail in rows:
        bad |= st == "FAIL"
        print(f"{st:8} {name}: {detail}")
    print("ce_pullup:", "FAILED" if bad else "OK")
    sys.exit(1 if bad else 0)
