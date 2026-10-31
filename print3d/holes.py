# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Nicolas Marc.
"""Finding and filling holes in a triangle mesh — pure NumPy, no Qt.

A hole is a loop of *boundary* half-edges: a triangle edge ``a → b``
whose twin ``b → a`` belongs to no triangle. The patch that closes it
walks the loop the other way, so its triangles face the same side as the
surface around them.

Filling, by the textbook steps:

1. triangulate the loop (ear clipping on the plane that fits it best;
   a fan around its centre when the loop folds over itself there);
2. *flat cap*: stop there;
3. *smooth patch*: split the patch's inner edges until they are about as
   long as the rim's, then place the new points by bi-harmonic fairing
   (``L² x = 0``, uniform Laplacian), with the rim and the ring of points
   around it held still: the patch continues the slope of the surface.
"""
from __future__ import annotations

import numpy as np

from . import mesh3d


# ---------------------------------------------------------------------------
# Finding
# ---------------------------------------------------------------------------

def boundary_loops(idx):
    """Loops of rim vertices (``idx``: ``(M, 3)`` triangles), each in
    the order the PATCH must take. A vertex where two holes touch is
    handled by taking each outgoing rim edge once."""
    idx = np.asarray(idx, np.int64)
    half = {}
    for a, b, c in idx:
        for u, v in ((a, b), (b, c), (c, a)):
            half[(int(u), int(v))] = half.get((int(u), int(v)), 0) + 1
    rim = [(u, v) for (u, v) in half if (v, u) not in half]
    out_edges: dict = {}
    for u, v in rim:
        out_edges.setdefault(u, []).append(v)
    used = set()
    loops = []
    for start in rim:
        if start in used:
            continue
        loop = [start[0]]
        used.add(start)
        cur = start[1]
        ok = False
        for _ in range(len(rim) + 1):
            if cur == loop[0]:
                ok = True
                break
            loop.append(cur)
            nxt = [w for w in out_edges.get(cur, []) if (cur, w) not in used]
            if not nxt:
                break
            used.add((cur, nxt[0]))
            cur = nxt[0]
        if ok and len(loop) >= 3:
            for part in split_pinched(loop):
                if len(part) >= 3:
                    loops.append(part[::-1])   # the patch walks it backwards
    return loops


def split_pinched(loop):
    """A rim that passes twice through one vertex (two holes touching at
    a corner) as simple loops, each closed on its own."""
    out = []
    stack = []
    where: dict = {}
    for v in loop:
        if v in where:
            k = where[v]
            out.append(stack[k:])
            for w in stack[k + 1:]:
                where.pop(w, None)
            stack = stack[:k + 1]
        else:
            where[v] = len(stack)
            stack.append(v)
    out.append(stack)
    return out


def find(tris, quantum: float = 1e-7):
    """``(verts, idx, loops)`` of a triangle soup (welded)."""
    verts, idx = mesh3d.weld(tris, quantum)
    good = (idx[:, 0] != idx[:, 1]) & (idx[:, 1] != idx[:, 2]) & (idx[:, 0] != idx[:, 2])
    idx = idx[good]
    return verts, idx, boundary_loops(idx)


# ---------------------------------------------------------------------------
# Triangulating a loop
# ---------------------------------------------------------------------------

def _plane(points):
    c = points.mean(axis=0)
    _u, _s, vt = np.linalg.svd(points - c)
    return c, vt[0], vt[1], vt[2]


def _segments_cross(p, q):
    """Does the closed 2D polyline ``p`` cross itself? (O(n²), n small)."""
    n = len(p)
    a = p
    b = np.roll(p, -1, axis=0)
    for i in range(n):
        for j in range(i + 2, n):
            if i == 0 and j == n - 1:
                continue
            d1 = _orient(a[j], b[j], a[i])
            d2 = _orient(a[j], b[j], b[i])
            d3 = _orient(a[i], b[i], a[j])
            d4 = _orient(a[i], b[i], b[j])
            if d1 * d2 < 0 and d3 * d4 < 0:
                return True
    return False


