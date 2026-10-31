import csv
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CALC = ROOT / "hardware" / "calc"


def run(script, *args):
    return subprocess.run([sys.executable, str(CALC / script), *args], capture_output=True, text=True, cwd=ROOT)


def test_selftests():
    assert "OK" in run("power_budget.py", "--selftest").stdout
    assert "OK" in run("bom_check.py", "--selftest").stdout


def test_bom_has_required_columns_and_no_bad_numbers():
    rows = list(csv.DictReader(open(ROOT / "hardware/weatherstation-v1/bom.csv", newline="")))
    assert {"Comment", "Designator", "Footprint", "Quantity", "LCSC Part #"} <= set(rows[0])
    r = run("bom_check.py", "hardware/weatherstation-v1")
    assert "FAIL" not in r.stdout and r.returncode == 0


def test_strict_fails_while_part_numbers_are_missing():
    assert run("bom_check.py", "hardware/weatherstation-v1", "--strict").returncode == 1
