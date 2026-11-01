"""Power checks for a solar/USB cell board from its profile (board.yaml `design`): BQ25798 charger set points, cell limits,
buck-boost input at cut-off, protection ordering, energy budget.

Rows: OK, WARN, FAIL, MISSING. An input with a null value is MISSING (fill it from its source, never guess); an input
without `source` is WARN (unsourced). `source: assumption` is allowed and printed, so a reader sees what is still a guess.
Formulas: C-rate = ICHG / capacity; cell voltage at the regulator input = cut-off - (path resistance x peak current);
the TPS63802 minimum input is the datasheet recommended value (section 8.3).
Usage: uv run --package weatherstation-hardware python hardware/calc/power_budget.py hardware/<board> [--selftest]
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

    # BQ25798 charger (USB + PV): register values that firmware writes before CE is released (usb-charger-bq25798.md)
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
    vco, path = val(ce, "vcutoff_firmware_v", rows), val(bb, "path_r_ohm", rows)
    vin_min, pk = val(bb, "vin_min_v", rows), val(ld, "peak_a", rows)
    if None not in (vco, path, vin_min, pk):
        vin = vco - path * pk
        m = vin - vin_min
        rows.append(("OK" if m >= 0.2 else ("WARN" if m >= 0 else "FAIL"), "buck-boost input at cutoff",
                     f"cell {vco} V minus {path * pk * 1000:.0f} mV path drop at {pk} A = {vin:.2f} V, minimum {vin_min} V, margin {m * 1000:+.0f} mV"))
    # HY2112-CB current sense: two FETs in series across CS (drop = 2 x Rds x I) must stay inside the overcurrent thresholds
    rds, occ, ocd = val(hy, "fet_rds_ohm", rows), val(hy, "oc_charge_v", rows), val(hy, "oc_discharge_v", rows)
    if rds is not None and occ is not None and ichg is not None:
        drop = 2 * rds * ichg
        rows.append(("OK" if drop <= occ - 0.02 else ("WARN" if drop <= occ else "FAIL"), "HY2112 charge overcurrent margin",
                     f"charge {ichg} A gives {drop * 1000:.0f} mV across M60+M61, trip at {occ * 1000:.0f} mV (want 20 mV margin)"))
    if rds is not None and ocd is not None and pk is not None:
        drop = 2 * rds * pk
        rows.append(("OK" if drop <= ocd - 0.02 else ("WARN" if drop <= ocd else "FAIL"), "HY2112 discharge overcurrent margin",
                     f"peak load {pk} A gives {drop * 1000:.0f} mV, trip at {ocd * 1000:.0f} mV"))
    # Hardware protection (HY2112-CB) must act below the firmware cut-off, and above the cell's own cut-off
    vdl, vcell_min = val(ce, "hy2112_overdischarge_v", rows), val(ce, "vcut_cell_v", rows)
    if None not in (vco, vdl, vcell_min):
        rows.append(("OK" if vcell_min <= vdl < vco else "FAIL", "cut-off ordering",
                     f"cell spec {vcell_min} V <= HY2112 detection {vdl} V < firmware cut-off {vco} V (sensors off first)"))

    # energy budget
    need = ("period_s", "esp_active_s", "esp_active_ma", "sensor_on_s", "sensor_ma", "sleep_ua")
    cyv = {n: val(cy, n, rows, f"cycle.{n}") for n in need}
    if None not in cyv.values():
        q = (cyv["esp_active_s"] * cyv["esp_active_ma"] + cyv["sensor_on_s"] * cyv["sensor_ma"]) / cyv["period_s"] + cyv["sleep_ua"] / 1000
        wh = q * 3.2 * 24 / 1000  # LFP nominal 3.2 V (all currents are at the cell)
        rows.append(("OK", "average current", f"{q:.1f} mA at a {cyv['period_s']} s cycle, {wh:.2f} Wh/day"))
        cell = val(ce, "cell_mah", rows)
        if cell:
            rows.append(("OK", "battery autonomy", f"{cell * 0.8 / (q * 24):.1f} days from 80 % of {cell} mAh without sun"))
        pw, psh, eff = (val(so, n, rows, f"solar.{n}") for n in ("panel_w", "psh_worst_h", "system_eff"))
        if None not in (pw, psh, eff):
            y = pw * psh * eff
            rows.append(("OK" if y >= wh * 1.5 else "WARN", "worst-month solar yield", f"{y:.2f} Wh/day vs {wh:.2f} Wh/day need (want 1.5x margin)"))
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
    return ok_vreg and ok_rate and ok_bb


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
