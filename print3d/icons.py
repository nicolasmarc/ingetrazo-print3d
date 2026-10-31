# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Nicolas Marc.
"""Icons of the 3D Print panel, drawn in code (IngeTrazo has no icon
registry for extensions). Our own simple glyphs on a 24 × 24 grid."""
from __future__ import annotations

import math

_SIZE = 24
_DPR = 3            # drawn at 3x, crisp on high-DPI screens

INK = "#3b4250"
BLUE = "#3a7bd5"
RED = "#d9382f"
GREEN = "#2e9d4f"
VIOLET = "#7b52c7"
ORANGE = "#e07b22"


def _pen(color, w=1.6):
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QColor, QPen
    p = QPen(QColor(color))
    p.setWidthF(w)
    p.setCapStyle(Qt.RoundCap)
    p.setJoinStyle(Qt.RoundJoin)
    return p


def _brush(color, alpha=255):
    from PySide6.QtGui import QBrush, QColor
    c = QColor(color)
    c.setAlpha(alpha)
    return QBrush(c)


def _poly(*pts):
    from PySide6.QtCore import QPointF
    from PySide6.QtGui import QPolygonF
    return QPolygonF([QPointF(x, y) for x, y in pts])


def _arrow(p, x0, y0, x1, y1, color, head=3.5, w=1.6):
    from PySide6.QtCore import QPointF
    from PySide6.QtCore import Qt
    p.setPen(_pen(color, w))
    p.drawLine(QPointF(x0, y0), QPointF(x1, y1))
    a = math.atan2(y1 - y0, x1 - x0)
    p.setBrush(_brush(color))
    p.setPen(Qt.NoPen)
    p.drawPolygon(_poly((x1, y1),
                        (x1 - head * math.cos(a - 0.5), y1 - head * math.sin(a - 0.5)),
                        (x1 - head * math.cos(a + 0.5), y1 - head * math.sin(a + 0.5))))


def _cube(p, x, y, s, fill, ink=INK):
    """A small isometric cube with its top-left-front corner near (x, y)."""
    d = s * 0.45
    p.setPen(_pen(ink, 1.3))
    p.setBrush(_brush(fill, 70))
    p.drawPolygon(_poly((x, y + d), (x + s, y + d), (x + s, y + d + s), (x, y + d + s)))
    p.setBrush(_brush(fill, 130))
    p.drawPolygon(_poly((x, y + d), (x + d, y), (x + s + d, y), (x + s, y + d)))
    p.setBrush(_brush(fill, 40))
    p.drawPolygon(_poly((x + s, y + d), (x + s + d, y), (x + s + d, y + s), (x + s, y + d + s)))


# ---- one function per icon ----------------------------------------------------

def _analyse(p):
    _cube(p, 3, 6, 10, BLUE)
    p.setPen(_pen(INK, 2.0))
    p.setBrush(_brush("#ffffff", 220))
    p.drawEllipse(11, 9, 8, 8)
    p.drawLine(18, 16, 22, 20)
    p.setPen(_pen(GREEN, 1.6))
    p.drawPolyline(_poly((12.8, 13), (14.6, 14.8), (17.2, 11.4)))


def _inspector(p):
    p.setPen(_pen(INK, 1.5))
    p.setBrush(_brush(BLUE, 60))
    p.drawPolygon(_poly((12, 2.5), (20, 5.5), (19, 14), (12, 21.5), (5, 14), (4, 5.5)))
    p.setPen(_pen(GREEN, 2.2))
    p.drawPolyline(_poly((8, 11.5), (11, 14.5), (16.5, 8.5)))


def _overhangs(p):
    # a T-shaped bracket whose overhanging underside is red
    p.setPen(_pen(INK, 1.3))
    p.setBrush(_brush(BLUE, 70))
    p.drawPolygon(_poly((9, 21), (9, 10), (3, 10), (3, 5), (21, 5), (21, 10), (15, 10), (15, 21)))
    p.setPen(_pen(RED, 2.4))
    p.drawLine(3.6, 10.6, 8.6, 10.6)
    p.drawLine(15.4, 10.6, 20.4, 10.6)
    p.setPen(_pen(INK, 1.3))
    p.drawLine(1.5, 21.5, 22.5, 21.5)


