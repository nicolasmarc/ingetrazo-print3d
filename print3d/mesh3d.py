# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Nicolas Marc.
"""Printability analyses on triangle soups — pure NumPy, no Qt.

Every function takes triangles as an ``(M, 3, 3)`` float array in model
units (IngeTrazo works in metres) and returns plain arrays or dicts. The
panel converts the print settings (millimetres at a print scale) to model
units before calling.

The methods are textbook ones: Newell / cross-product normals and areas,
the Möller–Trumbore ray-triangle test, ray parity for point-in-solid,
closest point on a triangle, signed tetrahedron volumes. A uniform grid
keeps the ray and distance queries local.
"""
from __future__ import annotations

import math

import numpy as np

_EPS = 1e-12


# ---------------------------------------------------------------------------
# Basics
# ---------------------------------------------------------------------------

def as_tris(tris) -> np.ndarray:
    t = np.asarray(tris, dtype=float).reshape(-1, 3, 3)
    return t


def normals_areas(tris):
    """Unit normals ``(M, 3)`` (right-hand winding) and areas ``(M,)``."""
    t = as_tris(tris)
    n = np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0])
    ln = np.linalg.norm(n, axis=1)
    area = 0.5 * ln
    with np.errstate(invalid="ignore", divide="ignore"):
        unit = np.where(ln[:, None] > _EPS, n / ln[:, None], 0.0)
    return unit, area


def unit(v) -> np.ndarray:
    v = np.asarray(v, dtype=float)
    return v / max(np.linalg.norm(v), _EPS)


def frame(up):
    """An orthonormal frame ``(e1, e2, up)`` around the build direction."""
    up = unit(up)
    ref = np.array([1.0, 0.0, 0.0]) if abs(up[0]) < 0.9 else np.array([0.0, 1.0, 0.0])
    e1 = unit(np.cross(ref, up))
    e2 = np.cross(up, e1)
    if abs(up[2]) > 0.9:            # keep world X / Y for a vertical build
        e1 = unit(np.cross(np.array([0.0, 1.0, 0.0]), up))
        e2 = np.cross(up, e1)
    return e1, e2, up


def rotation_between(a, b) -> tuple[np.ndarray, float]:
    """``(axis, degrees)`` of the shortest rotation taking ``a`` onto ``b``."""
    a, b = unit(a), unit(b)
    c = float(np.clip(a @ b, -1.0, 1.0))
    axis = np.cross(a, b)
    if np.linalg.norm(axis) < 1e-9:
        if c > 0:
            return np.array([0.0, 0.0, 1.0]), 0.0
        ref = np.array([1.0, 0.0, 0.0]) if abs(a[0]) < 0.9 else np.array([0.0, 1.0, 0.0])
        return unit(np.cross(a, ref)), 180.0
    return unit(axis), math.degrees(math.acos(c))


def rotate(points, axis, degrees, centre=(0.0, 0.0, 0.0)) -> np.ndarray:
    """Rodrigues rotation of ``points`` about ``axis`` through ``centre``."""
    k = unit(axis)
    th = math.radians(degrees)
    kx = np.array([[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]])
    r = np.eye(3) + math.sin(th) * kx + (1 - math.cos(th)) * (kx @ kx)
    p = np.asarray(points, dtype=float)
    c = np.asarray(centre, dtype=float)
    return (p - c) @ r.T + c


def weld(tris, quantum: float = 1e-7):
    """Shared vertices: ``(verts (V, 3), index (M, 3))``. Corners closer
    than ``quantum`` become one vertex."""
    t = as_tris(tris)
    flat = t.reshape(-1, 3)
    key = np.round(flat / quantum).astype(np.int64)
    _, first, inv = np.unique(key, axis=0, return_index=True, return_inverse=True)
    return flat[first], inv.reshape(-1, 3)


def signed_volume(tris) -> float:
    t = as_tris(tris)
    return float(np.einsum("ij,ij->i", t[:, 0], np.cross(t[:, 1], t[:, 2])).sum() / 6.0)


def drop_degenerate(tris, min_area: float = 1e-14):
    t = as_tris(tris)
    _n, a = normals_areas(t)
    return a > min_area


