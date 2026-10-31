# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Nicolas Marc.
"""Gyroid infill under a skin — no Qt.

The gyroid is the triply periodic minimal surface
``G = sin kx cos ky + sin ky cos kz + sin kz cos kx`` (k = 2π / cell).
The sheet ``|G| < t`` is a wall of nearly even thickness; measured on the
sheet, ``t ≈ 1.47 · k · wall / 2`` (fitted once against the wall
thickness check of :mod:`mesh3d`, see the tests).

The part (a closed triangle mesh, in print millimetres) is kept as a skin
of the chosen thickness: the part eroded by a ball (a Minkowski
difference) is the inside, filled with the gyroid sheet; the skin is the
part minus that inside. Meshing and booleans are done by manifold3d, the
library IngeTrazo itself ships for its Solid Tools.
"""
from __future__ import annotations

import math

import numpy as np

from .lang import N_

#: Sheet parameter ↔ wall thickness (see the module text and the tests).
WALL_FACTOR = 1.47
#: Above this the sheet closes up into a solid block.
T_MAX = 1.1


class Cancelled(Exception):
    """The user stopped the computation."""


class LatticeError(Exception):
    """The part cannot take an infill (open, too thin, too big...).
    ``key`` is the English text, ``kw`` its values (the panel translates)."""

    def __init__(self, key: str, **kw) -> None:
        super().__init__(key.format(**kw) if kw else key)
        self.key = key
        self.kw = kw


#: Triangles of a gyroid sheet ≈ TRI_FACTOR · volume / (cell · res²),
#: measured on manifold3d's mesher (see the tests).
TRI_FACTOR = 40.0
#: Beyond this the file, the slicer and IngeTrazo's memory suffer.
MAX_TRIANGLES = 2_000_000
#: Points the mesher asks the gyroid for (one Python call each, ~5 µs).
MAX_POINTS = 3_000_000


def plan(size, cell: float, wall: float, volume: float | None = None):
    """``(resolution, estimated triangles)`` for a part of ``volume``
    (mm³) in a box of ``size`` (mm): the mesher samples the whole box, the
    triangles follow the part. Fine enough for the wall where the budget
    allows, coarser for a big part, refused when even a coarse mesh would
    be too heavy."""
    box = float(np.prod(np.maximum(np.asarray(size, float), 1e-9)))
    vol = box if volume is None else min(float(volume), box)
    res = max(min(wall / 2.0, cell / 12.0), 0.05)
    coarsest = max(min(wall * 1.25, cell / 6.0), res)

    def tris(r):
        return TRI_FACTOR * vol / (cell * r * r)

    def points(r):
        return 2.0 * box / r ** 3
    while (tris(res) > MAX_TRIANGLES or points(res) > MAX_POINTS) and res < coarsest:
        res = min(res * 1.15, coarsest)
    if tris(res) > MAX_TRIANGLES or points(res) > MAX_POINTS:
        raise LatticeError(N_("too big for this cell: about {n} million triangles, take a larger cell"),
                           n=f"{tris(res) / 1e6:.1f}")
    return res, tris(res)


def sheet_level(cell: float, wall: float) -> float:
    k = 2.0 * math.pi / cell
    return WALL_FACTOR * k * wall / 2.0


def check(params) -> list[str]:
    """Problems with a setting, as English keys (the panel translates)."""
    out = []
    if params["wall"] <= 0 or params["cell"] <= 0 or params["skin"] < 0:
        out.append("bad")
    elif sheet_level(params["cell"], params["wall"]) > T_MAX:
        out.append("too thick")
    return out


def _manifold():
    try:
        import manifold3d
    except ImportError as exc:      # pragma: no cover - IngeTrazo ships it
        raise LatticeError(N_("no manifold3d")) from exc
    return manifold3d


