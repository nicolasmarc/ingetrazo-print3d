"""Hole filling on shapes with a known answer."""
import math
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from print3d import holes, mesh3d  # noqa: E402
from shapes import box  # noqa: E402


def uv_sphere(r=1.0, nu=48, nv=24):
    """A closed sphere, outward triangles."""
    pts = [(0, 0, r)]
    for i in range(1, nv):
        th = math.pi * i / nv
        for j in range(nu):
            ph = 2 * math.pi * j / nu
            pts.append((r * math.sin(th) * math.cos(ph), r * math.sin(th) * math.sin(ph),
                        r * math.cos(th)))
    pts.append((0, 0, -r))
    P = np.array(pts)
    S = len(P) - 1

    def v(i, j):
        return 1 + (i - 1) * nu + (j % nu)
    tris = []
    for j in range(nu):
        tris.append((0, v(1, j), v(1, j + 1)))
        tris.append((S, v(nv - 1, j + 1), v(nv - 1, j)))
    for i in range(1, nv - 1):
        for j in range(nu):
            a, b, c, d = v(i, j), v(i, j + 1), v(i + 1, j + 1), v(i + 1, j)
            tris += [(a, d, c), (a, c, b)]
    t = P[np.array(tris)]
    if mesh3d.signed_volume(t) < 0:
        t = t[:, ::-1]
    return t


def _closed(t):
    _v, idx = mesh3d.weld(t)
    return holes.boundary_loops(idx) == []


def test_a_closed_mesh_has_no_hole():
    assert holes.find(uv_sphere())[2] == []
    assert holes.find(box(0, 0, 0, 1, 1, 1))[2] == []


def test_flat_hole_in_a_box_is_capped_flat():
    t = box(0, 0, 0, 2, 2, 2)
    n, _a = mesh3d.normals_areas(t)
    opened = t[~(n[:, 2] > 0.99)]               # top removed
    verts, idx, loops = holes.find(opened)
    assert len(loops) == 1 and len(loops[0]) == 4
    for smooth in (False, True):
        patch = holes.fill(verts, idx, loops[0], smooth)
        closed = np.concatenate([opened, patch])
        assert _closed(closed)
        assert mesh3d.signed_volume(closed) == pytest.approx(8.0, rel=1e-9)
        assert np.allclose(patch[:, :, 2], 2.0)   # flat stays flat


def test_curved_hole_in_a_sphere_follows_the_sphere():
    s = uv_sphere(1.0, 64, 32)
    c = s.mean(axis=1)
    cut = (c[:, 0] > 0.75)                       # a cap of the sphere
    opened = s[~cut]
    verts, idx, loops = holes.find(opened)
    assert len(loops) == 1
    smooth = holes.fill(verts, idx, loops[0], True)
    flat = holes.fill(verts, idx, loops[0], False)
    for patch in (smooth, flat):
        assert _closed(np.concatenate([opened, patch]))
    exact = mesh3d.signed_volume(s)
    v_smooth = mesh3d.signed_volume(np.concatenate([opened, smooth]))
    v_flat = mesh3d.signed_volume(np.concatenate([opened, flat]))
    # the smooth patch bulges out like the missing cap: much closer
    assert abs(v_smooth - exact) < 0.35 * abs(v_flat - exact)
    r = np.linalg.norm(smooth.reshape(-1, 3), axis=1)
    assert r.max() < 1.03                         # no bump past the sphere
    n, a = mesh3d.normals_areas(smooth)
    folded = (n * smooth.mean(axis=1)).sum(axis=1) < 0
    assert a[folded].sum() < 0.005 * a.sum()     # at most a sliver on the jagged rim


def test_long_curved_slit_and_several_holes():
    s = uv_sphere(1.0, 64, 32)
    c = s.mean(axis=1)
    z = s[:, :, 2]
    x = s[:, :, 0]
    slit = (np.abs(z) <= 0.1).all(axis=1) & (x > 0.3).all(axis=1)   # along the equator
    dot = (z > 0.97).all(axis=1)                                     # at the pole
    opened = s[~(slit | dot)]
    patches, count, failed = holes.fill_all(opened, smooth=True)
    assert count == 2 and failed == 0
    closed = np.concatenate([opened] + patches)
    assert _closed(closed)
    assert mesh3d.signed_volume(closed) == pytest.approx(mesh3d.signed_volume(s), rel=0.01)


def test_patch_faces_outwards():
    s = uv_sphere()
    opened = s[3:]
    patches, _n, _f = holes.fill_all(opened)
    n, _a = mesh3d.normals_areas(patches[0])
    cen = patches[0].mean(axis=1)
    assert ((n * cen).sum(axis=1) > 0).all()


def test_rim_segments_for_drawing():
    t = box(0, 0, 0, 1, 1, 1)[2:]
    segs, loops = holes.rim_segments(t)
    assert segs.shape == (4, 2, 3) and len(loops) == 1


def test_pinched_rim_splits_into_simple_loops():
    assert holes.split_pinched([1, 2, 3, 4, 2, 5, 6]) == [[2, 3, 4], [1, 2, 5, 6]]
    s = uv_sphere(1.0, 48, 24)
    c = s.mean(axis=1)
    holed = s[~((c[:, 0] > 0.85) | (c[:, 2] > 0.95))]
    patches, n, failed = holes.fill_all(holed)
    closed = np.concatenate([holed] + patches)
    _v, idx = mesh3d.weld(closed)
    from collections import Counter
    cnt = Counter()
    for a, b, c2 in idx:
        for u, v in ((a, b), (b, c2), (c2, a)):
            cnt[(min(u, v), max(u, v))] += 1
    assert set(cnt.values()) == {2}               # every edge between two triangles
