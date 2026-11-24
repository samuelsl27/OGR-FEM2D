# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""The Spanish of the messages of the operations (``api/messages.py``,
``FEM_MESSAGES``): the key is the English template, its fields kept."""

ES = {
    "The model refuses it ({count} problems): {first}":
        "El modelo lo rechaza ({count} problemas): {first}",
    "The model refuses it: {first}": "El modelo lo rechaza: {first}",
    "Every problem, with its rule and where, is in the details.":
        "Cada problema, con su regla y dónde, está en los detalles.",
    "The file cannot be read ({count} problems): {first}":
        "El archivo no se puede leer ({count} problemas): {first}",
    "The file cannot be read: {first}": "El archivo no se puede leer: {first}",
    "{name}: OGR FEM2D opens .ogrfem2d, .ogr (OGR Slip2D) and .dxf files.":
        "{name}: OGR FEM2D abre archivos .ogrfem2d, .ogr (OGR Slip2D) y .dxf.",
    "{name}: a model is saved as .ogrfem2d.": "{name}: un modelo se guarda como .ogrfem2d.",
    "Model {model} has no file yet.": "El modelo {model} todavía no tiene archivo.",
    "Give the path to save it to.": "Da la ruta donde guardarlo.",
    "Model {model} has unsaved changes.": "El modelo {model} tiene cambios sin guardar.",
    "Save it (project_save), or close it with discard_changes=true.":
        "Guárdalo (project_save), o ciérralo con discard_changes=true.",
    "history action": "acción de la historia",
    "steps must be between 1 and 200.": "steps tiene que estar entre 1 y 200.",
    "{where} must be text.": "{where} tiene que ser texto.",
    "argument of {op}": "argumento de {op}",
    "A stretch of a boundary needs both its start and its end, or neither (all of it).":
        "Un tramo de un contorno necesita su inicio y su fin, o ninguno (todo el contorno).",
    "Give a stretch of a boundary (boundary, start, end) or a vertex, one of the two.":
        "Da un tramo de un contorno (boundary, start, end) o un vértice, uno de los dos.",
    'arcs[{index}] must be {{"segment": k, "centre": [x, y]}}.':
        'arcs[{index}] tiene que ser {{"segment": k, "centre": [x, y]}}.',
    "Give the radius or a point the circle goes through, one of the two.":
        "Da el radio o un punto por el que pase el círculo, uno de los dos.",
    "There is no place {index} for a stage: there are {count} stages, from 0 to {count}.":
        "No hay lugar {index} para una fase: hay {count} fases, de 0 a {count}.",
    'strata[{index}] must be {{"bottom", "unit_weight", "k", "kz"}}.':
        'strata[{index}] tiene que ser {{"bottom", "unit_weight", "k", "kz"}}.',
    "A point load is at a vertex: give vertex, not boundary.":
        "Una carga puntual está en un vértice: da vertex, no boundary.",
    "A distributed load is on a stretch of a boundary: give boundary (and start, end), not vertex.":
        "Una carga repartida está en un tramo de un contorno: da boundary (y start, end), no "
        "vertex.",
    "{name} is both given and cleared.": "{name} se da y se borra a la vez.",
    'windows[{index}] must be {{"polygon": [[x, y], ...], "size": h}}.':
        'windows[{index}] tiene que ser {{"polygon": [[x, y], ...], "size": h}}.',
    "Model {model} has no file: the results are written beside it.":
        "El modelo {model} no tiene archivo: los resultados se escriben junto a él.",
    "Save it first (project_save).": "Guárdalo antes (project_save).",
    "Model {model} has changes that are not in its file.":
        "El modelo {model} tiene cambios que no están en su archivo.",
    "Save it first (project_save): the results carry the file's fingerprint, and would be "
    "stale at once.":
        "Guárdalo antes (project_save): los resultados llevan la huella del archivo, y nacerían "
        "obsoletos.",
    "The results are {status} ({message}).": "Los resultados están {status} ({message}).",
    "Calculate the model again (analysis_run), or read them as they are with "
    "allow_invalid=true: every answer then says their state.":
        "Calcula otra vez el modelo (analysis_run), o léelos como están con allow_invalid=true: "
        "cada respuesta dice entonces su estado.",
    "The field cannot be drawn so: {what}": "El campo no se puede dibujar así: {what}",
}
