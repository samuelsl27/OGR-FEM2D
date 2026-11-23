# Plan de implementación — Spec 004, modelo FEM y proyecto `.ogrfem2d`

> **Para aprobar (2026-11-23)**, con D1–D16 de `spec.md`: las ✔ las eligió la propietaria, y las
> demás son propuestas. Ninguna fórmula se programa antes de estar en la tabla «Formulación» como
> leída.

## Enfoque

0. **T0, antes de programar.** El ADR-0004 (formato propio y malla dentro) y las correcciones de
   `AGENTS.md`, ADR-0003, `tech-stack.md` y `plan_de_desarrollo.md` donde dicen `.ogr`. Es un cambio
   del contrato y va en su propio commit, con el OK de la propietaria.
1. **v0.0.9: el modelo como valor inmutable** (dataclasses congeladas, como `EngineModel` y
   `MeshInput`) y su validación, sin Qt, en un paquete nuevo `ogr_fem2d/model/`, fuera del motor
   (regla 11) y del mallador.
2. **Lo que se traduce**: regiones, fases, campo y carga inicial, condiciones y cargas, cada pieza
   probada por separado sobre mallas que ya existen.
3. **La traducción** a `MeshInput` y a `EngineModel`, con la procedencia de cada objeto, para que los
   errores nombren el contorno, la región o la fase.
4. **El archivo, la huella y el deshacer.**
5. **La apertura de un `.ogr` de Slip2D y de un DXF**, con el núcleo fijado (v0.2.6).
6. **Los tres casos**: el 005 con su modelo, y el 006 y el 007 nuevos con su estudio.

El motor (`ogr_fem2d/engine/`), el mallador (`ogr_fem2d/mesh/`), `rust/` y la CI no se tocan, así
que no hace falta rama corta. Del núcleo no se pide nada que bloquee: la única petición (los arcos en
DXF, D13) se escribe y sigue su camino.

## Lo que se reutiliza

| De dónde | Qué | Para qué |
|---|---|---|
| `ogr_fem2d/engine/initial_stress.py` | `constant_field`, `gravitational_field`, `Stratum`, `integration_point_coordinates` | El campo en cada punto de integración, con la conversión de signo y las restricciones de la axisimetría (spec 002, D3) |
| `ogr_fem2d/mesh/geometry.py` | `MeshInput`, `Region`, `SegmentSpec`, `Arc`, `Window`, `MeshSettings`, `validate` y sus cruces exactos | El modelo da un `MeshInput`; las reglas de cruce no se reescriben |
| `ogr_fem2d/mesh/mesher.py` | `mesh`, `Mesh.boundaries` (los (elemento, lado) de cada tramo), `to_engine` | Mallar, y llevar cargas y condiciones a nudos y lados |
| `ogr_core.units` | `UnitSystem` y la lista de sistemas | El sistema que se muestra (D5) |
| `ogr_core.loads.loads` | `LoadOrientation` | Las orientaciones de las cargas repartidas (RF-10) |
| `ogr_core.project.commands` | `CommandStack`, que solo pide al objeto `execute(obj)` y `undo(obj)` | Deshacer y rehacer (RF-15) |
| `ogr_core.project.project` | `Project.load` | Leer un `.ogr` de Slip2D (D16) |
| `ogr_core.dxf.reader` | el lector DXF, con los arcos aplanados | Abrir un DXF (D13) |

## Archivos que se tocan

