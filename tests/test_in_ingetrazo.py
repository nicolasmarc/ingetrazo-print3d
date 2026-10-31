"""The extension inside a real IngeTrazo window (needs IngeTrazo's sources:
``INGETRAZO_SRC``, default ``~/ingetrazo``; skipped without them).

The extension is installed from a copy into a private ``XDG_DATA_HOME``,
so an autosave of another run can never open a «Recover it?» dialog."""
import os
import shutil
import sys
from pathlib import Path

import numpy as np
import pytest

HERE = Path(__file__).resolve().parent
SRC = Path(os.environ.get("INGETRAZO_SRC", Path.home() / "ingetrazo"))
if not (SRC / "main.py").exists():
    pytest.skip("IngeTrazo sources not found", allow_module_level=True)

sys.path.insert(0, str(SRC))
sys.path.insert(0, str(HERE))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="module")
def window(tmp_path_factory):
    data = tmp_path_factory.mktemp("xdg")
    os.environ["XDG_DATA_HOME"] = str(data)
    plugins = data / "ingetrazo" / "plugins"
    plugins.mkdir(parents=True)
    shutil.copytree(HERE.parent / "print3d", plugins / "print3d",
                    ignore=shutil.ignore_patterns("__pycache__"))
    os.chdir(SRC)
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    from views.main_window import MainWindow
    win = MainWindow()
    win.resize(1400, 900)
    win.show()
    app.processEvents()
    assert not getattr(win, "_extension_load_errors", {}), win._extension_load_errors
    yield win
    # no close(): the test document is «unsaved» and close() would ask
    win.hide()


@pytest.fixture
def panel(window):
    from PySide6.QtWidgets import QApplication
    import demo
    sc = window.viewport.scene
    sc.groups.clear()
    sc.selection.clear()
    window.viewport.history.clear()
    demo.build(sc)
    p = [w for w in QApplication.instance().allWidgets() if type(w).__name__ == "Panel"
         and type(w).__module__.endswith("print3d.panel")][0]
    p.scale.setCurrentText("1:1")
    p.direction.setCurrentIndex(0)
    p.bed.setCurrentIndex(1)
    p.angle.setValue(45)
    p.wall.setValue(0.8)
    p.gap.setValue(0.3)
    p.clear()
    return p


def _text(p):
    import re
    return re.sub(r"<[^>]+>", "", p.summary.text().replace("&#9679;", "*"))


def test_every_check_on_the_bench(panel):
    panel.run(["watertight", "overhangs", "thickness", "cavities", "gaps", "fits"])
    s = _text(panel)
    assert "Watertight parts: 5 / 5" in s
    # the bracket's arm undersides (2 × 20 × 15 mm) and the ceiling of the
    # hollow box's void (15 × 15 mm); nothing else overhangs
    over = panel.layers["overhangs"][0]
    from print3d import mesh3d
    assert mesh3d.normals_areas(over)[1].sum() == pytest.approx(
        2 * 20e-3 * 15e-3 + 15e-3 * 15e-3, rel=1e-6)
    assert "Walls under 0.8 mm" in s and "thinnest 0.50 mm" in s
    assert "Trapped cavities: 1 (violet), 3.3" in s            # 15 mm cube: 3.375 cm³
    assert "Gaps under 0.30 mm: 1" in s and "smallest 0.20 mm" in s
    assert "Size at 1:1: 90 × 55 × 38 mm — fits the bed" in s


def test_selection_limits_the_check(panel):
    sc = panel.scene
    sc.selection.add(sc.groups[1])            # the fin alone
    try:
        panel.run(["thickness"])
        assert panel.scope.text() == "1 selected parts"
    finally:
        sc.selection.clear()


def test_best_orientation_and_apply_is_one_undo_step(panel):
    sc = panel.scene
    console = sc.groups[0]
    sc.selection.add(console)
    before = [v.position.toTuple() for v in console.mesh.vertices]
    panel.run(["orient"])
    rows = panel.orient_lay.count()
    assert rows == 3
    best = panel._last_best[0]
    # the T stands on its broad side or on its bar: no support at all
    assert best["support_volume"] == pytest.approx(0.0, abs=1e-15)
    panel.apply_orientation(best["up"])
    after = np.array([v.position.toTuple() for v in console.mesh.vertices])
    assert not np.allclose(after, before)
    assert after[:, 2].min() == pytest.approx(0.0, abs=1e-9)   # still on the bed
    vp = panel.app.viewport
    vp.history.undo()
    restored = [v.position.toTuple() for v in console.mesh.vertices]
    assert np.allclose(restored, before)
    sc.selection.clear()