def _orient(a, b, c):
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def ear_clip(p2):
    """Triangles (index triples) of a simple counter-clockwise polygon.
    The «no corner inside the ear» test is vectorised over the polygon."""
    P = np.asarray(p2, float)
    rest = list(range(len(P)))
    tris = []
    k = 0
    stall = 0
    while len(rest) > 3:
        m = len(rest)
        if stall > m:
            return None
        k %= m
        i, j, l = rest[(k - 1) % m], rest[k], rest[(k + 1) % m]
        a, b, c = P[i], P[j], P[l]
        if _orient(a, b, c) <= 1e-18 * max(1.0, float(np.abs(P).max()) ** 2):
            k += 1
            stall += 1
            continue
        others = np.array([o for o in rest if o not in (i, j, l)], np.int64)
        q = P[others]
        d1 = (b[0] - a[0]) * (q[:, 1] - a[1]) - (b[1] - a[1]) * (q[:, 0] - a[0])
        d2 = (c[0] - b[0]) * (q[:, 1] - b[1]) - (c[1] - b[1]) * (q[:, 0] - b[0])
        d3 = (a[0] - c[0]) * (q[:, 1] - c[1]) - (a[1] - c[1]) * (q[:, 0] - c[0])
        if np.any((d1 >= 0) & (d2 >= 0) & (d3 >= 0)):
            k += 1
            stall += 1
            continue
        tris.append((i, j, l))
        rest.pop(k)
        stall = 0
    tris.append(tuple(rest))
    return tris


def triangulate_loop(points, fan: bool = False):
    """``(points, tris)`` closing the loop ``points`` (in patch order):
    ear clipping on the best-fit plane, else a fan around the centre (one
    new point)."""
    pts = np.asarray(points, float)
    n = len(pts)
    if n == 3:
        return pts, np.array([[0, 1, 2]])
    c, e1, e2, _nrm = _plane(pts)
    p2 = np.c_[(pts - c) @ e1, (pts - c) @ e2]
    area = 0.5 * np.sum(p2[:, 0] * np.roll(p2[:, 1], -1) - p2[:, 1] * np.roll(p2[:, 0], -1))
    flip = area < 0
    q2 = p2.copy()
    if flip:
        q2[:, 1] *= -1.0                       # look from the other side
    tris = None if fan or _segments_cross(q2, None) else ear_clip(q2)
    if tris is not None:
        return pts, np.array(tris, np.int64)
    # fan around the centre
    out = np.vstack([pts, pts.mean(axis=0)])
    fan = np.array([[i, (i + 1) % n, n] for i in range(n)], np.int64)
    return out, fan


# ---------------------------------------------------------------------------
# Refining and fairing
# ---------------------------------------------------------------------------

def refine(points, tris, n_rim: int, target: float, rounds: int = 6):
    """Split the inner edges (not the rim's ``0..n_rim-1`` chain) longer
    than ``target``, red-green style, until none is."""
    pts = [p for p in np.asarray(points, float)]
    tris = [tuple(int(v) for v in t) for t in tris]

    def is_rim(a, b):
        if a >= n_rim or b >= n_rim:
            return False
        return (b - a) % n_rim in (1, n_rim - 1)

    for _ in range(rounds):
        mids = {}
        P = np.asarray(pts)
        T = np.asarray(tris, np.int64)
        E = np.unique(np.sort(np.concatenate([T[:, [0, 1]], T[:, [1, 2]], T[:, [2, 0]]]), axis=1), axis=0)
        long = np.linalg.norm(P[E[:, 0]] - P[E[:, 1]], axis=1) > target
        for a, b in E[long].tolist():
            if not is_rim(a, b):
                mids[(a, b)] = None
        if not mids:
            break
        for key in mids:
            mids[key] = len(pts)
            pts.append(0.5 * (P[key[0]] + P[key[1]]))
        new = []
        for a, b, c in tris:
            m = [mids.get((min(u, v), max(u, v))) for u, v in ((a, b), (b, c), (c, a))]
            k = sum(x is not None for x in m)
            if k == 0:
                new.append((a, b, c))
                continue
            # rotate so the pattern is canonical
            v = [a, b, c]
            for r in range(3):
                mm = m[r:] + m[:r]
                vv = v[r:] + v[:r]
                if k == 1 and mm[0] is not None:
                    break
                if k == 2 and mm[2] is None:
                    break
                if k == 3:
                    break
            p0, p1, p2 = vv
            mab, mbc, mca = mm
            if k == 1:
                new += [(p0, mab, p2), (mab, p1, p2)]
            elif k == 2:
                new += [(mab, p1, mbc), (p0, mab, mbc), (p0, mbc, p2)]
            else:
                new += [(p0, mab, mca), (mab, p1, mbc), (mca, mbc, p2), (mab, mbc, mca)]
        tris = new
    return np.asarray(pts), np.asarray(tris, np.int64)


