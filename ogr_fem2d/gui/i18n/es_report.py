# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""The Spanish of the report and of what decides the result (spec 006, T33;
``model/report_messages.py``)."""

ES = {
    # words
    "yes": "sí",
    "no": "no",
    "closed": "cerrado",
    "open": "abierto",
    "points": "puntos",
    "nodes": "nudos",
    "solved": "resuelta",
    "not solved (it changes nothing)": "no resuelta (no cambia nada)",
    "plane_strain": "deformación plana",
    "axisymmetric": "axisimetría",
    "external": "externo",
    "excavation": "excavación",
    "material": "material",
    "stage": "fase",
    "graded": "graduada",
    "uniform": "uniforme",
    "valid": "válidos",
    "stale": "obsoletos",
    "incomplete": "incompletos",
    "cancelled": "cancelados",
    "missing": "no hay",
    "damaged": "dañados",
    "not opened": "sin abrir",
    "none": "ninguno",
    # the sections
    "Project summary": "Resumen del proyecto",
    "Field stress": "Tensión de campo",
    "Boundaries": "Contornos",
    "Materials and assignments": "Materiales y asignaciones",
    "Conditions and loads": "Condiciones y cargas",
    "What decides the result (rule 12)": "Lo que decide el resultado (regla 12)",
    # the summary and the analysis
    "Title": "Título",
    "Author": "Autor",
    "Date": "Fecha",
    "Notes": "Notas",
    "Units shown": "Unidades mostradas",
    "Units kept": "Unidades guardadas",
    "m, kN, kPa, kN/m3 (the values do not change with the units shown)":
        "m, kN, kPa, kN/m3 (los valores no cambian con las unidades mostradas)",
    "Stages": "Fases",
    "Stage {n}": "Fase {n}",
    # the field stress
    "constant (compression positive)": "constante (compresión positiva)",
    "gravitational, horizontal strata (compression positive)":
        "gravitatoria, estratos horizontales (compresión positiva)",
    "Angle of sigma_1 from x": "Ángulo de sigma_1 desde x",
    "{value} deg": "{value}°",
    "Surface": "Superficie",
    "Stratum {n}": "Estrato {n}",
    "down to {bottom}, unit weight {gamma}, K {k}, Kz {kz}":
        "hasta {bottom}, peso específico {gamma}, K {k}, Kz {kz}",
    # the boundaries
    "{kind}, {closed}, {vertices} vertices, {arcs} arcs":
        "{kind}, {closed}, {vertices} vértices, {arcs} arcos",
    "{kind}, {closed}, {vertices} vertices, {arcs} arcs, divisions {divisions}":
        "{kind}, {closed}, {vertices} vértices, {arcs} arcos, divisiones {divisions}",
    "{boundary}: vertices": "{boundary}: vértices",
    # the materials
    "Materials": "Materiales",
    "E {E}, nu {nu}, unit weight {gamma}, initial loading {loading}":
        "E {E}, nu {nu}, peso específico {gamma}, carga inicial {loading}",
    "Region at {point}": "Región en {point}",
    "{material}; excavated: {stages}": "{material}; excavada: {stages}",
    "{stage}: {value}": "{stage}: {value}",
    # the conditions and the loads
    "Default of the external boundary": "Por defecto del contorno externo",
    "Condition {n}": "Condición {n}",
    "Condition {n} ({name})": "Condición {n} ({name})",
    "Load {n}": "Carga {n}",
    "Load {n} ({name})": "Carga {n} ({name})",
    "vertex {point}": "vértice {point}",
    "all of {boundary}": "todo {boundary}",
    "{boundary} from {start} to {end}": "{boundary} de {start} a {end}",
    "{where}: imposed ux {ux}, uy {uy}; factors: {factors}":
        "{where}: impuesto ux {ux}, uy {uy}; factores: {factors}",
    "{where}: {kind}; active: {active}": "{where}: {kind}; activa: {active}",
    "{where}: distributed {orientation}, from {start} to {end}; factors: {factors}":
        "{where}: repartida {orientation}, de {start} a {end}; factores: {factors}",
    "{where}: distributed {orientation}, from {start} to {end}, angle {angle} deg; "
    "factors: {factors}":
        "{where}: repartida {orientation}, de {start} a {end}, ángulo {angle}°; "
        "factores: {factors}",
    "{where}: point {orientation}, {force} (per metre out of plane); factors: {factors}":
        "{where}: puntual {orientation}, {force} (por metro fuera del plano); factores: "
        "{factors}",
    "{where}: point {orientation}, {force} (per metre out of plane), angle {angle} deg; "
    "factors: {factors}":
        "{where}: puntual {orientation}, {force} (por metro fuera del plano), ángulo {angle}°; "
        "factores: {factors}",
    # the mesh
    "none: Mesh > Mesh": "ninguna: Malla > Mallar",
    "State": "Estado",
    "of another geometry or other settings: mesh again before calculating":
        "de otra geometría o de otros ajustes: vuelve a mallar antes de calcular",
    "Kind": "Tipo",
    "Nodes per element": "Nudos por elemento",
    "Nodes": "Nudos",
    "Elements": "Elementos",
    "Bound B": "Cota B",
    "{b}, guarantees angles above {angle} deg": "{b}, garantiza ángulos mayores de {angle}°",
    "Smallest angle": "Ángulo menor",
    "Largest angle": "Ángulo mayor",
    "Nodes on the excavations (or on the external, without any)":
        "Nudos en las excavaciones (o en el externo, si no hay)",
    "Added on {segment}": "Añadidos en {segment}",
    "Arcs": "Arcos",
    "Nodes on the axis": "Nudos en el eje",
    "{n}: u_r = 0 there, set by the engine (spec 002, D1 bis)":
        "{n}: allí u_r = 0, lo pone el motor (spec 002, D1 bis)",
    "Warning": "Aviso",
    # what decides the result
    "{value} ({why})": "{value} ({why})",
    # the results
    "{state}": "{state}",
    "{state}: {message}": "{state}: {message}",
    "Written by": "Escritos por",
    "Engine": "Motor",
    "Kept as": "Guardados en",
    "Stage {stage}": "Fase {stage}",
    "Stage {stage} ({name})": "Fase {stage} ({name})",
    "{solved}; greatest displacement {u} at node {node}":
        "{solved}; mayor desplazamiento {u} en el nudo {node}",
    "{stage}: {quantity} at the {at}": "{stage}: {quantity} en los {at}",
    "max {max} at {max_at}, min {min} at {min_at}":
        "máx. {max} en {max_at}, mín. {min} en {min_at}",
    "{stage}: reactions": "{stage}: reacciones",
    "({rx}, {ry}) per metre out of plane": "({rx}, {ry}) por metro fuera del plano",
    "{stage}: reactions on {boundary}": "{stage}: reacciones en {boundary}",
    "no results: calculate the model": "no hay resultados: calcula el modelo",
    "the model changed after the calculation": "el modelo cambió después del cálculo",
    # what decides the result: what, and why
    "units": "unidades",
    "m, kN, kPa, kN/m3": "m, kN, kPa, kN/m3",
    "the model stores and the engine receives kPa (D5); {units} is only what is shown":
        "el modelo guarda y el motor recibe kPa (D5); {units} es solo lo que se muestra",
    "analysis": "análisis",
    "plane strain or axisymmetry": "deformación plana o axisimetría",
    "default_restraint": "restricción por defecto",
    "the external boundary where no condition says otherwise (D16)":
        "el contorno externo donde ninguna condición dice otra cosa (D16)",
    "material {material}: initial_loading": "material {material}: carga inicial",
    "what its elements start with (D11)": "con lo que empiezan sus elementos (D11)",
    "mesh: kind": "malla: tipo",
    "mesh: nodes_per_element": "malla: nudos por elemento",
    "mesh: quality_bound": "malla: cota de calidad",
    "mesh: boundary_nodes": "malla: nudos del contorno",
    "mesh: max_size": "malla: tamaño máximo",
    "mesh: size": "malla: tamaño",
    "mesh: elements": "malla: elementos",
    "mesh: windows": "malla: ventanas",
    "spec 003": "spec 003",
    "B; with sqrt 2 no angle below 20.7 degrees (Shewchuk 2002a)":
        "B; con raíz de 2 ningún ángulo menor de 20,7 grados (Shewchuk 2002a)",
    "graded mesh (spec 003, D5)": "malla graduada (spec 003, D5)",
    "graded mesh": "malla graduada",
    "uniform mesh": "malla uniforme",
    "size bounds (spec 003, D9)": "límites de tamaño (spec 003, D9)",
    "solver: steps": "resolución: escalones",
    "the engine's default (D9: in elasticity it does not move the number)":
        "el defecto del motor (D9: en elasticidad no mueve el número)",
    "solver: tolerance": "resolución: tolerancia",
    "solver: max_iterations": "resolución: iteraciones máximas",
    "solver: max_cuts": "resolución: cortes máximos",
    "the engine's default (D9)": "el defecto del motor (D9)",
    "point loads": "cargas puntuales",
    "the force of the whole ring": "la fuerza de todo el anillo",
    "the engine's convention in axisymmetry (spec 002, D2)":
        "el convenio del motor en axisimetría (spec 002, D2)",
}
