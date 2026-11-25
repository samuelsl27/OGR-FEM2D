# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""The Spanish of the dialogs of the model (spec 006, T23 onward)."""

ES = {
    # the Analysis menu and the stages
    "Project Settings...": "Ajustes del proyecto...",
    "Add Stage": "Añadir fase",
    "Rename Stage...": "Renombrar fase...",
    "Delete Stage": "Borrar fase",
    "Rename Stage": "Renombrar fase",
    "Stage %s": "Fase %s",
    "Name of the stage:": "Nombre de la fase:",
    "The only stage cannot be deleted: add another first.":
        "La única fase no se puede borrar: añade antes otra.",
    # the project settings
    "Project Settings": "Ajustes del proyecto",
    "General": "General",
    "Project Summary": "Resumen del proyecto",
    "A section of a long body: no strain out of the plane; a load is per metre out of the plane.":
        "Una sección de un cuerpo largo: sin deformación fuera del plano; una carga es por metro "
        "fuera del plano.",
    "A body of revolution: x is the radius and the axis is x = 0, so the model lies on x ≥ 0; "
    "a point load is of the whole ring.":
        "Un cuerpo de revolución: x es el radio y el eje es x = 0, así que el modelo está en "
        "x ≥ 0; una carga puntual es la de todo el anillo.",
    "Units": "Unidades",
    "Shown in": "Se muestra en",
    "The values are kept in m, kN and kPa: the unit system changes what is shown and how what is "
    "typed is read, never the values.":
        "Los valores se guardan en m, kN y kPa: el sistema de unidades cambia lo que se muestra y "
        "cómo se lee lo que se escribe, nunca los valores.",
    "Title": "Título",
    "Author": "Autor",
    "Date": "Fecha",
    "Notes": "Notas",
    "Apply": "Aplicar",
    # the field stress
    "Field Stress...": "Tensión de campo...",
    "Field Stress": "Tensión de campo",
    "Constant": "Constante",
    "Gravity": "Gravitatoria",
    "Field stress type:": "Tipo de tensión de campo:",
    "Constant field (compression positive)": "Campo constante (compresión positiva)",
    "σ1, major in the plane (compression +)": "σ1, mayor en el plano (compresión +)",
    "σ3, minor in the plane (compression +)": "σ3, menor en el plano (compresión +)",
    "σz, out of the plane (compression +)": "σz, fuera del plano (compresión +)",
    "Angle of σ1 from the horizontal (anticlockwise)":
        "Ángulo de σ1 con la horizontal (antihorario)",
    "In axisymmetry σz is the hoop stress σθ: the field needs σr = σθ and τrz = 0 (radial "
    "equilibrium), so σ1 horizontal at 0° (or σ3 at 90°) equal to σz.":
        "En axisimetría σz es la tensión circunferencial σθ: el campo necesita σr = σθ y "
        "τrz = 0 (equilibrio radial), así que σ1 horizontal a 0° (o σ3 a 90°) igual a σz.",
    "Gravitational field (compression positive)": "Campo gravitatorio (compresión positiva)",
    "Elevation of the ground surface": "Cota de la superficie del terreno",
    "The strata from the top down, each to its bottom: σv is the weight of what is above, "
    "σh = K σv in the plane and σz = Kz σv out of it.":
        "Los estratos de arriba abajo, cada uno hasta su base: σv es el peso de lo que hay "
        "encima, σh = K σv en el plano y σz = Kz σv fuera de él.",
    "Bottom (%s)": "Base (%s)",
    "Unit weight (%s)": "Peso específico (%s)",
    "K": "K",
    "Kz": "Kz",
    "Add Stratum": "Añadir estrato",
    "Remove Stratum": "Quitar estrato",
    "Stratum %d: write its %s.": "Estrato %d: escribe su %s.",
    # the mesh
    "Mesh Setup...": "Ajustes de la malla...",
    "Mesh Setup": "Ajustes de la malla",
    "Discretize": "Discretizar",
    "Discretize and Mesh": "Discretizar y mallar",
    "Reset Mesh": "Quitar la malla",
    "There is no mesh.": "No hay malla.",
    "Graded": "Graduada",
    "Uniform": "Uniforme",
    "Mesh type": "Tipo de malla",
    "3-noded triangles": "Triángulos de 3 nudos",
    "6-noded triangles": "Triángulos de 6 nudos",
    "Element type": "Tipo de elemento",
    "Quality bound B": "Cota de calidad B",
    "smallest angle guaranteed: %.1f°": "ángulo mínimo garantizado: %.1f°",
    "(to be given)": "(por dar)",
    "(none)": "(ninguna)",
    "Nodes on the excavations": "Nudos en las excavaciones",
    "Nodes on the external": "Nudos en el externo",
    "Longest edge (optional)": "Lado máximo (opcional)",
    "Element size": "Tamaño del elemento",
    "Number of elements (about)": "Número de elementos (aproximado)",
    "Refinement windows": "Ventanas de refinamiento",
    "x min (%s)": "x mín (%s)",
    "y min (%s)": "y mín (%s)",
    "x max (%s)": "x máx (%s)",
    "y max (%s)": "y máx (%s)",
    "Size (%s)": "Tamaño (%s)",
    "Add Window": "Añadir ventana",
    "Remove Window": "Quitar ventana",
    "Discretize first.": "Discretiza antes.",
    "a polygon of %d vertices": "un polígono de %d vértices",
    "Window %d: its corners and its size must be numbers.":
        "Ventana %d: sus esquinas y su tamaño tienen que ser números.",
    "No mesh: Mesh > Discretize and Mesh": "Sin malla: Malla > Discretizar y mallar",
    "Mesh of another geometry: Mesh > Discretize and Mesh":
        "Malla de otra geometría: Malla > Discretizar y mallar",
    "Mesh: %d nodes, %d elements T%d": "Malla: %d nudos, %d elementos T%d",
    "Quality bound B = %.4g (smallest angle guaranteed %.1f°)":
        "Cota de calidad B = %.4g (ángulo mínimo garantizado %.1f°)",
    "Smallest angle of the mesh: %.2f°": "Ángulo mínimo de la malla: %.2f°",
    "Warning of the mesher: %s": "Aviso del mallador: %s",
    "Discretized: %d nodes on %d segments. Then: Mesh > Discretize and Mesh.":
        "Discretizado: %d nudos en %d segmentos. Después: Malla > Discretizar y mallar.",
    "Meshing...": "Mallando...",
    "Meshed: %d nodes, %d elements; smallest angle %.1f° (B = %.4g).":
        "Mallado: %d nudos, %d elementos; ángulo mínimo %.1f° (B = %.4g).",
    "Warnings of the mesher: %d (see the mesh on the status bar).":
        "Avisos del mallador: %d (mira la malla en la barra de estado).",
    # the unit systems of the suite (ogr_core.units.unit_system.SYSTEMS)
    "Metric, stress as kPa": "Métrico, tensiones en kPa",
    "Metric, stress as MPa": "Métrico, tensiones en MPa",
    "Metric, stress as tonnes/m²": "Métrico, tensiones en toneladas/m²",
    "Imperial, stress as tons/ft²": "Imperial, tensiones en toneladas cortas/ft²",
    "Imperial, stress as ksf": "Imperial, tensiones en ksf",
    "Imperial, stress as psf": "Imperial, tensiones en psf",
}