| Archivo | Qué es | RF |
|---|---|---|
| `docs/decisiones/ADR-0004-formato-ogrfem2d.md` (nuevo) | formato propio, apertura del `.ogr` de Slip2D, malla dentro del archivo | D1, D3 |
| `AGENTS.md`, `docs/decisiones/ADR-0003-…`, `spec/constitution/tech-stack.md`, `plan_de_desarrollo.md` | `.ogr` → `.ogrfem2d` donde nombran el formato de este programa | D1 |
| `ogr_fem2d/model/__init__.py` (nuevo) | el paquete del modelo | — |
| `ogr_fem2d/model/model.py` (nuevo) | dataclasses: `Boundary` (tipo, vértices, abierto o cerrado, arcos y divisiones por segmento), `Material` (E, ν, γ, modo de carga inicial), `Assignment` (punto y material o excavada por fase), `Stage` (id, nombre), `FieldStress`, `Condition`, `Load`, `MeshSettings`, `Summary`, `Model`; `validate()` con `Problem` (regla, sitio, por qué), como el motor | RF-1, 3, 5, 6 |
| `ogr_fem2d/model/regions.py` (nuevo) | de los contornos a puntos, segmentos y caras con sus huecos, en orden canónico (D15) | RF-1 |
| `ogr_fem2d/model/stages.py` (nuevo) | insertar (copia la fase anterior), borrar, renombrar; asignar con propagación o «solo esta fase»; RF-4 | RF-3, 4 |
| `ogr_fem2d/model/conventions.py` (nuevo) | el único cambio de signo: el campo (llamando a `initial_stress`) y la carga normal | RF-8 |
| `ogr_fem2d/model/field.py` (nuevo) | tensión inicial por punto y peso propio por material según el modo (D11) | RF-7 |
| `ogr_fem2d/model/conditions.py` (nuevo) | restricciones, liberaciones e impuestos a nudos, con precedencia y unión (D16) | RF-9 |
| `ogr_fem2d/model/loads.py` (nuevo) | cargas a `EdgeLoad` y `NodalLoad`, factor por fase | RF-10 |
| `ogr_fem2d/model/translate.py` (nuevo) | `to_mesh_input`, `mesh` (malla y su huella de entrada), `to_engine`; la procedencia de cada punto, segmento y región, y el reetiquetado de los errores | RF-11, 12 |
| `ogr_fem2d/model/ogr_file.py` (nuevo) | lectura y escritura del `.ogrfem2d`: forma, versión, programa, malla compacta | RF-13 |
| `ogr_fem2d/model/fingerprint.py` (nuevo) | huella del modelo y del documento (D12) | RF-16 |
| `ogr_fem2d/model/history.py` (nuevo) | el documento (un modelo inmutable cada vez) y la orden «antes / después» sobre `CommandStack` | RF-15 |
| `ogr_fem2d/model/import_slip2d.py` (nuevo) | de un `Project` del núcleo a un `Model`, con su informe | RF-14 |
| `ogr_fem2d/model/import_dxf.py` (nuevo) | de las polilíneas del lector a contornos, con el mapa de capas y su informe | RF-14 |
| `docs/modelo/formato.md` (nuevo) | el `.ogrfem2d` sección a sección, los convenios y las reglas, como `docs/motor/entrada.md` | RF-13 |
| `validacion/casos/005-kirsch-malla-general/modelo.ogrfem2d` (nuevo) | el modelo del caso, con su malla | D4 |
| `validacion/casos/006-carga-en-faja-malla-general/` (nuevo) | `caso.md`, `esperado.json`, `modelo.ogrfem2d` | D4 |
| `validacion/casos/007-cavidad-esferica-malla-general/` (nuevo) | lo mismo | D4 |
| `tests/test_model_*_v009.py` (nuevos) | ver «Estrategia de pruebas» | todos |
| `Promts_desarrollo/2026_11_xx_peticion_ogr_core_arcos_en_dxf.md` (fuera del repositorio) | la petición de D13 | D13 |
| `pyproject.toml`, `ogr_fem2d/__init__.py` | versión 0.0.9 | — |
| `docs/changelog/CHANGELOG_v0.0.9.md` (nuevo) | qué se encontró | — |

## El `.ogrfem2d`

JSON en UTF-8, con estas secciones en este orden. El detalle de cada campo va en
`docs/modelo/formato.md`, en la T1.

