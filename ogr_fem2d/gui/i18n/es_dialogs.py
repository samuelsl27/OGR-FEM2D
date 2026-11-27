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
    # the materials and the assignment
    "Define Materials...": "Definir materiales...",
    "Define Materials": "Definir materiales",
    "Assign Properties...": "Asignar propiedades...",
    "Add": "Añadir",
    "Delete": "Borrar",
    "Name": "Nombre",
    "Colour": "Color",
    "Initial element loading": "Carga inicial del elemento",
    "Field stress only": "Solo tensión de campo",
    "Field stress and body force": "Tensión de campo y peso propio",
    "Body force only": "Solo peso propio",
    "None": "Ninguna",
    "Unit weight": "Peso específico",
    "Elastic properties (isotropic)": "Propiedades elásticas (isótropo)",
    "Young's modulus E": "Módulo de Young E",
    "Poisson's ratio ν": "Coeficiente de Poisson ν",
    "(E and ν to be given)": "(E y ν por dar)",
    "The unit weight acts only with an initial loading that has the body force.":
        "El peso específico solo actúa con una carga inicial que tenga el peso propio.",
    "Material %d": "Material %d",
    "Assign": "Asignar",
    "Choose, then click inside the regions:": "Elige y haz clic dentro de las regiones:",
    "Excavate": "Excavar",
    "Fill": "Rellenar",
    "This stage only": "Solo esta fase",
    "An excavation or a fill in the stage shown only; without it, from that stage on.":
        "Una excavación o un relleno solo en la fase que se ve; sin marcar, desde esa fase "
        "en adelante.",
    "Click inside the regions [Esc: stop].": "Haz clic dentro de las regiones [Esc: "
        "terminar].",
    "Assigned in the stage shown.": "Asignado en la fase que se ve.",
    "Assign Material": "Asignar material",
    "%s cannot be taken away once given: write its value.":
        "%s no se puede quitar una vez dado: escribe su valor.",
    # the conditions and the loads
    "Restrain X": "Restringir X",
    "Restrain Y": "Restringir Y",
    "Restrain X, Y": "Restringir X, Y",
    "Free": "Liberar",
    "Impose Displacement...": "Imponer desplazamiento...",
    "Impose Displacement": "Imponer desplazamiento",
    "External Default...": "Por defecto del externo...",
    "External Default": "Por defecto del externo",
    "Where no condition says otherwise, the external is:":
        "Donde ninguna condición diga otra cosa, el externo está:",
    "Restrained in X": "Restringido en X",
    "Restrained in Y": "Restringido en Y",
    "Restrained in X and Y": "Restringido en X e Y",
    "Free (no restraint)": "Libre (sin restricción)",
    "Delete Condition": "Borrar condición",
    "Add Distributed Load...": "Añadir carga repartida...",
    "Add Distributed Load": "Añadir carga repartida",
    "Add Point Load...": "Añadir carga puntual...",
    "Add Point Load": "Añadir carga puntual",
    "Delete Load": "Borrar carga",
    "Factors by Stage...": "Factores por fase...",
    "Factors by Stage": "Factores por fase",
    "Click the segments or vertices (within %d pixels) [Esc: stop].":
        "Haz clic en los segmentos o vértices (a menos de %d píxeles) [Esc: terminar].",
    "Nothing of that kind there.": "Ahí no hay nada de ese tipo.",
    "A point load goes on a vertex.": "Una carga puntual va en un vértice.",
    "A distributed load goes on a segment.": "Una carga repartida va en un segmento.",
    "(not imposed)": "(no impuesto)",
    "ux (+ towards +x)": "ux (+ hacia +x)",
    "uy (+ upward)": "uy (+ hacia arriba)",
    "Then click the segments or vertices where it goes.":
        "Después haz clic en los segmentos o vértices donde va.",
    "Choose where": "Escoger dónde",
    "of the whole ring": "del anillo entero",
    "per metre out of the plane": "por metro fuera del plano",
    "Magnitude (%s)": "Magnitud (%s)",
    "(as at the start)": "(como al inicio)",
    "Magnitude at the start": "Magnitud al inicio",
    "Magnitude at the end": "Magnitud al final",
    "Normal to the boundary (+ into the ground)": "Normal al contorno (+ hacia el terreno)",
    "Vertical (+ downward)": "Vertical (+ hacia abajo)",
    "Horizontal (+ towards +x)": "Horizontal (+ hacia +x)",
    "At an angle from the horizontal (anticlockwise)":
        "Con un ángulo desde la horizontal (antihorario)",
    "At an angle to the boundary (anticlockwise)":
        "Con un ángulo respecto al contorno (antihorario)",
    "Orientation": "Orientación",
    "Angle": "Ángulo",
    "Only for an orientation at an angle.": "Solo para una orientación con ángulo.",
    "Then click the vertices where it goes.": "Después haz clic en los vértices donde va.",
    "Then click the segments where it goes (start to end, in the order of the boundary's "
    "vertices).":
        "Después haz clic en los segmentos donde va (del inicio al final, en el orden de los "
        "vértices del contorno).",
    "The total in a stage is factor × value (0 takes a load off); a restraint is ticked where "
    "it acts; an imposed displacement with no factor does not act there.":
        "El total en una fase es factor × valor (0 quita una carga); una restricción va "
        "marcada donde actúa; un desplazamiento impuesto sin factor no actúa ahí.",
    "point load": "carga puntual",
    "distributed load": "carga repartida",
    "imposed displacement": "desplazamiento impuesto",
    "restraint %s": "restricción %s",
    "Row %d, %s: write a number.": "Fila %d, %s: escribe un número.",
    # files: importing, recent, the report
    "Import OGR Slip2D Model...": "Importar un modelo de OGR Slip2D...",
    "Import DXF...": "Importar DXF...",
    "Import": "Importar",
    "Open Recent": "Abrir reciente",
    "Clear the List": "Vaciar la lista",
    "(no model opened yet)": "(todavía ningún modelo)",
    "The list is empty.": "La lista está vacía.",
    "%s is no longer there: taken off the list.": "%s ya no está: quitado de la lista.",
    "Conversion Report": "Informe de la conversión",
    "Converted from %s": "Convertido desde %s",
    "What came": "Lo que vino",
    "What did not come": "Lo que no vino",
    "Defaults taken (they change the result: check them)":
        "Valores por defecto tomados (cambian el resultado: revísalos)",
    "What was changed": "Lo que se cambió",
    "Still to do in the model": "Lo que falta en el modelo",
    "Nothing.": "Nada.",
    # T29
    "Segment Divisions...": "Divisiones del segmento...",
    "Segment Divisions": "Divisiones del segmento",
    "Divisions of each segment clicked (0: the mesher decides):":
        "Divisiones de cada segmento en que hagas clic (0: decide el mallador):",
    "Click a segment, not a vertex.": "Haz clic en un segmento, no en un vértice.",
    "The stretch grows to the segment clicked.": "El tramo crece hasta el segmento del clic.",
    # a problem of the model, by its rule (gui/problems.py)
    "The kind of analysis is not one the program knows.":
        "El tipo de análisis no es uno que el programa conozca.",
    "The unit system is not one the program knows.":
        "El sistema de unidades no es uno que el programa conozca.",
    "A boundary is not well formed: draw it again.": "Un contorno está mal formado: dibújalo otra vez.",
    "Two boundaries share an id, or one has none.":
        "Dos contornos comparten identificador, o uno no tiene.",
    "An arc or the divisions of a segment are not well given.":
        "Un arco o las divisiones de un segmento están mal dados.",
    "A model has exactly one external boundary: Boundaries > Add External.":
        "Un modelo tiene exactamente un contorno externo: Contornos > Añadir externo.",
    "In axisymmetry the model lies on x ≥ 0: move the vertex, or choose plane strain.":
        "En axisimetría el modelo está en x ≥ 0: mueve el vértice, o elige deformación plana.",
    "A material is not well given: Properties > Define Materials.":
        "Un material está mal dado: Propiedades > Definir materiales.",
    "Two materials share an id, or one has none.":
        "Dos materiales comparten identificador, o uno no tiene.",
    "A stage is not well given: Analysis > Project Settings.":
        "Una fase está mal dada: Análisis > Ajustes del proyecto.",
    "An assignment is not well given: Properties > Assign Properties.":
        "Una asignación está mal dada: Propiedades > Asignar propiedades.",
    "An excavated region cannot come back in a later stage.":
        "Una región excavada no puede volver en una fase posterior.",
    "The field stress is not well given: Loading > Field Stress.":
        "La tensión de campo está mal dada: Cargas > Tensión de campo.",
    "The default restraint of the external is not one the program knows.":
        "La restricción por defecto del externo no es una que el programa conozca.",
    "A condition is not well given: Displacements.":
        "Una condición está mal dada: Desplazamientos.",
    "A load is not well given: Loading.": "Una carga está mal dada: Cargas.",
    "The mesh is not well formed: Mesh > Discretize and Mesh.":
        "La malla está mal formada: Malla > Discretizar y mallar.",
    "An arc is not well given: its centre must make an arc of its segment.":
        "Un arco está mal dado: su centro tiene que hacer un arco de su segmento.",
    "Two boundaries share a segment with different attributes.":
        "Dos contornos comparten un segmento con atributos distintos.",
    "Two boundaries cross where neither has a vertex.":
        "Dos contornos se cruzan donde ninguno tiene un vértice.",
    "A boundary ends inside the model without meeting another.":
        "Un contorno acaba dentro del modelo sin encontrar a otro.",
    "A boundary goes outside the external.": "Un contorno sale fuera del externo.",
    "A region has no material yet: Properties > Assign Properties.":
        "Una región todavía no tiene material: Propiedades > Asignar propiedades.",
    "A region has two assignments: keep one.": "Una región tiene dos asignaciones: deja una.",
    "An assignment point is in no region.": "Un punto de asignación no está en ninguna región.",
    "the region with outline through %s": "la región cuyo contorno pasa por %s",
    "segment %s of boundary %s": "el segmento %s del contorno %s",
    "boundary %s": "el contorno %s",
    "material %s": "el material %s",
    "stage %s": "la fase %s",
    "assignment at %s": "la asignación en %s",
    "condition %s": "la condición %s",
    "load %s": "la carga %s",
    "stratum %s": "el estrato %s",
    "point %s": "el punto %s",
    "the model": "el modelo",
    "the mesh settings": "los ajustes de la malla",
    "the field stress": "la tensión de campo",
    "the mesh": "la malla",
    # meshing in a child process
    "Meshing": "Mallado",
    "Meshing cancelled: the model is as it was.": "Mallado cancelado: el modelo está como estaba.",
    "The mesher failed: %s": "El mallador falló: %s",
    # the calculation (T30)
    "Compute": "Calcular",
    "Calculation": "Cálculo",
    "Queue": "Cola",
    "Log": "Registro",
    "Kind": "Tipo",
    "State": "Estado",
    "Time (s)": "Tiempo (s)",
    "Queued": "En cola",
    "Running": "En marcha",
    "Done": "Terminado",
    "Failed": "Falló",
    "Cancelled": "Cancelado",
    "Crashed": "Interrumpido",
    "Close": "Cerrar",
    "Cancel the Calculation": "Cancelar el cálculo",
    "Closes this window; a calculation goes on: Window > Calculation shows it again.":
        "Cierra esta ventana; el cálculo sigue: Ventana > Cálculo la vuelve a mostrar.",
    "Cancelling: the stage being solved ends, or the process is stopped.":
        "Cancelando: termina la fase que se está resolviendo, o se para el proceso.",
    "Calculation started (%d stages).": "Cálculo empezado (%d fases).",
    "Complete: the %d stages are solved, written in %s.":
        "Completo: las %d fases están resueltas, escritas en %s.",
    "Incomplete: stage %s could not be solved; the %d stages before it are written in %s. "
    "The engine says: %s":
        "Incompleto: la fase %s no se pudo resolver; las %d fases anteriores están escritas en "
        "%s. El motor dice: %s",
    "No calculation is running.": "No hay ningún cálculo en marcha.",
    "No calculation yet: Analysis > Compute.": "Todavía no hay cálculos: Análisis > Calcular.",
    "Cancelled: its process was stopped during a stage, and the results before it stay as "
    "they were.":
        "Cancelado: su proceso se paró durante una fase, y los resultados de antes quedan como "
        "estaban.",
    "Cancelled between two stages: the stages solved are written, and the results say they "
    "are cancelled.":
        "Cancelado entre dos fases: las fases resueltas están escritas, y los resultados dicen "
        "que están cancelados.",
    "Stage %s: %d steps, last iteration %d.": "Fase %s: %d escalones, última iteración %d.",
    "Stage %s solved.": "Fase %s resuelta.",
    "Stage %s solved: %d steps, last iteration %d.":
        "Fase %s resuelta: %d escalones, última iteración %d.",
    "Stage %s: nothing changes in it, nothing to solve.":
        "Fase %s: en ella no cambia nada, no hay nada que resolver.",
    "Stage %s of %d: solving...": "Fase %s de %d: resolviendo...",
    "Starting the calculation...": "Empezando el cálculo...",
    "The calculation failed: %s": "El cálculo falló: %s",
    "The calculation's process ended without saying why: %s":
        "El proceso del cálculo terminó sin decir por qué: %s",
    "The results are written beside the model's file, with its fingerprint: the model is "
    "saved first.":
        "Los resultados se escriben junto al archivo del modelo, con su huella: antes se guarda "
        "el modelo.",
    "Save and Compute": "Guardar y calcular",
    "Calculating: Window > Calculation shows how it goes.":
        "Calculando: Ventana > Cálculo muestra cómo va.",
    "A calculation is running": "Hay un cálculo en marcha",
    "Closing stops the calculation that is running: its results will not be complete.":
        "Cerrar para el cálculo en marcha: sus resultados no estarán completos.",
    "Stop it and Close": "Pararlo y cerrar",
    "Not calculated: %s": "No calculado: %s",
    "(and %d more problems)": "(y %d problemas más)",
    "There is no mesh: Mesh > Discretize and Mesh.": "No hay malla: Malla > Discretizar y mallar.",
    "The mesh is of another geometry: Mesh > Discretize and Mesh.":
        "La malla es de otra geometría: Malla > Discretizar y mallar.",
    "The mesh is of another geometry or other settings: Mesh > Discretize and Mesh.":
        "La malla es de otra geometría o de otros ajustes: Malla > Discretizar y mallar.",
    "A material has no E or no ν, which the calculation needs: Properties > Define Materials.":
        "Un material no tiene E o ν, que el cálculo necesita: Propiedades > Definir materiales.",
    # the unit systems of the suite (ogr_core.units.unit_system.SYSTEMS)
    "Metric, stress as kPa": "Métrico, tensiones en kPa",
    "Metric, stress as MPa": "Métrico, tensiones en MPa",
    "Metric, stress as tonnes/m²": "Métrico, tensiones en toneladas/m²",
    "Imperial, stress as tons/ft²": "Imperial, tensiones en toneladas cortas/ft²",
    "Imperial, stress as ksf": "Imperial, tensiones en ksf",
    "Imperial, stress as psf": "Imperial, tensiones en psf",
}
