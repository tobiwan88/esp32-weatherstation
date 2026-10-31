"""Power checks for a solar/USB Li-ion board from its profile (board.yaml `design`): charger set points, LDO headroom, energy budget.

Rows: OK, WARN, FAIL, MISSING. An input with a null value is MISSING (fill it from its source, never guess); an input
without `source` is WARN (unsourced). `source: assumption` is allowed and printed, so a reader sees what is still a guess.
Formulas: CN3791 MPPT divider Vset = Vmppt x (1 + Rtop/Rbot) and ICH = Vcs/Rcs (CN3791 datasheet, application section);
TP4056 IBAT = 1200 / RPROG[kohm] mA (TP4056 datasheet, "PROG pin"); linear dissipation = (Vin - Vbat) x I (basic);
LDO dropout scaled linearly with current from one datasheet point (conservative for small currents).
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
    c, t, b, l, ld, cy, so, pn = (design.get(k, {}) for k in ("cn3791", "tp4056", "battery", "ldo", "load", "cycle", "solar", "panel"))

    # CN3791 solar charger
    vm, vcs = val(c, "vmppt_v", rows), val(c, "vcs_v", rows)
    rt, rb, rcs = c.get("r_top_ohm"), c.get("r_bottom_ohm"), c.get("rcs_ohm")
    drop = val(c, "diode_drop_v", rows)
    if None not in (vm, rt, rb, drop):
        vset = vm * (1 + rt / rb)
        rows.append(("OK", "CN3791 MPPT set point", f"CN3791 VCC regulated to {vset:.2f} V, panel pin about {vset + drop:.2f} V (diode {drop} V)"))
        vmp = val(pn, "vmp_v", rows, "panel Vmp")
        if vmp is not None:
            err = (vset + drop - vmp) / vmp * 100
            rows.append(("OK" if abs(err) <= 5 else "WARN", "MPPT vs panel Vmp", f"{err:+.1f} % (panel {vmp} V); keep within +-5 %"))
    if None not in (vcs, rcs):
        ich = vcs / rcs
        rows.append(("OK", "CN3791 charge current", f"{ich:.2f} A at Rcs {rcs} ohm"))
        pw, pv = so.get("panel_w"), pn.get("vmp_v", {}).get("value")
        if pw and pv:
            rows.append(("OK" if pw / pv <= ich else "WARN", "panel current vs Rcs", f"panel Imp about {pw / pv:.2f} A, charger limit {ich:.2f} A"))

    # TP4056 USB charger
    k, prog, vusb = val(t, "k_ma_kohm", rows), t.get("prog_ohm"), t.get("vin_v")
    vbat_typ = b.get("vtyp_v")
    if None not in (k, prog, vusb, vbat_typ):
        i = k / (prog / 1000)
        p = (vusb - vbat_typ) * i / 1000
        rows.append(("OK", "TP4056 charge current", f"{i:.0f} mA at RPROG {prog / 1000:g} kohm"))
        rows.append(("OK" if p <= t.get("max_diss_w", 0.6) else "WARN", "TP4056 dissipation", f"{p:.2f} W at {vusb} V in, {vbat_typ} V cell (limit {t.get('max_diss_w', 0.6)} W; pad + vias)"))

    # LDO headroom at the battery cutoff
    vco, rds = val(b, "vcutoff_v", rows), l.get("q1_rds_ohm")
    dv, di = (l.get("dropout_v_at_a") or [None, None])
    pk, vmin = val(ld, "peak_a", rows), val(ld, "sensor_vmin_v", rows)
    if None not in (vco, rds, dv, di, pk, vmin):
        vin = vco - rds * pk
        dout = dv * min(pk / di, 1.0)
        vout = min(l.get("vout_v", 3.3), vin - dout)
        m = vout - vmin
        rows.append(("OK" if m >= 0.05 else ("WARN" if m >= 0 else "FAIL"), "LDO headroom at cutoff",
                     f"cell {vco} V -> rail {vout:.2f} V at {pk} A peak, sensor minimum {vmin} V, margin {m * 1000:+.0f} mV"))

    # energy budget
    need = ("period_s", "esp_active_s", "esp_active_ma", "sen66_on_s", "sen66_ma", "sleep_ua")
    cyv = {n: val(cy, n, rows, f"cycle.{n}") for n in need}
    if None not in cyv.values():
        q = (cyv["esp_active_s"] * cyv["esp_active_ma"] + cyv["sen66_on_s"] * cyv["sen66_ma"]) / cyv["period_s"] + cyv["sleep_ua"] / 1000
        wh = q * 3.7 * 24 / 1000
        rows.append(("OK", "average current", f"{q:.1f} mA at a {cyv['period_s']} s cycle, {wh:.2f} Wh/day"))
        cell = val(b, "cell_mah", rows)
        if cell:
            rows.append(("OK", "battery autonomy", f"{cell * 0.8 / (q * 24):.1f} days from 80 % of {cell} mAh without sun"))
        pw, psh, eff = (val(so, n, rows, f"solar.{n}") for n in ("panel_w", "psh_worst_h", "system_eff"))
        if None not in (pw, psh, eff):
            y = pw * psh * eff
            rows.append(("OK" if y >= wh * 1.5 else "WARN", "worst-month solar yield", f"{y:.2f} Wh/day vs {wh:.2f} Wh/day need (want 1.5x margin)"))
    return rows


def selftest() -> bool:
    d = {"cn3791": {"vmppt_v": {"value": 1.205, "source": "x"}, "vcs_v": {"value": 0.12, "source": "x"}, "diode_drop_v": {"value": 0.3, "source": "x"},
                    "r_top_ohm": 39000, "r_bottom_ohm": 10000, "rcs_ohm": 0.12},
         "tp4056": {"k_ma_kohm": {"value": 1200, "source": "x"}, "prog_ohm": 3000, "vin_v": 5.0}, "battery": {"vtyp_v": 3.7}}
    r = {x[1]: x[2] for x in run(d)}
    return "5.90 V" in r["CN3791 MPPT set point"] and "1.00 A" in r["CN3791 charge current"] and "400 mA" in r["TP4056 charge current"]


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
