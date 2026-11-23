"""Power checks for a solar/USB cell board from its profile (board.yaml `design`): BQ25798 charger set points, cell limits,
buck-boost input at cut-off, protection ordering, energy budget.

Rows: OK, WARN, FAIL, MISSING. An input with a null value is MISSING (fill it from its source, never guess); an input
without `source` is WARN (unsourced). `source: assumption` is allowed and printed, so a reader sees what is still a guess.
A check group runs only when its section is in the profile (charger, buckboost, hy2112, cycle): a split system (power
board + main board) checks each group on the board that owns the part; a present section with a null value is MISSING.
Formulas: C-rate = ICHG / capacity; cell voltage at the regulator input = cut-off - (path resistance x peak current);
the TPS63802 minimum input is the datasheet recommended value (section 8.3).
Sleep current (section `sleep`): a sum of named loads, each at the cell or on +3V3; a +3V3 load reaches the cell as
I x 3.3 V / (Vcell x eff) (power conservation through the buck-boost, light-load efficiency from the profile); the sum
replaces the bare target in the average current and FAILs above the target `cycle.sleep_ua`.
Rail-on loads (`cycle.rail_on_loads`, optional): loads that draw only while the sensor rail is on (a bleed resistor:
I = v / ohm, or ua), converted to the cell like a +3V3 sleep load and added for `sensor_on_s` per cycle (not in sleep).
Autonomy = 80 % of the capacity / (average current x 24 h); FAIL below `cycle.autonomy_days_min`.
Usage: python3 hardware/calc/power_budget.py hardware/<board> [--selftest]
"""

import sys
from pathlib import Path

import yaml


def val(d: dict, key: str, rows: list, label: str | None = None):
    """Return d[key]['value']; append MISSING/WARN rows for null value / missing source."""
    item = d.get(key)
    name = label or key
    if not isinstance(item, dict) or item.get("value") is None:
        rows.append(("MISSING", name, "value is null in board.yaml"))
        return None
    if not item.get("source"):
        rows.append(("WARN", name, f"{item['value']} has no source"))
    return item["value"]


