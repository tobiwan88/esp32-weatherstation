"""Switched sensor rail (P-FET high-side switch with a gate-drain ramp capacitor) and the outdoor cable feed, from a board
profile (board.yaml `design.rail_switch`).

Circuit: P-FET source on the always-on rail, drain = switched rail with the load capacitance; gate pulled up to the rail
by Rpu; an N-FET pulls the gate low through Rs; Cgd (external, plus the FET's Crss) from gate to drain sets the ramp.
Formulas (Miller plateau model, as TI SLVA156 "Using MOSFETs as load switches" / SLVA670 slew-rate control):
  plateau |Vgs| = Vth + sqrt(I_inrush / K), K from the forward transconductance: gfs = 2 sqrt(K x Id) at the datasheet
  test current (square law); solved together with the ramp by fixed-point iteration
  gate current on the plateau  Ig = (V - |Vgs|) / Rs - |Vgs| / Rpu  (N-FET on-resistance neglected against Rs)
  ramp dV/dt = Ig / (Cgd + Crss); ramp time = V / (dV/dt); inrush = C_load x dV/dt; FET energy = C_load x V^2 / 2
  delay before the ramp: the gate falls from V towards V x Rs / (Rs + Rpu) with tau = (Rs || Rpu) x (Cgd + Ciss)
  (Cgd sees the discharged load as ground) until it reaches V - |Vgs|
  final gate drive |Vgs| = V x Rpu / (Rs + Rpu): must reach the Rds(on) test voltage of the datasheet
  turn-off (review follow-up B1, 2026-11-21): the gate rises through Rpu alone, tau_g = Rpu x (Cgd + Ciss), from the final
  drive |Vgs| to Vth: t_gate = tau_g x ln(|Vgs final| / Vth). The drain is NOT pulled up by a Miller plateau: once the FET
  is off, the rail only discharges through its loads and the bleed resistor (sensors asleep or off: bleed only),
  tau_bleed = R_bleed x C_load, 5 tau to below 1 % (sensor power-on reset needs the rail near 0 V before re-enabling).
  Without a bleed the rail decays only through leakage (tens of seconds): FAIL when r_bleed_ohm is missing.
  The bleed draws V / R_bleed while the rail is on (reported; counted in calc/power_budget.py as an active load).
  cold start: while +3V3 ramps, C48 holds the gate near the (discharged) drain and R40 charges it towards the source with
  tau_g; a +3V3 ramp shorter than tau_g lets the FET conduct weakly and 3V3_SW rises part-way without SENSOR_EN (WARN:
  firmware drains it before the first enable, scope it on the first board)
  rail dip with the slow ramp: the regulator's datasheet load-step dip scaled linearly to the inrush step (assumption:
  same output capacitance class as the datasheet test); FAIL when the rail falls below the MCU's minimum supply
  without the ramp (old circuit, switch closes in about a microsecond, the regulator cannot follow): charge sharing
  V_after = V x C_rail / (C_rail + C_load) (reported for comparison)
Cable feed (series resistor in the supply pin of an outdoor connector): short-circuit current V / R and its power
I^2 R against the resistor rating (want <= 50 %), drop at the maximum cable load against the I/O limit (VDD + 0.3 V on
the remote sensor with the pull-ups on the board side: drop <= 0.3 V).
Rows: OK, WARN, FAIL, MISSING (null value), WARN for an input without source. Last line `rail_switch: OK|FAILED`.
Usage: python3 hardware/calc/rail_switch.py hardware/<board> [--selftest]
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


def ramp(v, rs, rpu, cgd, vth, k, c_load):
    """(|Vgs| plateau, gate current A, dV/dt V/s, inrush A) by fixed-point iteration."""
    vpl = vth
    for _ in range(100):
        ig = (v - vpl) / rs - vpl / rpu
        dvdt = ig / cgd
        i = c_load * dvdt
        new = vth + math.sqrt(i / k)
        if abs(new - vpl) < 1e-9:
            break
        vpl = new
    return vpl, ig, dvdt, i


def run(design: dict) -> list:
    rows: list = []
    rsw = design.get("rail_switch")
    if not rsw:
        return rows
    names = ("v_rail", "rs_ohm", "rpu_ohm", "cgd_ext_f", "crss_f", "ciss_f", "vth_v", "gfs_s", "gfs_id_a", "vgs_rds_spec_v",
             "c_load_eff_f", "c_load_nom_f", "c_rail_eff_f", "v_min_mcu", "dip_ref_v", "dip_ref_step_a", "inrush_max_a")
    x = {n: val(rsw, n, rows) for n in names}
    if None in x.values():
        return rows
    v, rs, rpu = x["v_rail"], x["rs_ohm"], x["rpu_ohm"]
    cgd = x["cgd_ext_f"] + x["crss_f"]
    k = x["gfs_s"] ** 2 / (4 * x["gfs_id_a"])
    vg_final = v * rpu / (rs + rpu)
    rows.append(("OK" if vg_final >= x["vgs_rds_spec_v"] else "FAIL", "final gate drive",
                 f"|Vgs| = {v} V x {rpu / 1e3:g}k / ({rs / 1e3:g}k + {rpu / 1e3:g}k) = {vg_final:.2f} V "
                 f"(Rds(on) specified at {x['vgs_rds_spec_v']} V)"))
    worst_i = 0.0
    for label, vth in (("Vth min", x["vth_v"][0]), ("Vth typ", x["vth_v"][1]), ("Vth max", x["vth_v"][2])):
        for cl_name, cl in (("C_load eff", x["c_load_eff_f"]), ("C_load nominal", x["c_load_nom_f"])):
            vpl, ig, dvdt, i = ramp(v, rs, rpu, cgd, vth, k, cl)
            worst_i = max(worst_i, i)
            t_ramp = v / dvdt
            tau = (rs * rpu / (rs + rpu)) * (cgd + x["ciss_f"])
            v_inf = v * rs / (rs + rpu)
            t_delay = tau * math.log((v - v_inf) / ((v - vpl) - v_inf))
            dip = x["dip_ref_v"] * i / x["dip_ref_step_a"]
            st = "OK" if i <= x["inrush_max_a"] and v - dip >= x["v_min_mcu"] else "FAIL"
            rows.append((st, f"turn-on {label}, {cl_name}",
                         f"plateau |Vgs| {vpl:.2f} V, gate current {ig * 1e6:.0f} uA, delay {t_delay * 1e3:.3f} ms, "
                         f"ramp {t_ramp * 1e3:.2f} ms ({dvdt / 1e3:.1f} V/ms), inrush {i:.3f} A into {cl * 1e6:.1f} uF "
                         f"(limit {x['inrush_max_a']} A), rail dip about {dip * 1e3:.0f} mV -> {v - dip:.2f} V "
                         f"(MCU minimum {x['v_min_mcu']} V)"))
    tau_g = rpu * (cgd + x["ciss_f"])
    t_gate = turn_off_gate(vg_final, x["vth_v"][0], tau_g)
    rows.append(("OK", "turn-off: gate", f"tau_g = {rpu / 1e3:g}k x {(cgd + x['ciss_f']) * 1e9:.1f} nF = {tau_g * 1e3:.2f} ms; "
                 f"FET off after at most {t_gate * 1e3:.1f} ms (|Vgs| {vg_final:.2f} V -> Vth min {x['vth_v'][0]} V)"))
    rb = (rsw.get("r_bleed_ohm") or {}).get("value")
    if rb is None:
        rows.append(("FAIL", "turn-off: rail discharge", "no bleed resistor (r_bleed_ohm): the rail decays only through "
                     "leakage (about 30 s), sensors get no clean power-on reset when re-enabled"))
    else:
        if not rsw["r_bleed_ohm"].get("source"):
            rows.append(("WARN", "r_bleed_ohm", f"{rb} has no source"))
        for cl_name, cl in (("C_load eff", x["c_load_eff_f"]), ("C_load nominal", x["c_load_nom_f"])):
            tau, t5 = bleed(rb, cl)
            rows.append(("OK", f"turn-off: rail discharge, {cl_name}",
                         f"tau = {rb / 1e3:g}k x {cl * 1e6:.1f} uF = {tau:.2f} s, 5 tau = {t5:.1f} s to below 1 % "
                         f"(firmware waits this long before re-enabling, or soft-resets the sensors)"))
        rows.append(("OK", "bleed current while on", f"{v} V / {rb / 1e3:g}k = {v / rb * 1e6:.0f} uA on +3V3 "
                     f"(only while the rail is on; none in deep sleep)"))
    rows.append(("WARN", "cold start", f"while +3V3 ramps, C48 holds the gate near the discharged drain and R40 charges it "
                 f"with tau_g {tau_g * 1e3:.2f} ms: a faster +3V3 ramp turns Q40 on weakly and 3V3_SW rises part-way "
                 f"without SENSOR_EN (firmware: drain for 5 tau before the first enable; scope 3V3_SW at first power-up)"))
    e = x["c_load_nom_f"] * v * v / 2
    rows.append(("OK", "FET energy per turn-on", f"{e * 1e3:.2f} mJ (C_load nominal x V^2 / 2)"))
    v_after = v * x["c_rail_eff_f"] / (x["c_rail_eff_f"] + x["c_load_eff_f"])
    rows.append(("OK", "without the ramp (old circuit, comparison)",
                 f"charge sharing {x['c_rail_eff_f'] * 1e6:.0f} uF rail into {x['c_load_eff_f'] * 1e6:.0f} uF load: "
                 f"rail falls to about {v_after:.2f} V (MCU minimum {x['v_min_mcu']} V)"))
    cab = design.get("cable_feed")
    if cab:
        r, p_rated, i_load = val(cab, "r_ohm", rows), val(cab, "p_rated_w", rows), val(cab, "i_load_max_a", rows)
        drop_max = val(cab, "drop_max_v", rows)
        if None not in (r, p_rated, i_load, drop_max):
            i_sc = v / r
            p = i_sc * i_sc * r
            rows.append(("OK" if p <= 0.5 * p_rated else ("WARN" if p <= p_rated else "FAIL"), "cable feed short circuit",
                         f"{v} V / {r:g} ohm = {i_sc * 1e3:.0f} mA, {p * 1e3:.0f} mW in the resistor (rated {p_rated * 1e3:.0f} mW, want <= 50 %)"))
            d = i_load * r
            rows.append(("OK" if d <= drop_max else "FAIL", "cable feed drop",
                         f"{i_load * 1e3:g} mA x {r:g} ohm = {d * 1e3:.0f} mV (limit {drop_max * 1e3:.0f} mV)"))
    return rows


def turn_off_gate(vg_final: float, vth: float, tau_g: float) -> float:
    """Time for |Vgs| to decay from the final drive to Vth through Rpu (s)."""
    return tau_g * math.log(vg_final / vth)


def bleed(r: float, c: float) -> tuple[float, float]:
    """(tau, 5 tau) of the rail discharging through the bleed resistor alone (s)."""
    return r * c, 5 * r * c


def selftest() -> bool:
    # K = 17^2 / (4 x 4) = 18.06 A/V^2; Vth 0.9 V, 33 uF: plateau about 1.03 V, Ig = 2.29/10k - 1.03/100k = 219 uA,
    # dV/dt = 219 uA / 22.055 nF = 9.9 V/ms, inrush 0.33 A, ramp 0.34 ms
    vpl, ig, dvdt, i = ramp(3.32, 10e3, 100e3, 22.055e-9, 0.9, 17 ** 2 / 16, 33e-6)
    ok_on = abs(i - 0.327) < 0.01 and abs(3.32 / dvdt - 0.335e-3) < 0.01e-3 and 1.0 < vpl < 1.06
    # turn-off: 22k x 28.6 uF = 0.629 s, 5 tau = 3.15 s; gate 100k x 22.7 nF = 2.27 ms, ln(3.02 / 0.5) = 1.80 -> 4.08 ms
    tau, t5 = bleed(22e3, 28.6e-6)
    ok_off = abs(tau - 0.629) < 0.001 and abs(t5 - 3.146) < 0.005
    ok_gate = abs(turn_off_gate(3.02, 0.5, 100e3 * 22.7e-9) - 4.08e-3) < 0.02e-3
    return ok_on and ok_off and ok_gate


def main() -> int:
    if "--selftest" in sys.argv:
        ok = selftest()
        print("rail_switch selftest:", "OK" if ok else "FAILED")
        return 0 if ok else 1
    board = Path(sys.argv[1])
    rows = run(yaml.safe_load((board / "board.yaml").read_text()).get("design", {}))
    for st, name, detail in rows:
        print(f"{st:8} {name}: {detail}")
    bad = any(st == "FAIL" for st, _, _ in rows)
    print("rail_switch:", "FAILED" if bad else "OK")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