def test_lay_flat_on_a_face(panel):
    sc = panel.scene
    fin = sc.groups[1]
    from print3d import bodies as B
    body = [b for b in B.collect(sc)[0] if b.group is fin][0]
    # the big side of the fin, facing -Y
    from print3d import mesh3d
    n, a = mesh3d.normals_areas(body.tris)
    j = int(np.argmax(a * (n @ [0, -1, 0] > 0.99)))
    panel._lay_flat(body, n[j])
    pts = np.array([v.position.toTuple() for v in fin.mesh.vertices])
    size = np.ptp(pts, axis=0)
    assert size[2] == pytest.approx(0.5e-3, abs=1e-9)       # now lying flat
    assert pts[:, 2].min() == pytest.approx(0.0, abs=1e-9)
    panel.app.viewport.history.undo()


def test_pick_ray_hits_the_part_under_the_cursor(panel, window):
    vp = window.viewport
    vp.camera.set_view("top")
    window._on_zoom_extents()
    panel.arm_lay_flat()
    assert panel.picking
    # the middle of the screen sees some part (or nothing): never a crash
    panel._pick(vp, vp.width() / 2, vp.height() / 2)
    assert not panel.picking


def test_exports(panel, tmp_path):
    lib3mf = pytest.importorskip("lib3mf")
    from PySide6.QtWidgets import QFileDialog
    out = tmp_path / "banc.3mf"
    orig = QFileDialog.getSaveFileName
    QFileDialog.getSaveFileName = staticmethod(lambda *a, **k: (str(out), ""))
    try:
        panel.export_3mf()
        stl = tmp_path / "banc.stl"
        QFileDialog.getSaveFileName = staticmethod(lambda *a, **k: (str(stl), ""))
        panel.export_stl()
    finally:
        QFileDialog.getSaveFileName = orig
    w = lib3mf.get_wrapper()
    model = w.CreateModel()
    model.QueryReader("3mf").ReadFromFile(str(out))
    names = []
    it = model.GetMeshObjects()
    lo = np.full(3, np.inf)
    hi = -lo
    while it.MoveNext():
        mo = it.GetCurrentMeshObject()
        names.append(mo.GetName())
        v = np.array([x.Coordinates[:] for x in mo.GetVertices()])
        lo, hi = np.minimum(lo, v.min(0)), np.maximum(hi, v.max(0))
    assert names == ["Console", "Ailette", "Boîte creuse", "Pion A", "Pion B"]
    assert np.allclose(lo, 0, atol=1e-4)
    assert np.allclose(hi, [90, 55, 38], atol=1e-3)               # millimetres
    assert stl.stat().st_size == 84 + 50 * int.from_bytes(stl.read_bytes()[80:84], "little")


def test_texts_follow_the_language(panel):
    lang = sys.modules[type(panel).__module__.rsplit(".", 1)[0] + ".lang"]
    lang._forced = "es"
    try:
        panel.run(["fits"])
        assert "Tamaño a 1:1" in _text(panel)
    finally:
        lang._forced = None


def test_click_a_face_to_lay_it_flat(panel, window):
    """The whole path: arm, the Select tool asks the extension under the
    click, the part turns (one undo step)."""
    from PySide6.QtWidgets import QApplication
    vp = window.viewport
    vp.camera.set_view("top")
    window._on_zoom_extents()
    QApplication.processEvents()
    console = panel.scene.groups[0]
    top_of_bar = np.array([[25e-3, 7.5e-3, 38e-3]])
    px, py, front = panel.app.world_to_pixels(top_of_bar)
    assert front[0]
    panel.arm_lay_flat()
    hit = vp.pick_extension_item(float(px[0]), float(py[0]))
    assert hit is not None
    vp.set_extension_pick(hit)
    for _ in range(5):
        QApplication.processEvents()
    pts = np.array([v.position.toTuple() for v in console.mesh.vertices])
    low = pts[pts[:, 2] < 1e-6]
    # upside down: the 50 mm bar now lies on the bed
    assert np.ptp(low[:, 0]) == pytest.approx(50e-3, abs=1e-7)
    assert pts[:, 2].max() == pytest.approx(38e-3, abs=1e-7)
    vp.history.undo()
    pts = np.array([v.position.toTuple() for v in console.mesh.vertices])
    assert np.ptp(pts[pts[:, 2] < 1e-6][:, 0]) == pytest.approx(10e-3, abs=1e-7)


