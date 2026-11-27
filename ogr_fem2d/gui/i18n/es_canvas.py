# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""The Spanish of the canvas and its tools (spec 006, T21 and T22)."""

ES = {
    # the Boundaries menu
    "Add Excavation": "Añadir excavación",
    "Add External": "Añadir externo",
    "Add Material Boundary": "Añadir contorno de material",
    "Add Stage Boundary": "Añadir contorno de fase",
    "Add Circular Excavation": "Añadir excavación circular",
    "Arc": "Arco",
    "Enter Coordinates...": "Introducir coordenadas...",
    "Enter Coordinates": "Introducir coordenadas",
    "Finish Boundary": "Terminar el contorno",
    "Move Vertex": "Mover vértice",
    "Insert Vertex": "Insertar vértice",
    "Delete Vertex": "Borrar vértice",
    "Delete Boundary": "Borrar contorno",
    # what the tools say
    "Click or type the first vertex [Enter: finish, Esc: cancel, Backspace: undo].":
        "Haz clic o escribe el primer vértice [Intro: terminar, Esc: cancelar, Retroceso: "
        "deshacer].",
    "Next vertex [a: arc, Enter: finish, Esc: cancel].":
        "Siguiente vértice [a: arco, Intro: terminar, Esc: cancelar].",
    "Click or type a point the arc goes through.":
        "Haz clic o escribe un punto por el que pase el arco.",
    "Click or type the end of the arc.": "Haz clic o escribe el final del arco.",
    "Click or type the centre of the circle.": "Haz clic o escribe el centro del círculo.",
    "Click or type a point of the circle (or @radius<0).":
        "Haz clic o escribe un punto del círculo (o @radio<0).",
    "Click the vertex to move.": "Haz clic en el vértice que quieres mover.",
    "Click or type where the vertex goes.": "Haz clic o escribe adónde va el vértice.",
    "Click the segment where the vertex goes.": "Haz clic en el segmento donde va el vértice.",
    "Click the vertex to delete.": "Haz clic en el vértice que quieres borrar.",
    "Click the boundary to delete.": "Haz clic en el contorno que quieres borrar.",
    "Cancelled.": "Cancelado.",
    "Boundary added.": "Contorno añadido.",
    "Boundary added; vertices put where it cuts others: %d":
        "Contorno añadido; vértices puestos donde corta a otros: %d",
    "No vertex within %d pixels of the click.": "Ningún vértice a menos de %d píxeles del clic.",
    "No boundary within %d pixels of the click.":
        "Ningún contorno a menos de %d píxeles del clic.",
    "Typed points are for drawing: Boundaries > Add.":
        "Los puntos escritos son para dibujar: Contornos > Añadir.",
    "Draw a boundary first: Boundaries > Add.": "Dibuja antes un contorno: Contornos > Añadir.",
    # the table of coordinates
    "The vertices in order; an empty row is skipped.":
        "Los vértices en orden; una fila vacía no cuenta.",
    "X (%s)": "X (%s)",
    "Y (%s)": "Y (%s)",
    "Add Row": "Añadir fila",
    "Add the vertices": "Añadir los vértices",
    "Row %d: X and Y must be numbers.": "Fila %d: X e Y tienen que ser números.",
    # the errors of drawing (canvas/tools.py)
    "An arc starts at a vertex: give the first vertex before it.":
        "Un arco empieza en un vértice: da antes el primer vértice.",
    "The boundary is closed: finish it, or undo the last step.":
        "El contorno está cerrado: termínalo, o deshaz el último paso.",
    "The point an arc goes through cannot be its start.":
        "El punto por el que pasa un arco no puede ser su inicio.",
    "That point is the last vertex already.": "Ese punto ya es el último vértice.",
    "That point is a vertex of this boundary already.": "Ese punto ya es un vértice de este contorno.",
    "Nothing is drawn yet.": "Todavía no hay nada dibujado.",
    "A closed boundary needs three vertices, an open one two.":
        "Un contorno cerrado necesita tres vértices; uno abierto, dos.",
}