def run(design: dict) -> list:
    rows: list = []
    ch, ce, bb, ld, cy, so, pn, hy = (design.get(k, {}) for k in ("charger", "cell", "buckboost", "load", "cycle", "solar", "panel", "hy2112"))

    has = set(design)
    vreg = acc = ichg = vmax = cap = None
    # BQ25798 charger (USB + PV): register values that firmware writes before CE is released (usb-charger-bq25798.md)
    if "charger" in has:
        vreg, acc, ichg = val(ch, "vreg_v", rows), val(ch, "vreg_accuracy_mv", rows), val(ch, "ichg_a", rows)
        vmax, cap = val(ce, "vmax_v", rows), val(ce, "cell_mah", rows)
    if vreg is not None and vmax is not None:
        if acc is None:
            rows.append(("MISSING", "VREG vs cell maximum", f"VREG {vreg} V, cell maximum {vmax} V; accuracy of the BQ25798 VREG not in the profile"))
        else:
            worst = vreg + acc / 1000
            rows.append(("OK" if worst <= vmax else "FAIL", "VREG vs cell maximum", f"VREG {vreg} V + {acc} mV accuracy = {worst:.3f} V, cell maximum {vmax} V"))
    if ichg is not None and cap is not None:
        c_rate = ichg / (cap / 1000)
        rows.append(("OK" if c_rate <= 0.5 else "FAIL", "charge current vs 0.5C", f"{ichg} A on {cap} mAh = {c_rate:.2f}C (limit 0.5C at 0-20 C, the coldest band that allows 0.5C)"))

    # TPS63802 buck-boost (3.3 V): input at the firmware cut-off must stay above the minimum input voltage
    vco = val(ce, "vcutoff_firmware_v", rows) if {"buckboost", "hy2112"} & has else None
    pk = val(ld, "peak_a", rows) if {"buckboost", "hy2112"} & has else None
    path = vin_min = None
    if "buckboost" in has:
        path, vin_min = val(bb, "path_r_ohm", rows), val(bb, "vin_min_v", rows)
    if None not in (vco, path, vin_min, pk):
        vin = vco - path * pk
        m = vin - vin_min
        rows.append(("OK" if m >= 0.2 else ("WARN" if m >= 0 else "FAIL"), "buck-boost input at cutoff",
                     f"cell {vco} V minus {path * pk * 1000:.0f} mV path drop at {pk} A = {vin:.2f} V, minimum {vin_min} V, margin {m * 1000:+.0f} mV"))
    # HY2112-CB current sense: two FETs in series across CS (drop = 2 x Rds x I) must stay inside the overcurrent thresholds
    rds = occ = ocd = vdl = vcell_min = None
    if "hy2112" in has:
        rds, occ, ocd = val(hy, "fet_rds_ohm", rows), val(hy, "oc_charge_v", rows), val(hy, "oc_discharge_v", rows)
        vdl, vcell_min = val(ce, "hy2112_overdischarge_v", rows), val(ce, "vcut_cell_v", rows)
    if rds is not None and occ is not None and ichg is not None:
        drop = 2 * rds * ichg
        rows.append(("OK" if drop <= occ - 0.02 else ("WARN" if drop <= occ else "FAIL"), "HY2112 charge overcurrent margin",
                     f"charge {ichg} A gives {drop * 1000:.0f} mV across M60+M61, trip at {occ * 1000:.0f} mV (want 20 mV margin)"))
    if rds is not None and ocd is not None and pk is not None:
        drop = 2 * rds * pk
        rows.append(("OK" if drop <= ocd - 0.02 else ("WARN" if drop <= ocd else "FAIL"), "HY2112 discharge overcurrent margin",
                     f"peak load {pk} A gives {drop * 1000:.0f} mV, trip at {ocd * 1000:.0f} mV"))
    # Hardware protection (HY2112-CB) must act below the firmware cut-off, and above the cell's own cut-off
    if None not in (vco, vdl, vcell_min):
        rows.append(("OK" if vcell_min <= vdl < vco else "FAIL", "cut-off ordering",
                     f"cell spec {vcell_min} V <= HY2112 detection {vdl} V < firmware cut-off {vco} V (sensors off first)"))

    # sleep current: sum of the loads that stay on in deep sleep (replaces the bare target when present)
    sleep_sum = None
    sl = design.get("sleep")
    if sl:
        vcell, eff = val(sl, "vcell_v", rows, "sleep.vcell_v"), val(sl, "buckboost_eff", rows, "sleep.buckboost_eff")
        loads = sl.get("loads") or {}
        if vcell and eff:
            typ = mx = 0.0
            parts = []
            for name, ld in loads.items():
                if not ld.get("source"):
                    rows.append(("WARN", f"sleep load {name}", "no source"))
                k = 1.0 if ld.get("rail", "cell") == "cell" else 3.3 / (vcell * eff)
                t = ld["ua"] * k
                m = ld.get("ua_max", ld["ua"]) * k
                typ, mx = typ + t, mx + m
                parts.append(f"{name} {t:.1f}")
            sleep_sum = typ
            target = (cy.get("sleep_ua") or {}).get("value")
            st = "OK" if target is None or typ <= target else "FAIL"
            rows.append((st, "sleep current sum", f"{typ:.1f} uA typ, {mx:.1f} uA with datasheet maxima, at the cell "
                         f"(target {target} uA): " + ", ".join(parts)))

    # energy budget
    if "cycle" not in has:
        return rows
    need = ("period_s", "esp_active_s", "esp_active_ma", "sensor_on_s", "sensor_ma", "sleep_ua")
    cyv = {n: val(cy, n, rows, f"cycle.{n}") for n in need}
    if None not in cyv.values():
        sleep_ma = (sleep_sum if sleep_sum is not None else cyv["sleep_ua"]) / 1000
        o3 = {n: cy.get(n, {}).get("value") for n in ("o3_on_s", "o3_ma", "o3_period_s")}  # optional slow sensor (ZE25-O3)
        o3_ma = o3["o3_on_s"] * o3["o3_ma"] / o3["o3_period_s"] if None not in o3.values() else 0.0
        if o3_ma:
            rows.append(("OK", "slow sensor (O3) share", f"{o3['o3_on_s']} s at {o3['o3_ma']} mA every {o3['o3_period_s']} s = "
                         f"{o3_ma:.1f} mA average"))

        rail_ma = 0.0
        if cy.get("rail_on_loads"):
            vcell = ((sl or {}).get("vcell_v") or {}).get("value") or 3.2
            eff = ((sl or {}).get("buckboost_eff") or {}).get("value") or 0.85
            parts = []
            for name, ld in cy["rail_on_loads"].items():
                if not ld.get("source"):
                    rows.append(("WARN", f"rail-on load {name}", "no source"))
                ua = ld["v"] / ld["ohm"] * 1e6 if "ohm" in ld else ld["ua"]
                k = 1.0 if ld.get("rail", "cell") == "cell" else 3.3 / (vcell * eff)
                rail_ma += ua * k / 1000
                parts.append(f"{name} {ua:.0f} uA on {ld.get('rail', 'cell')} = {ua * k:.0f} uA at the cell")
            rows.append(("OK", "rail-on loads (sensor window only)", ", ".join(parts) +
                         f" for {cyv['sensor_on_s']} s per cycle (not in the sleep sum)"))

        def average(period):
            return (cyv["esp_active_s"] * cyv["esp_active_ma"] + cyv["sensor_on_s"] * (cyv["sensor_ma"] + rail_ma)) / period \
                + sleep_ma + o3_ma
        q = average(cyv["period_s"])
        wh = q * 3.2 * 24 / 1000  # LFP nominal 3.2 V (all currents are at the cell)
        rows.append(("OK", "average current", f"{q:.1f} mA at a {cyv['period_s']} s cycle, {wh:.2f} Wh/day "
                     f"(sleep {sleep_ma * 1000:.0f} uA {'sum' if sleep_sum is not None else 'target'})"))
        cell = val(ce, "cell_mah", rows)
        dmin = (cy.get("autonomy_days_min") or {}).get("value")
        if cell:
            days = cell * 0.8 / (q * 24)
            st = "OK" if dmin is None or days >= dmin else "FAIL"
            rows.append((st, "battery autonomy", f"{days:.1f} days from 80 % of {cell} mAh without sun"
                         + (f" (minimum {dmin} days)" if dmin is not None else " (no minimum in the profile)")))
            fast = (cy.get("fast_period_s") or {}).get("value")
            if fast:  # firmware mode with USB or strong sun: reported, not judged against the autonomy minimum
                qf = average(fast)
                rows.append(("OK", "fast cycle (USB or strong sun only)", f"{qf:.1f} mA at {fast} s, "
                             f"{qf * 3.2 * 24 / 1000:.2f} Wh/day, {cell * 0.8 / (qf * 24):.1f} days if it ran without sun"))
        pw, psh, eff = (val(so, n, rows, f"solar.{n}") for n in ("panel_w", "psh_worst_h", "system_eff"))
        if None not in (pw, psh, eff):
            y = pw * psh * eff
            rows.append(("OK" if y >= wh * 1.5 else "WARN", "worst-month solar yield",
                         f"{y:.2f} Wh/day vs {wh:.2f} Wh/day need: margin {y / wh:.2f}x (want 1.5x)"))
    return rows


