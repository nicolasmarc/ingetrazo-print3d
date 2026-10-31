"""Simple closed shapes as triangle arrays, outward winding."""
import math

import numpy as np


def box(x0, y0, z0, x1, y1, z1, inward=False):
    p = np.array([[x0, y0, z0], [x1, y0, z0], [x1, y1, z0], [x0, y1, z0],
                  [x0, y0, z1], [x1, y0, z1], [x1, y1, z1], [x0, y1, z1]], float)
    quads = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5),
             (2, 3, 7, 6), (3, 0, 4, 7)]
    tris = []
    for a, b, c, d in quads:
        tris += [(a, b, c), (a, c, d)]
    t = p[np.array(tris)]
    if inward:
        t = t[:, ::-1]
    return t


def tube(r_out, r_in, h, n=48):
    """A closed tube (annulus extruded along z), outward winding."""
    ang = np.linspace(0, 2 * math.pi, n, endpoint=False)
    co, si = np.cos(ang), np.sin(ang)
    tris = []
    for i in range(n):
        j = (i + 1) % n
        oi0 = (r_out * co[i], r_out * si[i], 0)
        oj0 = (r_out * co[j], r_out * si[j], 0)
        oi1 = (r_out * co[i], r_out * si[i], h)
        oj1 = (r_out * co[j], r_out * si[j], h)
        ii0 = (r_in * co[i], r_in * si[i], 0)
        ij0 = (r_in * co[j], r_in * si[j], 0)
        ii1 = (r_in * co[i], r_in * si[i], h)
        ij1 = (r_in * co[j], r_in * si[j], h)
        tris += [(oi0, oj0, oj1), (oi0, oj1, oi1)]          # outer wall
        tris += [(ii0, ii1, ij1), (ii0, ij1, ij0)]          # inner wall
        tris += [(oi1, oj1, ij1), (oi1, ij1, ii1)]          # top
        tris += [(oi0, ii0, ij0), (oi0, ij0, oj0)]          # bottom
    return np.array(tris, float)


def tee():
    """A T: a 10 × 10 × 30 post under a 50 × 10 × 10 bar (closed solid
    made of two touching boxes is fine for overhang tests)."""
    return np.concatenate([box(20, 0, 0, 30, 10, 30), box(0, 0, 30, 50, 10, 40)])
