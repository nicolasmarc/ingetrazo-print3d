# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Nicolas Marc.
"""3D Print — get IngeTrazo models ready for a 3D printer.

Checks (overhangs, wall thickness, trapped cavities, gaps between parts,
size against the bed), the orientation that needs the least support,
laying a part flat on a face, a gyroid infill under a skin, and export to
3MF with colours or STL at the print scale. The analyses only draw over the view: the document changes
only when you turn parts (one undo step)."""
__version__ = "0.2.2"


def setup(app):
    from .lang import t
    from .panel import Panel

    panel = Panel(app)
    dock = app.add_panel(t("3D Print"), panel)
    menu = app.add_menu(t("3D Print"))
    menu.addAction(t("3D Print panel"), lambda: app.show_panel(dock))
    menu.addAction(t("Analyse"), lambda: (app.show_panel(dock), panel.analyse_all()))
    menu.addAction(t("Gyroid infill") + "…",
                   lambda: (app.show_panel(dock), panel.open_section("gyroid")))
    menu.addSeparator()
    menu.addAction(t("Export 3MF") + "…", panel.export_3mf)
    menu.addAction(t("Export STL") + "…", panel.export_stl)
    app._print3d_panel = panel
