# Changelog

## 0.3.0 — 2026-10-31

- Repair: show the holes of the parts (rims in orange), fill every hole in
  one undo step, or click near a rim to fill that one. Smooth patch (it
  carries on the curve around the hole: bi-harmonic fairing) or flat cap;
  a hole in a flat face always gets one flat face. A patch that would not
  close cleanly once IngeTrazo welds its corners falls back to a simpler
  one, never to a broken surface. The Stanford bunny's 16 holes close in
  a few seconds.

## 0.2.2 — 2026-10-31

- Gyroid infill: the mesh resolution follows the part's size, and a part
  too big for its cell (over about 2 million triangles, some 2 GB of
  memory) is refused with the advice to take a larger cell, instead of
  running for minutes. A 10 cm organic part takes cells of about 10 mm.

## 0.2.1 — 2026-10-31

- The panel's sections fold under their titles (remembered); Gyroid
  infill starts folded and opens from Extensions ▸ 3D Print ▸ Gyroid
  infill…. The custom bed sizes show only for a custom bed.

## 0.2.0 — 2026-10-31

- Gyroid infill: the selected parts keep a skin and their inside becomes a
  gyroid sheet (cell size, wall and skin set in printed millimetres). The
  setting is kept with the part (one undo step) and the infill is built at
  export, so the model stays light; a cut previews it in the view, with
  the material saved.

## 0.1.0 — 2026-10-31

- First version. Checks drawn over the view: watertight parts (through
  IngeTrazo's Solid Inspector), overhangs, wall thickness, trapped
  cavities, gaps between parts, size against the printer bed.
- Best orientation (three proposals) and lay flat on a face, each one
  undo step.
- Export to 3MF (one object per part, with colours) and binary STL, in
  millimetres at the print scale and orientation.
- Panel and menu in English, French and Spanish, following IngeTrazo's
  language.
