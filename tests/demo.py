"""A small print test bench built with IngeTrazo's own Mesh and Group:
a bracket with an overhang, a thin fin, a hollow box, two pegs 0.2 mm
apart. Sizes in metres (the parts are a few centimetres)."""
import numpy as np

MM = 0.001


def _v(p):
    from PySide6.QtGui import QVector3D
    return QVector3D(float(p[0]), float(p[1]), float(p[2]))


def _face(mesh, pts, outward, colour):
    pts = [np.asarray(p, float) for p in pts]
    n = np.zeros(3)
    for i in range(len(pts)):
        a, b = pts[i], pts[(i + 1) % len(pts)]
        n += np.cross(a, b)
    if np.dot(n, outward) < 0:
        pts = pts[::-1]
    f = mesh.add_face([_v(p) for p in pts])
    f.attrs = {"color": tuple(colour)}
    return f


def extrude(mesh, profile_xz, y0, y1, colour, sign=1.0):
    """A prism: ``profile_xz`` (counter-clockwise in x-z) swept from y0 to
    y1. ``sign=-1`` turns every face inwards (a void)."""
    prof = [np.array(p, float) for p in profile_xz]
    _face(mesh, [(x, y0, z) for x, z in prof], np.array([0, -sign, 0]), colour)
    _face(mesh, [(x, y1, z) for x, z in prof], np.array([0, sign, 0]), colour)
    for i in range(len(prof)):
        (xa, za), (xb, zb) = prof[i], prof[(i + 1) % len(prof)]
        out = sign * np.array([zb - za, 0.0, -(xb - xa)])
        _face(mesh, [(xa, y0, za), (xb, y0, zb), (xb, y1, zb), (xa, y1, za)], out, colour)


def rect(x0, z0, x1, z1):
    return [(x0, z0), (x1, z0), (x1, z1), (x0, z1)]


def build(scene):
    from core.group import Group
    from core.mesh import Mesh

    def group(name):
        g = Group(Mesh(), name)
        scene.groups.append(g)
        return g

    g = group("Console")
    t_profile = [(20, 0), (30, 0), (30, 30), (50, 30), (50, 38), (0, 38), (0, 30), (20, 30)]
    extrude(g.mesh, [(x * MM, z * MM) for x, z in t_profile], 0, 15 * MM, (0.90, 0.45, 0.15))

    g = group("Ailette")
    extrude(g.mesh, rect(60 * MM, 0, 90 * MM, 20 * MM), 0, 0.5 * MM, (0.20, 0.45, 0.85))

    g = group("Boîte creuse")
    extrude(g.mesh, rect(0, 0, 25 * MM, 25 * MM), 30 * MM, 55 * MM, (0.25, 0.65, 0.35))
    extrude(g.mesh, rect(5 * MM, 5 * MM, 20 * MM, 20 * MM), 35 * MM, 50 * MM,
            (0.25, 0.65, 0.35), sign=-1.0)

    g = group("Pion A")
    extrude(g.mesh, rect(60 * MM, 0, 70 * MM, 12 * MM), 30 * MM, 40 * MM, (0.55, 0.35, 0.75))
    g = group("Pion B")
    extrude(g.mesh, rect(70.2 * MM, 0, 80 * MM, 12 * MM), 30 * MM, 40 * MM, (0.80, 0.80, 0.80))
    scene.version += 1
