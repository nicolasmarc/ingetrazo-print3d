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


class LatticeError(Exception):
    """The part cannot take an infill (open, too thin...)."""


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
           resolution: float | None = None, ball_segments: int = 12):
    """The part with its inside turned into a gyroid sheet.

    ``tris``: the closed part in millimetres. Returns a manifold3d
    ``Manifold`` (``to_tris`` for triangles) and a dict of figures:
    ``{"volume", "solid_volume", "triangles"}``."""
    m3 = _manifold()
    part = to_manifold(tris)
    solid = part.volume()
    if skin > 0:
        inner = part.minkowski_difference(m3.Manifold.sphere(skin, ball_segments))
    else:
        inner = part
    if inner.is_empty() or inner.volume() <= 0:
        raise LatticeError(N_("too thin"))
    res = resolution or max(min(wall / 2.0, cell / 12.0), 0.05)
    lo = np.array(inner.bounding_box()[:3]) - res
    hi = np.array(inner.bounding_box()[3:]) + res
    sheet = m3.Manifold.level_set(gyroid_field(cell, wall),
                                  [*lo.tolist(), *hi.tolist()], res)
    out = (part - inner) + (inner ^ sheet) if skin > 0 else (part ^ sheet)
    return out, {"volume": out.volume(), "solid_volume": solid,
                 "triangles": out.num_tri()}


def section(man, z: float):
    """Polygons (lists of ``(x, y)``) of the cut at height ``z``."""
    cs = man.slice(z)
    return [np.asarray(p, float) for p in cs.to_polygons()]