def fair(points, tris, fixed, ring_edges=(), iters: int = 4000, tol: float = 1e-10):
    """Bi-harmonic fairing: move the free points so ``K² x = 0`` (``K`` the
    graph Laplacian of the patch plus ``ring_edges``, the edges joining the
    rim to the surface around it); ``fixed`` points do not move. Conjugate
    gradients on the symmetric system, edge lists only (no dense matrix)."""
    pts = np.asarray(points, float).copy()
    n = len(pts)
    t = np.asarray(tris, np.int64).reshape(-1, 3)
    e = np.concatenate([t[:, [0, 1]], t[:, [1, 2]], t[:, [2, 0]],
                        np.asarray(ring_edges, np.int64).reshape(-1, 2)])
    e = np.unique(np.sort(e, axis=1), axis=0)
    e = e[e[:, 0] != e[:, 1]]
    deg = np.bincount(e.ravel(), minlength=n).astype(float)

    def K(x):
        out = deg[:, None] * x
        np.add.at(out, e[:, 0], -x[e[:, 1]])
        np.add.at(out, e[:, 1], -x[e[:, 0]])
        return out
    is_fixed = np.zeros(n, bool)
    is_fixed[np.asarray(list(fixed), np.int64)] = True
    free = ~is_fixed
    if not free.any():
        return pts

    def A(xf):
        x = np.zeros_like(pts)
        x[free] = xf
        return K(K(x))[free]
    xc = np.where(is_fixed[:, None], pts, 0.0)
    b = -K(K(xc))[free]
    x = pts[free].copy()
    r = b - A(x)
    p = r.copy()
    rs = (r * r).sum(axis=0)
    b2 = max(float((b * b).sum()), 1e-300)
    for _ in range(iters):
        if float(rs.sum()) <= tol * tol * b2:
            break
        Ap = A(p)
        alpha = rs / np.maximum((p * Ap).sum(axis=0), 1e-300)
        x += p * alpha
        r -= Ap * alpha
        rs_new = (r * r).sum(axis=0)
        p = r + p * (rs_new / np.maximum(rs, 1e-300))
        rs = rs_new
    pts[free] = x
    return pts


def delaunay_flips(p2, tris, n_rim: int, max_flips: int | None = None):
    """Lawson edge flips on the 2D layout ``p2``: an inner edge whose
    opposite corner lies inside the other triangle's circumcircle is
    flipped (rim edges never). Evens out the long thin triangles of ear
    clipping, which fairing would otherwise fold. Incremental: only the
    edges around a flip are looked at again."""
    t = [list(map(int, x)) for x in tris]
    P = [(float(x), float(y)) for x, y in p2]

    def ccw(a, b, c):
        return _orient(P[a], P[b], P[c])

    def incircle(a, b, c, d):
        dx, dy = P[d]
        ax, ay = P[a][0] - dx, P[a][1] - dy
        bx, by = P[b][0] - dx, P[b][1] - dy
        cx, cy = P[c][0] - dx, P[c][1] - dy
        det = ((ax * ax + ay * ay) * (bx * cy - cx * by)
               - (bx * bx + by * by) * (ax * cy - cx * ay)
               + (cx * cx + cy * cy) * (ax * by - bx * ay))
        return det > 1e-15 * (ax * ax + ay * ay + 1e-300) ** 2

    def is_rim(a, b):
        return a < n_rim and b < n_rim and (b - a) % n_rim in (1, n_rim - 1)

    def key(u, v):
        return (u, v) if u < v else (v, u)

    owners: dict = {}
    for k, (a, b, c) in enumerate(t):
        for u, v in ((a, b), (b, c), (c, a)):
            owners.setdefault(key(u, v), []).append(k)

    def directed(k, u, v):
        """Third corner w if triangle k walks u -> v, else None."""
        a, b, c = t[k]
        for x, y, z in ((a, b, c), (b, c, a), (c, a, b)):
            if x == u and y == v:
                return z
        return None

    stack = [e for e, o in owners.items() if len(o) == 2 and not is_rim(*e)]
    flips = 0
    limit = max_flips if max_flips is not None else 50 * len(t) + 100
    while stack and flips < limit:
        e = stack.pop()
        o = owners.get(e)
        if not o or len(o) != 2 or is_rim(*e):
            continue
        k1, k2 = o
        u, v = e
        c = directed(k1, u, v)
        if c is None:
            k1, k2 = k2, k1
            c = directed(k1, u, v)
        d = directed(k2, v, u)
        if c is None or d is None:
            continue
        a, b = u, v
        if ccw(a, b, c) <= 0 or not incircle(a, b, c, d):
            continue
        if ccw(c, a, d) <= 1e-18 or ccw(d, b, c) <= 1e-18:
            continue                              # the quad is not convex
        t[k1] = [c, a, d]
        t[k2] = [d, b, c]
        del owners[e]
        owners[key(c, d)] = [k1, k2]
        ob = owners[key(b, c)]
        ob[ob.index(k1)] = k2
        oa = owners[key(a, d)]
        oa[oa.index(k2)] = k1
        stack += [key(a, c), key(b, c), key(a, d), key(b, d)]
        flips += 1
    return np.asarray(t, np.int64)


