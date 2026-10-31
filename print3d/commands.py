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
