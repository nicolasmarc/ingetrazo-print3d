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


def _triangles(faces, paint):
    from formats.meshexport import export_triangles
    tris, cols, owner, names = [], [], [], {}
    for i, f in enumerate(faces):
        if getattr(f, "interior", False):
            continue
        n = f.normal()
        nv = (n.x(), n.y(), n.z())
        rgb, mat = face_rgb(_shown(f.attrs, paint))
        for a, b, c in export_triangles(f):
            p = ((a.x(), a.y(), a.z()), (b.x(), b.y(), b.z()), (c.x(), c.y(), c.z()))
            u = np.subtract(p[1], p[0])
            v = np.subtract(p[2], p[0])
            if np.dot(np.cross(u, v), nv) < 0:
                p = (p[0], p[2], p[1])
            tris.append(p)
            cols.append(rgb)
            owner.append(i)
        if mat:
            from .export import hex_colour
            names.setdefault(hex_colour(rgb), str(mat))
    t = np.array(tris, float).reshape(-1, 3, 3)
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
        t, c, owner, names = _triangles(faces, getattr(g, "material", None))
        if len(t):
            bodies.append(Body(group_name(g, i), g, t, c, names, faces, owner))
    if loose and not from_sel:
        lm = getattr(scene, "loose_mesh", None)
        faces = [f for f in (lm.faces if lm is not None else [])
                 if scene.entity_visible(f)]
        if faces:
            t, c, owner, names = _triangles(faces, None)
            if len(t):
                bodies.append(Body(None, None, t, c, names, faces, owner))
    return bodies, from_sel


def watertight(body) -> bool:
    """IngeTrazo's own rule (``core.solids.solid_report``)."""
    if body.group is None:
        return False
    try:
        from core.group import world_mesh
        from core.solids import solid_report
        return bool(solid_report(world_mesh(body.group))[0])
    except Exception:  # noqa: BLE001
        return False