def test_gyroid_infill_apply_preview_export_undo(panel, tmp_path):
    pytest.importorskip("manifold3d")
    lib3mf = pytest.importorskip("lib3mf")
    from print3d import mesh3d
    sc = panel.scene
    console = sc.groups[0]
    vp = panel.app.viewport
    panel.cell.setValue(6.0)
    panel.sheet.setValue(0.8)
    panel.skin.setValue(1.2)
    panel.remove_infill()                      # nothing selected: refused
    assert panel.infill_of(console) is None
    sc.selection.add(console)
    panel.apply_infill()
    assert panel.infill_of(console) == {"cell": 6.0, "wall": 0.8, "skin": 1.2}
    panel.preview_infill()
    assert panel.layers.get("section")
    assert "less material" in panel.infill_info.text()
    sc.selection.clear()

    from PySide6.QtWidgets import QFileDialog
    out = tmp_path / "gyro.3mf"
    orig = QFileDialog.getSaveFileName
    QFileDialog.getSaveFileName = staticmethod(lambda *a, **k: (str(out), ""))
    try:
        panel.export_3mf()
    finally:
        QFileDialog.getSaveFileName = orig
    model = lib3mf.get_wrapper().CreateModel()
    model.QueryReader("3mf").ReadFromFile(str(out))
    it = model.GetMeshObjects()
    vols = {}
    while it.MoveNext():
        mo = it.GetCurrentMeshObject()
        v = np.array([x.Coordinates[:] for x in mo.GetVertices()])
        tri = np.array([x.Indices[:] for x in mo.GetTriangleIndices()])
        vols[mo.GetName()] = mesh3d.signed_volume(v[tri])
    solid = (50 * 8 + 10 * 30) * 15.0                # the T, mm³
    assert 0.25 * solid < vols["Console"] < 0.7 * solid
    assert vols["Ailette"] == pytest.approx(30 * 20 * 0.5, rel=1e-3)   # untouched

    vp.history.undo()                           # the infill goes
    vp.notify_scene_changed()                   # what the Undo command does
    assert panel.infill_of(console) is None
    assert not panel.layers.get("section")      # the model changed: cut dropped
    vp.history.redo()
    assert panel.infill_of(console) is not None
    vp.history.undo()
    panel._infill_cache.clear()


def _group_from_tris(scene, name, tris):
    from PySide6.QtGui import QVector3D
    from core.group import Group
    from core.mesh import Mesh
    g = Group(Mesh(), name)
    for tri in tris:
        f = g.mesh.add_face([QVector3D(*map(float, p)) for p in tri])
        f.attrs = {"color": (0.7, 0.6, 0.9)}
    scene.groups.append(g)
    scene.version += 1
    return g


def test_fill_holes_in_a_sphere_and_a_box(panel):
    from core.solids import solid_report
    from test_holes import uv_sphere
    from shapes import box
    sc = panel.scene
    sc.groups.clear()
    s = uv_sphere(0.04, 48, 24)                      # 8 cm ball, metres
    c = s.mean(axis=1)
    holed = s[~((c[:, 0] > 0.034) | (c[:, 2] > 0.038))]
    ball = _group_from_tris(sc, "Boule", holed)
    t = box(0.1, 0, 0, 0.13, 0.03, 0.03)
    n = np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0])
    cube = _group_from_tris(sc, "Cube", t[n[:, 2] <= 0.99 * np.linalg.norm(n, axis=1)])
    assert not solid_report(ball.mesh)[0] and not solid_report(cube.mesh)[0]

    assert panel.show_holes() == 3
    assert "3 holes in 2 parts" in panel.hole_info.text()
    panel.patch_mode.setCurrentIndex(0)              # smooth
    panel.fill_all_holes()
    ok, vol = solid_report(ball.mesh)
    assert ok
    assert any(e.soft for e in ball.mesh.edges)       # the patch reads smooth
    exact = 4 / 3 * np.pi * 0.04 ** 3
    assert vol == pytest.approx(exact, rel=0.03)
    ok, vol = solid_report(cube.mesh)
    assert ok and vol == pytest.approx(0.03 ** 3, rel=1e-6)
    assert len(cube.mesh.faces) == 11               # the top: ONE flat face
    vp = panel.app.viewport
    vp.history.undo()
    vp.notify_scene_changed()
    assert not solid_report(ball.mesh)[0] and not solid_report(cube.mesh)[0]
    assert "holes" not in panel.layers              # the model changed


