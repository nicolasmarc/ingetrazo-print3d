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