def selftest() -> bool:
    d = {"charger": {"vreg_v": {"value": 3.65, "source": "x"}, "vreg_accuracy_mv": {"value": 20, "source": "x"},
                     "ichg_a": {"value": 1.9, "source": "x"}},
         "cell": {"vmax_v": {"value": 3.75, "source": "x"}, "cell_mah": {"value": 3900, "source": "x"},
                  "vcutoff_firmware_v": {"value": 2.4, "source": "x"}, "hy2112_overdischarge_v": {"value": 2.10, "source": "x"},
                  "vcut_cell_v": {"value": 2.0, "source": "x"}},
         "buckboost": {"path_r_ohm": {"value": 0.15, "source": "x"}, "vin_min_v": {"value": 1.3, "source": "x"}},
         "load": {"peak_a": {"value": 0.35, "source": "x"}}}
    r = {x[1]: x for x in run(d)}
    ok_vreg = r["VREG vs cell maximum"][0] == "OK" and "3.670" in r["VREG vs cell maximum"][2]
    ok_rate = r["charge current vs 0.5C"][0] == "OK" and "0.49C" in r["charge current vs 0.5C"][2]
    ok_bb = r["buck-boost input at cutoff"][0] == "OK" and "2.35 V" in r["buck-boost input at cutoff"][2]
    # energy: 1800 s cycle, 15 s x 100 mA + 90 s x 190 mA = 18600 mAs / 1800 s = 10.33 mA; sleep sum: 10 uA at the cell
    # + 27.2 uA on +3V3 x 3.3 / (3.2 x 0.85) = 33.0 uA -> 43.0 uA; average 10.38 mA; 3900 mAh x 0.8 / (10.38 x 24) = 12.5 days
    e = {"cell": {"cell_mah": {"value": 3900, "source": "x"}},
         "cycle": {k: {"value": v, "source": "x"} for k, v in dict(period_s=1800, esp_active_s=15, esp_active_ma=100,
                   sensor_on_s=90, sensor_ma=190, sleep_ua=100, autonomy_days_min=7).items()},
         "sleep": {"vcell_v": {"value": 3.2, "source": "x"}, "buckboost_eff": {"value": 0.85, "source": "x"},
                   "loads": {"a": {"ua": 10, "rail": "cell", "source": "x"}, "b": {"ua": 27.2, "rail": "3v3", "source": "x"}}}}
    r = {x[1]: x for x in run(e)}
    ok_sleep = r["sleep current sum"][0] == "OK" and "43.0 uA typ" in r["sleep current sum"][2]
    ok_aut = r["battery autonomy"][0] == "OK" and "12.5 days" in r["battery autonomy"][2]
    e["cycle"]["autonomy_days_min"]["value"] = 13
    ok_fail = {x[1]: x for x in run(e)}["battery autonomy"][0] == "FAIL"
    return ok_vreg and ok_rate and ok_bb and ok_sleep and ok_aut and ok_fail


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        print("power_budget selftest:", "OK" if selftest() else "FAILED")
        sys.exit(0 if selftest() else 1)
    board = Path(sys.argv[1])
    rows = run(yaml.safe_load((board / "board.yaml").read_text()).get("design", {}))
    bad = False
    for st, name, detail in rows:
        bad |= st == "FAIL"
        print(f"{st:8} {name}: {detail}")
    print("power_budget:", "FAILED" if bad else "OK")
    sys.exit(1 if bad else 0)