| Sección | Qué lleva |
|---|---|
| `format`, `format_version`, `written_by` | `"ogr-fem2d"`, la versión del formato (1) y el programa con su versión |
| `summary` | título, autor, fecha, notas: no entra en la huella del modelo |
| `units` | el sistema que se muestra (un id de la lista del núcleo); los valores están siempre en m, kN, kPa y kN/m³ (D5) |
| `analysis` | `plane_strain` o `axisymmetric` |
| `boundaries` | id, tipo (`external`, `material`, `excavation`, `stage`), nombre, vértices, si es cerrado, y por segmento el arco (centro) y las divisiones forzadas |
| `materials` | id, nombre, color, E, ν, γ, modo de carga inicial |
| `stages` | id y nombre, en orden |
| `assignments` | un punto por región, y por id de fase el id de material o `excavated` |
| `field_stress` | `constant` (σ1, σ3, σz, ángulo; compresión positiva) o `gravitational` (superficie, estratos) |
| `conditions` | la condición por defecto del externo, explícita; y cada condición sobre un segmento (sus dos vértices) o un vértice: X, Y, XY, libre o desplazamiento impuesto, con su activación o su factor por fase |
| `loads` | repartidas (tramo entre dos vértices, magnitud al principio y al final, orientación y ángulo) y puntuales (vértice, magnitud, orientación), con su factor por fase |
| `mesh_settings` | los de `MeshSettings` de la spec 003, ventanas incluidas |
| `mesh` | `null`, o los nudos, los elementos con su región, los contornos (`Mesh.boundaries`), las notas y la huella del `MeshInput` del que salió |

Los vértices se nombran por sus coordenadas, que son exactas porque son los mismos números del
archivo. Así una carga o una condición no dependen del orden de los vértices en el contorno. Una
carga o una condición cuyos vértices ya no existen es un error que la nombra, nunca se pierde.

La malla va con un nudo y un elemento por línea (D3). El resto del archivo, sangrado. La escritura
es determinista: el mismo modelo da los mismos bytes.

## Decisiones de diseño

- **El modelo es un valor.** Cada edición da un modelo nuevo, y el documento guarda el actual. Con
  eso, deshacer es volver al anterior, y la orden de `CommandStack` guarda los dos (antes y
  después), sin copias profundas ni notificaciones.
- **La malla es de la geometría, no de los materiales (D3).** En el `MeshInput`, la «material» de
  cada región es **el índice de la región**, y `to_engine` pone el material de cada elemento en cada
  fase según la tabla de asignaciones. Por eso cambiar un material no invalida la malla, y la huella
  de la entrada de la malla no lleva materiales.
- **Orden canónico** (determinismo, y la clave del caso 005):
  - los puntos, en el orden en que aparecen en los contornos del archivo;
  - las regiones, por el menor índice de su contorno;
  - cada anillo, empezando por su menor índice, el contorno en sentido antihorario y los huecos en
    sentido horario;
  - los `SegmentSpec`, en el orden de los contornos.

  Con el modelo del 005 (externo cuadrado y excavación circular de cuatro arcos), esa regla da el
  `MeshInput` de `tests/_kirsch_mesh.py`, y el test lo afirma. Si no lo diera, es un hallazgo y se
  reporta antes de corregir nada (regla 6).
- **Regiones (D15).** Los segmentos de todos los contornos, sin repetir (el mismo segmento en dos
  contornos es uno, y con arcos distintos es un error), se comprueban con las reglas de cruce
  exactas de `mesh/geometry`. Las caras salen recorriendo el grafo plano, siguiendo en cada vértice
  el siguiente lado por ángulo; en un arco cuenta la tangente en el vértice. El anidamiento da los
  huecos, y la cara exterior del externo no es región. Un segmento que no separa dos caras (el
  extremo suelto de un contorno abierto) es un error.
- **Condiciones (D16).** Por cada nudo de la malla: el defecto si está en el externo, sustituido por
  la condición de los segmentos que lo contienen, y los segmentos que comparten el nudo se unen. La
  condición de un vértice manda sobre todo. Un impuesto en una componente sustituye a la restricción
  de esa componente. Dos impuestos distintos en el mismo grado de libertad son un error que nombra
  los dos.