def _wall(p):
    p.setPen(_pen(INK, 1.3))
    p.setBrush(_brush(BLUE, 70))
    p.drawRect(3, 3, 5, 18)
    p.drawRect(16, 3, 5, 18)
    _arrow(p, 12, 12, 8.6, 12, RED, 3.2, 1.4)
    _arrow(p, 12, 12, 15.4, 12, RED, 3.2, 1.4)


def _cavities(p):
    p.setPen(_pen(INK, 1.3))
    p.setBrush(_brush(BLUE, 70))
    p.drawRoundedRect(3, 3, 18, 18, 2, 2)
    from PySide6.QtCore import Qt
    pen = _pen(RED, 1.5)
    pen.setStyle(Qt.DashLine)
    p.setPen(pen)
    p.setBrush(_brush("#ffffff", 230))
    p.drawEllipse(7.5, 7.5, 9, 9)


def _gaps(p):
    p.setPen(_pen(INK, 1.3))
    p.setBrush(_brush(BLUE, 70))
    p.drawRect(2.5, 6, 7.5, 12)
    p.drawRect(14, 6, 7.5, 12)
    p.setPen(_pen(RED, 1.4))
    p.drawLine(10.5, 12, 13.5, 12)
    p.drawLine(10.5, 9.5, 10.5, 14.5)
    p.drawLine(13.5, 9.5, 13.5, 14.5)


def _fits(p):
    from PySide6.QtCore import Qt
    pen = _pen(INK, 1.2)
    pen.setStyle(Qt.DashLine)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)
    p.drawRect(3, 3, 18, 15)
    p.setPen(_pen(INK, 1.3))
    p.setBrush(_brush(INK, 200))
    p.drawRect(1.5, 18.5, 21, 3)
    p.setBrush(_brush(GREEN, 110))
    p.setPen(_pen(INK, 1.2))
    p.drawRect(8, 10, 8, 8)


def _lay_flat(p):
    p.setPen(_pen(INK, 1.3))
    p.setBrush(_brush(BLUE, 70))
    p.drawPolygon(_poly((6, 3), (17, 6), (15, 13), (4, 10)))
    _arrow(p, 10.5, 13.5, 10.5, 18.5, ORANGE, 3.2, 1.6)
    p.setPen(_pen(INK, 1.3))
    p.setBrush(_brush(INK, 200))
    p.drawRect(2, 19.5, 20, 2.5)


def _split(p):
    p.setPen(_pen(INK, 1.3))
    p.setBrush(_brush(GREEN, 80))
    p.drawPolygon(_poly((2.5, 6), (10, 6), (8, 12), (10, 18), (2.5, 18)))
    p.drawPolygon(_poly((14, 6), (21.5, 6), (21.5, 18), (14, 18), (12, 12)))


def _merge(p):
    p.setPen(_pen(INK, 1.3))
    p.setBrush(_brush(GREEN, 80))
    p.drawRect(3, 5, 11, 11)
    p.drawRect(10, 9, 11, 11)
    p.setPen(_pen(GREEN, 2.0))
    p.drawLine(10.8, 9.8, 13.2, 9.8)


def _tri_faces(p):
    p.setPen(_pen(INK, 1.0))
    p.setBrush(_brush(GREEN, 60))
    p.drawRect(2, 7, 8, 10)
    p.drawLine(2, 7, 10, 17)
    p.drawLine(2, 12, 6, 7)
    p.drawLine(6, 17, 10, 12)
    _arrow(p, 11.5, 12, 14.5, 12, INK, 2.8, 1.3)
    p.setPen(_pen(INK, 1.3))
    p.setBrush(_brush(GREEN, 110))
    p.drawRect(15, 7, 7, 10)


def _scale(p):
    from PySide6.QtCore import Qt
    p.setPen(_pen(INK, 1.3))
    p.setBrush(_brush(VIOLET, 80))
    p.drawRect(3, 11, 9, 9)
    pen = _pen(INK, 1.1)
    pen.setStyle(Qt.DashLine)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)
    p.drawRect(3, 4, 16, 16)
    _arrow(p, 10, 13, 18.5, 4.5, VIOLET, 3.2, 1.5)


def _hollow(p):
    p.setPen(_pen(INK, 1.3))
    p.setBrush(_brush(VIOLET, 110))
    p.drawRoundedRect(3, 3, 18, 18, 2, 2)
    p.setBrush(_brush("#ffffff", 255))
    p.drawRoundedRect(7, 7, 10, 10, 1, 1)


