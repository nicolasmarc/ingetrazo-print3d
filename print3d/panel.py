# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Nicolas Marc.
"""The 3D Print panel: print settings, analyses drawn over the view,
orienting the parts, export. Built inside ``setup(app)``."""
from __future__ import annotations

import math

import numpy as np
from PySide6.QtCore import QLocale, QPointF, QSettings, QSize, Qt, QTimer
from PySide6.QtGui import QColor, QPainterPath, QPen, QPolygonF
from PySide6.QtWidgets import (QApplication, QComboBox, QDockWidget, QSlider,
                               QDoubleSpinBox, QFileDialog, QFormLayout,
                               QGridLayout, QGroupBox, QHBoxLayout, QLabel,
                               QSizePolicy, QToolButton,
                               QPushButton, QScrollArea, QVBoxLayout, QWidget)

from . import bodies as B
from . import export, icons, lattice, mesh3d
from .lang import N_, lang, num, t

RED = QColor(220, 40, 40)
ORANGE = QColor(235, 130, 20)
VIOLET = QColor(130, 70, 200)
BLUE = QColor(30, 110, 230)
GREEN_DOT = "<span style='color:#2e9d4f'>&#9679;</span>"
WARN_DOT = "<span style='color:#d9822b'>&#9679;</span>"
BAD_DOT = "<span style='color:#d33'>&#9679;</span>"
GREY_DOT = "<span style='color:#999'>&#9679;</span>"

DIRECTIONS = [(N_("+Z (up)"), (0, 0, 1)), ("−Z", (0, 0, -1)), ("+Y", (0, 1, 0)),
              ("−Y", (0, -1, 0)), ("+X", (1, 0, 0)), ("−X", (-1, 0, 0))]
BEDS = [(180, 180, 180), (220, 220, 250), (256, 256, 256), (300, 300, 300),
        (350, 350, 400), (130, 80, 160)]
SCALES = ["1:1", "1:5", "1:10", "1:20", "1:25", "1:50", "1:100", "1:200", "2:1"]
_KEY = "print3d/"
MAX_DRAWN = 30000
#: Faces this close count as lying on one another (IngeTrazo welds at 0.1 mm).
TOUCH_M = 1e-4
#: Under this printed distance two parts touch (mm).
CONTACT_MM = 0.01


def dir_label(u) -> str:
    """``+X`` … ``−Z`` for an axis, else the three components."""
    for i, axis in enumerate("XYZ"):
        if abs(abs(u[i]) - 1.0) < 1e-6:
            return ("+" if u[i] > 0 else "−") + axis
    return "(" + " ; ".join(num(float(c) + 0.0, 2) for c in u) + ")"


def parse_scale(text: str) -> float:
    """``"1:50"`` → print millimetres per model millimetre (0.02)."""
    try:
        a, b = text.replace(",", ".").split(":")
        v = float(a) / float(b)
        return v if v > 0 and math.isfinite(v) else 1.0
    except (ValueError, ZeroDivisionError):
        return 1.0


