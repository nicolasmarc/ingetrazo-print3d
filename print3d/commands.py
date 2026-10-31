# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Nicolas Marc.
"""Turning parts for printing, as ONE undo step: IngeTrazo's own group
rotate and move commands, run together."""
from __future__ import annotations

from core.history import Command, MoveGroupCommand, RotateGroupCommand
from PySide6.QtGui import QVector3D


def _v(p) -> QVector3D:
    return QVector3D(float(p[0]), float(p[1]), float(p[2]))


class ReorientCommand(Command):
    """Rotate ``groups`` together about ``centre`` (``axis``, ``degrees``),
    then move them by ``lift``."""

    keeps_paint = True

    def __init__(self, groups, centre, axis, degrees: float, lift) -> None:
        self.steps = []
        if abs(degrees) > 1e-9:
            self.steps += [RotateGroupCommand(g, _v(centre), _v(axis), float(degrees))
                           for g in groups]
        if any(abs(float(x)) > 1e-12 for x in lift):
            self.steps += [MoveGroupCommand(g, _v(lift)) for g in groups]

    def do(self, scene) -> None:
        for s in self.steps:
            s.do(scene)

    def undo(self, scene) -> None:
        for s in reversed(self.steps):
            s.undo(scene)


class SetInfillCommand(Command):
    """Give ``groups`` a gyroid infill (``value``: the settings) or take
    it away (``None``). Kept in ``group.ext[key]``: saved in the .igz and
    carried by copies."""

    def __init__(self, groups, key: str, value) -> None:
        self.groups = list(groups)
        self.key = key
        self.value = dict(value) if value else None
        self.before = [getattr(g, "ext", None) for g in self.groups]
        self.before = [dict(e) if e else None for e in self.before]

    def do(self, scene) -> None:
        for g in self.groups:
            ext = dict(getattr(g, "ext", None) or {})
            own = dict(ext.get(self.key) or {})
            if self.value is None:
                own.pop("gyroid", None)
            else:
                own["gyroid"] = dict(self.value)
            if own:
                ext[self.key] = own
            else:
                ext.pop(self.key, None)
            g.ext = ext or None
        scene.version += 1

    def undo(self, scene) -> None:
        for g, ext in zip(self.groups, self.before):
            g.ext = dict(ext) if ext else None
        scene.version += 1