def _thicken(p):
    p.setPen(_pen(INK, 1.3))
    p.setBrush(_brush(VIOLET, 90))
    p.drawRect(3, 9.5, 18, 5)
    _arrow(p, 12, 9, 12, 3, VIOLET, 3, 1.4)
    _arrow(p, 12, 15, 12, 21, VIOLET, 3, 1.4)


def _smooth(p):
    from PySide6.QtGui import QPainterPath
    from PySide6.QtCore import Qt
    p.setPen(_pen(INK, 1.0))
    p.setBrush(Qt.NoBrush)
    p.drawPolyline(_poly((2, 9), (6, 4), (10, 10), (14, 3), (18, 9), (22, 5)))
    path = QPainterPath()
    path.moveTo(2, 18)
    path.cubicTo(8, 12, 16, 22, 22, 15)
    p.setPen(_pen(VIOLET, 2.2))
    p.drawPath(path)


def _reduce(p):
    p.setPen(_pen(INK, 0.9))
    p.setBrush(_brush(VIOLET, 60))
    p.drawPolygon(_poly((2, 18), (11, 18), (6.5, 5)))
    p.drawLine(4.25, 11.5, 8.75, 11.5)
    p.drawLine(4.25, 11.5, 6.5, 18)
    p.drawLine(8.75, 11.5, 6.5, 18)
    _arrow(p, 12, 12, 15, 12, INK, 2.8, 1.3)
    p.setPen(_pen(INK, 1.3))
    p.setBrush(_brush(VIOLET, 110))
    p.drawPolygon(_poly((15.5, 18), (22.5, 18), (19, 7)))


def _remesh(p):
    p.setPen(_pen(INK, 1.0))
    p.setBrush(_brush(VIOLET, 60))
    p.drawRect(3, 3, 18, 18)
    for i in (9, 15):
        p.drawLine(3, i, 21, i)
        p.drawLine(i, 3, i, 21)
    p.drawLine(3, 3, 21, 21)
    p.drawLine(3, 15, 9, 21)
    p.drawLine(15, 3, 21, 9)


def _wrap(p):
    from PySide6.QtGui import QPainterPath
    from PySide6.QtCore import Qt
    p.setPen(_pen(INK, 1.0))
    p.setBrush(_brush(INK, 40))
    p.drawRect(6, 9, 5, 8)
    p.drawEllipse(12, 7, 6, 6)
    path = QPainterPath()
    path.moveTo(4, 12)
    path.cubicTo(3, 3, 21, 1, 21, 10)
    path.cubicTo(22, 20, 6, 23, 4, 12)
    p.setPen(_pen(VIOLET, 2.0))
    p.setBrush(Qt.NoBrush)
    p.drawPath(path)


def _doc(p, color):
    p.setPen(_pen(INK, 1.3))
    p.setBrush(_brush("#ffffff"))
    p.drawPolygon(_poly((5, 2.5), (15, 2.5), (19.5, 7), (19.5, 21.5), (5, 21.5)))
    p.drawPolyline(_poly((15, 2.5), (15, 7), (19.5, 7)))