def to_manifold(tris):
    m3 = _manifold()
    from . import mesh3d
    keep = mesh3d.drop_degenerate(tris)
    verts, idx = mesh3d.weld(np.asarray(tris, float)[keep], quantum=1e-5)
    good = (idx[:, 0] != idx[:, 1]) & (idx[:, 1] != idx[:, 2]) & (idx[:, 0] != idx[:, 2])
    mesh = m3.Mesh(vert_properties=np.ascontiguousarray(verts, np.float32),
                   tri_verts=np.ascontiguousarray(idx[good], np.uint32))
    man = m3.Manifold(mesh)
    if man.status() != m3.Error.NoError or man.is_empty():
        raise LatticeError(N_("not watertight"))
    if man.volume() < 0:
        raise LatticeError(N_("not watertight"))
    return man


def to_tris(man) -> np.ndarray:
    me = man.to_mesh()
    v = np.asarray(me.vert_properties, float)[:, :3]
    t = np.asarray(me.tri_verts, np.int64)
    return v[t]


def gyroid_field(cell: float, wall: float):
    k = 2.0 * math.pi / cell
    t = sheet_level(cell, wall)
    sin, cos = math.sin, math.cos

    def f(x, y, z):
        return t - abs(sin(k * x) * cos(k * y) + sin(k * y) * cos(k * z)
                       + sin(k * z) * cos(k * x))
    return f


def infill(tris, cell: float, wall: float, skin: float,
           resolution: float | None = None, ball_segments: int = 8, progress=None):
    """The part with its inside turned into a gyroid sheet.

    ``tris``: the closed part in millimetres. Returns a manifold3d
    ``Manifold`` (``to_tris`` for triangles) and a dict of figures:
    ``{"volume", "solid_volume", "triangles"}``.

    ``progress(stage, fraction)`` — ``stage`` an English text, ``fraction``
    0..1 or ``None`` when unknown — is called along the way; returning
    ``False`` stops with :class:`Cancelled`. The mesher asks the gyroid for
    each grid point, which is what drives the fraction."""
    def report(stage, frac=None):
        if progress is not None and progress(stage, frac) is False:
            raise Cancelled()
    m3 = _manifold()
    pts = np.asarray(tris, float).reshape(-1, 3)
    part = to_manifold(tris)
    solid = part.volume()
    res_planned, _est = plan(pts.max(0) - pts.min(0), cell, wall, solid)
    report(N_("Skin…"))
    if skin > 0:
        # the inside only bounds the gyroid: a copy simplified to an eighth
        # of the skin is eroded (the erosion costs the product of the face
        # counts: 30 s → 7 s on a 20 000-triangle bunny), the outside of the
        # part stays exactly as modelled
        rough = part.simplify(skin / 8.0) if hasattr(part, "simplify") else part
        inner = rough.minkowski_difference(m3.Manifold.sphere(skin, ball_segments))
    else:
        inner = part
    if inner.is_empty() or inner.volume() <= 0:
        raise LatticeError(N_("too thin"))
    res = resolution or res_planned
    lo = np.array(inner.bounding_box()[:3]) - res
    hi = np.array(inner.bounding_box()[3:]) + res
    field = gyroid_field(cell, wall)
    if progress is not None:
        expected = max(2.4 * float(np.prod(hi - lo)) / res ** 3, 1.0)
        count = [0]
        base = field

        def field(x, y, z):               # noqa: F811 — the counted one
            count[0] += 1
            if count[0] % 4000 == 0:
                report(N_("Gyroid…"), min(count[0] / expected, 0.99))
            return base(x, y, z)
        report(N_("Gyroid…"), 0.0)
    sheet = m3.Manifold.level_set(field, [*lo.tolist(), *hi.tolist()], res)
    report(N_("Assembling…"))
    out = (part - inner) + (inner ^ sheet) if skin > 0 else (part ^ sheet)
    n_tri = out.num_tri()                 # the booleans run here
    report(N_("Assembling…"), 1.0)
    return out, {"volume": out.volume(), "solid_volume": solid, "triangles": n_tri}


def section(man, z: float):
    """Polygons (lists of ``(x, y)``) of the cut at height ``z``."""
    cs = man.slice(z)
    return [np.asarray(p, float) for p in cs.to_polygons()]