def unfold(pts, tris, fixed, normal, rounds: int = 30):
    """Fairing can fold a few small triangles along a jagged rim: pull
    their free corners to the middle of their neighbours until every
    triangle faces the patch's side again."""
    pts = pts.copy()
    t = np.asarray(tris, np.int64)
    e = np.unique(np.sort(np.concatenate([t[:, [0, 1]], t[:, [1, 2]], t[:, [2, 0]]]), axis=1), axis=0)
    deg = np.bincount(e.ravel(), minlength=len(pts)).astype(float)
    free = np.ones(len(pts), bool)
    free[list(fixed)] = False
    for _ in range(rounds):
        n = np.cross(pts[t[:, 1]] - pts[t[:, 0]], pts[t[:, 2]] - pts[t[:, 0]])
        bad = (n @ normal) <= 0
        if not bad.any():
            break
        move = np.zeros(len(pts), bool)
        move[t[bad].ravel()] = True
        move &= free
        if not move.any():
            break
        s = np.zeros_like(pts)
        np.add.at(s, e[:, 0], pts[e[:, 1]])
        np.add.at(s, e[:, 1], pts[e[:, 0]])
        avg = s / np.maximum(deg, 1)[:, None]
        pts[move] = avg[move]
    return pts


def is_flat(points, rel: float = 1e-4) -> bool:
    """A rim lying in one plane (a hole in a flat face)."""
    pts = np.asarray(points, float)
    c, _e1, _e2, nrm = _plane(pts)
    size = max(float(np.ptp(pts, axis=0).max()), 1e-12)
    return float(np.abs((pts - c) @ nrm).max()) <= rel * size


# ---------------------------------------------------------------------------
# One hole
# ---------------------------------------------------------------------------

def _closes(rim, patch, quantum, taken=()):
    """Does ``patch`` close the rim as a clean surface once corners closer
    than ``quantum`` are merged (what the host's weld will do)? Every rim
    edge used once by the patch, every inner edge twice, none flat."""
    from collections import Counter
    def key(p):
        return tuple(np.round(np.asarray(p) / quantum).astype(np.int64))
    rk = [key(p) for p in rim]
    rim_edges = {frozenset((rk[i], rk[(i + 1) % len(rk)])) for i in range(len(rk))}
    cnt = Counter()
    for tri in patch:
        k = [key(p) for p in tri]
        if len(set(k)) < 3:
            return False
        for a, b in ((k[0], k[1]), (k[1], k[2]), (k[2], k[0])):
            cnt[frozenset((a, b))] += 1
    for e, n in cnt.items():
        if (e in rim_edges and n != 1) or (e not in rim_edges and n != 2):
            return False
        if e in taken:
            return False                       # an edge the surface already has
    return all(cnt.get(e, 0) == 1 for e in rim_edges)


def fill(verts, idx, loop, smooth: bool = True, max_points: int = 6000,
         quantum: float | None = None):
    """Like :func:`_fill`, checked: with ``quantum`` (the host's weld
    distance) a smooth patch that would not close cleanly once welded
    falls back to the flat cap."""
    if quantum is None:
        return _fill(verts, idx, loop, smooth, max_points)
    rim = np.asarray(verts, float)[loop]
    # chords the surface already has between two rim corners (a triangle
    # bridging the hole's edge): the patch must not lay a second one there
    pos = {int(v): k for k, v in enumerate(loop)}
    n = len(loop)
    key_of = {k: tuple(np.round(rim[k] / quantum).astype(np.int64)) for k in range(n)}
    taken = set()
    sub = np.asarray(idx, np.int64)
    sub = sub[np.isin(sub, list(pos)).sum(axis=1) >= 2]
    for a, b, c in sub:
        for u, v in ((a, b), (b, c), (c, a)):
            if int(u) in pos and int(v) in pos:
                i, j = pos[int(u)], pos[int(v)]
                if (j - i) % n not in (1, n - 1):
                    taken.add(frozenset((key_of[i], key_of[j])))
    tries = [(smooth, False), (smooth, True)] if smooth else []
    tries += [(False, False), (False, True)]
    for sm, fan in tries:
        try:
            patch = _fill(verts, idx, loop, sm, max_points, fan)
        except Exception:  # noqa: BLE001
            continue
        if _closes(rim, patch, quantum, taken):
            return patch
    raise ValueError("the patch does not close the hole")


