# OGR FEM2D v0.0.9

**Fase 1, tercera parte: el modelo y su archivo** (spec 004). Lo que define el ingeniero, en un
`.ogrfem2d` propio con su malla (ADR-0004), y su traducción determinista a la entrada del mallador y
del motor. Este archivo cuenta lo que fue entrando, tarea a tarea.

## La spec, el plan y las tareas (2026-11-23)

Revisados contra el estado del código, del núcleo (`v0.2.6`) y de OGR Slip2D, y aprobados con D1–D16
(`spec/features/004-modelo-y-proyecto/`). Lo que se encontró al revisarla:

- **El `Project` del núcleo no sirve como modelo FEM ni como archivo común.** Es el modelo de
  equilibrio límite: no tiene E ni ν, ni contornos de excavación o de fase, ni arcos. Lee una lista
  fija de secciones y pierde al guardar las que no conoce. Un tipo de contorno desconocido hace que el
  archivo no se pueda abrir. Nunca lee `format_version`.
- **Los programas de referencia tienen dos formatos** (`M02` §5.2 y §6.2, `F01` del análisis de
  interfaz). El de elementos finitos guarda la malla y abre el de equilibrio límite convirtiéndolo.
  Decidido así (D1 y ADR-0004): FEM2D tiene su `.ogrfem2d` y abre el `.ogr` de Slip2D. Lo que se
  comparte es el código del núcleo.
- **La huella de Slip2D vive en su `ogr_api`, no en el núcleo**: aquí se escribe la de este archivo,
  sin copiar código del núcleo (D12).

## T0 — aprobación y ADR-0004 (2026-11-23)

ADR-0004 escrito. `AGENTS.md`, ADR-0003, `tech-stack.md`, `plan_de_desarrollo.md` y
`validacion/README.md` nombran el `.ogrfem2d`.

## T1 — el modelo y sus reglas (2026-11-23)

Paquete nuevo `ogr_fem2d/model/`, fuera del motor y del mallador (regla 11). `model.py`: el modelo
como valor (dataclasses congeladas), con contornos, materiales, fases, asignaciones, tensión de
campo, condiciones, cargas, ajustes de malla y malla guardada, y `problems()`/`validate()`, todos los
problemas a la vez, cada uno con su regla y su sitio. `docs/modelo/formato.md`: el modelo, el archivo,
la traducción y las reglas.

- **Hallazgo al escribir D10: la tabla región × fase necesita el material del estado inicial.** La
  tensión de campo es la del estado antes de la primera fase, y una región excavada en la primera
  fase necesita un material para ese estado; además, RF-4 no deja cambiar el material entre fases. Por
  eso la asignación lleva **un material por región** y, por fase, si está excavada. El material por
  fase llegará con la spec 012, que cambiará el formato con su versión.
- 17 reglas, cada una con su caso, y la tabla cubre exactamente `model.RULES`
  (`tests/test_model_input_v009.py`, 17 tests). 27 mutaciones: tres sobrevivían (el índice de un
  segmento fuera de rango, un modelo sin externo y una malla con un nudo que no existe) y llevaron a
  tres tests; al final, 27 de 27.

## T2 — de los contornos a las regiones (2026-11-23)

`model/regions.py`: puntos y segmentos sin repetir (el mismo lado en dos contornos es uno), los
cruces con los predicados exactos del mallador, las caras del grafo plano recorriendo los medios
lados, los recorridos que pasan dos veces por un vértice partidos en anillos simples, los huecos por
anidamiento y una asignación por región. Orden canónico.

- **Hallazgo y corrección (regla 6, ya corregido): el cero negativo.** En el vértice donde una
  circunferencia toca una recta, el arco que sale hacia la izquierda tiene la tangente (−1, −0.0), y
  `atan2(−0.0, −1)` da −π en vez de π: ese lado se ordenaba el primero alrededor del vértice en vez
  del último, y las caras salían mal (las seis caras del modelo de la tangente, como lados sueltos).
  Lo cazó el test de la tangente, escrito para el desempate por curvatura. Se suma 0.0 a las
  componentes antes del `atan2`.
