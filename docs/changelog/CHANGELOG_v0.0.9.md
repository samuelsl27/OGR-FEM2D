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
