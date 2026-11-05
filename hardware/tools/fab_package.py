"""JLCPCB production files for one or more boards: gerbers + drill zip, BOM and CPL (pick and place) in JLC's columns.

Usage (from the repo root, after `source scripts/kicad-env.sh`):
  python3 -I hardware/tools/fab_package.py [--require-clean] [--offline] hardware/<board>/<board>.kicad_pcb [...]
  --fit-only (with --offline in the gate): placement fit only, no DRC, no files; a part without a cached fab footprint
  is a MISSING row (passes), FAIL/CHECK fail. Run it as soon as a footprint is placed, not only at order time.
Writes hardware/out/fab/<board>/ only (gitignored); the board is only read.

- Gate first: DRC with schematic parity and refilled zones must report 0 violations and 0 unconnected items; a
  warning may be waived per part in <board>/drc-waivers.csv (type, ref, reason), errors never.
- Gerbers follow JLC's KiCad guide: Protel extensions, soldermask subtracted from silk, zones checked, no X2, no netlist
  attributes; Excellon in mm, decimal, PTH and NPTH in separate files, absolute origin, no map file. ${GIT_SHA} on the
  silk is resolved to the commit (with -dirty when hardware/ has uncommitted changes; --require-clean refuses that).
- BOM: Comment, Designator, Footprint, LCSC Part #; one line per LCSC number. Parts without an LCSC field, or marked
  DNP / excluded from BOM (holes, test pads, solder jumpers, hand-soldered connectors, the DNP SCD41) are left out.
- CPL: Designator, Mid X, Mid Y, Layer, Rotation. Not KiCad's origin and angle plus a guessed correction table:
  JLC's placement preview draws its own (EasyEDA) footprint of the LCSC part, so each part's EasyEDA footprint is
  fetched (easyeda.com component API, cached per part in its own folder under hardware/out/fab/easyeda/) and fitted onto
  the placed KiCad pads: the rotation (0/90/180/270) and the board point of the EasyEDA origin that put its pads on
  ours. Pads are paired by pad number; the fit must land every pad within FIT_TOL_MM. Parts whose pad numbers differ
  from KiCad's are fitted by pad geometry and must be listed in GEOMETRY_OK after a human looked at the result.
  Still confirm ICs, connectors and polarised parts in JLC's placement preview before paying.
The downloaded JSON is untrusted data: this script only parses it with json, and must run with python3 -I.
"""

import csv
import json
import math
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import zipfile
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "hardware/out/fab"
CACHE = OUT / "easyeda"
EASYEDA = "https://easyeda.com/api/products/{}/components?version=6.4.19.5"
UNIT_MM = 0.254          # EasyEDA canvas unit = 10 mil
FIT_TOL_MM = 0.25        # worst pad-centre error for a plain OK (land patterns of two libraries differ a little)
LAND_TOL_MM = 0.5        # worst pad-centre error accepted when the rotation is unambiguous (status LAND)
AMBIGUITY_MM = 0.3       # the next-best rotation must be at least this much worse
# LCSC parts whose EasyEDA pad numbers differ from KiCad's: fitted on geometry; the rotation printed by the run was
# checked by hand against both drawings. Value = expected rotation correction (CPL angle minus KiCad angle).
GEOMETRY_OK: dict[str, tuple[set[int], str]] = {
    # JST SM04B-SRSS-TB: EasyEDA numbers the two mounting tabs 5/6, KiCad "MP"; all 6 pads within 1 um at 0 deg
    # (a 180 deg fit would put the tabs in front of the pins), so pin 1 lands on pin 1.
    "C160404": ({0}, "pads within 0.001 mm at 0 deg; tabs behind the pins"),
    # HRO TYPE-C-31-M-12: EasyEDA and KiCad name the pads differently (A1..B12 vs numbers); the 4 shell legs and the
    # 12 signal pads fit within 0.11 mm at 0 deg correction, the next-best angle is off by 4 mm (the shell legs are
    # not symmetric front to back); the origin differs by 1.5 mm and is taken from the fit.
    "C165948": ({0}, "all pads within 0.11 mm at 0 deg, next angle 4 mm off"),
    # CMF4532F-900 (HongyeX): EasyEDA numbers the pads 1-2 across the width, EMTEK/KiCad 1-2 along a winding; the
    # body is symmetric under 180 deg, so 90 and 270 put the same part on the same lands (EasyEDA drawn turned 90 deg).
    "C963746": ({90, 270}, "180-degree-symmetric 4-pad choke; lands match within 0.08 mm"),
}


