# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Nicolas Marc.
"""3MF and binary STL writers — pure Python + NumPy, no Qt.

3MF follows the 3MF Core Specification (3MF Consortium, public): an OPC
zip with ``[Content_Types].xml``, ``_rels/.rels`` and ``3D/3dmodel.model``.
Each body becomes one ``object`` with its own welded vertices, and its
colours one ``basematerials`` group (a colour per triangle through
``pid`` / ``p1``). Units: millimetres. Both writers take the triangles
already placed at print size and orientation.
"""
from __future__ import annotations

import struct
import zipfile
from xml.sax.saxutils import escape, quoteattr

import numpy as np

from . import mesh3d

_CT = ('<?xml version="1.0" encoding="UTF-8"?>\n'
       '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
       '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
       '<Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>'
       '</Types>\n')
_RELS = ('<?xml version="1.0" encoding="UTF-8"?>\n'
         '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
         '<Relationship Target="/3D/3dmodel.model" Id="rel0" '
         'Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>'
         '</Relationships>\n')
_NS = "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"
_DEFAULT_RGB = (0.80, 0.80, 0.80)


def hex_colour(rgb) -> str:
    r, g, b = (int(round(255 * min(max(float(c), 0.0), 1.0))) for c in list(rgb)[:3])
    return f"#{r:02X}{g:02X}{b:02X}FF"


def _clean(tris, colours):
    t = mesh3d.as_tris(tris)
    keep = mesh3d.drop_degenerate(t)
    cols = None if colours is None else np.asarray(colours, float)[keep]
    return t[keep], cols


def _num(v: float) -> str:
    s = f"{v:.6f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def write_3mf(path, bodies, app_name: str = "IngeTrazo 3D Print") -> dict:
    """``bodies``: ``[{"name", "tris" (M,3,3) mm, "colours" (M,3) 0..1 or
    None}]``. Returns counts ``{"objects", "triangles"}``."""
    res, items = [], []
    next_id = 1
    n_tri = 0
    for body in bodies:
        t, cols = _clean(body["tris"], body.get("colours"))
        if not len(t):
            continue
        if cols is None:
            cols = np.tile(_DEFAULT_RGB, (len(t), 1))
        keys = [hex_colour(c) for c in cols]
        palette = list(dict.fromkeys(keys))
        pidx = {k: i for i, k in enumerate(palette)}
        mat_id = next_id
        obj_id = next_id + 1
        next_id += 2
        names = body.get("colour_names") or {}
        res.append(f'<basematerials id="{mat_id}">' + "".join(
            f'<base name={quoteattr(names.get(k, k))} displaycolor="{k}"/>'
            for k in palette) + "</basematerials>")
        verts, idx = mesh3d.weld(t, quantum=1e-6)
        parts = [f'<object id="{obj_id}" type="model" name={quoteattr(str(body.get("name") or "Body"))} '
                 f'pid="{mat_id}" pindex="0"><mesh><vertices>']
        parts += [f'<vertex x="{_num(x)}" y="{_num(y)}" z="{_num(z)}"/>' for x, y, z in verts]
        parts.append("</vertices><triangles>")
        for (a, b, c), k in zip(idx, keys):
            if a == b or b == c or a == c:
                continue                      # collapsed by the weld
            parts.append(f'<triangle v1="{a}" v2="{b}" v3="{c}" pid="{mat_id}" p1="{pidx[k]}"/>')
            n_tri += 1
        parts.append("</triangles></mesh></object>")
        res.append("".join(parts))
        items.append(f'<item objectid="{obj_id}"/>')
    model = ('<?xml version="1.0" encoding="UTF-8"?>\n'
             f'<model unit="millimeter" xml:lang="en-US" xmlns="{_NS}">'
             f'<metadata name="Application">{escape(app_name)}</metadata>'
             "<resources>" + "".join(res) + "</resources>"
             "<build>" + "".join(items) + "</build></model>\n")
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", _CT)
        z.writestr("_rels/.rels", _RELS)
        z.writestr("3D/3dmodel.model", model)
    return {"objects": len(items), "triangles": n_tri}


def write_stl(path, bodies, header: str = "IngeTrazo 3D Print") -> int:
    """Binary STL of every body together (STL has no objects nor colours).
    Returns the triangle count."""
    allt = [_clean(b["tris"], None)[0] for b in bodies]
    t = np.concatenate(allt) if allt else np.zeros((0, 3, 3))
    n, _a = mesh3d.normals_areas(t)
    rec = np.zeros(len(t), dtype=[("n", "<f4", 3), ("v", "<f4", (3, 3)), ("attr", "<u2")])
    rec["n"] = n
    rec["v"] = t
    with open(path, "wb") as f:
        f.write(header.encode("ascii", "replace")[:80].ljust(80, b" "))
        f.write(struct.pack("<I", len(t)))
        f.write(rec.tobytes())
    return len(t)
