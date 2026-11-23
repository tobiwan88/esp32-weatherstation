"""I2C bus and pulse-port checks from a board profile (board.yaml `design.i2c_bus` and `design.pulse_port`).

I2C (NXP UM10204 rev 7, table 10 and section 7.1):
  bus capacitance Cb = PCB traces + cable (pF/m x length) + sum of device pin capacitances (ESD parts included)
  rise time (30 % to 70 %) tr = 0.8473 x Rp x Cb, limit 1000 ns at 100 kHz (standard mode), 300 ns at 400 kHz
  minimum pull-up Rp_min = (VDD - VOL) / IOL with VOL 0.4 V, IOL 3 mA; external module pull-ups count in parallel
Pulse port (reed contacts to GND, pull-up to the always-on rail, series R + C at the GPIO):
  closed-contact current I = VDD / Rp per input, compared with the sleep budget share
  release edge: the pin reaches VIH = 0.75 x VDD (ESP32-S3-WROOM-1 v1.8 table 6-3) after ln(4) x Rp x C;
  the maximum pulse rate is 1 / (2 x that time) (equal high and low times)
Rows: OK, WARN, FAIL, MISSING (null value), WARN for a missing source. Last line `i2c_bus: OK|FAILED`.
Usage: python3 hardware/calc/i2c_bus.py hardware/<board> [--selftest]
"""

import math
import sys
from pathlib import Path

import yaml


def val(d: dict, key: str, rows: list):
    item = d.get(key)
    if not isinstance(item, dict) or item.get("value") is None:
        rows.append(("MISSING", key, "value is null in board.yaml"))
        return None
    if not item.get("source"):
        rows.append(("WARN", key, f"{item['value']} has no source"))
    return item["value"]


def par(*r):
    return 1 / sum(1 / x for x in r if x)


def run(design: dict) -> list:
    rows: list = []
    bus = design.get("i2c_bus")
    if bus:
        vdd, rp, f = val(bus, "vdd_v", rows), val(bus, "pullup_ohm", rows), val(bus, "freq_khz", rows)
        pcb, cab_pf_m, cab_m = val(bus, "pcb_pf", rows), val(bus, "cable_pf_per_m", rows), val(bus, "cable_m", rows)
        devs = val(bus, "devices_pf", rows) or {}
        ext = val(bus, "module_pullups_ohm", rows) or []
        if None not in (vdd, rp, f, pcb, cab_pf_m, cab_m):
            cb = pcb + cab_pf_m * cab_m + sum(devs.values())
            limit = 1000 if f <= 100 else 300
            tr = 0.8473 * rp * cb * 1e-3  # ohm x pF = 1e-12 s -> ns: x 1e-3
            detail = (f"Rp {rp / 1000:g}k, Cb {cb:.0f} pF (PCB {pcb}, cable {cab_pf_m} pF/m x {cab_m} m, "
                      f"{len(devs)} devices {sum(devs.values()):g} pF): tr {tr:.0f} ns, limit {limit} ns at {f} kHz")
            rows.append(("OK" if tr <= limit else "FAIL", "I2C rise time", detail))
            rp_eff = par(rp, *ext)
            iol = (vdd - 0.4) / rp_eff * 1000
            rows.append(("OK" if iol <= 3.0 else "FAIL", "I2C pull-up strength",
                         f"board {rp / 1000:g}k || modules {[f'{e / 1000:g}k' for e in ext]} = {rp_eff:.0f} ohm: "
                         f"low level sinks {iol:.2f} mA (limit 3 mA at VOL 0.4 V)"))
            rp_max = limit / (0.8473 * cb * 1e-3)
            rows.append(("OK", "I2C pull-up window", f"{(vdd - 0.4) / 3.0 * 1000:.0f} ohm (3 mA) <= Rp <= {rp_max:.0f} ohm (rise time)"))
    pp = design.get("pulse_port")
    if pp:
        vdd, rp, c = val(pp, "vdd_v", rows), val(pp, "pullup_ohm", rows), val(pp, "cap_f", rows)
        n, budget, fmax = val(pp, "inputs", rows), val(pp, "sleep_budget_ua", rows), val(pp, "max_rate_hz", rows)
        if None not in (vdd, rp, n, budget):
            i = vdd / rp * 1e6
            share = n * i / budget
            rows.append(("OK" if share <= 0.1 else "WARN" if share <= 0.25 else "FAIL", "pulse pull-up leakage",
                         f"{n} contacts closed: {n} x {vdd} V / {rp / 1e3:g}k = {n * i:.1f} uA, {share:.0%} of the {budget} uA sleep budget (want <= 10 %)"))
        if None not in (rp, c, fmax):
            t = math.log(4) * rp * c
            rate = 1 / (2 * t)
            rows.append(("OK" if rate >= fmax else "FAIL", "pulse release edge",
                         f"ln4 x {rp / 1e3:g}k x {c * 1e9:g} nF = {t * 1e3:.1f} ms to VIH: max {rate:.0f} Hz (need {fmax} Hz)"))
    return rows


def selftest() -> bool:
    d = {"i2c_bus": {k: {"value": v, "source": "t"} for k, v in dict(vdd_v=3.3, pullup_ohm=10000, freq_khz=100, pcb_pf=20,
         cable_pf_per_m=50, cable_m=1, devices_pf={"a": 10}, module_pullups_ohm=[]).items()}}
    r = {name: st for st, name, _ in run(d)}
    ok = r["I2C rise time"] == "OK"  # 0.8473 x 10k x 80 pF = 678 ns
    d["i2c_bus"]["cable_m"]["value"] = 2
    ok &= {name: st for st, name, _ in run(d)}["I2C rise time"] == "FAIL"  # 130 pF -> 1101 ns
    d["i2c_bus"]["module_pullups_ohm"]["value"] = [2200, 2200]
    d["i2c_bus"]["pullup_ohm"]["value"] = 2200
    ok &= {name: st for st, name, _ in run(d)}["I2C pull-up strength"] == "FAIL"  # 733 ohm -> 3.95 mA
    return ok


def main() -> int:
    if "--selftest" in sys.argv:
        ok = selftest()
        print("i2c_bus selftest:", "OK" if ok else "FAILED")
        return 0 if ok else 1
    board = Path(sys.argv[1])
    design = yaml.safe_load((board / "board.yaml").read_text()).get("design", {})
    rows = run(design)
    for st, name, detail in rows:
        print(f"{st:8} {name}: {detail}")
    bad = any(st == "FAIL" for st, _, _ in rows)
    print("i2c_bus:", "FAILED" if bad else "OK")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
