"""The analyses on cases with a known answer."""
import math
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from print3d import mesh3d as m  # noqa: E402
from shapes import box, tee, tube  # noqa: E402


def test_cube_volume_and_normals_point_out():
    c = box(0, 0, 0, 2, 3, 4)
    assert m.signed_volume(c) == pytest.approx(24.0)
    n, a = m.normals_areas(c)
    assert a.sum() == pytest.approx(2 * (6 + 8 + 12))
    cen = c.mean(axis=1) - np.array([1, 1.5, 2])
    assert np.all((n * cen).sum(axis=1) > 0)


def test_tube_volume_matches_the_annulus():
    t = tube(10, 8, 5, n=360)
    exact = math.pi * (100 - 64) * 5
    assert m.signed_volume(t) == pytest.approx(exact, rel=1e-3)


def test_cube_on_the_bed_has_no_overhang():
    c = box(0, 0, 0, 1, 1, 1)
    assert not m.overhangs(c).any()


def test_floating_cube_bottom_overhangs():
    c = box(0, 0, 0, 1, 1, 1)
    level = -1.0                       # the bed is lower: the cube floats
    over = m.overhangs(c, level=level)
    n, a = m.normals_areas(c)
    assert a[over].sum() == pytest.approx(1.0)
    assert np.allclose(n[over], [0, 0, -1])


def test_tee_overhang_is_the_underside_of_the_bar():
    t = tee()
    over = m.overhangs(t)
    _n, a = m.normals_areas(t)
    # bar underside 50 × 10 minus the 10 × 10 where the post meets it
    # (the two boxes touch there; that face still points down)
    assert a[over].sum() == pytest.approx(50 * 10)


def test_limit_angle():
    # a 30° roof seen from below: normal 30° from straight down
    th = math.radians(30)
    tri = np.array([[[0, 0, 1], [0, 1, 1], [1, 0, 1 + math.tan(th)]]], float)
    tri = tri[:, ::-1] if (m.normals_areas(tri)[0] @ [0, 0, 1])[0] > 0 else tri
    # 30° from horizontal = 60° from vertical: supported only when the
    # limit is above 60°
    assert m.overhangs(tri, level=-1, limit_deg=45).all()
    assert not m.overhangs(tri, level=-1, limit_deg=65).any()


def test_wall_thickness_of_a_thin_plate():
    plate = box(0, 0, 0, 20, 20, 0.6)
    th = m.wall_thickness(plate, min_wall=0.8)
    n, _a = m.normals_areas(plate)
    big = np.abs(n[:, 2]) > 0.9
    assert np.allclose(th[big], 0.6, atol=1e-6)
    thick = box(0, 0, 0, 20, 20, 2.0)
    assert np.isinf(m.wall_thickness(thick, min_wall=0.8)).all()


def test_tube_wall_is_measured():
    t = tube(10, 9.5, 20, n=180)
    th = m.wall_thickness(t, min_wall=1.0)
    n, _a = m.normals_areas(t)
    side = np.abs(n[:, 2]) < 0.1
    assert np.nanmedian(th[side]) == pytest.approx(0.5, abs=0.01)


def test_concave_corner_is_not_a_thin_wall():
    l_shape = np.concatenate([box(0, 0, 0, 10, 10, 2), box(0, 0, 2, 2, 10, 10)])
    th = m.wall_thickness(l_shape, min_wall=1.0)
    assert np.isinf(th).all()


def test_shells_and_cavity():
    outer = box(0, 0, 0, 10, 10, 10)
    void = box(3, 3, 3, 6, 6, 6, inward=True)
    lone = box(20, 0, 0, 21, 1, 1)
    t = np.concatenate([outer, void, lone])
    assert m.shells(t).max() == 2
    cav = m.cavities(t)
    assert len(cav) == 1
    assert cav[0]["volume"] == pytest.approx(27.0)
    assert np.allclose(cav[0]["centre"], [4.5, 4.5, 4.5], atol=1.6)


def test_no_cavity_in_a_tube():
    assert m.cavities(tube(10, 8, 5)) == []


