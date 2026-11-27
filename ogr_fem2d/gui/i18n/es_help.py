# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""The Spanish of the help (spec 006, T36; ``gui/help``). The names of the
menus and of their entries are those of ``es_menus``."""

ES = {
    # the pages' titles
    "The work, in order": "El trabajo, en orden",
    "Drawing the model": "Dibujar el modelo",
    "Meshing": "Mallar",
    "Calculating": "Calcular",
    "Interpreting the results": "Interpretar los resultados",
    "Units, signs and what decided a result": "Unidades, signos y lo que decidió un resultado",
    "The agent bridge": "El puente con el agente",
    "The validation cases": "Los casos de validación",
    "Materials, stages, loads and conditions": "Materiales, fases, cargas y condiciones",
    # start
    "2-D geotechnical analysis by finite elements: stresses and displacements in plane strain "
    "or axisymmetry, by stages of construction.":
        "Análisis geotécnico 2D por elementos finitos: tensiones y desplazamientos en "
        "deformación plana o en axisimetría, por fases de construcción.",
    "In this phase the materials are linear elastic and isotropic and the elements are "
    "triangles of three or six nodes. Plasticity, water, supports and joints come in later "
    "phases: their menus are there, disabled, saying when.":
        "En esta fase los materiales son elásticos lineales e isótropos y los elementos son "
        "triángulos de tres o seis nudos. La plasticidad, el agua, el sostenimiento y las "
        "juntas llegan en fases posteriores: sus menús están, deshabilitados, diciendo cuándo.",
    # the model
    "Analysis > Project Settings sets the analysis (plane strain or axisymmetry), the units "
    "shown and the title. Every value is kept in m, kN and kPa; the units shown only change "
    "how they are written.":
        "Análisis > Ajustes del proyecto fija el análisis (deformación plana o axisimetría), "
        "las unidades que se muestran y el título. Todo valor se guarda en m, kN y kPa; las "
        "unidades que se muestran solo cambian cómo se escribe.",
    "Boundaries > Add External, Add Excavation, Add Material Boundary, Add Stage Boundary and "
    "Add Circular Excavation draw by clicks or by typed points. In the X, Y field of the status "
    "bar: x, y (or x; y with decimal commas), @dx, dy from the last point, or @distance<angle "
    "in degrees, then Enter. A (Arc) draws an arc through a point; T (Enter Coordinates) takes "
    "a table; Enter finishes, Esc cancels, Backspace undoes the last vertex.":
        "Contornos > Añadir externo, Añadir excavación, Añadir contorno de material, Añadir "
        "contorno de fase y Añadir excavación circular dibujan con clics o con puntos "
        "escritos. En el campo X, Y de la barra de estado: x, y (o x; y con coma decimal), "
        "@dx, dy desde el último punto, o @distancia<ángulo en grados, y después Intro. A "
        "(Arco) dibuja un arco por un punto; T (Introducir coordenadas) toma una tabla; Intro "
        "termina, Esc cancela y Retroceso deshace el último vértice.",
    "Where a boundary cuts another, a vertex is put in both.":
        "Donde un contorno corta a otro, se pone un vértice en los dos.",
    "Properties > Define Materials gives E, nu, the unit weight and the initial loading of "
    "each material; Assign Properties puts one in a region by a click, or excavates or fills "
    "a region, from the stage shown on or in that stage only.":
        "Propiedades > Definir materiales da E, nu, el peso específico y la carga inicial de "
        "cada material; Asignar propiedades pone uno en una región con un clic, o excava o "
        "rellena una región, desde la fase que se muestra o solo en esa fase.",
    "Analysis > Add Stage, Rename Stage and Delete Stage make the stages; the tabs below the "
    "canvas choose the one shown.":
        "Análisis > Añadir fase, Renombrar fase y Borrar fase hacen las fases; las pestañas "
        "bajo el lienzo eligen la que se muestra.",
    "Loading > Field Stress gives the initial stresses; Add Distributed Load and Add Point "
    "Load go on segments or vertices, with Factors by Stage. Displacements restrains or "
    "imposes them on the boundaries; External Default is what the external boundary has "
    "where nothing else is said.":
        "Cargas > Tensión de campo da las tensiones iniciales; Añadir carga repartida y "
        "Añadir carga puntual van en tramos o en vértices, con Factores por fase. "
        "Desplazamientos los restringe o los impone en los contornos; Por defecto del externo "
        "es lo que tiene el contorno externo donde no se dice otra cosa.",
    "Loads and imposed displacements are given in totals for each stage: the program works "
    "out what changes from one stage to the next.":
        "Las cargas y los desplazamientos impuestos se dan en totales de cada fase: el programa "
        "calcula lo que cambia de una fase a la siguiente.",
    # the mesh
    "Mesh > Mesh Setup chooses the mesh type (graded or uniform), the element type (triangles "
    "of three or six nodes), the quality bound, the nodes on the excavations or the element "
    "size, and the refinement windows. Segment Divisions fixes the nodes of a segment.":
        "Malla > Ajustes de la malla elige el tipo de malla (graduada o uniforme), el tipo de "
        "elemento (triángulos de tres o seis nudos), la cota de calidad, los nudos en las "
        "excavaciones o el tamaño del elemento, y las ventanas de refinado. Divisiones del "
        "segmento fija los nudos de un segmento.",
    "Meshing is two steps: Discretize puts the nodes on the boundaries, and Discretize and "
    "Mesh (Ctrl+M) makes the elements. A mesh is part of the model and is saved with it; "
    "Reset Mesh removes it.":
        "Mallar son dos pasos: Discretizar pone los nudos en los contornos, y Discretizar y "
        "mallar (Ctrl+M) hace los elementos. La malla es parte del modelo y se guarda con él; "
        "Quitar la malla la quita.",
    "A case fixes its mesh: a different mesh is a different case.":
        "Un caso fija su malla: otra malla es otro caso.",
    # calculating
    "Analysis > Compute (F9) calculates the saved model (it asks to save it first if it has "
    "changes) in a process of its own: the window goes on, and Window > Calculation shows the "
    "queue, the stage being solved, the log and the summary. Cancel stops it between two "
    "stages, or stops the process.":
        "Análisis > Calcular (F9) calcula el modelo guardado (si tiene cambios, pide guardarlo "
        "antes) en un proceso propio: la ventana sigue, y Ventana > Cálculo muestra la cola, "
        "la fase que se resuelve, el registro y el resumen. Cancelar lo para entre dos fases, "
        "o para el proceso.",
    "The results go to a file next to the model, with the same name and .h5. It carries the "
    "fingerprint of the model it is of: results of a model that changed since are said to be "
    "of another model, and shown as such, never as valid. A calculation that stopped keeps "
    "the stages it solved, and says so.":
        "Los resultados van a un archivo junto al modelo, con el mismo nombre y .h5. Lleva la "
        "huella del modelo del que son: los de un modelo que cambió después se dicen de otro "
        "modelo y se muestran así, nunca como válidos. Un cálculo que se paró guarda las fases "
        "que resolvió, y lo dice.",
    # interpreting
    "Analysis > Interpret (F10) opens the results: a tab per stage, the quantity chosen in the "
    "list, its contours and its legend. The legend says the quantity, its unit, its "
    "convention, the stage and where the values come from.":
        "Análisis > Interpretar (F10) abre los resultados: una pestaña por fase, la magnitud "
        "elegida en la lista, sus contornos y su leyenda. La leyenda dice la magnitud, su "
        "unidad, su convenio, la fase y de dónde salen los valores.",
    "Stresses and strains are recovered at the nodes, material by material (superconvergent "
    "patch recovery, Zienkiewicz and Taylor 2000, §14.4): a contact between two materials "
    "keeps a value on each side. Displacements are the finite-element field.":
        "Las tensiones y las deformaciones se recuperan en los nudos, material a material "
        "(recuperación por parches superconvergente, Zienkiewicz y Taylor 2000, §14.4): un "
        "contacto entre dos materiales guarda un valor a cada lado. Los desplazamientos son el "
        "campo de elementos finitos.",
    "Results > Contour Options sets the intervals, the palette and the range; the range is "
    "that of the stage, that of all stages, or one of your own, and always the whole range: a "
    "peak is never cut. Absolute Value draws the absolute value.":
        "Resultados > Opciones de contorno fija los intervalos, la paleta y el rango; el rango "
        "es el de la fase, el de todas las fases o uno propio, y siempre el rango entero: un "
        "pico nunca se recorta. Valor absoluto dibuja el valor absoluto.",
    "The value under the cursor is interpolated exactly at the point, not read off the "
    "colours.":
        "El valor bajo el cursor se interpola exactamente en el punto, no se lee de los "
        "colores.",
    "Query: along a line or a polyline, on a boundary (or at a distance to one side of it), at "
    "every node, or at a point through the stages. Each query has its table, its chart and its "
    "export, and says what decided it.":
        "Consulta: a lo largo de una línea o de una polilínea, sobre un contorno (o a una "
        "distancia a un lado de él), en todos los nudos, o en un punto a lo largo de las fases. "
        "Cada consulta tiene su tabla, su gráfico y su exportación, y dice lo que la decidió.",
    "Analysis > Report (F11) writes the model, the mesh, what decided the result and the "
    "results, and saves them as HTML or text.":
        "Análisis > Informe (F11) escribe el modelo, la malla, lo que decidió el resultado y "
        "los resultados, y los guarda en HTML o en texto.",
    # conventions
    "Units: kept in m, kN and kPa; shown in the units of Project Settings.":
        "Unidades: se guardan en m, kN y kPa; se muestran en las de Ajustes del proyecto.",
    "Stresses and strains are shown compression positive and shortening positive, as is the "
    "custom in geotechnics; displacements are positive along +x and +y. The engine works "
    "tension positive: the change is made in one place.":
        "Las tensiones y las deformaciones se muestran con la compresión y el acortamiento "
        "positivos, como es costumbre en geotecnia; los desplazamientos son positivos según +x "
        "y +y. El motor trabaja con la tracción positiva: el cambio se hace en un solo sitio.",
    "In axisymmetry x is the radius and y the axis; the circumferential stress is sigma z, and "
    "reactions are of the whole ring.":
        "En axisimetría x es el radio e y el eje; la tensión circunferencial es sigma z, y las "
        "reacciones son del anillo entero.",
    "A value that changes the result without being drawn (the analysis, the default "
    "restraint, the initial loading, the settings of the mesh and of the engine) is said with "
    "the result: in the panel What decided it of the interpretation, in each query and in the "
    "report.":
        "Un valor que cambia el resultado sin estar dibujado (el análisis, la restricción por "
        "defecto, la carga inicial, los ajustes de la malla y del motor) se dice con el "
        "resultado: en el panel Lo que lo decidió de la interpretación, en cada consulta y en "
        "el informe.",
    # the bridge
    "Tools > Agent Bridge (MCP) lets the MCP server of this program work on the model of this "
    "window: what an agent does is drawn here and is undone with Edit > Undo. The bridge "
    "listens only on this computer, and only to who has its key, which is in a file only you "
    "can read.":
        "Herramientas > Puente con el agente (MCP) deja que el servidor MCP de este programa "
        "trabaje sobre el modelo de esta ventana: lo que hace un agente se dibuja aquí y se "
        "deshace con Edición > Deshacer. El puente solo escucha en este equipo, y solo a quien "
        "tiene su clave, que está en un archivo que solo tú puedes leer.",
    "While a calculation is running an agent can ask and follow it, but not edit: the results "
    "being written are of the model as it was.":
        "Con un cálculo en marcha un agente puede preguntar y seguirlo, pero no editar: los "
        "resultados que se escriben son del modelo tal como estaba.",
    # the cases
    "Each case is checked against an external reference (a closed solution, a published case "
    "or an identity), with a tolerance fixed before measuring. Their sheets are written in "
    "Spanish.":
        "Cada caso se comprueba contra una referencia externa (una solución cerrada, un caso "
        "publicado o una identidad), con una tolerancia fijada antes de medir. Sus fichas están "
        "escritas en español.",
    "The cases are not with this copy of the program: they are in the folder validacion/casos "
    "of its source repository.":
        "Los casos no están con esta copia del programa: están en la carpeta validacion/casos "
        "de su repositorio de fuentes.",
    "%s %% relative": "%s %% relativa",
    "%s absolute (over the case's scale)": "%s absoluta (sobre la escala del caso)",
    "Case": "Caso",
    "Source": "Fuente",
    "Tolerance": "Tolerancia",
    "Sheet": "Ficha",
    "Open a copy of the model": "Abrir una copia del modelo",
    "Where the copy of the case goes": "Dónde va la copia del caso",
    "There is already a file %s: choose another folder.":
        "Ya hay un archivo %s: elige otra carpeta.",
    "The help follows no link out of it: %s": "La ayuda no sigue enlaces fuera de ella: %s",
    # the menu entry
    "Help Topics": "Temas de ayuda",
}