- **El desempate por curvatura y la tangente no son adornos**: el modelo `touching` (un triángulo
  dentro de un círculo que toca una recta en el punto de tangencia, seis lados en un vértice) da las
  caras mal si se ordena por la cuerda.
- 15 tests en `tests/test_model_regions_v009.py`: área y Euler en seis modelos (túnel con arcos,
  estratos, excavación partida por un contorno de fase abierto, lente con otra lente dentro,
  circunferencia tangente, y la de seis lados), orden canónico, y cada regla de `regions.RULES` con su
  caso. 18 mutaciones; cinco sobrevivían al principio y llevaron a dos modelos y tres comprobaciones; al
  final, 18 de 18.

## T3 — las fases y las ediciones que dependen de ellas (2026-11-23)

`model/stages.py`: insertar (copia la fase anterior, o la primera si va delante: propuesta propia de
D10), borrar, renombrar, y excavar, asignar material, activar condiciones y poner factores desde la
fase k en adelante o «solo esta fase». RF-4: una región excavada que vuelve, y un cambio de material
entre fases, se rechazan.

- 15 tests en `tests/test_model_stages_v009.py`. 13 mutaciones: sobrevivía la comprobación de un id de
  fase repetido al insertar, que era redundante (la validación del modelo ya lo rechaza con la misma
  regla) y se quitó; al final, 12 de 12.

## T4 — el cambio de signo, el campo y los modos de carga inicial (2026-11-23)

`model/conventions.py` (el único cambio de signo: el campo, por `engine/initial_stress.py`, y la
carga normal) y `model/field.py` (la tensión inicial y el peso propio según el modo, D11).

- **Hallazgo y corrección (regla 6, para revisar): el K de un punto sobre el fondo de un estrato.** El
  preproceso de la spec 002 toma K y Kz del estrato en el que cae la cota del punto, y un punto
  justo en el fondo de un estrato cae en el de arriba. Con los estratos sobre contornos de material la
  malla tiene lados sobre el contacto, y el T6 tiene puntos de integración en el centro de sus lados:
  el elemento de abajo recibía en ellos el K del estrato de arriba. El campo gravitatorio, que debía
  estar en equilibrio con el peso, movía el modelo 1.6·10⁻⁶ m, 2·10⁻⁵ de su escala. Ahora σv es la
  columna sobre el punto (continua, JCZ ec. 13.1) y K y Kz son los del estrato que contiene el
  centroide del elemento (ec. 13.5 por estrato: σh salta en el contacto, y cada elemento tiene su lado
  del salto). La corrección está en `model/field.py`; el preproceso del motor no se tocó. Con ella el
  desplazamiento es redondeo.
- 10 tests en `tests/test_model_field_v009.py`: los signos; el campo gravitatorio con su peso no
  mueve el modelo (identidad); el campo en cada punto es la columna con el K de su elemento, también
  en el contacto; los cuatro modos dan cuatro estados distintos (regla 7) y cada uno es lo que dice;
  en axisimetría, un campo sin equilibrio radial es un error. 8 mutaciones: sobrevivía cambiar Kz por K
  (los estratos de prueba tenían K = Kz), y los estratos pasaron a tener Kz distinto; al final, 8 de 8.

## T5 — las condiciones en los nudos (2026-11-23)

`model/conditions.py`: por segmento, la unión de los tramos que actúan (o el defecto del externo);
por nudo, la unión de sus segmentos; el vértice manda; los desplazamientos impuestos en totales, con
su factor, que sustituyen a la restricción de su componente.

- **Hallazgo y corrección en el mallador de la spec 003 (regla 6, para revisar): un hueco lleno de
  dos regiones se tomaba por un vacío.** `mesh/pslg.py` ponía un punto de vacío (donde el núcleo no
  malla) en todo hueco cuyo anillo no fuera el contorno de una región. Una excavación partida en dos por
  un contorno de fase (avance y destroza) llena el hueco de la roca con dos regiones, y el núcleo
  rechazaba la semilla de una de ellas, «en un vacío». Salió al escribir el test de un impuesto en un
  nudo sin elementos activos. Ahora un hueco es un vacío cuando no contiene ninguna semilla. Con un
  hueco lleno de una región o vacío, nada cambia (las mallas de la spec 003 y su huella, iguales).
  `tests/test_mesh_split_hole_v009.py`, 4 tests.