- **Cargas.** Una carga repartida sobre un tramo de varios segmentos se interpola linealmente por la
  longitud a lo largo del tramo (la de arco en los arcos), y se convierte en un `EdgeLoad` por cada
  lado de la malla. La normal, con `normal=True` y el signo cambiado (D6); las demás orientaciones,
  en componentes globales. En cada fase, el lado tiene que tener un solo elemento activo: si no, el
  error de RF-10. La puntual va a un `NodalLoad` en el nudo del vértice.
- **Errores que nombran el modelo (RF-12).** `translate` guarda, para cada punto, segmento y región
  del `MeshInput`, de qué contorno, vértice o asignación sale. Los `Problem` del mallador (sitio
  «segment a-b», «region r») y del motor (elemento, nudo, fase) se reescriben con esos nombres, sin
  perder el original.
- **Huella (D12).** `json.dumps` con `sort_keys=True` y `separators=(",", ":")` de una vista del
  modelo: la del modelo sin `summary`, `units`, nombres ni colores; la del documento, el archivo
  entero. Después, SHA-256.
- **Abrir un `.ogr` de Slip2D.** Lo abre `Project.load` del núcleo fijado; un archivo que el núcleo
  no abre da el error del núcleo. Los «laterales» son los segmentos del externo sobre la x mínima y
  la x máxima, y el «fondo», los de la y mínima; el resto es superficie (la regla de `M02` §5.2, que
  aquí se escribe explícita). Las cargas de Slip2D con extremos que no son vértices insertan el
  vértice en el segmento, y el informe lo dice.

## Formulación

No entra mecánica nueva. Las fórmulas que se usan ya están leídas y en el código (spec 002).

| Qué | Fuente | Dónde | Estado |
|---|---|---|---|
| Campo constante girado | Jaeger, Cook y Zimmerman (2007) | §2.3, ecs. (2.28)–(2.30), pág. 19 | **Leído** (spec 002; `initial_stress.py`) |
| Campo gravitatorio con estratos horizontales | Jaeger, Cook y Zimmerman (2007) | §13.2, ecs. (13.1) y (13.5), págs. 400–401 | **Leído** (spec 002, D3) |
| Restricciones del campo en axisimetría | Timoshenko y Goodier (1951) | §116, ec. (177), pág. 343 | **Leído** (enmienda de D3 de la spec 002) |
| Fuerzas del anillo entero en axisimetría | Zienkiewicz y Taylor (2000) | §5.2.6, pág. 118 | **Leído** (spec 002, D2) |
| Carga repartida lineal a lo largo de un tramo | — | Interpolación lineal por la longitud (de arco, en los arcos) | Geometría elemental |
| Caras de un grafo plano | de Berg, Cheong, van Kreveld y Overmars (2008), *Computational Geometry*, 3.ª ed., cap. 2 | — | **No está en la bibliografía.** Es un algoritmo, no una fórmula: se valida con las identidades de área y de Euler |
| Característica de Euler de un grafo plano | — | V − E + F = 1 + C, con C las componentes conexas y F contando la cara exterior | Teorema clásico (Euler) |
| Huella | FIPS 180-4 (SHA-256) | `hashlib` | Biblioteca estándar |
| Caso 006 | Michell (1902), en Timoshenko y Goodier (1951) | §34, ec. (f), págs. 92–95 | **Leído** (caso 004) |
| Caso 007 | Lamé (1852), en Timoshenko y Goodier (1951) | §121, ecs. (197)–(198), págs. 358–359 | **Leído** (caso 003) |

**Convenio:** el archivo, en el del usuario (compresión positiva, carga normal hacia el terreno); el
motor, en tracción positiva (regla 10). La conversión va en `conventions.py` y en ningún otro sitio.

## Anomalías (regla 6)

Ninguna todavía. Dos cosas a vigilar, que se reportarán si aparecen:
- que el orden canónico no reproduzca el `MeshInput` hecho a mano del 005;
- que la apertura de Slip2D dé áreas distintas de las de `build_regions` en algún modelo, porque
  esa función repara los polígonos inválidos con `buffer(0)` sin decirlo.

## Estrategia de pruebas

