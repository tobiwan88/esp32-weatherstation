"""Placement fit of fab_package.py: a footprint turned and moved on the board is found again (angle and origin)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import fab_package as fp  # noqa: E402

# SOT-23-like EasyEDA footprint, origin-relative, y down
EDA = [("1", 1.0, 0.95), ("2", 1.0, -0.95), ("3", -1.0, 0.0)]


def placed(deg, ox, oy):
    return [(n, *(a + b for a, b in zip(fp.rot(x, y, deg), (ox, oy)))) for n, x, y in EDA]


def test_rotation_is_counter_clockwise_seen_from_top():
    # y down: +x turned 90 deg counter-clockwise (as seen) points to -y (up on the screen)
    assert fp.rot(1.0, 0.0, 90) == (0.0, -1.0)


def test_fit_finds_angle_and_origin():
    for deg in (0, 90, 180, 270):
        got_deg, cx, cy, err, next_err = fp.fit(placed(deg, 120.0, 130.5), EDA, by_number=True)
        assert (got_deg, round(cx, 6), round(cy, 6)) == (deg, 120.0, 130.5)
        assert err < 1e-9 and next_err > 1.0


def test_geometry_fit_ignores_pad_names():
    board = [(f"K{n}", x, y) for n, x, y in placed(270, 10.0, 20.0)]
    got_deg, cx, cy, err, _ = fp.fit(board, EDA, by_number=False)
    assert (got_deg, round(cx, 6), round(cy, 6)) == (270, 10.0, 20.0) and err < 1e-9
