# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Nicolas Marc.
"""The model as bodies to print: one per top-level group (its nested
groups folded in), in world coordinates (metres), with the colour each
triangle shows. Reads IngeTrazo's document; changes nothing."""
from __future__ import annotations

import numpy as np

DEFAULT_RGB = (0.80, 0.80, 0.80)
_TEXTURE_RGB: dict = {}


class Body:
    __slots__ = ("name", "group", "tris", "colours", "colour_names", "faces",
                 "tri_face")

    def __init__(self, name, group, tris, colours, colour_names, faces, tri_face):
        self.name = name
        self.group = group              # None for the loose geometry
        self.tris = tris                # (M, 3, 3) metres, world
        self.colours = colours          # (M, 3) sRGB 0..1
        self.colour_names = colour_names
        self.faces = faces              # the world-mesh faces (for picking)
        self.tri_face = tri_face        # (M,) index into faces


def texture_rgb(path):
    """Mean colour of a texture image (cached); ``None`` if unreadable."""
    if not path:
        return None
    if path in _TEXTURE_RGB:
        return _TEXTURE_RGB[path]
    rgb = None
    try:
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QImage
        img = QImage(str(path))
        if not img.isNull():
            img = img.scaled(32, 32, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
            img = img.convertToFormat(QImage.Format_RGBA8888)
            buf = np.frombuffer(bytes(img.constBits()), np.uint8)
            px = buf[: 32 * 32 * 4].reshape(-1, 4).astype(float)
            w = px[:, 3] / 255.0
            if w.sum() > 0:
                rgb = tuple((px[:, :3] * w[:, None]).sum(0) / w.sum() / 255.0)
    except Exception:  # noqa: BLE001 — a missing texture is only grey
        rgb = None
    _TEXTURE_RGB[path] = rgb
    return rgb


def face_rgb(attrs):
    """``(rgb, name)`` a face shows: its colour, else its texture's mean."""
    attrs = attrs or {}
    name = attrs.get("mat")
    col = attrs.get("color")
    if col is not None and len(col) >= 3:
        return tuple(float(c) for c in col[:3]), name
    tex = attrs.get("texture") or {}
    rgb = texture_rgb(tex.get("path"))
    if rgb is not None:
        return rgb, name
    return DEFAULT_RGB, name


def _shown(attrs, material):
    try:
        from core.materials import effective_attrs
        return effective_attrs(attrs, material) if material else attrs
    except Exception:  # noqa: BLE001
        return attrs


def _triangles(faces, paint, drop_slivers: bool = True):
    """Every face's triangles, facing the face's own side; colours per
    triangle. Bodies keep the slivers (``drop_slivers=False``): a closed
    surface without its thinnest triangles is no longer closed, and the
    gyroid infill refused a bunny the analysis called watertight. A triangle face (most of an STL) is taken as it is; other
    faces go through IngeTrazo's triangulation, turned by one vectorised
    test at the end."""
    from formats.meshexport import export_triangles
    tris, cols, owner, names, fnorm = [], [], [], {}, []
    style: dict = {}
    for i, f in enumerate(faces):
        if getattr(f, "interior", False):
            continue
        key = id(f.attrs) if f.attrs is not None else None
        hit = style.get(key)
        if hit is None:
            hit = style[key] = face_rgb(_shown(f.attrs, paint))
        rgb, mat = hit
        loop = getattr(f, "loop", None)
        if loop is not None and len(loop) == 3 and not getattr(f, "hole_loops", None):
            tris.append([v.position.toTuple() for v in loop])
            cols.append(rgb)
            owner.append(i)
            fnorm.append(None)
        else:
            n = f.normal()
            nv = (n.x(), n.y(), n.z())
            src = export_triangles(f) if drop_slivers else f.triangulate()
            for a, b, c in src:
                tris.append([a.toTuple(), b.toTuple(), c.toTuple()])
                cols.append(rgb)
                owner.append(i)
                fnorm.append(nv)
        if mat:
            from .export import hex_colour
            names.setdefault(hex_colour(rgb), str(mat))
    t = np.array(tris, float).reshape(-1, 3, 3)
    poly = np.array([k for k, nv in enumerate(fnorm) if nv is not None], np.int64)
    if len(poly):
        nv = np.array([fnorm[k] for k in poly], float)
        tt = t[poly]
        n = np.cross(tt[:, 1] - tt[:, 0], tt[:, 2] - tt[:, 0])
        flip = poly[(n * nv).sum(axis=1) < 0]
        t[flip] = t[flip][:, ::-1]
    if drop_slivers and len(t):
        tri_faces = np.array([nv is None for nv in fnorm], bool)
        area = 0.5 * np.linalg.norm(np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0]), axis=1)
        keep = ~tri_faces | (area >= 1e-9)
        t = t[keep]
        cols = np.asarray(cols, float).reshape(-1, 3)[keep]
        owner = np.asarray(owner, np.int64)[keep]
        return t, cols, owner, names
    return t, np.array(cols, float).reshape(-1, 3), np.array(owner, np.int64), names


def group_name(g, i: int) -> str:
    name = getattr(g, "name", "") or ""
    comp = getattr(g, "component", None)
    if not name and comp is not None:
        name = getattr(comp, "name", "") or ""
    return name or f"Body {i + 1}"


def candidate_groups(scene, selected_only: bool = True):
    """Top-level groups to print: the selected ones, else every visible
    one. Figures (face-me billboards) are never parts."""
    groups = [g for g in getattr(scene, "groups", [])
              if scene.entity_visible(g) and not getattr(g, "billboard", False)]
    if selected_only:
        sel = [g for g in groups if g in scene.selection]
        if sel:
            return sel, True
    return groups, False


def collect(scene, selected_only: bool = True, loose: bool = True):
    """``(bodies, from_selection)``."""
    from core.group import world_mesh
    groups, from_sel = candidate_groups(scene, selected_only)
    bodies = []
    for i, g in enumerate(groups):
        wm = world_mesh(g)
        faces = list(wm.faces)
        t, c, owner, names = _triangles(faces, getattr(g, "material", None), drop_slivers=False)
        if len(t):
            bodies.append(Body(group_name(g, i), g, t, c, names, faces, owner))
    if loose and not from_sel:
        lm = getattr(scene, "loose_mesh", None)
        faces = [f for f in (lm.faces if lm is not None else [])
                 if scene.entity_visible(f)]
        if faces:
            t, c, owner, names = _triangles(faces, None, drop_slivers=False)
            if len(t):
                bodies.append(Body(None, None, t, c, names, faces, owner))
    return bodies, from_sel


def watertight(body) -> bool:
    """IngeTrazo's rule (``core.solids.solid_report``: every edge between
    exactly two faces, a volume), checked on the group's own mesh edges —
    without the volume pass, which the analyses do not need."""
    if body.group is None:
        return False
    try:
        mesh = body.group.mesh
        if getattr(body.group, "children", None):
            from core.group import world_mesh
            mesh = world_mesh(body.group)
        if not mesh.faces:
            return False
        for e in mesh.edges:
            if sum(1 for f in e.faces if not getattr(f, "interior", False)) != 2:
                return False
        return True
    except Exception:  # noqa: BLE001
        return False