def git(*a: str) -> str:
    return subprocess.run(["git", *a], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()


def git_sha(require_clean: bool) -> str:
    sha = git("rev-parse", "--short", "HEAD")
    if git("status", "--porcelain", "--", "hardware"):
        if require_clean:
            sys.exit("uncommitted changes under hardware/: commit them before building the order package")
        print(f"WARNING: uncommitted changes under hardware/: silk shows {sha}-dirty. Commit, then rerun before ordering.")
        sha += "-dirty"
    return sha


def run(*args: str) -> str:
    r = subprocess.run(args, capture_output=True, text=True)
    if r.returncode:
        sys.exit(f"{' '.join(args[:4])} failed:\n{r.stdout}{r.stderr}")
    return r.stdout


def drc_gate(pcb: Path, tmp: Path) -> None:
    """0 violations and 0 unconnected items, except warnings listed in <board>/drc-waivers.csv (type, ref, reason)."""
    rpt = tmp / "drc.json"
    subprocess.run(["kicad-cli", "pcb", "drc", "--format", "json", "--refill-zones", "--schematic-parity",
                    "--severity-all", "-o", str(rpt), str(pcb)], capture_output=True)
    d = json.loads(rpt.read_text())
    wf = pcb.parent / "drc-waivers.csv"
    waivers = {(r["type"], r["ref"]): r["reason"] for r in csv.DictReader(wf.open())} if wf.exists() else {}
    refs = lambda v: [i["description"].split()[-1] for i in v["items"]]
    open_ = [v for v in d["violations"]
             if v["severity"] != "warning" or not all((v["type"], r) in waivers for r in refs(v))]
    waived = len(d["violations"]) - len(open_)
    other = len(d["unconnected_items"]) + len(d.get("schematic_parity", []))
    if open_ or other:
        lines = [f"  {v['type']}: {v['description']} ({', '.join(refs(v))})" for v in open_]
        sys.exit(f"{pcb.name}: DRC not clean ({len(open_)} violations, {other} unconnected/parity):\n" + "\n".join(lines))
    print(f"{pcb.stem}: DRC clean" + (f" ({waived} waived warnings, {wf.name})" if waived else ""))


def copper_layers(pcb: Path) -> list[str]:
    text = pcb.read_text()
    inner = sorted(set(re.findall(r'\(\d+ "(In\d+\.Cu)" (?:signal|power|mixed)', text)), key=lambda s: int(s[2:-3]))
    return ["F.Cu", *inner, "B.Cu"]


def gerbers(pcb: Path, out: Path, sha: str) -> Path:
    g = out / "gerbers"
    g.mkdir(parents=True, exist_ok=True)
    for f in g.iterdir():
        f.unlink()
    layers = ",".join(copper_layers(pcb) + ["F.Paste", "B.Paste", "F.Silkscreen", "B.Silkscreen", "F.Mask", "B.Mask",
                                            "Edge.Cuts"])
    run("kicad-cli", "pcb", "export", "gerbers", "--layers", layers, "--subtract-soldermask", "--check-zones",
        "--no-x2", "--no-netlist", "-D", f"GIT_SHA={sha}", "-o", f"{g}/", str(pcb))
    run("kicad-cli", "pcb", "export", "drill", "--format", "excellon", "--excellon-separate-th", "--excellon-units", "mm",
        "--excellon-zeros-format", "decimal", "--drill-origin", "absolute", "-o", f"{g}/", str(pcb))
    for f in g.glob("*.gbrjob"):
        f.unlink()
    for f in g.iterdir():  # privacy: no home path or user name in the files that leave the house
        if re.search(rb"/Users/|/home/|" + os.environ.get("USER", "\x00").encode(), f.read_bytes()):
            sys.exit(f"{f}: contains a local path or user name")
    for old in out.glob(f"{pcb.stem}-*gerbers.zip"):
        old.unlink()
    z = out / f"{pcb.stem}-{sha}-gerbers.zip"
    with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in sorted(g.iterdir()):
            zf.write(f, f.name)
    return z


def easyeda_pads(lcsc: str, offline: bool) -> tuple[str, list[tuple[str, float, float]]]:
    """(footprint title, [(pad number, x mm, y mm)]) of the LCSC part's EasyEDA footprint, origin-relative, y down."""
    folder = CACHE / lcsc
    f = folder / "component.json"
    if not f.exists():
        if offline:
            sys.exit(f"{lcsc}: no cached EasyEDA footprint and --offline given")
        req = urllib.request.Request(EASYEDA.format(lcsc), headers={"User-Agent": "weatherstation-hardware"})
        for wait in (60, 180, 0):  # polite: one request every few seconds, back off when the server says no
            time.sleep(3)
            try:
                with urllib.request.urlopen(req, timeout=30) as r:
                    data = r.read()
                break
            except urllib.error.HTTPError as e:
                if not wait or e.code not in (403, 429, 503):
                    sys.exit(f"{lcsc}: EasyEDA answered {e.code}; rerun later (cached parts are kept)")
                print(f"{lcsc}: EasyEDA answered {e.code}, waiting {wait} s")
                time.sleep(wait)
        folder.mkdir(parents=True, exist_ok=True)
        f.write_bytes(data)
    res = json.loads(f.read_text())["result"]
    if str((res.get("lcsc") or {}).get("number")) != lcsc:
        sys.exit(f"{lcsc}: EasyEDA answer is for another part ({(res.get('lcsc') or {}).get('number')})")
    pkg = res["packageDetail"]
    ds = pkg["dataStr"]
    ox, oy = float(ds["head"]["x"]), float(ds["head"]["y"])
    pads = []
    for s in ds["shape"]:
        if s.startswith("PAD~"):
            f_ = s.split("~")
            pads.append((f_[8], (float(f_[2]) - ox) * UNIT_MM, (float(f_[3]) - oy) * UNIT_MM))
    if not pads:
        sys.exit(f"{lcsc}: EasyEDA footprint has no pads")
    return pkg["title"], pads


def rot(x: float, y: float, deg: int) -> tuple[float, float]:
    """Counter-clockwise as seen from the top, in y-down board coordinates (KiCad and EasyEDA both draw y down)."""
    c, s = round(math.cos(math.radians(deg))), round(math.sin(math.radians(deg)))
    return x * c + y * s, -x * s + y * c


def centres(pads: list[tuple[str, float, float]]) -> dict[str, tuple[float, float]]:
    """One point per pad number (split pads with one number, e.g. a thermal pad, average to their centre)."""
    acc = defaultdict(list)
    for n, x, y in pads:
        acc[n].append((x, y))
    return {n: (sum(p[0] for p in v) / len(v), sum(p[1] for p in v) / len(v)) for n, v in acc.items() if n}


def fit(kicad: list[tuple[str, float, float]], eda: list[tuple[str, float, float]], by_number: bool):
    """Best (rotation, origin x, origin y, worst error mm, worst error of the next-best rotation) mapping EasyEDA pads
    onto the board pads."""
    fits = []
    for deg in (0, 90, 180, 270):
        if by_number:
            k, e = centres(kicad), centres(eda)
            common = sorted(set(k) & set(e))
            pairs = [(k[n], rot(*e[n], deg)) for n in common]
        else:  # geometry: centroid of all pads, then nearest neighbour
            ke = [(x, y) for _, x, y in kicad]
            er = [rot(x, y, deg) for _, x, y in eda]
            kc = (sum(p[0] for p in ke) / len(ke), sum(p[1] for p in ke) / len(ke))
            ec = (sum(p[0] for p in er) / len(er), sum(p[1] for p in er) / len(er))
            pairs = [(min(ke, key=lambda q: math.dist(q, (p[0] - ec[0] + kc[0], p[1] - ec[1] + kc[1]))), p) for p in er]
        cx = sum(a[0] - b[0] for a, b in pairs) / len(pairs)
        cy = sum(a[1] - b[1] for a, b in pairs) / len(pairs)
        fits.append((max(math.dist(a, (b[0] + cx, b[1] + cy)) for a, b in pairs), deg, cx, cy))
    fits.sort()
    err, deg, cx, cy = fits[0]
    return deg, cx, cy, err, fits[1][0]


def placements(parts: list[dict], offline: bool) -> tuple[list[list[str]], list[str], bool]:
    rows, report, ok = [], [], True
    for p in parts:
        if not p["lcsc"] or p["dnp"] or p["exclude_bom"]:
            continue
        if p["side"] != "Top":
            sys.exit(f"{p['ref']}: assembled part on the bottom: not handled (mirrored EasyEDA fit)")
        if offline and not (CACHE / p["lcsc"] / "component.json").exists():
            report.append(f"MISSING {p['ref']:5} {p['lcsc']:10} no cached fab footprint: run once without --offline")
            continue
        title, eda = easyeda_pads(p["lcsc"], offline)
        kicad = [(q["num"], q["x"], q["y"]) for q in p["pads"]]
        knum, enum = set(centres(kicad)), set(centres(eda))
        by_number = (knum == enum or (len(knum & enum) >= 2 and knum & enum == knum)) and p["lcsc"] not in GEOMETRY_OK
        deg, cx, cy, err, next_err = fit(kicad, eda, by_number)
        corr = round(deg - p["rot"]) % 360
        how = "numbers" if by_number else "geometry"
        # OK: every pad within FIT_TOL_MM. LAND: the two libraries draw the lands differently (pad length, odd corner
        # pads) but the rotation is unambiguous (the next-best angle is clearly worse) and no pad is off by more than
        # LAND_TOL_MM; the centre is the least-squares fit of all pads.
        unambiguous = next_err - err >= AMBIGUITY_MM
        status = "OK" if err <= FIT_TOL_MM and unambiguous else "LAND" if err <= LAND_TOL_MM and unambiguous else "FAIL"
        if not by_number:  # geometry fits need a human-confirmed entry; symmetric parts list every valid correction
            want = GEOMETRY_OK.get(p["lcsc"])
            if want is not None and corr in want[0] and err <= LAND_TOL_MM:
                status = "OK" if err <= FIT_TOL_MM else "LAND"
            elif status != "FAIL":
                status = "CHECK"
        if status not in ("OK", "LAND"):
            ok = False
        report.append(f"{status:5} {p['ref']:5} {p['lcsc']:10} {p['footprint'].split(':')[1][:44]:44} vs {title[:38]:38} "
                      f"{how:8} rot {deg:3} (KiCad {p['rot']:g}, corr {corr:3}) "
                      f"offset {math.dist((cx, cy), (p['x'], p['y'])):.2f} mm, worst pad {err:.3f} mm (next angle {next_err:.2f})")
        # JLC's CPL takes KiCad's position-file convention: y up (negated board y), angle counter-clockwise
        rows.append([p["ref"], f"{cx:.4f}mm", f"{-cy:.4f}mm", "Top", f"{deg % 360}"])
    return rows, report, ok


def bom(parts: list[dict]) -> list[list[str]]:
    groups = defaultdict(list)
    for p in parts:
        if p["lcsc"] and not p["dnp"] and not p["exclude_bom"]:
            groups[p["lcsc"]].append(p)
    natural = lambda r: [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", r)]
    rows = []
    for lcsc, ps in sorted(groups.items(), key=lambda g: natural(min((p["ref"] for p in g[1]), key=natural))):
        fps = {p["footprint"].split(":")[1] for p in ps}
        if len(fps) > 1:
            sys.exit(f"{lcsc}: one LCSC number on several footprints {fps}")
        refs = sorted((p["ref"] for p in ps), key=natural)
        rows.append([" / ".join(sorted({p["value"] for p in ps})), ",".join(refs), fps.pop(), lcsc])
    return rows


def main() -> None:
    flags = {a for a in sys.argv[1:] if a.startswith("--")}
    boards = [Path(a).resolve() for a in sys.argv[1:] if not a.startswith("--")]
    fit_only = "--fit-only" in flags
    sha = "" if fit_only else git_sha("--require-clean" in flags)
    py = os.environ.get("KICAD_PYTHON")
    if not py:
        sys.exit("KICAD_PYTHON not set: source scripts/kicad-env.sh")
    failed = False
    for pcb in boards:
        out = OUT / pcb.stem
        out.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            if not fit_only:
                drc_gate(pcb, tmp)
                z = gerbers(pcb, out, sha)
            subprocess.run([py, str(ROOT / "hardware/tools/pcb_parts.py"), str(pcb), str(tmp / "parts.json")],
                           check=True, capture_output=True)
            parts = json.loads((tmp / "parts.json").read_text())
        rows, report, ok = placements(parts, "--offline" in flags)
        if fit_only:  # gate mode (scripts/hw-check.sh): fit report only, no files written
            print("\n".join(r for r in report if not r.startswith("OK ")) or f"{pcb.stem}: all {len(rows)} placements fit")
            print(f"placement fit {pcb.stem}: {'OK' if ok else 'FAILED'}")
            failed |= not ok
            continue
        b = bom(parts)
        with open(out / f"{pcb.stem}-bom.csv", "w", newline="") as f:
            csv.writer(f).writerows([["Comment", "Designator", "Footprint", "LCSC Part #"], *b])
        with open(out / f"{pcb.stem}-cpl.csv", "w", newline="") as f:
            csv.writer(f).writerows([["Designator", "Mid X", "Mid Y", "Layer", "Rotation"], *rows])
        (out / "placement-fit.txt").write_text("\n".join(report) + "\n")
        (out / "VERSION.txt").write_text(f"{pcb.stem} {sha}\n")
        print("\n".join(r for r in report if not r.startswith("OK ")) or f"{pcb.stem}: all {len(rows)} placements fit")
        print(f"{pcb.stem}: {z.name}, {len(b)} BOM lines, {len(rows)} placements -> {out.relative_to(ROOT)}/")
        failed |= not ok
    sys.exit("placement fit: open items above (FAIL = no fit, CHECK = geometry fit not confirmed)" if failed else 0)


if __name__ == "__main__":
    main()
