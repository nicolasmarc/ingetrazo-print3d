# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Nicolas Marc.
"""Texts of the extension: English source, French and Spanish (IngeTrazo's
language; other languages fall back to English). Spanish follows the words
IngeTrazo already uses («Inspector de sólidos», «hermético»…)."""
from __future__ import annotations

FR = {
    "3D Print": "Impression 3D",
    "3D Print panel": "Panneau Impression 3D",
    "Print setup": "Réglages d'impression",
    "Build direction": "Direction d'impression",
    "+Z (up)": "+Z (haut)",
    "Print scale": "Échelle d'impression",
    "Printed size : model size, e.g. 1:50 for a building model.":
        "Taille imprimée : taille du modèle, par exemple 1:50 pour un bâtiment.",
    "Printer bed": "Plateau",
    "Custom…": "Personnalisé…",
    "Overhang limit": "Limite de surplomb",
    "Faces leaning further than this from the vertical need support.":
        "Les faces plus inclinées que cet angle par rapport à la verticale demandent des supports.",
    "Minimum wall": "Paroi minimale",
    "Thinner walls may not print: about two nozzle widths in FDM.":
        "Une paroi plus fine risque de ne pas s'imprimer : environ deux largeurs de buse en FDM.",
    "Minimum gap": "Jeu minimal",
    "Parts closer than this may fuse together when printed.":
        "Des pièces plus proches que ce jeu risquent de se souder à l'impression.",
    "Ready to print?": "Prêt à imprimer ?",
    "Select parts, or nothing for the whole model, then press Analyse.":
        "Sélectionnez des pièces, ou rien pour tout le modèle, puis cliquez sur Analyser.",
    "Selected parts, or the whole model when nothing is selected.":
        "Les pièces sélectionnées, ou tout le modèle quand rien n'est sélectionné.",
    "{n} selected parts": "{n} pièces sélectionnées",
    "Whole model: {n} parts": "Tout le modèle : {n} pièces",
    "Analyse": "Analyser",
    "Every check below at once.": "Tous les contrôles ci-dessous d'un coup.",
    "Solid Inspector…": "Inspecteur de solides…",
    "Holes, open and over-connected edges, reversed faces: IngeTrazo's own Solid Inspector.":
        "Trous, arêtes ouvertes ou sur-connectées, faces inversées : l'Inspecteur de solides d'IngeTrazo.",
    "The Solid Inspector is in Window ▸ Panels.": "L'Inspecteur de solides est dans Fenêtre ▸ Panneaux.",
    "Clear the view": "Effacer de la vue",
    "Inspect": "Inspecter",
    "Overhangs": "Surplombs",
    "Faces that need support, in red.": "Les faces qui demandent des supports, en rouge.",
    "Wall thickness": "Épaisseur de paroi",
    "Walls thinner than the minimum, in orange.": "Les parois plus fines que le minimum, en orange.",
    "Trapped cavities": "Cavités fermées",
    "Closed voids inside a part, in violet: resin or powder stays trapped.":
        "Les vides fermés dans une pièce, en violet : la résine ou la poudre y reste piégée.",
    "Gaps between parts": "Jeux entre pièces",
    "Parts closer than the minimum gap, in blue: they may print fused.":
        "Les pièces plus proches que le jeu minimal, en bleu : elles risquent de s'imprimer soudées.",
    "Fits the build volume": "Tient sur le plateau",
    "Size at the print scale against the printer bed (drawn around the parts).":
        "La taille à l'échelle d'impression comparée au plateau (dessiné autour des pièces).",
    "Lay flat on a face": "Poser sur une face",
    "Then click a face: the part turns so that face rests on the bed.":
        "Cliquez ensuite sur une face : la pièce tourne pour reposer sur cette face.",
    "Best orientation": "Orientation optimale",
    "The three ways to stand the parts that need the least support.":
        "Les trois façons de poser les pièces qui demandent le moins de supports.",
    "Export": "Exporter",
    "3MF (colours)…": "3MF (couleurs)…",
    "One object per part with its colours, in millimetres at the print scale and orientation.":
        "Un objet par pièce avec ses couleurs, en millimètres, à l'échelle et dans l'orientation d'impression.",
    "Binary STL…": "STL binaire…",
    "Every part in one STL, in millimetres at the print scale and orientation.":
        "Toutes les pièces dans un seul STL, en millimètres, à l'échelle et dans l'orientation d'impression.",
    "Export 3MF": "Exporter en 3MF",
    "Export STL": "Exporter en STL",
    "{n} parts written to {f}": "{n} pièces écrites dans {f}",
    "{n} triangles written to {f}": "{n} triangles écrits dans {f}",
    "Close the group you are editing first.": "Fermez d'abord le groupe en cours d'édition.",
    "Nothing to print: no visible faces.": "Rien à imprimer : aucune face visible.",
    "The model changed: press Analyse again.": "Le modèle a changé : cliquez à nouveau sur Analyser.",
    "Watertight parts": "Pièces étanches",
    "see the Solid Inspector": "voir l'Inspecteur de solides",
    "Overhangs > {a}°": "Surplombs > {a}°",
    "of the surface": "de la surface",
    "(red)": "(en rouge)",
    "supports needed": "supports nécessaires",
    "No overhang: no support needed": "Aucun surplomb : pas de supports",
    "Walls under {w}": "Parois sous {w}",
    "triangles": "triangles",
    "(orange)": "(en orange)",
    "thinnest {w}": "la plus fine {w}",
    "No wall under {w}": "Aucune paroi sous {w}",
    "(violet)": "(en violet)",
    "add a drain hole for resin or powder": "prévoir un trou d'évacuation en résine ou en poudre",
    "No trapped cavity": "Aucune cavité fermée",
    "Gaps: a single part": "Jeux : une seule pièce",
    "Gaps under {g}": "Jeux sous {g}",
    "(blue)": "(en bleu)",
    "smallest {g}": "le plus petit {g}",
    "No gap under {g}": "Aucun jeu sous {g}",
    "{n} contacts between parts: they print as one piece":
        "{n} contacts entre pièces : elles s'impriment d'un seul tenant",
    "Size at {s}": "Taille au {s}",
    "fits the bed": "tient sur le plateau",
    "fits the bed, turned a quarter": "tient sur le plateau, tournée d'un quart",
    "too big for the bed": "trop grande pour le plateau",
    "Best orientations: below, Apply turns the parts":
        "Meilleures orientations : ci-dessous, Appliquer tourne les pièces",
    "{n} parts turned as one block: select a part to orient it alone":
        "{n} pièces tournées d'un bloc : sélectionnez une pièce pour l'orienter seule",
    "top": "haut",
    "supports about {v}": "supports env. {v}",
    "height {h}": "hauteur {h}",
    "Apply": "Appliquer",
    "Loose geometry": "Géométrie libre",
    "Loose geometry cannot turn: make it a group first.":
        "La géométrie libre ne peut pas tourner : faites-en d'abord un groupe.",
    "Already in that position.": "Déjà dans cette position.",
    "Parts turned for printing": "Pièces tournées pour l'impression",
    "Click the face to lay on the bed (Select tool).":
        "Cliquez sur la face à poser sur le plateau (outil Sélection).",
    "No part under the cursor.": "Aucune pièce sous le curseur.",
    "Laid flat on that face": "Posée sur cette face",
    'Gyroid infill':
        'Remplissage gyroïde',
    'Lightens a part: it keeps a skin, its inside becomes a gyroid. Made at export; the model stays light.':
        "Allège une pièce : elle garde une peau, son intérieur devient un gyroïde. Construit à l'export : le modèle reste léger.",
    'Cell size':
        'Taille de cellule',
    'Size of one gyroid cell, printed.':
        "Taille d'une cellule du gyroïde, à l'impression.",
    'Gyroid wall':
        'Paroi du gyroïde',
    "Thickness of the gyroid's wall, printed.":
        "Épaisseur de la paroi du gyroïde, à l'impression.",
    'Skin':
        'Peau',
    'Solid outer wall kept around the gyroid; 0 = gyroid only.':
        'Paroi extérieure pleine gardée autour du gyroïde ; 0 = gyroïde seul.',
    'Apply to the selection':
        'Appliquer à la sélection',
    'The selected parts get a gyroid infill with these settings (one undo step).':
        "Les pièces sélectionnées reçoivent un remplissage gyroïde avec ces réglages (une étape d'annulation).",
    'Remove':
        'Retirer',
    'The selected parts print solid again.':
        "Les pièces sélectionnées s'impriment de nouveau pleines.",
    'Preview a cut':
        'Aperçu en coupe',
    'Builds the infill of the selected parts and draws a cut through it.':
        'Construit le remplissage des pièces sélectionnées et en dessine une coupe.',
    'Height of the cut':
        'Hauteur de la coupe',
    'Select the parts first.':
        "Sélectionnez d'abord les pièces.",
    'Gyroid infill on {n} parts':
        'Remplissage gyroïde sur {n} pièces',
    '{n} parts print solid again':
        "{n} pièces s'impriment de nouveau pleines",
    'The wall is too thick for this cell: the gyroid would close up.':
        'Paroi trop épaisse pour cette cellule : le gyroïde se refermerait.',
    'Parts with an infill: {names}':
        'Pièces avec remplissage : {names}',
    'Give the selected parts a gyroid infill first.':
        "Donnez d'abord un remplissage gyroïde aux pièces sélectionnées.",
    '{p} % less material, {n} triangles':
        '{p} % de matière en moins, {n} triangles',
    'Gyroid wall under the minimum wall':
        'Paroi du gyroïde sous la paroi minimale',
    'Closed skin: resin or powder stays inside, add drain holes':
        "Peau fermée : la résine ou la poudre reste dedans, prévoir des trous d'évacuation",
    '{p}: infill left out ({why})':
        '{p} : remplissage non fait ({why})',
    'no manifold3d':
        'manifold3d absent',
    'not watertight':
        'pièce non étanche',
    'too thin':
        'pièce plus fine que sa peau',
    'too big for this cell: about {n} million triangles, take a larger cell':
        'trop grande pour cette cellule : environ {n} millions de triangles, prendre une cellule plus grande',
    'Repair':
        'Réparer',
    'Holes':
        'Trous',
    'Smooth patch':
        'Rustine lisse',
    'Flat cap':
        'Bouchon plat',
    'Smooth: the patch carries on the curve around the hole. Flat: a plain cap. A hole in a flat face is always capped flat.':
        'Lisse : la rustine prolonge la courbure autour du trou. Plat : un simple bouchon. Un trou dans une face plane est toujours bouché à plat.',
    'Show holes':
        'Voir les trous',
    'Finds the holes of the selected parts (or all) and draws their rims.':
        'Cherche les trous des pièces sélectionnées (ou de toutes) et dessine leurs bords.',
    'Fill one hole':
        'Boucher un trou',
    "Then click near a hole's rim: that hole is closed.":
        "Cliquez ensuite près du bord d'un trou : ce trou est bouché.",
    'Fill every hole':
        'Boucher tous les trous',
    'Closes every hole of the selected parts (or all) in one undo step.':
        "Bouche tous les trous des pièces sélectionnées (ou de toutes) en une étape d'annulation.",
    '{n} holes in {p} parts (rims in orange)':
        '{n} trous dans {p} pièces (bords en orange)',
    'No hole: every part is closed':
        'Aucun trou : toutes les pièces sont fermées',
    '{n} holes filled ({f} faces)':
        '{n} trous bouchés ({f} faces)',
    '{n} could not be filled':
        "{n} n'ont pas pu être bouchés",
    'Click near the rim of the hole to fill (Select tool).':
        'Cliquez près du bord du trou à boucher (outil Sélection).',
    'No hole rim near the cursor.':
        'Aucun bord de trou près du curseur.',
    '{n} flat or doubled faces removed':
        '{n} faces aplaties ou en double retirées',
    'Import STL…':
        'Importer un STL…',
    'Imports an STL cleaned for IngeTrazo: corners closer than its 0.1 mm weld are merged properly first, so fine meshes in millimetres arrive whole.':
        "Importe un STL nettoyé pour IngeTrazo : les sommets plus proches que sa soudure de 0,1 mm sont d'abord fusionnés proprement, les maillages fins en millimètres arrivent intacts.",
    'Import STL':
        'Importer un STL',
    'Unit of the file':
        'Unité du fichier',
    'Could not read {f}: {e}':
        'Impossible de lire {f} : {e}',
    '{n} triangles imported':
        '{n} triangles importés',
    '{k} edges under {d} merged':
        '{k} arêtes de moins de {d} fusionnées',
    'At {s} the parts print {d} long: check the print scale. Wall and gap checks skipped.':
        "Au {s}, les pièces font {d} imprimées : vérifiez l'échelle d'impression. Contrôles de parois et de jeux non faits.",
    'Skin…':
        'Peau…',
    'Gyroid…':
        'Gyroïde…',
    'Assembling…':
        'Assemblage…',
    'Cancel':
        'Annuler',
    'Stopped.':
        'Arrêté.',
    'Stopped: nothing written.':
        "Arrêté : rien n'a été écrit.",
}