| Nivel | Test | Invariante |
|---|---|---|
| Entrada | Cada regla de `validate()` con un modelo que la incumple | el error dice el sitio y la regla |
| Regiones | Rectángulo con estratos, túnel con arcos, contornos de fase abiertos, hueco suelto; cada error de D15 con su modelo roto | Σ áreas = área del externo; Euler; el culpable, nombrado |
| Fases | Insertar delante, en medio y al final; borrar; renombrar; propagar y «solo esta fase»; reactivar y cambiar de material, rechazados | D10, RF-4 |
| Signos | Compresión de campo → negativa en el motor; presión normal positiva → hacia el terreno, en un contorno exterior y en uno de excavación | D6, RF-8 |
| Carga inicial | Gravitatorio con peso propio y superficie horizontal: desplazamiento nulo; los cuatro modos dan cuatro resultados distintos | D11, regla 7 |
| Condiciones | Defecto explícito; liberar un segmento no suelta la esquina del vecino; el vértice manda; impuesto sobre restricción; dos impuestos en conflicto | D16, RF-9 |
| Cargas | Uniforme y lineal sobre varios segmentos (resultante y momento exactos); cada orientación; factor por fase (0 = ausente); carga en un contacto activo, rechazada; axisimetría | RF-10 |
| Traducción | El mismo modelo dos veces: `MeshInput` y `EngineModel` iguales bit a bit; los errores del mallador y del motor, con el nombre del objeto del modelo | RF-12 |
| Malla | Mover un vértice o cambiar un ajuste: malla de otro modelo, rechazada; cambiar un material: la malla sirve | RF-11, D3 |
| Archivo | Ida y vuelta: mismo modelo y mismos bytes; versión posterior, clave desconocida y tipo erróneo, con su error | RF-13 |
| Huella | Tabla de mutaciones: cada dato que mueve el resultado la cambia; nombre, color, resumen y unidades, no | RF-16 |
| Deshacer | Una secuencia de ediciones, deshecha entera y rehecha: modelos idénticos | RF-15 |
| Unidades | Tensiones ×1000: desplazamientos iguales y tensiones proporcionales, a redondeo | homogeneidad |
| Slip2D | Un `Project` creado con la API del núcleo dentro del test: regiones y áreas como `build_regions`; el informe lista cada cosa que no se trae; restricciones de laterales, fondo y superficie | RF-14, D16 |
| DXF | Un DXF escrito en el test con capas de los cuatro tipos y un arco: contornos y aviso del arco aplanado | RF-14, D13 |
| Casos | 005 (bit a bit con el hecho a mano, y su 0.5 %); 006 y 007 con la tolerancia de antes de medir y su estudio | D4 |
| Regresión | Casos 001 a 004, bit a bit | no se toca lo validado |

Cada test lleva su cabecera (qué invariante protege) y tiene dientes: una mutación sistemática por
invariante (`{etiqueta: (archivo, texto, sustituto)}`), anotada en `tasks.md`.

## Riesgos

| Riesgo | Cómo se detecta o se acota |
|---|---|
| El caso 005 por el modelo pide otra resolución de 28 000 T6 (el motor de referencia es lento, T16 de la 003) | Se resuelve solo el caso; las identidades siguen en su test, y la entrada del motor se compara sin resolver |
| El `.ogrfem2d` con la malla del 005 pesa varios MB en `validacion/` | Se mide en la T15 y se anota en el changelog; si molesta en git, se propone otra forma (no se decide sola) |
| El orden canónico no reproduce el `MeshInput` hecho a mano del 005 | El test de la T15 lo dice; hallazgo, regla 6 |
| La apertura de Slip2D depende de la versión del núcleo fijada | El test crea el `Project` con la API del núcleo fijado, no con un archivo de Slip2D |
| Las caras del grafo plano con arcos (tangentes iguales en un vértice) | Los dos arcos tangentes del mismo lado se desempatan por la curvatura; con un test que lo pone a prueba |
| Que los casos 006 y 007 no converjan con la graduada sola, como pasó en el 005 | El estudio lo dice; una ventana, como en el 005, es decisión de la propietaria |