- 13 tests en `tests/test_model_conditions_v009.py`. 14 mutaciones (13 de las condiciones y la del
  vacío), 14 cazadas.

## T6 — las cargas en lados y nudos (2026-11-23)

`model/loads.py`: la carga repartida, lineal en la longitud a lo largo del tramo, en un `EdgeLoad` por
lado sobre su único elemento activo; la normal con el signo cambiado y las demás orientaciones en
componentes; la puntual, en el nudo de su vértice.

- 12 tests en `tests/test_model_loads_v009.py`: resultante y momento exactos de una carga lineal sobre
  dos segmentos; cada orientación empuja donde dice, en una superficie inclinada donde todas difieren;
  la misma carga con el contorno dibujado en los dos sentidos; una presión en la pared del túnel empuja
  hacia la roca con la resultante 2πap; una carga lineal a lo largo de un arco va por su longitud; el
  factor de cada fase; una carga sobre un contacto activo o sobre la pared antes de excavarla, error;
  la puntual, también en axisimetría (el anillo entero). 14 mutaciones: dos sobrevivían (leer al revés
  la cadena de un segmento y medir un arco por su cuerda) y llevaron a dos tests; al final, 14 de 14.

## T7 y T8 — la traducción al mallador y al motor (2026-11-23)

`model/translate.py`: el `MeshInput` canónico (la etiqueta de cada región es su índice, D3), la malla
con la huella de su entrada, y el `EngineModel` con los materiales, las fases, las condiciones, las
cargas y el estado inicial. La malla de otro modelo se rechaza (RF-11), y los errores del mallador y
del motor vuelven con los nombres del modelo (RF-12).

- **El túnel del caso 005 da exactamente el `MeshInput` escrito a mano** en `tests/_kirsch_mesh.py`
  (el riesgo del plan no se dio).
- 14 tests en `tests/test_model_translate_v009.py`. 11 mutaciones, 11 cazadas.

## T9 — el archivo `.ogrfem2d` (2026-11-23)

`model/ogr_file.py`: las secciones en su orden, todas las claves siempre, lo que depende de la fase
como objeto con clave el id de la fase; escritura determinista (un nudo, un elemento y un vértice por
línea); lectura estricta, todos los problemas a la vez.

- 13 tests en `tests/test_model_file_v009.py`: la ida y vuelta da el mismo modelo y los mismos bytes,
  en disco también, y la misma entrada del motor; la forma; nada se pierde en silencio (versión
  posterior, otro formato, clave que falta o sobra, tipo erróneo, fases de otro modelo, texto que no es
  JSON) y después las reglas del modelo. 11 mutaciones: dos sobrevivían (un `true` donde va un entero, y
  los lados de un tramo de la malla en varias líneas) y llevaron a dos comprobaciones; al final, 11 de 11.

## T10 — las huellas (2026-11-23)

`model/fingerprint.py`: SHA-256 de un JSON canónico; la del modelo sin resumen, unidades mostradas,
nombres, colores ni notas de la malla; la del documento, todo menos quién lo escribió.

- **Precisión de D12 al escribir los tests: los ids tampoco cambian el resultado.** Con los ids en la
  huella, renombrar una fase la movía sin que nada del cálculo cambiara. La huella del modelo nombra
  los contornos, los materiales y las fases por su lugar (su orden sí es parte del modelo) y lo que
  depende de la fase va en el orden de las fases.
- 8 tests en `tests/test_model_fingerprint_v009.py`: 19 datos que mueven el resultado la mueven, 8 que
  no, no (los ids renombrados en todas partes, entre ellos); la del documento cambia con todo; las dos
  sobreviven al archivo; el texto canónico.

## T11 — deshacer y rehacer (2026-11-23)

`model/history.py`: un `Document` con el modelo actual y una orden «antes / después» sobre el
`CommandStack` del núcleo, que solo pide `execute` y `undo` al objeto.

- 5 tests en `tests/test_model_history_v009.py`. 9 mutaciones de T10 y T11, 9 cazadas.
