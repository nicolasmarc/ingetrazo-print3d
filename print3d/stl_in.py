# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Nicolas Marc.
"""STL import for printing — reading, then making the mesh survive
IngeTrazo's weld. No Qt.

IngeTrazo merges corners closer than 0.1 mm (``core.mesh``). A fine STL
in millimetres has triangles smaller than that: merged blindly, they
collapse into faces with two corners, doubled faces and edges between four
faces. Here the mesh is cleaned *before* it reaches IngeTrazo: corners
that coincide exactly are joined, then every edge shorter than the weld
(times a margin) is collapsed in a way that keeps the surface a surface
(the link condition: the two ends share no neighbour but the corners of
the triangles on that edge) and never turns a triangle over. What is
lost is finer than any printer draws.
"""
from __future__ import annotations

import struct

import numpy as np

from . import mesh3d

#: Metres per file unit, as the import dialog offers them.
UNITS = {"mm": 0.001, "cm": 0.01, "m": 1.0, "in": 0.0254}


def read_stl(path) -> np.ndarray:
    """Triangles ``(M, 3, 3)`` in the file's own unit (binary or ASCII)."""
    data = open(path, "rb").read()
    if len(data) >= 84:
        (n,) = struct.unpack_from("<I", data, 80)
        if 84 + 50 * n == len(data):
            rec = np.frombuffer(data, dtype=np.dtype([("n", "<f4", 3), ("v", "<f4", (3, 3)),
                                                      ("a", "<u2")]), count=n, offset=84)
            return rec["v"].astype(float)
    text = data.decode("ascii", "replace")
    pts = []
    for line in text.splitlines():
        parts = line.split()
        if len(parts) == 4 and parts[0].lower() == "vertex":
            pts.append([float(x) for x in parts[1:]])
    if not pts or len(pts) % 3:
        raise ValueError("not an STL file")
    return np.asarray(pts, float).reshape(-1, 3, 3)


def _edges(T):
    E = np.concatenate([T[:, [0, 1]], T[:, [1, 2]], T[:, [2, 0]]])
    return np.unique(np.sort(E, axis=1), axis=0)


def collapse_short_edges(V, T, min_len: float, passes: int = 30):
    """Collapse the edges shorter than ``min_len``; returns ``(V, T, n)``."""
    V = np.asarray(V, float).copy()
    T = np.asarray(T, np.int64).copy()
    total = 0
    for _ in range(passes):
        E = _edges(T)
        L = np.linalg.norm(V[E[:, 0]] - V[E[:, 1]], axis=1)
        order = np.argsort(L)
        order = order[L[order] < min_len]
        if not len(order):
            break
        vt = [[] for _ in range(len(V))]
        for k, tri in enumerate(T.tolist()):
            for v in tri:
                vt[v].append(k)
        # rim corners: on an edge used by one triangle
        Ed = np.sort(np.concatenate([T[:, [0, 1]], T[:, [1, 2]], T[:, [2, 0]]]), axis=1)
        uniq, cnt = np.unique(Ed, axis=0, return_counts=True)
        rim_edges = {tuple(e) for e in uniq[cnt == 1].tolist()}
        on_rim = np.zeros(len(V), bool)
        for a, b in rim_edges:
            on_rim[a] = on_rim[b] = True
        alive = np.ones(len(T), bool)
        locked = np.zeros(len(V), bool)
        Tl = T.tolist()
        done = 0
        for u, v in E[order].tolist():
            if locked[u] or locked[v]:
                continue
            tu = [k for k in vt[u] if alive[k]]
            tv = [k for k in vt[v] if alive[k]]
            shared = set(tu) & set(tv)
            if not shared:
                continue
            nu = {w for k in tu for w in Tl[k]} - {u}
            nv = {w for k in tv for w in Tl[k]} - {v}
            opp = {w for k in shared for w in Tl[k]} - {u, v}
            if (nu & nv) - {u, v} != opp:
                continue                          # would pinch the surface
            edge_on_rim = (min(u, v), max(u, v)) in rim_edges
            if on_rim[u] and on_rim[v] and not edge_on_rim:
                continue                          # would join two rims
            if on_rim[v] and not on_rim[u]:
                u, v = v, u
                tu, tv = tv, tu
            pos = V[u] if (on_rim[u] and not on_rim[v]) else 0.5 * (V[u] + V[v])
            # no triangle around may turn over
            ok = True
            for k in set(tu) | set(tv):
                if k in shared:
                    continue
                tri = Tl[k]
                old = V[tri]
                new = np.array([pos if w in (u, v) else V[w] for w in tri])
                n0 = np.cross(old[1] - old[0], old[2] - old[0])
                n1 = np.cross(new[1] - new[0], new[2] - new[0])
                if np.dot(n0, n1) <= 0:
                    ok = False
                    break
            if not ok:
                continue
            V[u] = pos
            for k in shared:
                alive[k] = False
            for k in tv:
                if alive[k]:
                    Tl[k] = [u if w == v else w for w in Tl[k]]
                    vt[u].append(k)
            locked[list(nu | nv | {u, v})] = True
            done += 1
        T = np.asarray(Tl, np.int64)[alive]
        total += done
        if not done:
            break
    used = np.unique(T)
    remap = -np.ones(len(V), np.int64)
    remap[used] = np.arange(len(used))
    return V[used], remap[T], total


def prepare(tris, weld: float, margin: float = 2.0):
    """The triangles ready for a mesh that welds at ``weld`` (model units):
    ``(tris, report)``."""
    t = mesh3d.as_tris(tris)
    keep = mesh3d.drop_degenerate(t, 0.0)
    V, T = mesh3d.weld(t[keep], quantum=max(weld * 1e-6, 1e-12))
    good = (T[:, 0] != T[:, 1]) & (T[:, 1] != T[:, 2]) & (T[:, 0] != T[:, 2])
    T = T[good]
    E = _edges(T)
    before = int((np.linalg.norm(V[E[:, 0]] - V[E[:, 1]], axis=1) < weld * margin).sum())
    V, T, n = collapse_short_edges(V, T, weld * margin)
    E = _edges(T)
    left = int((np.linalg.norm(V[E[:, 0]] - V[E[:, 1]], axis=1) < weld).sum())
    return V[T], {"triangles_in": int(len(t)), "triangles_out": int(len(T)),
                  "short_edges": before, "collapsed": n, "left": left}
