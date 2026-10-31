# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Nicolas Marc.
"""The unit the panel speaks in, after the document's units system.

Printed sizes are small: a metric document (m, cm or mm) reads them in
millimetres, an imperial one (inches, feet, feet-inches, fractions) in
inches. Everything is stored in millimetres; only what is shown changes."""
from __future__ import annotations

from .lang import num

IN_MM = 25.4
IN3_CM3 = 16.387064
IMPERIAL = {"in", "ft", "ft-in", "in-frac", "ft-in-frac"}
_forced: str | None = None


def document_unit() -> str:
    if _forced:
        return _forced
    try:
        from core.units import model_unit
        return model_unit() or "m"
    except Exception:  # noqa: BLE001 — outside IngeTrazo
        return "m"


def imperial() -> bool:
    return document_unit() in IMPERIAL


def unit() -> str:
    """``"in"`` or ``"mm"``."""
    return "in" if imperial() else "mm"


def factor() -> float:
    """Millimetres per shown unit."""
    return IN_MM if imperial() else 1.0


def suffix() -> str:
    return ' in' if imperial() else " mm"


def length(mm: float, nd: int | None = None) -> str:
    """A printed length, in the shown unit with its mark."""
    if imperial():
        return f"{num(mm / IN_MM, 3 if nd is None else nd + 2)} in"
    return f"{num(mm, 1 if nd is None else nd)} mm"


def size(xyz_mm) -> str:
    if imperial():
        return " × ".join(num(v / IN_MM, 2) for v in xyz_mm) + " in"
    return " × ".join(f"{v:.0f}" for v in xyz_mm) + " mm"


def volume(cm3: float) -> str:
    if imperial():
        return f"{num(cm3 / IN3_CM3, 2)} in³"
    return f"{num(cm3, 2)} cm³"