class Panel(QWidget):
    def __init__(self, app) -> None:
        super().__init__()
        self.app = app
        self.layers: dict = {}          # name -> drawing data
        self.shown: set = set()         # the layers drawn now
        self.result = None
        self.analysed_cv = None
        self.picking = False
        self.busy = False
        self.orient_rows: list = []
        self._asked_depth = None
        self._infill_cache: dict = {}
        self.infill_preview: list = []
        self.preview_cv = None
        self._settings = QSettings()
        self.sections: dict = {}
        self._build()
        app.add_overlay(self._paint)
        app.on_document_changed(self._document_changed)
        app.add_pickable(pick=self._pick, on_select=None, delete=None)
        inst = QApplication.instance()
        if inst is not None:              # let the infill meshes go before exit
            inst.aboutToQuit.connect(self._infill_cache.clear)

    # ---- widgets -------------------------------------------------------------
    def _button(self, key, text, slot, tip=None):
        b = QPushButton(t(text))
        ic = icons.icon(key)
        if ic is not None:
            b.setIcon(ic)
            b.setIconSize(QSize(20, 20))
        b.setMinimumHeight(30)
        b.setStyleSheet("text-align: left; padding-left: 6px;")
        if tip:
            b.setToolTip(t(tip))
        b.clicked.connect(slot)
        return b

    def _section(self, key, title, default_open=True):
        """A section that folds under its title (remembered per user)."""
        sec = QWidget()
        v = QVBoxLayout(sec)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(2)
        head = QToolButton()
        head.setText(title)
        head.setCheckable(True)
        head.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        head.setAutoRaise(True)
        head.setStyleSheet("QToolButton { font-weight: bold; border: none; text-align: left; padding: 2px; }")
        head.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        body = QGroupBox()
        v.addWidget(head)
        v.addWidget(body)
        sec.head, sec.body = head, body
        stored = self._settings.value(_KEY + "open_" + key, None)
        is_open = default_open if stored is None else str(stored).lower() in ("true", "1")

        def show(on, k=key):
            head.setArrowType(Qt.DownArrow if on else Qt.RightArrow)
            body.setVisible(on)
            self._settings.setValue(_KEY + "open_" + k, bool(on))
        head.toggled.connect(show)
        head.setChecked(is_open)
        show(is_open)
        self.sections[key] = sec
        return sec

    def open_section(self, key) -> None:
        sec = self.sections.get(key)
        if sec is not None:
            sec.head.setChecked(True)

    def _spin(self, key, default, lo, hi, suffix, decimals=1, step=0.1):
        w = QDoubleSpinBox()
        loc = {"es": QLocale.Spanish, "fr": QLocale.French}.get(lang())
        if loc is not None:
            w.setLocale(QLocale(loc))
        w.setRange(lo, hi)
        w.setDecimals(decimals)
        w.setSingleStep(step)
        w.setSuffix(suffix)
        w.setValue(float(self._settings.value(_KEY + key, default)))
        w.valueChanged.connect(lambda v, k=key: self._settings.setValue(_KEY + k, v))
        return w

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        inner = QWidget()
        lay = QVBoxLayout(inner)
        lay.setContentsMargins(6, 6, 6, 6)
        lay.setSpacing(6)

        sec = self._section("setup", t("Print setup"), True)
        box = sec.body
        form = QFormLayout(box)
        self.direction = QComboBox()
        for label, _v in DIRECTIONS:
            self.direction.addItem(t(label))
        self.direction.setCurrentIndex(int(self._settings.value(_KEY + "direction", 0)))
        self.direction.currentIndexChanged.connect(
            lambda i: self._settings.setValue(_KEY + "direction", i))
        self.scale = QComboBox()
        self.scale.setEditable(True)
        self.scale.addItems(SCALES)
        self.scale.setCurrentText(str(self._settings.value(_KEY + "scale", "1:1")))
        self.scale.currentTextChanged.connect(
            lambda s: self._settings.setValue(_KEY + "scale", s))
        self.scale.setToolTip(t("Printed size : model size, e.g. 1:50 for a building model."))
        self.bed = QComboBox()
        for x, y, z in BEDS:
            self.bed.addItem(f"{x} × {y} × {z} mm")
        self.bed.addItem(t("Custom…"))
        bed_row = self.bed_row = QWidget()
        bl = QHBoxLayout(bed_row)
        bl.setContentsMargins(0, 0, 0, 0)
        self.bed_xyz = [self._spin(f"bed_{a}", d, 10, 2000, " mm", 0, 10)
                        for a, d in zip("xyz", (220, 220, 250))]
        for w in self.bed_xyz:
            bl.addWidget(w)
        self.bed.setCurrentIndex(int(self._settings.value(_KEY + "bed", 1)))
        self.bed.currentIndexChanged.connect(self._bed_changed)
        self._bed_changed(self.bed.currentIndex())
        self.angle = self._spin("angle", 45, 0, 89, " °", 0, 1)
        self.angle.setToolTip(t("Faces leaning further than this from the vertical need support."))
        self.wall = self._spin("wall", 0.8, 0.1, 20, " mm", 1, 0.1)
        self.wall.setToolTip(t("Thinner walls may not print: about two nozzle widths in FDM."))
        self.gap = self._spin("gap", 0.3, 0.05, 10, " mm", 2, 0.05)
        self.gap.setToolTip(t("Parts closer than this may fuse together when printed."))
        form.addRow(t("Build direction"), self.direction)
        form.addRow(t("Print scale"), self.scale)
        form.addRow(t("Printer bed"), self.bed)
        form.addRow("", bed_row)
        self.setup_form = form
        self._bed_changed(self.bed.currentIndex())
        form.addRow(t("Overhang limit"), self.angle)
        form.addRow(t("Minimum wall"), self.wall)
        form.addRow(t("Minimum gap"), self.gap)
        lay.addWidget(sec)

        sec = self._section("ready", t("Ready to print?"), True)
        box = sec.body
        v = QVBoxLayout(box)
        self.scope = QLabel()
        self.scope.setWordWrap(True)
        self.scope.setStyleSheet("color: gray;")
        v.addWidget(self.scope)
        self.summary = QLabel(t("Select parts, or nothing for the whole model, then press Analyse."))
        self.summary.setTextFormat(Qt.RichText)
        self.summary.setWordWrap(True)
        v.addWidget(self.summary)
        row = QHBoxLayout()
        row.addWidget(self._button("analyse", N_("Analyse"), self.analyse_all,
                                   N_("Every check below at once.")))
        row.addWidget(self._button("inspector", N_("Solid Inspector…"), self.open_inspector,
                                   N_("Holes, open and over-connected edges, reversed faces: IngeTrazo's own Solid Inspector.")))
        v.addLayout(row)
        self.clear_btn = QPushButton(t("Clear the view"))
        self.clear_btn.clicked.connect(self.clear)
        v.addWidget(self.clear_btn)
        lay.addWidget(sec)

        sec = self._section("inspect", t("Inspect"), True)
        box = sec.body
        g = QGridLayout(box)
        g.setSpacing(4)
        tools = [
            (N_("Overhangs"), lambda: self.run(["overhangs"]),
             N_("Faces that need support, in red.")),
            (N_("Wall thickness"), lambda: self.run(["thickness"]),
             N_("Walls thinner than the minimum, in orange.")),
            (N_("Trapped cavities"), lambda: self.run(["cavities"]),
             N_("Closed voids inside a part, in violet: resin or powder stays trapped.")),
            (N_("Gaps between parts"), lambda: self.run(["gaps"]),
             N_("Parts closer than the minimum gap, in blue: they may print fused.")),
            (N_("Fits the build volume"), lambda: self.run(["fits"]),
             N_("Size at the print scale against the printer bed (drawn around the parts).")),
            (N_("Lay flat on a face"), self.arm_lay_flat,
             N_("Then click a face: the part turns so that face rests on the bed.")),
        ]
        for i, (label, slot, tip) in enumerate(tools):
            g.addWidget(self._button(label, label, slot, tip), i // 2, i % 2)
        best = self._button("Best orientation", N_("Best orientation"),
                            lambda: self.run(["orient"]),
                            N_("The three ways to stand the parts that need the least support."))
        g.addWidget(best, 3, 0, 1, 2)
        self.orient_box = QWidget()
        self.orient_lay = QVBoxLayout(self.orient_box)
        self.orient_lay.setContentsMargins(0, 0, 0, 0)
        g.addWidget(self.orient_box, 4, 0, 1, 2)
        lay.addWidget(sec)

        sec = self._section("gyroid", t("Gyroid infill"), False)
        box = sec.body
        form = QFormLayout(box)
        intro = QLabel(t("Lightens a part: it keeps a skin, its inside becomes a gyroid. Made at export; the model stays light."))
        intro.setWordWrap(True)
        intro.setStyleSheet("color: gray;")
        form.addRow(intro)
        self.cell = self._spin("cell", 6.0, 1.0, 200.0, " mm", 1, 0.5)
        self.cell.setToolTip(t("Size of one gyroid cell, printed."))
        self.sheet = self._spin("sheet", 0.8, 0.2, 20.0, " mm", 2, 0.1)
        self.sheet.setToolTip(t("Thickness of the gyroid's wall, printed."))
        self.skin = self._spin("skin", 1.2, 0.0, 50.0, " mm", 1, 0.2)
        self.skin.setToolTip(t("Solid outer wall kept around the gyroid; 0 = gyroid only."))
        form.addRow(t("Cell size"), self.cell)
        form.addRow(t("Gyroid wall"), self.sheet)
        form.addRow(t("Skin"), self.skin)
        row = QHBoxLayout()
        row.addWidget(self._button("Gyroid infill", N_("Apply to the selection"), self.apply_infill,
                                   N_("The selected parts get a gyroid infill with these settings (one undo step).")))
        rm = QPushButton(t("Remove"))
        rm.setToolTip(t("The selected parts print solid again."))
        rm.clicked.connect(self.remove_infill)
        row.addWidget(rm)
        form.addRow(row)
        row = QHBoxLayout()
        row.addWidget(self._button("Preview a cut", N_("Preview a cut"), self.preview_infill,
                                   N_("Builds the infill of the selected parts and draws a cut through it.")))
        self.cut = QSlider(Qt.Horizontal)
        self.cut.setRange(1, 99)
        self.cut.setValue(50)
        self.cut.setToolTip(t("Height of the cut"))
        self.cut.valueChanged.connect(self._update_cut)
        row.addWidget(self.cut, 1)
        form.addRow(row)
        self.infill_info = QLabel()
        self.infill_info.setTextFormat(Qt.RichText)
        self.infill_info.setWordWrap(True)
        form.addRow(self.infill_info)
        lay.addWidget(sec)

        sec = self._section("export", t("Export"), True)
        box = sec.body
        g = QGridLayout(box)
        g.addWidget(self._button("3MF (colours)…", N_("3MF (colours)…"), self.export_3mf,
                                 N_("One object per part with its colours, in millimetres at the print scale and orientation.")), 0, 0)
        g.addWidget(self._button("Binary STL…", N_("Binary STL…"), self.export_stl,
                                 N_("Every part in one STL, in millimetres at the print scale and orientation.")), 0, 1)
        lay.addWidget(sec)
        lay.addStretch(1)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setWidget(inner)
        root.addWidget(scroll)
        self._update_scope()

    def _bed_changed(self, i) -> None:
        self._settings.setValue(_KEY + "bed", i)
        custom = i >= len(BEDS)
        for k, w in enumerate(self.bed_xyz):
            if not custom:
                w.blockSignals(True)
                w.setValue(BEDS[i][k])
                w.blockSignals(False)
            w.setEnabled(custom)
        form = getattr(self, "setup_form", None)
        if form is not None and hasattr(form, "setRowVisible"):
            form.setRowVisible(self.bed_row, custom)

    # ---- settings in model units --------------------------------------------
    @property
    def scene(self):
        return self.app.scene

    def up(self) -> np.ndarray:
        return np.array(DIRECTIONS[max(self.direction.currentIndex(), 0)][1], float)

    def k(self) -> float:
        """Print millimetres per model metre."""
        return 1000.0 * parse_scale(self.scale.currentText())

    def model_len(self, mm: float) -> float:
        return mm / self.k()

    def bed_mm(self):
        return [w.value() for w in self.bed_xyz]

    # ---- status -----------------------------------------------------------------
    def status(self, text: str, ms: int = 4000) -> None:
        fl = getattr(self.app.viewport, "flash_status", None)
        if fl is not None:
            fl(text, ms)

    def _update_scope(self, n=None, from_sel=None) -> None:
        if n is None:
            self.scope.setText(t("Selected parts, or the whole model when nothing is selected."))
        elif from_sel:
            self.scope.setText(t("{n} selected parts", n=n))
        else:
            self.scope.setText(t("Whole model: {n} parts", n=n))

    # ---- analysis -----------------------------------------------------------------
    def _bodies(self):
        if getattr(self.scene, "edit_group", None) is not None:
            self.status(t("Close the group you are editing first."), 5000)
            return None, None
        bodies, from_sel = B.collect(self.scene)
        if not bodies:
            self.status(t("Nothing to print: no visible faces."), 5000)
            return None, None
        return bodies, from_sel

    def analyse_all(self) -> None:
        self.run(["watertight", "overhangs", "thickness", "cavities", "gaps", "fits"],
                 show=("overhangs", "gaps", "cavities"))

    def run(self, what, show=None) -> None:
        """Run the checks in ``what``; draw the layers in ``show`` (all of
        them by default: one Inspect button = its own picture)."""
        if self.busy:
            return
        bodies, from_sel = self._bodies()
        if bodies is None:
            return
        self.busy = True
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            self._run(bodies, from_sel, what)
            self.shown = set(show if show is not None else what) | (
                {"section"} if "section" in self.layers else set())
        finally:
            QApplication.restoreOverrideCursor()
            self.busy = False
        self.app.viewport.update()

    def _run(self, bodies, from_sel, what) -> None:
        up = self.up()
        allt = np.concatenate([b.tris for b in bodies])
        level = mesh3d.bed_level(allt, up)
        tol = max(1e-6, 1e-6 * float(np.ptp(allt.reshape(-1, 3), axis=0).max()))
        k = self.k()
        self.layers = {key: v for key, v in self.layers.items() if key == "section"}
        self._clear_orient_rows()
        lines = []
        self.result = {"bodies": bodies, "up": up, "level": level}
        self._update_scope(len(bodies), from_sel)

        if "watertight" in what:
            closed = sum(1 for b in bodies if B.watertight(b))
            n = len(bodies)
            dot = GREEN_DOT if closed == n else WARN_DOT
            extra = "" if closed == n else " — " + t("see the Solid Inspector")
            lines.append(f"{dot} {t('Watertight parts')}: <b>{closed} / {n}</b>{extra}")

        if "overhangs" in what:
            over = mesh3d.overhangs(allt, up, self.angle.value(), level, tol)
            idx = np.nonzero(over)[0]
            if len(idx):
                over[idx[mesh3d.touching(allt[idx], allt, TOUCH_M)]] = False
            _n, area = mesh3d.normals_areas(allt)
            pct = 100.0 * area[over].sum() / max(area.sum(), 1e-30)
            self.layers["overhangs"] = (allt[over], RED)
            if over.any():
                lines.append(f"{WARN_DOT} {t('Overhangs > {a}°', a=f'{self.angle.value():.0f}')}: "
                             f"<b>{num(pct)} %</b> {t('of the surface')} "
                             f"<span style='color:#d33'>{t('(red)')}</span> — {t('supports needed')}")
            else:
                lines.append(f"{GREEN_DOT} {t('No overhang: no support needed')}")

        if "thickness" in what:
            mw = self.model_len(self.wall.value())
            thin_t, thinnest = [], math.inf
            for b in bodies:
                th = mesh3d.wall_thickness(b.tris, mw, tol=TOUCH_M)
                bad = np.isfinite(th)
                if bad.any():
                    thin_t.append(b.tris[bad])
                    thinnest = min(thinnest, float(th[bad].min()))
            if thin_t:
                tt = np.concatenate(thin_t)
                self.layers["thickness"] = (tt, ORANGE)
                lines.append(f"{BAD_DOT} {t('Walls under {w} mm', w=num(self.wall.value()))}: "
                             f"<b>{len(tt)}</b> {t('triangles')} "
                             f"<span style='color:#e07b22'>{t('(orange)')}</span>, "
                             f"{t('thinnest {w} mm', w=num(thinnest * k, 2))}")
            else:
                lines.append(f"{GREEN_DOT} {t('No wall under {w} mm', w=num(self.wall.value()))}")

        if "cavities" in what:
            cav = []
            for b in bodies:
                cav += mesh3d.cavities(b.tris)
            if cav:
                self.layers["cavities"] = (np.concatenate([c["tris"] for c in cav]), VIOLET)
                vol = sum(c["volume"] for c in cav) * k ** 3 / 1000.0
                lines.append(f"{WARN_DOT} {t('Trapped cavities')}: <b>{len(cav)}</b> "
                             f"<span style='color:#7b52c7'>{t('(violet)')}</span>, "
                             f"{num(vol, 2)} cm³ — {t('add a drain hole for resin or powder')}")
            else:
                lines.append(f"{GREEN_DOT} {t('No trapped cavity')}")

        if "gaps" in what:
            if len(bodies) < 2:
                lines.append(f"{GREY_DOT} {t('Gaps: a single part')}")
            else:
                gl = mesh3d.gaps([b.tris for b in bodies], self.model_len(self.gap.value()))
                close = [g for g in gl if g["distance"] * k > CONTACT_MM]
                touch = [g for g in gl if g["distance"] * k <= CONTACT_MM]
                self.layers["gaps"] = gl
                if close:
                    worst = close[0]["distance"] * k
                    lines.append(f"{WARN_DOT} {t('Gaps under {g} mm', g=num(self.gap.value(), 2))}: "
                                 f"<b>{len(close)}</b> "
                                 f"<span style='color:#1e6ee6'>{t('(blue)')}</span>, "
                                 f"{t('smallest {g} mm', g=num(worst, 2))}")
                else:
                    lines.append(f"{GREEN_DOT} {t('No gap under {g} mm', g=num(self.gap.value(), 2))}")
                if touch:
                    lines.append(f"{GREY_DOT} {t('{n} contacts between parts: they print as one piece', n=len(touch))}")

        if "fits" in what:
            ext = mesh3d.extents(allt, up) * k
            fit = mesh3d.fits(ext, self.bed_mm())
            self.layers["fits"] = True
            size = f"{ext[0]:.0f} × {ext[1]:.0f} × {ext[2]:.0f} mm"
            if fit["fits"]:
                note = t("fits the bed, turned a quarter") if fit["turned"] else t("fits the bed")
                dot = GREEN_DOT
            else:
                note = t("too big for the bed")
                dot = BAD_DOT
            lines.append(f"{dot} {t('Size at {s}', s=self.scale.currentText())}: <b>{size}</b> — {note}")

        if "orient" in what:
            best = mesh3d.orientations(allt, self.angle.value(), count=3)
            self._show_orientations(best, k)
            if best:
                lines.append(f"{GREEN_DOT} {t('Best orientations: below, Apply turns the parts')}")
                if len(bodies) > 1:
                    lines.append(f"{GREY_DOT} {t('{n} parts turned as one block: select a part to orient it alone', n=len(bodies))}")

        self.summary.setText("<br>".join(lines))
        self.analysed_cv = self.scene.content_version

    # ---- orientations ---------------------------------------------------------------
    def _clear_orient_rows(self) -> None:
        while self.orient_lay.count():
            w = self.orient_lay.takeAt(0).widget()
            if w is not None:
                w.deleteLater()

    def _show_orientations(self, best, k) -> None:
        self._clear_orient_rows()
        self._last_best = best
        groups = [b.group for b in self.result["bodies"]]
        can = all(g is not None for g in groups)
        for i, o in enumerate(best):
            row = QWidget()
            h = QHBoxLayout(row)
            h.setContentsMargins(0, 0, 0, 0)
            u = o["up"]
            vol = o["support_volume"] * k ** 3 / 1000.0
            text = (f"<b>{i + 1}.</b> {t('top')} {dir_label(u)}<br>"
                    f"{t('supports about {v} cm³', v=num(vol, 1))} · {t('height {h} mm', h=num(o['height'] * k, 0))}")
            lab = QLabel(text)
            lab.setTextFormat(Qt.RichText)
            h.addWidget(lab, 1)
            b = QPushButton(t("Apply"))
            b.setEnabled(can)
            if not can:
                b.setToolTip(t("Loose geometry cannot turn: make it a group first."))
            b.clicked.connect(lambda _c=False, d=u: self.apply_orientation(d))
            h.addWidget(b)
            self.orient_lay.addWidget(row)

    def apply_orientation(self, d) -> None:
        if not self.result:
            return
        bodies = self.result["bodies"]
        self._reorient([b.group for b in bodies],
                       np.concatenate([b.tris for b in bodies]), d, self.up(),
                       t("Parts turned for printing"))

    def _reorient(self, groups, tris, src, dst, message) -> None:
        """Turn ``groups`` so ``src`` points along ``dst``, keeping their
        lowest point where it was (one undo step)."""
        from .commands import ReorientCommand
        up = self.up()
        axis, deg = mesh3d.rotation_between(src, dst)
        pts = tris.reshape(-1, 3)
        centre = 0.5 * (pts.min(0) + pts.max(0))
        before = float((pts @ up).min())
        after = float((mesh3d.rotate(pts, axis, deg, centre) @ up).min())
        lift = up * (before - after)
        cmd = ReorientCommand(groups, centre, axis, deg, lift)
        if not cmd.steps:
            self.status(t("Already in that position."))
            return
        vp = self.app.viewport
        vp.history.execute(cmd)
        if getattr(vp.history, "last_error", None):
            self.status(vp.history.last_error, 6000)
            return
        vp.notify_scene_changed()
        self.status(message)
        QTimer.singleShot(0, lambda: self.run(["overhangs", "fits", "orient"]))

    # ---- lay flat ------------------------------------------------------------------------
    def arm_lay_flat(self) -> None:
        bodies, _sel = self._bodies()
        if bodies is None:
            return
        if not any(b.group is not None for b in bodies):
            self.status(t("Loose geometry cannot turn: make it a group first."), 5000)
            return
        self._pick_bodies = [b for b in bodies if b.group is not None]
        self.picking = True
        act = getattr(self.app.window, "_activate_tool", None)
        if act is not None:
            try:
                act("select")
            except Exception:  # noqa: BLE001
                pass
        self.status(t("Click the face to lay on the bed (Select tool)."), 8000)

    def _ray(self, px, py):
        vp = self.app.viewport
        cam = vp.camera
        w, h = max(vp.width(), 1), max(vp.height(), 1)
        x, y = 2.0 * px / w - 1.0, 1.0 - 2.0 * py / h
        inv, ok = (cam.projection_matrix() * cam.view_matrix()).inverted()
        if not ok:
            return None
        from PySide6.QtGui import QVector3D
        a = inv.map(QVector3D(x, y, -1.0))
        b = inv.map(QVector3D(x, y, 0.5))
        o = np.array(a.toTuple())
        d = np.array(b.toTuple()) - o
        if not np.all(np.isfinite(d)) or np.linalg.norm(d) == 0:
            return None
        return o, d / np.linalg.norm(d)

    def _pick(self, vp, px, py):
        if not self.picking:
            return None
        ray = self._ray(px, py)
        self.picking = False
        if ray is None:
            return None
        o, d = ray
        best = None
        for b in self._pick_bodies:
            tr = b.tris
            hit = mesh3d._ray_tri(np.broadcast_to(o, (len(tr), 3)),
                                  np.broadcast_to(d, (len(tr), 3)),
                                  tr[:, 0], tr[:, 1], tr[:, 2])
            hit[hit <= 0] = np.inf
            j = int(np.argmin(hit))
            if np.isfinite(hit[j]) and (best is None or hit[j] < best[0]):
                best = (hit[j], b, j)
        if best is None:
            self.status(t("No part under the cursor."))
            return None
        _t, body, j = best
        n, _a = mesh3d.normals_areas(body.tris[j:j + 1])
        QTimer.singleShot(0, lambda: self._lay_flat(body, n[0]))
        return ("lay-flat", id(body))

    def _lay_flat(self, body, normal) -> None:
        if hasattr(self.app, "release_pick"):
            self.app.release_pick()
        self._reorient([body.group], body.tris, normal, -self.up(),
                       t("Laid flat on that face"))

    # ---- drawing ---------------------------------------------------------------------------
    def clear(self) -> None:
        self.layers = {}
        self.shown = set()
        self.infill_preview = []
        self._clear_orient_rows()
        self.app.viewport.update()

    def _document_changed(self) -> None:
        cv = self.scene.content_version
        if self.infill_preview and cv != self.preview_cv:
            self.infill_preview = []
            self.layers.pop("section", None)
            self.app.viewport.update()
        if not self.layers or self.analysed_cv is None:
            return
        if cv != self.analysed_cv:
            for key in [k for k in self.layers if k != "section"]:
                self.layers.pop(key)
            self._clear_orient_rows()
            self.summary.setText(t("The model changed: press Analyse again."))
            self.app.viewport.update()

    def _paint(self, vp, painter) -> None:
        if not self.layers:
            return
        from PySide6.QtGui import QPainter
        painter.setRenderHint(QPainter.Antialiasing)
        eye = np.array(vp.camera.eye().toTuple())
        depth = self._depth(vp)
        for key in ("thickness", "overhangs", "cavities"):
            item = self.layers.get(key)
            if item is not None and key in self.shown:
                # a cavity is inside the part: drawn through it on purpose
                self._paint_tris(painter, item[0], item[1], eye, key != "cavities",
                                 depth if key != "cavities" else None)
        if self.layers.get("section") and "section" in self.shown:
            self._paint_section(painter, self.layers["section"])
        if self.layers.get("gaps") and "gaps" in self.shown:
            self._paint_gaps(painter, self.layers["gaps"])
        if self.layers.get("fits") and "fits" in self.shown:
            self._paint_bed(painter)

    # -- what is hidden: the depth IngeTrazo itself rendered ------------------
    def _depth(self, vp):
        """The viewport's depth snapshot for the view on screen, or None.

        IngeTrazo keeps the depth of the frame it drew for its own overlays
        (``_depth_snap``, read back with ``_capture_depth``, as its
        ``_depth_world_at`` does). Not a public API: anything unexpected
        and the layers are simply drawn without hiding (see through)."""
        try:
            cam = vp.camera
            key = tuple((cam.projection_matrix() * cam.view_matrix()).data())
            snap = getattr(vp, "_depth_snap", None)
            if snap is not None and tuple(snap[1].data()) == key:
                return snap
            if self._asked_depth != key and hasattr(vp, "_capture_depth"):
                self._asked_depth = key
                QTimer.singleShot(0, lambda: self._capture_depth(vp, key))
        except Exception:  # noqa: BLE001
            pass
        return None

    @staticmethod
    def _capture_depth(vp, key) -> None:
        try:
            painted = getattr(vp, "_painted_view", None)
            if painted is None or painted[0] != key or vp.context() is None:
                return
            vp.makeCurrent()
            try:
                vp._capture_depth(painted[1], painted[2])
            finally:
                vp.doneCurrent()
            vp.update()
        except Exception:  # noqa: BLE001
            pass

    @staticmethod
    def _seen(depth, pts) -> np.ndarray:
        """Which world points the rendered surface does not hide."""
        buf, mvp, inv, w, h, eye, fwd = depth
        m = np.array(mvp.data(), float).reshape(4, 4).T
        mi = np.array(inv.data(), float).reshape(4, 4).T
        ph = np.c_[pts, np.ones(len(pts))]
        c = ph @ m.T
        ok = c[:, 3] > 1e-9
        cw = np.where(ok, c[:, 3], 1.0)
        nx, ny = c[:, 0] / cw, c[:, 1] / cw
        ix = np.floor((nx + 1.0) * 0.5 * w).astype(np.int64)
        iy = np.floor((ny + 1.0) * 0.5 * h).astype(np.int64)
        inside = ok & (ix >= 0) & (ix < w) & (iy >= 0) & (iy < h)
        d = np.zeros(len(pts))
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                x = np.clip(ix + dx, 0, w - 1)
                y = np.clip(iy + dy, 0, h - 1)
                d = np.maximum(d, buf[y, x])
        q = np.c_[nx, ny, d * 2.0 - 1.0, np.ones(len(pts))] @ mi.T
        qw = np.where(np.abs(q[:, 3]) > 1e-12, q[:, 3], 1.0)
        surf = q[:, :3] / qw[:, None]
        e = np.array(eye.toTuple())
        f = np.array(fwd.toTuple())
        along_pt = (pts - e) @ f
        along_surf = (surf - e) @ f
        tol = 0.004 * np.abs(along_pt) + 1e-5
        hidden = inside & (d < 1.0) & (along_surf < along_pt - tol)
        return ~hidden

    def _paint_tris(self, painter, tris, colour, eye, cull, depth=None) -> None:
        if not len(tris):
            return
        if cull:
            n, _a = mesh3d.normals_areas(tris)
            facing = ((tris.mean(axis=1) - eye) * n).sum(axis=1) < 0
            tris = tris[facing]
        if depth is not None and len(tris):
            try:
                samples = mesh3d._samples(tris)            # (M, 4, 3)
                seen = self._seen(depth, samples.reshape(-1, 3)).reshape(-1, 4)
                tris = tris[seen.any(axis=1)]
            except Exception:  # noqa: BLE001 — never break the frame
                pass
        tris = tris[:MAX_DRAWN]
        if not len(tris):
            return
        px, py, front = self.app.world_to_pixels(tris.reshape(-1, 3))
        px, py, front = (np.asarray(px).reshape(-1, 3), np.asarray(py).reshape(-1, 3),
                         np.asarray(front).reshape(-1, 3))
        fill = QColor(colour)
        fill.setAlpha(150)
        painter.setPen(Qt.NoPen)
        painter.setBrush(fill)
        for i in np.nonzero(front.all(axis=1))[0]:
            painter.drawPolygon(QPolygonF([QPointF(px[i, j], py[i, j]) for j in range(3)]))

    def _paint_gaps(self, painter, gl) -> None:
        """The pairs too close, not the contacts (parts meant to touch)."""
        k = self.k()
        gl = [g for g in gl if g["distance"] * k > CONTACT_MM]
        if not gl:
            return
        pts = np.array([[g["pa"], g["pb"]] for g in gl], float).reshape(-1, 3)
        px, py, front = self.app.world_to_pixels(pts)
        painter.setFont(painter.font())
        for i, g in enumerate(gl):
            a, b = 2 * i, 2 * i + 1
            if not (front[a] and front[b]):
                continue
            pa, pb = QPointF(px[a], py[a]), QPointF(px[b], py[b])
            painter.setPen(QPen(BLUE, 3))
            painter.drawLine(pa, pb)
            painter.setBrush(BLUE)
            painter.setPen(Qt.NoPen)
            for q in (pa, pb):
                painter.drawEllipse(q, 5.0, 5.0)
            painter.setPen(QPen(BLUE))
            painter.drawText(pb + QPointF(8, -8), f"{num(g['distance'] * k, 2)} mm")

    def _paint_bed(self, painter) -> None:
        """The printer's volume at model scale, standing on the bed level
        and centred under the parts."""
        up = self.result["up"]
        e1, e2, u = mesh3d.frame(up)
        allt = np.concatenate([b.tris for b in self.result["bodies"]]).reshape(-1, 3)
        m = np.stack([e1, e2, u], axis=1)
        p = allt @ m
        c = 0.5 * (p.min(0) + p.max(0))
        bx, by, bz = (v / self.k() for v in self.bed_mm())
        size = mesh3d.extents(allt, up) * self.k()
        turned = mesh3d.fits(size, self.bed_mm())["turned"]
        if turned:
            bx, by = by, bx
        z0 = p.min(0)[2]
        corners = []
        for dz in (0.0, bz):
            for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
                q = np.array([c[0] + sx * bx / 2, c[1] + sy * by / 2, z0 + dz])
                corners.append(q @ m.T)
        px, py, front = self.app.world_to_pixels(np.array(corners))
        ok = mesh3d.fits(size, self.bed_mm())["fits"]
        pen = QPen(QColor(46, 157, 79, 170) if ok else RED, 1.5)
        pen.setStyle(Qt.DashLine)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        edges = [(0, 1), (1, 2), (2, 3), (3, 0), (4, 5), (5, 6), (6, 7), (7, 4),
                 (0, 4), (1, 5), (2, 6), (3, 7)]
        for a, b in edges:
            if front[a] and front[b]:
                painter.drawLine(QPointF(px[a], py[a]), QPointF(px[b], py[b]))

    # ---- other tools -------------------------------------------------------------------------------
    def open_inspector(self) -> None:
        for dock in self.app.window.findChildren(QDockWidget):
            if dock.objectName() in ("extension_solid_inspector",):
                self.app.show_panel(dock)
                return
        self.status(t("The Solid Inspector is in Window ▸ Panels."), 5000)

    def _print_frame(self, bodies):
        """World → print millimetres: turned so the build direction is +Z,
        scaled, the lowest corner of all the parts at the origin."""
        up = self.up()
        axis, deg = mesh3d.rotation_between(up, [0, 0, 1])
        k = self.k()
        allp = mesh3d.rotate(np.concatenate([b.tris.reshape(-1, 3) for b in bodies]),
                             axis, deg) * k
        return axis, deg, k, allp.min(0)

    @staticmethod
    def _to_print(frame, pts):
        axis, deg, k, lo = frame
        return mesh3d.rotate(np.asarray(pts, float).reshape(-1, 3), axis, deg) * k - lo

    @staticmethod
    def _to_world(frame, pts):
        axis, deg, k, lo = frame
        return mesh3d.rotate((np.asarray(pts, float).reshape(-1, 3) + lo) / k, axis, -deg)

    def _print_bodies(self, with_infill: bool = True):
        """The parts as the printer gets them: millimetres at the print
        scale, the build direction along +Z, the lowest corner at 0; a
        part with a gyroid infill gets it now."""
        bodies, _sel = self._bodies()
        if bodies is None:
            return None
        frame = self._print_frame(bodies)
        out, skipped = [], []
        for b in bodies:
            tris = self._to_print(frame, b.tris).reshape(-1, 3, 3)
            o = {"name": b.name or t("Loose geometry"), "tris": tris,
                 "colours": b.colours, "colour_names": b.colour_names}
            params = self.infill_of(b.group)
            if with_infill and params:
                try:
                    man, _info = self._infill(b, tris, params, frame)
                    o["tris"] = lattice.to_tris(man)
                    main = b.colours[np.argmax(mesh3d.normals_areas(b.tris)[1])]
                    o["colours"] = np.tile(main, (len(o["tris"]), 1))
                except lattice.LatticeError as exc:
                    skipped.append((o["name"], str(exc)))
            out.append(o)
        for name, why in skipped:
            self.status(t("{p}: infill left out ({why})", p=name, why=t(why)), 8000)
        return out

    # ---- gyroid infill ---------------------------------------------------------------
    def infill_of(self, group):
        if group is None:
            return None
        own = (getattr(group, "ext", None) or {}).get(self.app.key) or {}
        return own.get("gyroid")

    def _settings_infill(self):
        return {"cell": round(self.cell.value(), 3), "wall": round(self.sheet.value(), 3),
                "skin": round(self.skin.value(), 3)}

    def _set_infill(self, value) -> None:
        from .commands import SetInfillCommand
        if getattr(self.scene, "edit_group", None) is not None:
            self.status(t("Close the group you are editing first."), 5000)
            return
        groups, from_sel = B.candidate_groups(self.scene)
        if not from_sel:
            self.status(t("Select the parts first."), 5000)
            return
        vp = self.app.viewport
        vp.history.execute(SetInfillCommand(groups, self.app.key, value))
        vp.notify_scene_changed()
        n = len(groups)
        self.status(t("Gyroid infill on {n} parts", n=n) if value else
                    t("{n} parts print solid again", n=n))
        self._infill_summary()

    def apply_infill(self) -> None:
        params = self._settings_infill()
        if lattice.check(params):
            self.status(t("The wall is too thick for this cell: the gyroid would close up."), 6000)
            return
        self._set_infill(params)

    def remove_infill(self) -> None:
        self._set_infill(None)

    def _infill(self, body, tris_mm, params, frame):
        key = (id(body.group), self.scene.content_version, tuple(sorted(params.items())),
               tuple(np.round(np.r_[frame[0], frame[1], frame[2], frame[3]], 9)))
        hit = self._infill_cache.get(key)
        if hit is None:
            QApplication.setOverrideCursor(Qt.WaitCursor)
            try:
                hit = lattice.infill(tris_mm, params["cell"], params["wall"], params["skin"])
            finally:
                QApplication.restoreOverrideCursor()
            if len(self._infill_cache) > 8:
                self._infill_cache.clear()
            self._infill_cache[key] = hit
        return hit

    def _infill_summary(self, lines=None) -> None:
        bodies, _sel = B.collect(self.scene)
        with_inf = [b for b in bodies if self.infill_of(b.group)]
        if lines is None:
            lines = []
        if not with_inf:
            self.infill_info.setText("\n".join(lines))
            return
        names = ", ".join(b.name for b in with_inf[:4]) + ("…" if len(with_inf) > 4 else "")
        head = t("Parts with an infill: {names}", names=names)
        self.infill_info.setText("<br>".join([head] + lines))

    def preview_infill(self) -> None:
        bodies, _sel = self._bodies()
        if bodies is None:
            return
        targets = [b for b in bodies if self.infill_of(b.group)]
        if not targets:
            self.status(t("Give the selected parts a gyroid infill first."), 5000)
            return
        frame = self._print_frame(bodies)
        self.infill_preview = []
        lines = []
        for b in targets:
            params = self.infill_of(b.group)
            tris = self._to_print(frame, b.tris).reshape(-1, 3, 3)
            try:
                man, info = self._infill(b, tris, params, frame)
            except lattice.LatticeError as exc:
                lines.append(f"{BAD_DOT} {b.name}: {t(str(exc))}")
                continue
            self.infill_preview.append((b, man, frame))
            saved = 100.0 * (1.0 - info["volume"] / max(info["solid_volume"], 1e-12))
            lines.append(f"{GREEN_DOT} {b.name}: " + t("{p} % less material, {n} triangles",
                                                        p=num(saved, 0), n=f"{info['triangles']:,}".replace(",", " ")))
            if params["wall"] < self.wall.value():
                lines.append(f"{WARN_DOT} " + t("Gyroid wall under the minimum wall"))
            if params["skin"] > 0:
                lines.append(f"{GREY_DOT} " + t("Closed skin: resin or powder stays inside, add drain holes"))
        self._infill_summary(lines)
        self.preview_cv = self.scene.content_version
        self._update_cut()

    def _update_cut(self, *_a) -> None:
        if not self.infill_preview:
            return
        polys = []
        for _b, man, frame in self.infill_preview:
            bb = man.bounding_box()
            z = bb[2] + (bb[5] - bb[2]) * self.cut.value() / 100.0
            for p in lattice.section(man, z):
                pts = np.c_[p, np.full(len(p), z)]
                polys.append(self._to_world(frame, pts))
        self.layers["section"] = polys
        self.shown = set(self.shown) | {"section"}
        self.app.viewport.update()

    def _paint_section(self, painter, polys) -> None:
        if not polys:
            return
        path = QPainterPath()
        path.setFillRule(Qt.OddEvenFill)
        allp = np.concatenate(polys)
        px, py, front = self.app.world_to_pixels(allp)
        i = 0
        for p in polys:
            n = len(p)
            if front[i:i + n].all():
                path.moveTo(px[i], py[i])
                for j in range(i + 1, i + n):
                    path.lineTo(px[j], py[j])
                path.closeSubpath()
            i += n
        fill = QColor(VIOLET)
        fill.setAlpha(170)
        painter.setPen(QPen(QColor(70, 30, 120), 1))
        painter.setBrush(fill)
        painter.drawPath(path)

    def _ask_path(self, title, filt, suffix):
        path, _f = QFileDialog.getSaveFileName(self.app.window, title,
                                               str(self._settings.value(_KEY + "last_dir", "")), filt)
        if not path:
            return None
        if not path.lower().endswith(suffix):
            path += suffix
        from pathlib import Path
        self._settings.setValue(_KEY + "last_dir", str(Path(path).parent))
        return path

    def export_3mf(self) -> None:
        bodies = self._print_bodies()
        if bodies is None:
            return
        path = self._ask_path(t("Export 3MF"), "3MF (*.3mf)", ".3mf")
        if not path:
            return
        n = export.write_3mf(path, bodies)
        self.status(t("{n} parts written to {f}", n=n["objects"], f=path), 6000)

    def export_stl(self) -> None:
        bodies = self._print_bodies()
        if bodies is None:
            return
        path = self._ask_path(t("Export STL"), "STL (*.stl)", ".stl")
        if not path:
            return
        n = export.write_stl(path, bodies)
        self.status(t("{n} triangles written to {f}", n=n, f=path), 6000)