def test_gaps_between_bodies():
    a = box(0, 0, 0, 10, 10, 10)
    b = box(10.2, 0, 0, 20, 10, 10)       # 0.2 apart
    c = box(10, 20, 0, 20, 30, 10)        # far
    d = box(5, 5, 10, 8, 8, 12)           # sits on a: touching
    g = m.gaps([a, b, c, d], limit=0.5)
    pairs = {(x["a"], x["b"]): x["distance"] for x in g}
    assert pairs[(0, 1)] == pytest.approx(0.2)
    assert pairs[(0, 3)] == pytest.approx(0.0, abs=1e-9)
    assert (0, 2) not in pairs and (1, 2) not in pairs


def test_point_triangle_distance():
    a = np.array([[0, 0, 0.]]); b = np.array([[1, 0, 0.]]); c = np.array([[0, 1, 0.]])
    d, cp = m.point_tri_distance(np.array([[0.2, 0.2, 3.0]]), a, b, c)
    assert d[0] == pytest.approx(3.0)
    d, cp = m.point_tri_distance(np.array([[2.0, 0.0, 0.0]]), a, b, c)
    assert d[0] == pytest.approx(1.0) and np.allclose(cp[0], [1, 0, 0])


def test_extents_and_fits():
    c = box(0, 0, 0, 0.3, 0.1, 0.2)
    assert np.allclose(m.extents(c), [0.3, 0.1, 0.2])
    assert m.fits([300, 100, 200], [220, 320, 250]) == {"fits": True, "turned": True}
    assert m.fits([300, 100, 200], [220, 220, 250])["fits"] is False


def test_best_orientation_of_a_tee():
    best = m.orientations(tee(), limit_deg=45, count=3)
    assert len(best) == 3
    # flat on its broad side (±Y): no support, the lowest print
    for b in best[:2]:
        assert abs(b["up"][1]) == pytest.approx(1.0)
        assert b["support_volume"] == pytest.approx(0.0)
        assert b["height"] == pytest.approx(10.0)
        assert b["base_area"] == pytest.approx(800.0)
    # then upside down, standing on the bar
    assert np.allclose(best[2]["up"], [0, 0, -1], atol=1e-9)
    assert best[2]["base_area"] == pytest.approx(500.0)


def test_orientation_prefers_a_flat_base_to_a_balancing_act():
    # a plain cube: every tilted direction has no overhang either, but it
    # would stand on an edge
    best = m.orientations(box(0, 0, 0, 1, 1, 1), count=3)
    assert all(b["base_area"] == pytest.approx(1.0) for b in best)


def test_rotation_between_and_rotate():
    axis, deg = m.rotation_between([0, 0, 1], [0, 0, -1])
    assert deg == pytest.approx(180)
    p = m.rotate([[0, 0, 1]], axis, deg)
    assert np.allclose(p, [[0, 0, -1]], atol=1e-12)
    axis, deg = m.rotation_between([1, 0, 0], [0, 0, -1])
    assert np.allclose(m.rotate([[1, 0, 0]], axis, deg), [[0, 0, -1]], atol=1e-12)


def test_stacked_blocks_are_not_overhangs_nor_thin():
    # three courses of blocks, each a closed box, in one body
    t = np.concatenate([box(0, 0, z, 10, 2, z + 1) for z in range(3)])
    over = m.overhangs(t)
    assert over.sum() == 4                 # the two hidden undersides
    held = m.touching(t[over], t)
    assert held.all()
    th = m.wall_thickness(t, min_wall=1.5, tol=1e-4)
    n, _a = m.normals_areas(t)
    flat = np.abs(n[:, 2]) > 0.9
    assert np.isinf(th[flat]).all()        # the stacked faces are not walls


def test_a_real_overhang_is_not_touching():
    t = tee()
    over = m.overhangs(t)
    assert not m.touching(t[over], t).any()


def test_a_solid_sunk_into_another_is_not_a_cavity():
    t = np.concatenate([box(0, 0, 0, 10, 10, 10), box(3, 3, 3, 6, 6, 6)])
    assert m.cavities(t) == []