def _mf3(p):
    _doc(p, ORANGE)
    from PySide6.QtCore import Qt
    p.setPen(Qt.NoPen)
    for i, c in enumerate((RED, GREEN, BLUE, ORANGE)):
        p.setBrush(_brush(c))
        p.drawRect(7.5 + (i % 2) * 5, 9.5 + (i // 2) * 5, 4, 4)


def _stl(p):
    _doc(p, INK)
    p.setPen(_pen(INK, 1.1))
    p.setBrush(_brush(ORANGE, 120))
    p.drawPolygon(_poly((8, 18.5), (17, 18.5), (12.5, 10)))
    p.drawLine(12.5, 10, 12.5, 18.5)


def _orient(p):
    from PySide6.QtCore import QRectF
    _cube(p, 6, 9, 9, BLUE)
    p.setPen(_pen(ORANGE, 1.7))
    p.setBrush(_brush(ORANGE, 0))
    from PySide6.QtCore import Qt
    p.setBrush(Qt.NoBrush)
    p.drawArc(QRectF(2.5, 2.5, 19, 19), 30 * 16, 120 * 16)
    _arrow(p, 7.5, 4.3, 5.2, 6.4, ORANGE, 3.0, 1.5)
    p.setPen(_pen(INK, 1.3))
    p.setBrush(_brush(INK, 200))
    p.drawRect(2, 20, 20, 2)


def _gyroid(p):
    from PySide6.QtGui import QPainterPath
    from PySide6.QtCore import Qt
    p.setPen(_pen(INK, 1.3))
    p.setBrush(_brush(VIOLET, 40))
    p.drawRoundedRect(2.5, 2.5, 19, 19, 3, 3)
    p.setBrush(Qt.NoBrush)
    p.setPen(_pen(VIOLET, 1.8))
    for y0 in (7.0, 12.0, 17.0):
        path = QPainterPath()
        path.moveTo(3.5, y0)
        path.cubicTo(7, y0 - 4, 9, y0 + 4, 12, y0)
        path.cubicTo(15, y0 - 4, 17, y0 + 4, 20.5, y0)
        p.drawPath(path)


def _cut(p):
    from PySide6.QtCore import Qt
    _cube(p, 4, 6, 11, BLUE)
    p.setPen(_pen(VIOLET, 1.4))
    p.setBrush(_brush(VIOLET, 150))
    p.drawPolygon(_poly((1.5, 14), (14.5, 14), (21.5, 9), (8.5, 9)))
    p.setBrush(Qt.NoBrush)


def _hole_show(p):
    from PySide6.QtCore import Qt
    p.setPen(_pen(INK, 1.2))
    p.setBrush(_brush(BLUE, 70))
    p.drawRoundedRect(2.5, 4, 19, 16, 3, 3)
    p.setPen(_pen(ORANGE, 2.2))
    p.setBrush(_brush("#ffffff", 255))
    p.drawPolygon(_poly((8, 9), (14, 8), (16.5, 12.5), (13, 16), (7.5, 15)))


def _hole_fill_all(p):
    p.setPen(_pen(INK, 1.2))
    p.setBrush(_brush(GREEN, 70))
    p.drawRoundedRect(2.5, 4, 19, 16, 3, 3)
    p.setPen(_pen(GREEN, 1.6))
    p.setBrush(_brush(GREEN, 160))
    p.drawPolygon(_poly((8, 9), (14, 8), (16.5, 12.5), (13, 16), (7.5, 15)))
    p.setPen(_pen("#ffffff", 1.8))
    p.drawPolyline(_poly((9.5, 12), (11.5, 14), (15, 10)))


def _hole_fill_one(p):
    _hole_show(p)
    p.setPen(_pen(INK, 1.1))
    p.setBrush(_brush("#ffffff", 255))
    p.drawPolygon(_poly((13, 11), (13, 22), (15.6, 19.4), (17.6, 23.5), (19.3, 22.7),
                        (17.3, 18.6), (21, 18.6)))


def _stl_in(p):
    _doc(p, INK)
    p.setPen(_pen(INK, 1.1))
    p.setBrush(_brush(ORANGE, 120))
    p.drawPolygon(_poly((8, 18.5), (17, 18.5), (12.5, 10)))
    _arrow(p, 2.5, 6, 9.5, 6, BLUE, 3.0, 1.6)


_DRAW = {
    "analyse": _analyse, "inspector": _inspector,
    "Overhangs": _overhangs, "Wall thickness": _wall,
    "Trapped cavities": _cavities, "Gaps between parts": _gaps,
    "Fits the build volume": _fits, "Lay flat on a face": _lay_flat,
    "Best orientation": _orient,
    "Gyroid infill": _gyroid, "Preview a cut": _cut,
    "Show holes": _hole_show, "Fill every hole": _hole_fill_all,
    "Fill one hole": _hole_fill_one, "Import STL": _stl_in,
    "Split into bodies": _split, "Merge bodies": _merge,
    "Triangles → faces": _tri_faces,
    "Scale to size": _scale, "Hollow": _hollow, "Thicken": _thicken,
    "Smooth": _smooth, "Reduce": _reduce, "Remesh": _remesh,
    "Watertight wrap": _wrap,
    "3MF (colours)…": _mf3, "Binary STL…": _stl,
}


def icon(key):
    """A QIcon for ``key``; ``None`` when there is no drawing for it."""
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QIcon, QPainter, QPixmap
    fn = _DRAW.get(key)
    if fn is None:
        return None
    pm = QPixmap(_SIZE * _DPR, _SIZE * _DPR)
    pm.setDevicePixelRatio(_DPR)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    fn(p)
    p.end()
    return QIcon(pm)
