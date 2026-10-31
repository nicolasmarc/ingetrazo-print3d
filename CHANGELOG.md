# Changelog

## 0.4.2 — 2026-10-31

- The print scale belongs to the model: kept in its .igz (one undo step
  when changed), 1:1 for a model that has none — no longer carried from
  one model to the next (a bunny at 1:1 analysed at the 1:1000 left by a
  building hung IngeTrazo). A typed scale that is not one goes back.
- A print size under 2 mm or over 20 m is flagged («check the print
  scale») and the wall and gap checks are skipped instead of running away.

## 0.4.1 — 2026-10-31

- Analyse about three times faster on a mesh (the bunny: 3.5 s → 1.3 s):
  triangle faces are read directly and the rest turned in one vectorised
  pass, the watertight count reads the edges without a volume pass, and
  the parts are read once until the model or the selection changes.

## 0.4.0 — 2026-10-31

- Import STL… (Repair section and menu): reads binary or ASCII STL in mm,
  cm, m or inches and cleans it for IngeTrazo's 0.1 mm weld before it
  arrives: exact duplicates joined, edges under 0.2 mm collapsed while the
  surface stays a surface (link condition, no triangle turned over). The
  Stanford bunny in millimetres arrives with its holes only (IngeTrazo's
  own import makes edges between up to 21 faces of it).
- Hole search reads every triangle of the mesh, slivers included, and a
  patch is checked against a replay of IngeTrazo's weld (cell and the 26
  cells around) before it is added.

## 0.3.1 — 2026-10-31

- Fill every hole first removes faces with fewer than three corners and
  doubled faces (a worked bunny had 29 of them: edges between four faces,
  so not watertight even with no hole left).

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
