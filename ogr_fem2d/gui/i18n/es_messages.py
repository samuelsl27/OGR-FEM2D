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
    # the lines of the report of a conversion (model/import_messages.py)
    "distributed load {name}: its ends are not on the external boundary":
        "carga repartida {name}: sus extremos no están en el contorno externo",
    "a vertex inserted in the external boundary at {point}, an end of the distributed load "
    "{name}":
        "un vértice añadido al contorno externo en {point}, un extremo de la carga repartida "
        "{name}",
    "line load {name}: its point is not on the external boundary":
        "carga lineal {name}: su punto no está en el contorno externo",
    "a vertex inserted in the external boundary at {point}, the point of the line load {name}":
        "un vértice añadido al contorno externo en {point}, el punto de la carga lineal {name}",
    "a region with no material in Slip2D": "una región sin material en Slip2D",
    "the region with material {material} at {point} had no assignment of its own in Slip2D "
    "(inherited, or Slip2D's first material)":
        "la región con el material {material} en {point} no tenía asignación propia en Slip2D "
        "(heredada, o el primer material de Slip2D)",
    "distributed load {name}: Slip2D's normal pointed out of the ground; brought with the sign "
    "changed (D6)":
        "carga repartida {name}: la normal de Slip2D apuntaba fuera del terreno; traída con el "
        "signo cambiado (D6)",
    "distributed load {name}: runs the other way round the external boundary; its angle to the "
    "boundary + 180 degrees":
        "carga repartida {name}: recorre el contorno externo al revés; su ángulo respecto al "
        "contorno + 180 grados",
    "line load {name}: {orientation} at a corner of the boundary, where the boundary has no one "
    "direction":
        "carga lineal {name}: {orientation} en una esquina del contorno, donde el contorno no "
        "tiene una sola dirección",
    "line load {name}: {orientation} turned into an angle of {angle} degrees from the horizontal":
        "carga lineal {name}: {orientation} convertida en un ángulo de {angle} grados desde la "
        "horizontal",
    "conditions: the sides and the bottom of the external boundary fixed in x and y, the surface "
    "free (as the reference program)":
        "condiciones: los lados y la base del contorno externo fijos en x e y, la superficie "
        "libre (como el programa de referencia)",
    "materials: E and nu not given; the model is not translated to the engine until they are "
    "(D16)":
        "materiales: E y nu sin dar; el modelo no pasa al motor hasta que se den (D16)",
    "field stress: none (constant, zero); the gravitational field under the real ground surface "
    "is spec 009":
        "tensión de campo: ninguna (constante, cero); el campo gravitatorio bajo la superficie "
        "real del terreno es la spec 009",
    "one stage; the mesh settings by default (graded, six-node triangles, B = sqrt 2), "
    "boundary_nodes to be given":
        "una fase; los ajustes de malla por defecto (graduada, triángulos de seis nudos, "
        "B = raíz de 2), los nudos del contorno por dar",
    "{count} boundaries (1 external, {materials} material)":
        "{count} contornos (1 externo, {materials} de material)",
    "{count} materials (name, colour, unit weight)":
        "{count} materiales (nombre, color, peso específico)",
    "1 material (name, colour, unit weight)": "1 material (nombre, color, peso específico)",
    "{count} regions with their material": "{count} regiones con su material",
    "1 region with its material": "1 región con su material",
    "{count} loads": "{count} cargas",
    "1 load": "1 carga",
    "the strength of the materials (no law of this version uses it, spec 008) and their pore "
    "pressure settings":
        "la resistencia de los materiales (ninguna ley de esta versión la usa, spec 008) y sus "
        "ajustes de presión intersticial",
    "{count} boundaries of type {kind}": "{count} contornos del tipo {kind}",
    "1 boundary of type {kind}": "1 contorno del tipo {kind}",
    "{count} supports": "{count} soportes",
    "1 support": "1 soporte",
    "the water pressure grid, the seepage mesh and its results":
        "la malla de presiones de agua, la malla de filtración y sus resultados",
    "the analysis settings: methods, searches, seismic loading, statistics":
        "los ajustes del análisis: métodos, búsquedas, carga sísmica, estadística",
    "layer {layer} ({count} entities): not one of the four kinds of boundary":
        "capa {layer} ({count} entidades): no es de ninguno de los cuatro tipos de contorno",
    "layer {layer} (1 entity): not one of the four kinds of boundary":
        "capa {layer} (1 entidad): no es de ninguno de los cuatro tipos de contorno",
    "layer {layer}: {count} SPLINE came as straight pieces (the core's reader flattens them; the "
    "mid-side nodes will be on the chords)":
        "capa {layer}: {count} SPLINE llegaron como tramos rectos (el lector del núcleo las "
        "aplana; los nudos intermedios quedarán en las cuerdas)",
    "{count} {key}: {reason}; not read": "{count} {key}: {reason}; no leído",
    "not in the plane of the drawing (its extrusion leans away from Z)":
        "fuera del plano del dibujo (su extrusión se aparta de Z)",
    "could not be read (a malformed entity)": "no se pudo leer (una entidad mal formada)",
    "fewer than two distinct points": "menos de dos puntos distintos",
    "the core's reader does not read this type": "el lector del núcleo no lee este tipo",
    "{count} boundaries: {kinds}; {arcs} pieces of arc":
        "{count} contornos: {kinds}; {arcs} trozos de arco",
    "1 boundary: {kinds}; {arcs} pieces of arc": "1 contorno: {kinds}; {arcs} trozos de arco",
    "{count} external": "externos: {count}",
    "{count} material": "de material: {count}",
    "{count} excavation": "excavaciones: {count}",
    "1 excavation": "excavaciones: 1",
    "{count} stage": "de fase: {count}",
    "normal to the boundary": "normal al contorno",
    "vertical": "vertical",
    "horizontal": "horizontal",
    "at an angle from the horizontal": "con un ángulo desde la horizontal",
    "at an angle to the boundary": "con un ángulo respecto al contorno",
    "materials, assignments, stages, conditions and loads: none, the user's to give":
        "materiales, asignaciones, fases, condiciones y cargas: ninguno, los da el usuario",
}