ES = {
    "3D Print": "Impresión 3D",
    "3D Print panel": "Panel de Impresión 3D",
    "Print setup": "Configuración de impresión",
    "Build direction": "Dirección de impresión",
    "+Z (up)": "+Z (arriba)",
    "Print scale": "Escala de impresión",
    "Printed size : model size, e.g. 1:50 for a building model.":
        "Tamaño impreso : tamaño del modelo, por ejemplo 1:50 para un edificio.",
    "Printer bed": "Cama de la impresora",
    "Custom…": "Personalizada…",
    "Overhang limit": "Límite de voladizo",
    "Faces leaning further than this from the vertical need support.":
        "Las caras más inclinadas que este ángulo respecto a la vertical necesitan soportes.",
    "Minimum wall": "Pared mínima",
    "Thinner walls may not print: about two nozzle widths in FDM.":
        "Una pared más delgada puede no imprimirse: unos dos anchos de boquilla en FDM.",
    "Minimum gap": "Holgura mínima",
    "Parts closer than this may fuse together when printed.":
        "Piezas más cercanas que esta holgura pueden quedar unidas al imprimir.",
    "Ready to print?": "¿Listo para imprimir?",
    "Select parts, or nothing for the whole model, then press Analyse.":
        "Selecciona piezas, o nada para todo el modelo, y pulsa Analizar.",
    "Selected parts, or the whole model when nothing is selected.":
        "Las piezas seleccionadas, o todo el modelo cuando no hay selección.",
    "{n} selected parts": "{n} piezas seleccionadas",
    "Whole model: {n} parts": "Todo el modelo: {n} piezas",
    "Analyse": "Analizar",
    "Every check below at once.": "Todas las comprobaciones de abajo a la vez.",
    "Solid Inspector…": "Inspector de sólidos…",
    "Holes, open and over-connected edges, reversed faces: IngeTrazo's own Solid Inspector.":
        "Agujeros, aristas abiertas o sobreconectadas, caras invertidas: el Inspector de sólidos de IngeTrazo.",
    "The Solid Inspector is in Window ▸ Panels.": "El Inspector de sólidos está en Ventana ▸ Paneles.",
    "Clear the view": "Limpiar la vista",
    "Inspect": "Inspeccionar",
    "Overhangs": "Voladizos",
    "Faces that need support, in red.": "Las caras que necesitan soportes, en rojo.",
    "Wall thickness": "Espesor de pared",
    "Walls thinner than the minimum, in orange.": "Las paredes más delgadas que el mínimo, en naranja.",
    "Trapped cavities": "Cavidades cerradas",
    "Closed voids inside a part, in violet: resin or powder stays trapped.":
        "Los vacíos cerrados dentro de una pieza, en violeta: la resina o el polvo quedan atrapados.",
    "Gaps between parts": "Holguras entre piezas",
    "Parts closer than the minimum gap, in blue: they may print fused.":
        "Las piezas más cercanas que la holgura mínima, en azul: pueden imprimirse unidas.",
    "Fits the build volume": "Cabe en el volumen",
    "Size at the print scale against the printer bed (drawn around the parts).":
        "El tamaño a la escala de impresión frente a la cama (dibujada alrededor de las piezas).",
    "Lay flat on a face": "Apoyar sobre una cara",
    "Then click a face: the part turns so that face rests on the bed.":
        "Luego haz clic en una cara: la pieza gira para apoyarse sobre ella.",
    "Best orientation": "Orientación óptima",
    "The three ways to stand the parts that need the least support.":
        "Las tres formas de colocar las piezas que necesitan menos soportes.",
    "Export": "Exportar",
    "3MF (colours)…": "3MF (colores)…",
    "One object per part with its colours, in millimetres at the print scale and orientation.":
        "Un objeto por pieza con sus colores, en milímetros, a la escala y orientación de impresión.",
    "Binary STL…": "STL binario…",
    "Every part in one STL, in millimetres at the print scale and orientation.":
        "Todas las piezas en un solo STL, en milímetros, a la escala y orientación de impresión.",
    "Export 3MF": "Exportar a 3MF",
    "Export STL": "Exportar a STL",
    "{n} parts written to {f}": "{n} piezas escritas en {f}",
    "{n} triangles written to {f}": "{n} triángulos escritos en {f}",
    "Close the group you are editing first.": "Primero cierra el grupo que estás editando.",
    "Nothing to print: no visible faces.": "Nada que imprimir: ninguna cara visible.",
    "The model changed: press Analyse again.": "El modelo cambió: pulsa Analizar de nuevo.",
    "Watertight parts": "Piezas herméticas",
    "see the Solid Inspector": "ver el Inspector de sólidos",
    "Overhangs > {a}°": "Voladizos > {a}°",
    "of the surface": "de la superficie",
    "(red)": "(rojo)",
    "supports needed": "necesita soportes",
    "No overhang: no support needed": "Sin voladizos: no necesita soportes",
    "Walls under {w}": "Paredes bajo {w}",
    "triangles": "triángulos",
    "(orange)": "(naranja)",
    "thinnest {w}": "la más delgada {w}",
    "No wall under {w}": "Ninguna pared bajo {w}",
    "(violet)": "(violeta)",
    "add a drain hole for resin or powder": "prevé un orificio de drenaje para resina o polvo",
    "No trapped cavity": "Ninguna cavidad cerrada",
    "Gaps: a single part": "Holguras: una sola pieza",
    "Gaps under {g}": "Holguras bajo {g}",
    "(blue)": "(azul)",
    "smallest {g}": "la menor {g}",
    "No gap under {g}": "Ninguna holgura bajo {g}",
    "{n} contacts between parts: they print as one piece":
        "{n} contactos entre piezas: se imprimen en una sola pieza",
    "Size at {s}": "Tamaño a {s}",
    "fits the bed": "cabe en la cama",
    "fits the bed, turned a quarter": "cabe en la cama, girada un cuarto",
    "too big for the bed": "no cabe en la cama",
    "Best orientations: below, Apply turns the parts":
        "Mejores orientaciones: abajo, Aplicar gira las piezas",
    "{n} parts turned as one block: select a part to orient it alone":
        "{n} piezas giradas como un bloque: selecciona una pieza para orientarla sola",
    "top": "arriba",
    "supports about {v}": "soportes aprox. {v}",
    "height {h}": "altura {h}",
    "Apply": "Aplicar",
    "Loose geometry": "Geometría suelta",
    "Loose geometry cannot turn: make it a group first.":
        "La geometría suelta no puede girar: primero conviértela en grupo.",
    "Already in that position.": "Ya está en esa posición.",
    "Parts turned for printing": "Piezas giradas para imprimir",
    "Click the face to lay on the bed (Select tool).":
        "Haz clic en la cara que se apoyará en la cama (herramienta Seleccionar).",
    "No part under the cursor.": "Ninguna pieza bajo el cursor.",
    "Laid flat on that face": "Apoyada sobre esa cara",
    'Gyroid infill':
        'Relleno giroide',
    'Lightens a part: it keeps a skin, its inside becomes a gyroid. Made at export; the model stays light.':
        'Aligera una pieza: conserva una piel y su interior se vuelve un giroide. Se construye al exportar: el modelo sigue ligero.',
    'Cell size':
        'Tamaño de celda',
    'Size of one gyroid cell, printed.':
        'Tamaño de una celda del giroide, impreso.',
    'Gyroid wall':
        'Pared del giroide',
    "Thickness of the gyroid's wall, printed.":
        'Espesor de la pared del giroide, impreso.',
    'Skin':
        'Piel',
    'Solid outer wall kept around the gyroid; 0 = gyroid only.':
        'Pared exterior maciza que rodea el giroide; 0 = solo giroide.',
    'Apply to the selection':
        'Aplicar a la selección',
    'The selected parts get a gyroid infill with these settings (one undo step).':
        'Las piezas seleccionadas reciben un relleno giroide con estos ajustes (un paso de deshacer).',
    'Remove':
        'Quitar',
    'The selected parts print solid again.':
        'Las piezas seleccionadas vuelven a imprimirse macizas.',
    'Preview a cut':
        'Vista en corte',
    'Builds the infill of the selected parts and draws a cut through it.':
        'Construye el relleno de las piezas seleccionadas y dibuja un corte.',
    'Height of the cut':
        'Altura del corte',
    'Select the parts first.':
        'Primero selecciona las piezas.',
    'Gyroid infill on {n} parts':
        'Relleno giroide en {n} piezas',
    '{n} parts print solid again':
        '{n} piezas vuelven a imprimirse macizas',
    'The wall is too thick for this cell: the gyroid would close up.':
        'Pared demasiado gruesa para esta celda: el giroide se cerraría.',
    'Parts with an infill: {names}':
        'Piezas con relleno: {names}',
    'Give the selected parts a gyroid infill first.':
        'Primero da un relleno giroide a las piezas seleccionadas.',
    '{p} % less material, {n} triangles':
        '{p} % menos material, {n} triángulos',
    'Gyroid wall under the minimum wall':
        'Pared del giroide bajo la pared mínima',
    'Closed skin: resin or powder stays inside, add drain holes':
        'Piel cerrada: la resina o el polvo quedan dentro, prevé orificios de drenaje',
    '{p}: infill left out ({why})':
        '{p}: relleno no aplicado ({why})',
    'no manifold3d':
        'falta manifold3d',
    'not watertight':
        'pieza no hermética',
    'too thin':
        'pieza más delgada que su piel',
    'too big for this cell: about {n} million triangles, take a larger cell':
        'demasiado grande para esta celda: unos {n} millones de triángulos, usa una celda mayor',
    'Repair':
        'Reparar',
    'Holes':
        'Agujeros',
    'Smooth patch':
        'Parche suave',
    'Flat cap':
        'Tapa plana',
    'Smooth: the patch carries on the curve around the hole. Flat: a plain cap. A hole in a flat face is always capped flat.':
        'Suave: el parche continúa la curvatura alrededor del agujero. Plana: una tapa simple. Un agujero en una cara plana siempre se tapa plano.',
    'Show holes':
        'Ver agujeros',
    'Finds the holes of the selected parts (or all) and draws their rims.':
        'Busca los agujeros de las piezas seleccionadas (o de todas) y dibuja sus bordes.',
    'Fill one hole':
        'Tapar un agujero',
    "Then click near a hole's rim: that hole is closed.":
        'Luego haz clic cerca del borde de un agujero: se tapa ese agujero.',
    'Fill every hole':
        'Tapar todos los agujeros',
    'Closes every hole of the selected parts (or all) in one undo step.':
        'Tapa todos los agujeros de las piezas seleccionadas (o de todas) en un paso de deshacer.',
    '{n} holes in {p} parts (rims in orange)':
        '{n} agujeros en {p} piezas (bordes en naranja)',
    'No hole: every part is closed':
        'Ningún agujero: todas las piezas están cerradas',
    '{n} holes filled ({f} faces)':
        '{n} agujeros tapados ({f} caras)',
    '{n} could not be filled':
        '{n} no se pudieron tapar',
    'Click near the rim of the hole to fill (Select tool).':
        'Haz clic cerca del borde del agujero que quieres tapar (herramienta Seleccionar).',
    'No hole rim near the cursor.':
        'Ningún borde de agujero cerca del cursor.',
    '{n} flat or doubled faces removed':
        '{n} caras aplastadas o duplicadas eliminadas',
    'Import STL…':
        'Importar un STL…',
    'Imports an STL cleaned for IngeTrazo: corners closer than its 0.1 mm weld are merged properly first, so fine meshes in millimetres arrive whole.':
        'Importa un STL limpiado para IngeTrazo: los vértices más cercanos que su soldadura de 0,1 mm se fusionan antes correctamente, las mallas finas en milímetros llegan enteras.',
    'Import STL':
        'Importar un STL',
    'Unit of the file':
        'Unidad del archivo',
    'Could not read {f}: {e}':
        'No se pudo leer {f}: {e}',
    '{n} triangles imported':
        '{n} triángulos importados',
    '{k} edges under {d} merged':
        '{k} aristas de menos de {d} fusionadas',
    'At {s} the parts print {d} long: check the print scale. Wall and gap checks skipped.':
        'A {s} las piezas miden {d} impresas: revisa la escala de impresión. No se comprueban paredes ni holguras.',
    'Skin…':
        'Piel…',
    'Gyroid…':
        'Giroide…',
    'Assembling…':
        'Ensamblando…',
    'Cancel':
        'Cancelar',
    'Stopped.':
        'Detenido.',
    'Stopped: nothing written.':
        'Detenido: no se escribió nada.',
}

_ALL = {"fr": FR, "es": ES}
_forced: str | None = None


def N_(text: str) -> str:
    """Marks a text for translation where it is written; ``t`` translates
    it where it is shown."""
    return text


def lang() -> str:
    if _forced:
        return _forced
    try:
        from core.i18n import current_language
        code = current_language() or "en"
    except Exception:  # noqa: BLE001 — outside IngeTrazo
        code = "en"
    return code.replace("_", "-").split("-")[0].lower()


def t(text: str, **kw) -> str:
    s = _ALL.get(lang(), {}).get(text, text)
    return s.format(**kw) if kw else s


def num(x: float, nd: int = 1) -> str:
    """A number with the decimal mark of the language."""
    s = f"{x:.{nd}f}"
    return s.replace(".", ",") if lang() in ("fr", "es") else s
