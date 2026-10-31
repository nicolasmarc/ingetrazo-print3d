"""Gyroid infill under a skin, checked with the package's own analyses."""
import math
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

pytest.importorskip("manifold3d")

from print3d import lattice, mesh3d  # noqa: E402
from shapes import box, tee  # noqa: E402


def test_sheet_wall_matches_the_setting():
    """The wall the sheet gets is the wall asked for (±10 %)."""
    import manifold3d as m3
    cell, wall = 10.0, 0.8
    sheet = m3.Manifold.level_set(lattice.gyroid_field(cell, wall),
                                  [0, 0, 0, 30, 30, 30], 0.25)
    sheet = sheet ^ m3.Manifold.cube([30, 30, 30])
    t = lattice.to_tris(sheet)
    th = mesh3d.wall_thickness(t, 4 * wall, samples_per_tri=1)
    inner = ((t.mean(1) > 3) & (t.mean(1) < 27)).all(1) & np.isfinite(th)
    assert np.median(th[inner]) == pytest.approx(wall, rel=0.1)


def test_infill_keeps_a_closed_skin():
    part = box(0, 0, 0, 40, 30, 20)
    man, info = lattice.infill(part, cell=8.0, wall=0.8, skin=1.5)
    assert man.status().name == "NoError"
    assert info["solid_volume"] == pytest.approx(24000.0, rel=1e-6)
    # much lighter than the solid, much heavier than the skin alone
    skin_only = 24000.0 - 37 * 27 * 17
    assert skin_only < info["volume"] < 0.6 * 24000.0
    t = lattice.to_tris(man)
    lo, hi = t.reshape(-1, 3).min(0), t.reshape(-1, 3).max(0)
    assert np.allclose(lo, 0, atol=1e-3) and np.allclose(hi, [40, 30, 20], atol=1e-3)
    # the outside is untouched: a cut at mid height has the full outline
    polys = lattice.section(man, 10.0)
    outer = max(polys, key=lambda p: abs(_area(p)))
    assert abs(_area(outer)) == pytest.approx(40 * 30, rel=1e-3)
    assert len(polys) > 10                       # and the gyroid inside


def _area(p):
    x, y = p[:, 0], p[:, 1]
    return 0.5 * (np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))


def test_without_skin_the_whole_part_is_gyroid():
    man, info = lattice.infill(box(0, 0, 0, 30, 30, 30), cell=10.0, wall=0.8, skin=0.0)
    assert info["volume"] < 0.3 * 27000


def test_open_part_is_refused():
    part = box(0, 0, 0, 10, 10, 10)[:-2]          # one side missing
    with pytest.raises(lattice.LatticeError):
        lattice.infill(part, cell=5.0, wall=0.8, skin=1.0)


def test_part_thinner_than_its_skin_is_refused():
    with pytest.raises(lattice.LatticeError):
        lattice.infill(box(0, 0, 0, 20, 20, 1.5), cell=5.0, wall=0.8, skin=1.0)


def test_settings_check():
    assert lattice.check({"cell": 6.0, "wall": 0.8, "skin": 1.2}) == []
    assert lattice.check({"cell": 3.0, "wall": 1.5, "skin": 1.2}) == ["too thick"]
    assert lattice.check({"cell": 0.0, "wall": 0.8, "skin": 1.2}) == ["bad"]


def test_non_convex_part():
    man, info = lattice.infill(tee(), cell=6.0, wall=0.8, skin=1.2)
    assert 0.25 < info["volume"] / info["solid_volume"] < 0.75
