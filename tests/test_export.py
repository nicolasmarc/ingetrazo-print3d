"""3MF and STL files, read back by lib3mf (the 3MF Consortium's reference
library, a test tool only) and by a few lines of STL parsing."""
import os
import struct
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from print3d import export, mesh3d  # noqa: E402
from shapes import box, tube  # noqa: E402

lib3mf = pytest.importorskip("lib3mf")


def _read(path):
    w = lib3mf.get_wrapper()
    model = w.CreateModel()
    reader = model.QueryReader("3mf")
    reader.SetStrictModeActive(True)
    reader.ReadFromFile(str(path))
    for i in range(reader.GetWarningCount()):
        raise AssertionError(reader.GetWarning(i))
    return w, model


def test_3mf_objects_colours_and_volume(tmp_path):
    red = box(0, 0, 0, 10, 20, 5)
    cols = np.tile([0.85, 0.1, 0.1], (len(red), 1))
    cols[:2] = [0.1, 0.2, 0.9]                       # the bottom in blue
    pipe = tube(8, 6, 30, n=64) + [30, 0, 0]
    out = tmp_path / "t.3mf"
    n = export.write_3mf(out, [{"name": "Bloc rouge", "tris": red, "colours": cols},
                               {"name": "Tube", "tris": pipe, "colours": None}])
    assert n == {"objects": 2, "triangles": len(red) + len(pipe)}
    w, model = _read(out)
    assert model.GetUnit() == lib3mf.ModelUnit.MilliMeter
    meshes = model.GetMeshObjects()
    names, vols = [], []
    while meshes.MoveNext():
        mo = meshes.GetCurrentMeshObject()
        names.append(mo.GetName())
        assert mo.IsManifoldAndOriented()
        verts = np.array([v.Coordinates[:] for v in mo.GetVertices()])
        tris = np.array([t.Indices[:] for t in mo.GetTriangleIndices()])
        vols.append(mesh3d.signed_volume(verts[tris]))
        if mo.GetName() == "Bloc rouge":
            props = mo.GetAllTriangleProperties()
            group = model.GetBaseMaterialGroupByID(props[0].ResourceID)
            seen = {group.GetDisplayColor(p.PropertyIDs[0]).Red for p in props}
            assert seen == {round(0.85 * 255), round(0.1 * 255)}
    assert names == ["Bloc rouge", "Tube"]
    assert vols[0] == pytest.approx(1000.0)
    assert vols[1] == pytest.approx(mesh3d.signed_volume(pipe), rel=1e-6)


def test_degenerate_triangles_are_left_out(tmp_path):
    t = box(0, 0, 0, 1, 1, 1)
    sliver = np.array([[[0, 0, 0], [0.5, 0, 0], [1, 0, 0]]], float)
    out = tmp_path / "d.3mf"
    n = export.write_3mf(out, [{"name": "c", "tris": np.concatenate([t, sliver])}])
    assert n["triangles"] == 12
    _read(out)


def test_binary_stl(tmp_path):
    t = box(0, 0, 0, 2, 2, 2)
    out = tmp_path / "c.stl"
    assert export.write_stl(out, [{"tris": t}, {"tris": t + 5}]) == 24
    data = out.read_bytes()
    assert len(data) == 84 + 24 * 50
    (count,) = struct.unpack_from("<I", data, 80)
    assert count == 24
    nx, ny, nz = struct.unpack_from("<3f", data, 84)
    v = np.frombuffer(data, dtype="<f4", count=9, offset=96).reshape(3, 3)
    n = np.cross(v[1] - v[0], v[2] - v[0])
    assert np.allclose(n / np.linalg.norm(n), [nx, ny, nz])
