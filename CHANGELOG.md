# Changelog

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
