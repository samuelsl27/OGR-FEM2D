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
    # the unit systems of the suite (ogr_core.units.unit_system.SYSTEMS)
    "Metric, stress as kPa": "Métrico, tensiones en kPa",
    "Metric, stress as MPa": "Métrico, tensiones en MPa",
    "Metric, stress as tonnes/m²": "Métrico, tensiones en toneladas/m²",
    "Imperial, stress as tons/ft²": "Imperial, tensiones en toneladas cortas/ft²",
    "Imperial, stress as ksf": "Imperial, tensiones en ksf",
    "Imperial, stress as psf": "Imperial, tensiones en psf",
}