def _fill(verts, idx, loop, smooth: bool = True, max_points: int = 6000, fan: bool = False):
    """Triangles ``(K, 3, 3)`` closing ``loop`` (vertex ids into ``verts``,
    in patch order, from :func:`boundary_loops`). A flat rim always gets a
    flat cap: a hole in a flat face stays flat."""
    rim = np.asarray(verts, float)[loop]
    pts, tris = triangulate_loop(rim, fan)
    if not smooth or (is_flat(rim) and not fan):
        return pts[tris]
    n = len(loop)
    edges = np.linalg.norm(rim - np.roll(rim, -1, axis=0), axis=1)
    target = max(1.5 * float(np.mean(edges)), 1e-12)
    c, e1, e2, _nrm = _plane(rim)
    p2r = np.c_[(rim - c) @ e1, (rim - c) @ e2]
    flip_side = np.sum(p2r[:, 0] * np.roll(p2r[:, 1], -1)
                       - p2r[:, 1] * np.roll(p2r[:, 0], -1)) >= 0
    sgn = 1.0 if flip_side else -1.0

    def layout(p):
        return np.c_[(p - c) @ e1, sgn * ((p - c) @ e2)]
    tris = delaunay_flips(layout(pts), tris, n)
    for _ in range(8):                         # split, then even out, round by round
        before = len(pts)
        pts, tris = refine(pts, tris, n, target, rounds=1)
        if len(pts) == before or len(pts) > max_points:
            break
        tris = delaunay_flips(layout(pts), tris, n)
    if len(pts) > max_points:                  # a huge hole: keep it coarse
        pts, tris = triangulate_loop(rim, fan)
        return pts[tris]
    # the ring around the rim, from the surface, held still with the rim
    idx = np.asarray(idx, np.int64)
    pos = {int(v): k for k, v in enumerate(loop)}
    ring_pts, ring_edges, ring_id = [], [], {}
    hit = np.isin(idx, list(pos)).any(axis=1)
    for a, b, c in idx[hit]:
        for u, v in ((a, b), (b, c), (c, a)):
            u, v = int(u), int(v)
            if u in pos and v not in pos:
                if v not in ring_id:
                    ring_id[v] = len(pts) + len(ring_pts)
                    ring_pts.append(verts[v])
                ring_edges.append((pos[u], ring_id[v]))
            elif u in pos and v in pos and (v - u) not in (0,):
                pass
    allp = np.vstack([pts, np.asarray(ring_pts, float).reshape(-1, 3)])
    fixed = list(range(n)) + list(range(len(pts), len(allp)))
    if len(pts) > n:
        allp = fair(allp, tris, fixed, ring_edges)
        allp = unfold(allp, tris, set(fixed), np.cross(e1, e2) * (1 if flip_side else -1))
    return allp[:len(pts)][tris]


def fill_all(tris, smooth: bool = True):
    """Every hole of a triangle soup: ``(patches, loops_count, failed)``,
    ``patches`` a list of ``(K, 3, 3)`` arrays."""
    verts, idx, loops = find(tris)
    patches, failed = [], 0
    for loop in loops:
        try:
            patches.append(fill(verts, idx, loop, smooth))
        except Exception:  # noqa: BLE001 — one odd hole never stops the rest
            failed += 1
    return patches, len(loops), failed


def rim_segments(tris):
    """The rims of every hole, as segments ``(S, 2, 3)`` (for drawing)."""
    verts, _idx, loops = find(tris)
    segs = []
    for loop in loops:
        p = verts[loop]
        segs.append(np.stack([p, np.roll(p, -1, axis=0)], axis=1))
    return (np.concatenate(segs) if segs else np.zeros((0, 2, 3))), loops