def test_click_a_rim_fills_that_hole_only(panel, window):
    from PySide6.QtWidgets import QApplication
    from core.solids import solid_report
    from shapes import box
    sc = panel.scene
    sc.groups.clear()
    t = box(0, 0, 0, 0.03, 0.03, 0.03)
    n = np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0])
    n /= np.linalg.norm(n, axis=1, keepdims=True)
    cube = _group_from_tris(sc, "Cube", t[np.abs(n[:, 2]) < 0.99])   # no top, no bottom
    vp = window.viewport
    vp.camera.set_view("iso")
    window._on_zoom_extents()
    QApplication.processEvents()
    assert panel.show_holes() == 2
    panel.arm_fill_one()
    top_edge_mid = np.array([[0.015, 0.03, 0.03]])  # on the top hole's rim only
    px, py, _f = panel.app.world_to_pixels(top_edge_mid)
    hit = vp.pick_extension_item(float(px[0]), float(py[0]))
    assert hit is not None
    vp.set_extension_pick(hit)
    for _ in range(5):
        QApplication.processEvents()
    assert len(cube.mesh.faces) == 8 + 1             # the sides, and ONE cap
    assert panel.show_holes() == 1
    assert not solid_report(cube.mesh)[0]
    vp.history.undo()


def test_flat_and_doubled_faces_are_cleared_before_filling(panel):
    """Faces with two corners and doubled faces (seen on a bunny worked in
    IngeTrazo) leave edges between four faces: they go first."""
    from PySide6.QtGui import QVector3D
    from core.solids import solid_report
    from shapes import box
    sc = panel.scene
    sc.groups.clear()
    t = box(0, 0, 0, 0.03, 0.03, 0.03)
    cube = _group_from_tris(sc, "Cube", t[:-2])          # one side open
    a, b = cube.mesh.faces[0].loop[0], cube.mesh.faces[0].loop[1]
    cube.mesh.add_face([QVector3D(a.position), QVector3D(b.position)])   # flat
    f0 = cube.mesh.faces[1]
    cube.mesh.add_face([QVector3D(v.position) for v in f0.loop])          # doubled
    panel.fill_all_holes()
    ok, vol = solid_report(cube.mesh)
    assert ok and vol == pytest.approx(0.03 ** 3, rel=1e-6)
    panel.app.viewport.history.undo()


def test_stl_import_survives_the_weld(panel, tmp_path):
    """A fine STL in millimetres (a 40 mm ball whose poles have corners a
    few microns apart): IngeTrazo's own import welds it into edges between
    three faces and more; ours arrives closed."""
    import collections
    from core.scene import Scene
    from core.solids import solid_report
    from formats import stl
    from print3d import export
    from test_holes import uv_sphere
    ball = uv_sphere(20.0, 400, 200)                 # millimetres
    path = tmp_path / "boule.stl"
    export.write_stl(path, [{"tris": ball}])
    plain = Scene()
    stl.load_stl(plain, str(path), scale=0.001)
    bad = collections.Counter(len(e.faces) for e in plain.groups[0].mesh.edges)
    assert any(n != 2 for n in bad)                  # the weld broke it
    group, rep = panel.load_stl_group(str(path), 0.001, 1e-4)
    assert rep["collapsed"] > 0 and rep["left"] == 0
    ok, vol = solid_report(group.mesh)
    assert ok
    assert vol == pytest.approx(4 / 3 * np.pi * 0.02 ** 3, rel=0.01)
