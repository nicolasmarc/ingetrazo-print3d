# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Nicolas Marc.
"""The 3D Print tab's icon: a nozzle laying the top layer of a part.

IngeTrazo 0.6.2 shows the side tray's tabs as icons only; a panel without
one gets its initial. Drawn on IngeTrazo's 48-unit icon square, in the
theme's ink with the accent colour for the layer being laid, so it sits
with IngeTrazo's own tab icons. When the host lets us, the drawing is
registered under a key so a change of theme or accent redraws it; else a
plain QIcon is drawn once. Older IngeTrazo (no ``icon=``): no icon."""
from __future__ import annotations

KEY = "print3d_panel"


def draw(p, ink, accent) -> None:
    """Draw into a 48×48 square (the drawing keeps to 8..40), with the
    painter's pen already set to ``ink``."""
    from PySide6.QtCore import QPointF, QRectF, Qt
    from PySide6.QtGui import QColor, QPolygonF

    # the hot end: a block, then the nozzle narrowing to its tip
    p.setBrush(Qt.NoBrush)
    p.drawRoundedRect(QRectF(16, 7, 16, 7), 1.5, 1.5)
    p.drawPolygon(QPolygonF([QPointF(19, 14), QPointF(29, 14),
                             QPointF(25.5, 19), QPointF(22.5, 19)]))
    # the part: two layers already printed
    p.drawRoundedRect(QRectF(9, 35, 30, 4.5), 2.25, 2.25)
    p.drawRoundedRect(QRectF(12, 27.5, 24, 4.5), 2.25, 2.25)
    # the layer being laid, from the left up to the nozzle, in the accent
    p.save()
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(accent))
    p.drawRoundedRect(QRectF(14, 21, 11.5, 4), 2, 2)
    p.restore()


def _host_colours():
    """IngeTrazo's icon ink and accent, or the palette's text and orange."""
    from PySide6.QtGui import QColor
    from PySide6.QtWidgets import QApplication
    try:
        from views.theme import accent_color, icon_ink
        return icon_ink(), accent_color()
    except Exception:  # noqa: BLE001 — older host: the palette
        app = QApplication.instance()
        ink = app.palette().windowText().color() if app else QColor(40, 44, 52)
        return ink, QColor(232, 120, 40)


def qicon():
    """The icon drawn once, as a QIcon (when the host cannot redraw it)."""
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QIcon, QPainter, QPen, QPixmap
    ink, accent = _host_colours()
    pm = QPixmap(48, 48)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing, True)
    pen = QPen(ink, 2.2)
    pen.setJoinStyle(Qt.RoundJoin)
    pen.setCapStyle(Qt.RoundCap)
    p.setPen(pen)
    draw(p, ink, accent)
    p.end()
    return QIcon(pm)


def for_panel():
    """What to give ``add_panel(icon=...)``: the key of a drawing the host
    redraws with the theme, or a QIcon."""
    try:
        from views import icons as host
        table = getattr(host, "_DRAW", None)
        if isinstance(table, dict):
            if KEY not in table:
                table[KEY] = lambda p, ink: draw(p, ink, host._accent())
            if not host.tool_icon(KEY).isNull():
                return KEY
    except Exception:  # noqa: BLE001 — the host's drawing table changed
        pass
    return qicon()
