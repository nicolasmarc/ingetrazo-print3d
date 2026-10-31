# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Nicolas Marc.
"""Holes of IngeTrazo groups: finding them on a group's own mesh and
closing them, through :mod:`holes`. A component's holes are closed in its
shared definition (every copy gets them closed)."""
from __future__ import annotations

import numpy as np

from . import holes

#: IngeTrazo welds corners closer than this (``core.mesh._KEY_DECIMALS``).
try:
    from core.mesh import _KEY_DECIMALS as _DEC
    WELD = 10.0 ** -_DEC
except Exception:  # noqa: BLE001
    WELD = 1e-4


def matrix(group):
    """The group's placement as a NumPy 4×4 (identity for a classic group)."""
    m = getattr(group, "xform", None)
    if m is None:
        return np.eye(4)
    return np.array(m.data(), float).reshape(4, 4).T


def to_world(group, pts):
    m = matrix(group)
    p = np.asarray(pts, float).reshape(-1, 3)
    return p @ m[:3, :3].T + m[:3, 3]


class GroupHoles:
    """The holes of one group, in its mesh's own coordinates."""

    def __init__(self, group) -> None:
        from .bodies import _triangles
        self.group = group
        faces = [f for f in group.mesh.faces if not getattr(f, "interior", False)
                 and len(set(map(id, getattr(f, "loop", [])))) >= 3]
        self.faces = faces
        tris, _cols, owner, _names = _triangles(faces, None)
        self.tris = tris
        self.owner = owner
        self.verts, self.idx, self.loops = holes.find(tris)

    def rims_world(self):
        """One ``(n, 3)`` closed polyline per hole, in world space."""
        return [to_world(self.group, self.verts[loop]) for loop in self.loops]

    def attrs_near(self, loop):
        """The look of the faces around a hole (the patch wears it)."""
        rim = set(loop)
        hit = np.isin(self.idx, list(rim)).any(axis=1)
        owners = self.owner[np.nonzero(hit)[0]] if len(self.owner) == len(self.idx) else []
        if len(owners):
            k = np.bincount(owners).argmax()
            a = self.faces[int(k)].attrs
            return dict(a) if a else None
        return None


def clean(mesh) -> int:
    """Remove what no surface needs and every hole search trips on: faces
    with fewer than three distinct corners, and a second face over the
    same corners as another. Returns how many went."""
    seen = set()
    gone = []
    for f in list(mesh.faces):
        corners = frozenset(map(id, getattr(f, "loop", [])))
        if len(corners) < 3 or corners in seen:
            gone.append(f)
        else:
            seen.add(corners)
    for f in gone:
        mesh.remove_face(f)
    return len(gone)


def fill_group(group, smooth: bool = True, only=None) -> dict:
    """Close the holes of ``group`` (all of them, or the loops whose
    index is in ``only``). Adds faces to the group's mesh; returns
    ``{"filled", "failed", "faces"}``. The caller snapshots for undo."""
    from PySide6.QtGui import QVector3D
    mesh = group.mesh
    cleaned = clean(mesh) if only is None else 0
    gh = GroupHoles(group)
    filled = failed = added = 0
    for k, loop in enumerate(gh.loops):
        if only is not None and k not in only:
            continue
        rim = gh.verts[loop]
        attrs = gh.attrs_near(loop)
        try:
            if holes.is_flat(rim):
                # a hole in a flat face: one flat face, as drawn by hand
                faces = [mesh.add_face([QVector3D(*map(float, p)) for p in rim])]
            else:
                patch = holes.fill(gh.verts, gh.idx, loop, smooth=smooth, quantum=WELD)
                faces = [mesh.add_face([QVector3D(*map(float, p)) for p in tri])
                         for tri in patch]
        except Exception:  # noqa: BLE001 — one odd hole never stops the rest
            failed += 1
            continue
        for f in faces:
            if attrs:
                f.attrs = dict(attrs)
        if len(faces) > 1:
            # inside a smooth patch the seams are soft, as on IngeTrazo's
            # own curved surfaces: the patch reads as one surface
            new = set(map(id, faces))
            for e in _edges(mesh, faces):
                if len(e.faces) == 2 and all(id(x) in new for x in e.faces):
                    e.soft = True
        filled += 1
        added += len(faces)
    return {"filled": filled, "failed": failed, "faces": added, "cleaned": cleaned}


def _edges(mesh, faces):
    out = set()
    for f in faces:
        loop = list(getattr(f, "loop", []))
        for i in range(len(loop)):
            e = mesh.find_edge(loop[i], loop[(i + 1) % len(loop)])
            if e is not None:
                out.add(e)
    return out