# ---------------------------------------------------------------------------
# Uniform grid: candidate pairs between boxes
# ---------------------------------------------------------------------------

class _Grid:
    """Cells of size ``cell`` (a number, or one per axis: long thin
    triangles want flat cells) over the box ``lo``..``hi``, at most ``cap``
    cells per axis (a cell grows if needed)."""

    def __init__(self, lo, hi, cell, cap: int = 384) -> None:
        lo = np.asarray(lo, float)
        hi = np.asarray(hi, float)
        span = max(float(np.max(hi - lo)), _EPS)
        c = np.broadcast_to(np.asarray(cell, float), (3,))
        self.cell_v = np.maximum(c, max(span / cap, _EPS))
        self.cell = float(self.cell_v.min())
        self.lo = lo - self.cell_v
        self.n = np.floor((hi - self.lo) / self.cell_v).astype(np.int64) + 2

    def _cells(self, p):
        c = np.floor((np.asarray(p, float) - self.lo) / self.cell_v).astype(np.int64)
        return np.clip(c, 0, self.n - 1)

    def expand(self, box_lo, box_hi):
        """``(owner, key)``: one entry per (box, cell it overlaps)."""
        a = self._cells(box_lo)
        b = self._cells(box_hi)
        d = b - a + 1
        cnt = d[:, 0] * d[:, 1] * d[:, 2]
        owner = np.repeat(np.arange(len(a)), cnt)
        start = np.repeat(np.cumsum(cnt) - cnt, cnt)
        r = np.arange(int(cnt.sum())) - start
        dx = d[owner, 0]
        dy = d[owner, 1]
        ix = a[owner, 0] + r % dx
        iy = a[owner, 1] + (r // dx) % dy
        iz = a[owner, 2] + r // (dx * dy)
        key = ix + self.n[0] * (iy + self.n[1] * iz)
        return owner, key

    def index(self, t_lo, t_hi) -> None:
        """Register the target boxes once (several query batches follow)."""
        t_own, t_key = self.expand(t_lo, t_hi)
        order = np.argsort(t_key, kind="stable")
        self._t = (t_own[order], t_key[order], len(t_lo))

    def keys_of_points(self, pts):
        c = self._cells(pts)
        return c[:, 0] + self.n[0] * (c[:, 1] + self.n[1] * c[:, 2])

    def pairs(self, q_lo, q_hi, t_lo=None, t_hi=None, max_pairs: int = 25_000_000):
        """Unique ``(i_query, j_target)`` whose boxes share a cell."""
        if t_lo is not None:
            self.index(t_lo, t_hi)
        q_own, q_key = self.expand(q_lo, q_hi)
        return self._join(q_own, q_key, max_pairs)

    def pairs_along(self, starts, ends, max_pairs: int = 25_000_000):
        """Unique ``(i_query, j_target)``: targets in the cells a segment
        crosses (sampled every half cell)."""
        length = np.linalg.norm(ends - starts, axis=1).max() if len(starts) else 0.0
        k = int(math.ceil(length / (0.5 * self.cell))) + 1
        f = np.linspace(0.0, 1.0, k + 1)
        pts = starts[:, None, :] + (ends - starts)[:, None, :] * f[None, :, None]
        q_own = np.repeat(np.arange(len(starts)), k + 1)
        q_key = self.keys_of_points(pts.reshape(-1, 3))
        u = np.unique(q_own.astype(np.int64) * (int(np.prod(self.n)) + 1) + q_key)
        nn = int(np.prod(self.n)) + 1
        return self._join(u // nn, u % nn, max_pairs)

    def counts(self, q_lo, q_hi):
        """How many candidate targets each query box would get."""
        q_own, q_key = self.expand(q_lo, q_hi)
        _t_own, t_key, _n = self._t
        c = (np.searchsorted(t_key, q_key, "right")
             - np.searchsorted(t_key, q_key, "left"))
        return np.bincount(q_own, weights=c, minlength=len(q_lo))

    def _join(self, q_own, q_key, max_pairs):
        t_own, t_key, n_t = self._t
        left = np.searchsorted(t_key, q_key, "left")
        right = np.searchsorted(t_key, q_key, "right")
        cnt = right - left
        total = int(cnt.sum())
        if total == 0:
            return np.zeros(0, np.int64), np.zeros(0, np.int64)
        if total > max_pairs:
            raise MemoryError("too many candidate pairs")
        qi = np.repeat(q_own, cnt)
        start = np.repeat(left - (np.cumsum(cnt) - cnt), cnt)
        tj = t_own[np.arange(total) + start]
        pair = np.unique(qi.astype(np.int64) * (n_t + 1) + tj)
        return pair // (n_t + 1), pair % (n_t + 1)


def _cell_for(extent, scale: float):
    """Cell size per axis: about a triangle's size along that axis, never
    above ``scale`` nor much below a third of it... unless the triangles
    are much thinner along that axis (slivers of a cylinder)."""
    med = np.median(extent, axis=0)
    return np.clip(med, scale / 24.0, scale)


def _ray_tri(orig, dirs, a, b, c, eps=1e-12):
    """Möller–Trumbore, both sides. ``t`` per pair (``inf`` = no hit)."""
    e1 = b - a
    e2 = c - a
    p = np.cross(dirs, e2)
    det = np.einsum("ij,ij->i", e1, p)
    ok = np.abs(det) > eps
    inv = np.where(ok, 1.0 / np.where(ok, det, 1.0), 0.0)
    s = orig - a
    u = np.einsum("ij,ij->i", s, p) * inv
    q = np.cross(s, e1)
    v = np.einsum("ij,ij->i", dirs, q) * inv
    t = np.einsum("ij,ij->i", e2, q) * inv
    hit = ok & (u >= -1e-9) & (v >= -1e-9) & (u + v <= 1 + 1e-9)
    return np.where(hit, t, np.inf)


# ---------------------------------------------------------------------------
# Overhangs
# ---------------------------------------------------------------------------

def bed_level(tris, up) -> float:
    t = as_tris(tris)
    return float((t.reshape(-1, 3) @ unit(up)).min()) if len(t) else 0.0


def on_bed(tris, up, level=None, tol: float = 1e-5):
    """Triangles lying flat on the build plate, facing it."""
    t = as_tris(tris)
    up = unit(up)
    if level is None:
        level = bed_level(t, up)
    n, _a = normals_areas(t)
    h = t @ up
    return (h.max(axis=1) - level < tol) & ((n @ up) < -0.99)


def overhangs(tris, up=(0, 0, 1), limit_deg: float = 45.0, level=None,
              tol: float = 1e-5):
    """Mask of the triangles that need support: facing down more steeply
    than ``limit_deg`` measured from the vertical, and not on the bed."""
    t = as_tris(tris)
    up = unit(up)
    n, _a = normals_areas(t)
    down = n @ -up
    need = down > math.sin(math.radians(limit_deg)) + 1e-9
    return need & ~on_bed(t, up, level, tol)


def touching(query, targets, tol: float = 1e-4, chunk: int = 20_000):
    """Mask of the ``query`` triangles lying against a ``targets`` triangle
    that faces them (within ``tol``): the hidden faces where two blocks
    are stacked or butted. Such a face is neither an overhang (the block
    under it holds it up) nor the skin of a wall."""
    q = as_tris(query)
    tg = as_tris(targets)
    out = np.zeros(len(q), bool)
    if not len(q) or not len(tg):
        return out
    nq, aq = normals_areas(q)
    nt, _at = normals_areas(tg)
    pts = _samples(q)                               # (M, 4, 3)
    owner = np.repeat(np.arange(len(q)), 4)
    dirs = nq[owner]
    orig = pts.reshape(-1, 3) - dirs * tol
    ends = orig + dirs * (2 * tol)
    lo = np.minimum(orig.min(0), tg.reshape(-1, 3).min(0))
    hi = np.maximum(orig.max(0), tg.reshape(-1, 3).max(0))
    t_lo, t_hi = tg.min(axis=1), tg.max(axis=1)
    grid = _Grid(lo, hi, _cell_for(t_hi - t_lo, max(tol * 50, _EPS)))
    pad = 0.25 * grid.cell_v + tol
    grid.index(t_lo - pad, t_hi + pad)
    hits = np.zeros(len(orig), bool)
    for k in range(0, len(orig), chunk):
        sel = np.arange(k, min(k + chunk, len(orig)))
        qi, tj = grid.pairs(orig[sel] - tol, orig[sel] + tol)
        if not len(qi):
            continue
        ray = sel[qi]
        keep = (nt[tj] * dirs[ray]).sum(axis=1) < -0.95
        ray, tj = ray[keep], tj[keep]
        d = _ray_tri(orig[ray], dirs[ray], tg[tj, 0], tg[tj, 1], tg[tj, 2])
        ok = (d >= 0) & (d <= 2 * tol)
        hits[ray[ok]] = True
    votes = hits.reshape(-1, 4).sum(axis=1)
    return (votes >= 2) & (aq > 0)


# ---------------------------------------------------------------------------
# Wall thickness
# ---------------------------------------------------------------------------

def _samples(t):
    """Four points per triangle: the centroid and one towards each corner."""
    c = t.mean(axis=1)
    pts = [c] + [0.6 * t[:, k] + 0.2 * (t[:, (k + 1) % 3] + t[:, (k + 2) % 3])
                 for k in range(3)]
    return np.stack(pts, axis=1)          # (M, 4, 3)


def wall_thickness(tris, min_wall: float, chunk: int = 20_000,
                   samples_per_tri: int | None = None, tol: float = 0.0):
    """Thickness under each triangle where it is below ``min_wall``.

    From points on each triangle a ray goes straight in (against the
    normal); the first triangle met that faces the other way (the other
    skin of the wall) gives the thickness. ``inf`` = at least
    ``min_wall`` thick (or no opposite skin: an open sheet). With ``tol``,
    faces lying against one another (stacked blocks, :func:`touching`)
    are inside the print: the rays go through them."""
    t = as_tris(tris)
    m = len(t)
    out = np.full(m, np.inf)
    if m == 0 or min_wall <= 0:
        return out
    n, area = normals_areas(t)
    lo_all = t.reshape(-1, 3).min(axis=0)
    hi_all = t.reshape(-1, 3).max(axis=0)
    inner = touching(t, t, tol) if tol > 0 else np.zeros(m, bool)
    t_lo, t_hi = t.min(axis=1), t.max(axis=1)
    grid = _Grid(lo_all, hi_all, _cell_for(t_hi - t_lo, min_wall))
    pad = 0.25 * grid.cell_v
    grid.index(t_lo - pad, t_hi + pad)
    per = samples_per_tri or (4 if m <= 50_000 else 1)
    s = _samples(t)[:, :per]                    # (M, per, 3)
    owner = np.repeat(np.arange(m), per)
    pts = s.reshape(-1, 3)
    dirs = -n[owner]
    eps = 1e-9 * max(float(np.max(hi_all - lo_all)), 1.0)
    orig = pts + dirs * eps
    ends = orig + dirs * min_wall
    idx = np.nonzero((area[owner] > 0) & ~inner[owner])[0]
    todo = [idx[k:k + chunk] for k in range(0, len(idx), chunk)]
    while todo:
        sel = todo.pop()
        try:
            qi, tj = grid.pairs_along(orig[sel], ends[sel])
        except MemoryError:
            if len(sel) == 1:
                continue
            h = len(sel) // 2
            todo += [sel[:h], sel[h:]]
            continue
        if not len(qi):
            continue
        ray = sel[qi]
        src = owner[ray]
        keep = (tj != src) & ((n[tj] * n[src]).sum(axis=1) < -0.5) & ~inner[tj]
        ray, src, tj = ray[keep], src[keep], tj[keep]
        d = _ray_tri(orig[ray], dirs[ray], t[tj, 0], t[tj, 1], t[tj, 2])
        good = (d > tol) & (d <= min_wall)
        np.minimum.at(out, src[good], d[good] + eps)
    return out


# ---------------------------------------------------------------------------
# Shells and trapped cavities
# ---------------------------------------------------------------------------

def shells(tris):
    """Connected pieces of a triangle set (through shared corners):
    a label per triangle, ``0..k-1``."""
    t = as_tris(tris)
    if not len(t):
        return np.zeros(0, np.int64)
    _v, idx = weld(t)
    nv = int(idx.max()) + 1
    lab = np.arange(nv)
    u = np.concatenate([idx[:, 0], idx[:, 1]])
    w = np.concatenate([idx[:, 1], idx[:, 2]])
    while True:
        m = np.minimum(lab[u], lab[w])
        before = lab.copy()
        np.minimum.at(lab, lab[u], m)
        np.minimum.at(lab, lab[w], m)
        while True:
            nxt = lab[lab]
            if np.array_equal(nxt, lab):
                break
            lab = nxt
        if np.array_equal(lab, before):
            break
    tri_lab = lab[idx[:, 0]]
    _, out = np.unique(tri_lab, return_inverse=True)
    return out


_PARITY_DIR = unit([0.5773, 0.5779, 0.5767])


def inside(points, tris) -> np.ndarray:
    """Point-in-solid by ray parity (``tris`` a closed surface)."""
    p = np.asarray(points, float).reshape(-1, 3)
    t = as_tris(tris)
    res = np.zeros(len(p), bool)
    if not len(t):
        return res
    d = np.broadcast_to(_PARITY_DIR, (len(t), 3))
    for i, q in enumerate(p):
        o = np.broadcast_to(q, (len(t), 3))
        hits = _ray_tri(o, d, t[:, 0], t[:, 1], t[:, 2])
        res[i] = int(np.count_nonzero(np.isfinite(hits) & (hits > 1e-12))) % 2 == 1
    return res


def cavities(tris):
    """Closed voids inside a body: shells enclosed by an odd number of the
    body's other shells and turned inwards (their faces look into the
    void; a shell turned outwards inside another is a solid sunk into it,
    which prints merged). ``[{"volume", "centre", "tris"}]`` (volume > 0)."""
    t = as_tris(tris)
    lab = shells(t)
    k = int(lab.max()) + 1 if len(lab) else 0
    if k < 2:
        return []
    parts = [t[lab == i] for i in range(k)]
    signed = [signed_volume(p) for p in parts]
    vols = [abs(v) for v in signed]
    out = []
    for i, p in enumerate(parts):
        if signed[i] >= 0:
            continue
        probe = p[0, 0]
        depth = 0
        for j, q in enumerate(parts):
            if j == i or vols[j] <= vols[i]:
                continue
            lo, hi = q.reshape(-1, 3).min(0), q.reshape(-1, 3).max(0)
            if np.any(probe < lo) or np.any(probe > hi):
                continue
            if inside(probe[None], q)[0]:
                depth += 1
        if depth % 2 == 1:
            out.append({"volume": vols[i],
                        "centre": p.reshape(-1, 3).mean(axis=0),
                        "tris": p})
    return out


# ---------------------------------------------------------------------------
# Gaps between bodies
# ---------------------------------------------------------------------------

def _seg_dist2(p, a, b):
    ab = b - a
    tt = np.einsum("ij,ij->i", p - a, ab) / np.maximum(
        np.einsum("ij,ij->i", ab, ab), _EPS)
    tt = np.clip(tt, 0.0, 1.0)
    c = a + ab * tt[:, None]
    return np.einsum("ij,ij->i", p - c, p - c), c


def point_tri_distance(p, a, b, c):
    """Distance from each point to its triangle, and the closest points."""
    n = np.cross(b - a, c - a)
    nn = np.maximum(np.einsum("ij,ij->i", n, n), _EPS)
    dist_plane = np.einsum("ij,ij->i", p - a, n) / nn
    q = p - n * dist_plane[:, None]
    # barycentric inside test of the projection
    def side(x, y):
        return np.einsum("ij,ij->i", np.cross(y - x, q - x), n)
    ins = (side(a, b) >= 0) & (side(b, c) >= 0) & (side(c, a) >= 0)
    d2 = np.where(ins, np.einsum("ij,ij->i", p - q, p - q), np.inf)
    best = np.where(ins[:, None], q, 0.0)
    for x, y in ((a, b), (b, c), (c, a)):
        e2, cp = _seg_dist2(p, x, y)
        take = e2 < d2
        d2 = np.where(take, e2, d2)
        best = np.where(take[:, None], cp, best)
    return np.sqrt(d2), best


def _closest_batched(grid, pts, r, dst, chunk: int = 20_000,
                     max_pairs: int = 2_000_000):
    """Smallest point-triangle distance between ``pts`` and ``dst`` among
    the grid candidates, batch by batch (bounded memory). ``None`` or
    ``(d, point, closest)``."""
    best = None
    todo = [np.arange(k, min(k + chunk, len(pts))) for k in range(0, len(pts), chunk)]
    while todo:
        sel = todo.pop()
        try:
            qi, tj = grid.pairs(pts[sel] - r, pts[sel] + r, max_pairs=max_pairs)
        except MemoryError:
            if len(sel) == 1:
                continue
            h = len(sel) // 2
            todo += [sel[:h], sel[h:]]
            continue
        if not len(qi):
            continue
        p = pts[sel[qi]]
        d, cp = point_tri_distance(p, dst[tj, 0], dst[tj, 1], dst[tj, 2])
        k = int(np.argmin(d))
        if best is None or d[k] < best[0]:
            best = (float(d[k]), p[k], cp[k])
    return best


def _surface_points(t):
    return np.concatenate([t.reshape(-1, 3), t.mean(axis=1),
                           0.5 * (t[:, 0] + t[:, 1]), 0.5 * (t[:, 1] + t[:, 2]),
                           0.5 * (t[:, 2] + t[:, 0])])


def gaps(bodies, limit: float, budget: float = 5e6):
    """Pairs of bodies closer than ``limit`` (model units).

    ``bodies``: list of ``(M, 3, 3)`` arrays. Returns
    ``[{"a", "b", "distance", "pa", "pb"}]`` sorted by distance;
    a distance of 0 means touching or overlapping (they print as one).
    A pair checked on part of its points only (too dense for ``budget``
    point-triangle tests) carries ``"approx": True``."""
    bodies = [as_tris(b) for b in bodies]
    boxes = [(b.reshape(-1, 3).min(0), b.reshape(-1, 3).max(0)) if len(b) else None
             for b in bodies]
    out = []
    for i in range(len(bodies)):
        for j in range(i + 1, len(bodies)):
            if boxes[i] is None or boxes[j] is None:
                continue
            (alo, ahi), (blo, bhi) = boxes[i], boxes[j]
            if np.any(alo - limit > bhi) or np.any(blo - limit > ahi):
                continue
            best = None
            approx = False
            for s, o in ((i, j), (j, i)):
                src, dst = bodies[s], bodies[o]
                dlo, dhi = boxes[o]
                pts = _surface_points(src)
                near = np.all((pts >= dlo - limit) & (pts <= dhi + limit), axis=1)
                pts = pts[near]
                if not len(pts):
                    continue
                t_lo, t_hi = dst.min(1), dst.max(1)
                keep = np.all((t_hi >= pts.min(0) - limit) & (t_lo <= pts.max(0) + limit), axis=1)
                dst = dst[keep]
                if not len(dst):
                    continue
                lo = np.minimum(pts.min(0), dst.reshape(-1, 3).min(0))
                hi = np.maximum(pts.max(0), dst.reshape(-1, 3).max(0))
                grid = _Grid(lo, hi, max(limit, _EPS))
                r = np.full(3, limit)
                grid.index(dst.min(1), dst.max(1))
                cnt = grid.counts(pts - r, pts + r)
                if cnt.sum() > budget:
                    # too much work: the points with the fewest candidates
                    # first, then an even spread of the rest
                    approx = True
                    order = np.argsort(cnt, kind="stable")
                    keep_n = int(np.searchsorted(np.cumsum(cnt[order]), budget))
                    pts = pts[np.sort(order[:max(keep_n, 1)])]
                hit = _closest_batched(grid, pts, r, dst)
                if hit is not None and (best is None or hit[0] < best[0]):
                    d, pa, pb = hit
                    best = (d, pa, pb) if s == i else (d, pb, pa)
            if best is not None and best[0] < limit:
                # overlapping solids: a point of one inside the other
                out.append({"a": i, "b": j, "distance": best[0],
                            "pa": best[1], "pb": best[2], "approx": approx})
    out.sort(key=lambda g: g["distance"])
    return out


# ---------------------------------------------------------------------------
# Size against the printer's bed
# ---------------------------------------------------------------------------

def extents(tris, up=(0, 0, 1)) -> np.ndarray:
    """Size along (e1, e2, up) of the build frame."""
    t = as_tris(tris).reshape(-1, 3)
    if not len(t):
        return np.zeros(3)
    e1, e2, u = frame(up)
    m = np.stack([e1, e2, u], axis=1)
    p = t @ m
    return p.max(0) - p.min(0)


def fits(size_mm, bed_mm) -> dict:
    """Does a box ``size_mm`` (x, y, z) fit the bed ``bed_mm`` (x, y, z),
    as it is or turned a quarter on the plate?"""
    sx, sy, sz = (float(v) for v in size_mm)
    bx, by, bz = (float(v) for v in bed_mm)
    straight = sx <= bx and sy <= by and sz <= bz
    turned = sy <= bx and sx <= by and sz <= bz
    return {"fits": straight or turned, "turned": (not straight) and turned}


# ---------------------------------------------------------------------------
# Best orientation
# ---------------------------------------------------------------------------

def _sphere(n: int) -> np.ndarray:
    """``n`` directions spread evenly (golden spiral)."""
    i = np.arange(n) + 0.5
    phi = np.arccos(1 - 2 * i / n)
    th = math.pi * (1 + 5 ** 0.5) * i
    return np.stack([np.cos(th) * np.sin(phi), np.sin(th) * np.sin(phi),
                     np.cos(phi)], axis=1)


def orientations(tris, limit_deg: float = 45.0, count: int = 3,
                 samples: int = 400, tol: float = 1e-5):
    """The ``count`` build directions that need the least support.

    Each candidate direction (an even spread, plus the normals of the
    largest faces, which give the flat bases) is scored by the support it
    calls for: for every overhanging triangle, its area projected on the
    bed times its height above the bed (a support volume), then the print
    height breaks ties. A direction that leaves the part standing on an
    edge or a point (no face flat on the bed) comes after every one with a
    flat base. Returns ``[{"up", "support_area", "support_volume",
    "height", "base_area"}]``, best first, directions at least 15° apart."""
    t = as_tris(tris)
    if not len(t):
        return []
    n, a = normals_areas(t)
    big = np.argsort(a)[::-1][:24]
    cand = np.concatenate([_sphere(samples), -n[big], np.eye(3), -np.eye(3)])
    cand = cand / np.linalg.norm(cand, axis=1, keepdims=True)
    cen = t.mean(axis=1)
    pts = t.reshape(-1, 3)
    sin_lim = math.sin(math.radians(limit_deg))
    res = []
    for k in range(0, len(cand), 64):
        d = cand[k:k + 64]                          # (K, 3)
        down = -(n @ d.T)                           # (M, K)
        hp = pts @ d.T                              # (3M, K)
        level = hp.min(axis=0)                      # (K,)
        top = hp.reshape(len(t), 3, -1).max(axis=1) # (M, K)
        bed = (top - level < tol) & (down > 0.99)
        over = (down > sin_lim + 1e-9) & ~bed
        h = (cen @ d.T) - level
        proj = a[:, None] * np.clip(down, 0, None)
        area = (a[:, None] * over).sum(axis=0)
        vol = (proj * h * over).sum(axis=0)
        height = hp.max(axis=0) - level
        base = (a[:, None] * bed).sum(axis=0)
        for j in range(len(d)):
            res.append((float(vol[j]), float(height[j]), float(area[j]), d[j],
                        float(base[j])))
    scale = max(float(a.sum()), _EPS)
    res.sort(key=lambda r: (r[4] < 1e-6 * scale, round(r[0] / scale ** 1.5, 9), r[1]))
    out = []
    for vol, height, area, d, base in res:
        if all(float(d @ o["up"]) < math.cos(math.radians(15)) for o in out):
            out.append({"up": d, "support_area": area,
                        "support_volume": vol, "height": height,
                        "base_area": base})
            if len(out) == count:
                break
    return out


def total_area(tris) -> float:
    return float(normals_areas(tris)[1].sum())
