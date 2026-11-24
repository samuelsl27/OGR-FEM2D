# Spec 004 — Modelo FEM y proyecto `.ogrfem2d`

> **Cerrada (2026-11-23)**: criterios de finalización cumplidos (changelog v0.0.9, T19).
> **Aprobada (2026-11-23)**, con D1–D16 tal como están abajo: las marcadas ✔ las eligió la
> propietaria al revisar la spec, y las demás se aprobaron como se propusieron. Fase 1 del plan de
> desarrollo (`spec/constitution/plan_de_desarrollo.md`, «Spec 004 — Modelo FEM y proyecto
> `.ogrfem2d`»). Solo el **qué** y el **porqué**; el cómo, en `plan.md`. Versión: **v0.0.9**.

## La revisión (2026-11-23)

- [x] Contrastada con el código y con las specs cerradas. Ya existen la entrada del motor
      (`docs/motor/entrada.md`: `EngineModel`, `Stage`, cargas en totales, excavación por
      desactivación) y la del mallador (`docs/malla/entrada.md`: `MeshInput`, regiones, arcos,
      divisiones forzadas, ventanas, `Mesh.boundaries`, `to_engine`). Los campos de tensión inicial
      están en `engine/initial_stress.py`: reciben compresión positiva y convierten. Ningún caso
      tiene modelo; el 005 se construye a mano en `tests/_kirsch_mesh.py`.
- [x] Mirados el núcleo en la etiqueta fijada (v0.2.6; su `main` no trae nada nuevo que importe
      aquí) y Slip2D. El `Project` del núcleo es de equilibrio límite y no sirve como modelo FEM:
      - no tiene E ni ν, ni contornos de excavación o de fase, ni arcos;
      - al guardar pierde las secciones que no conoce;
      - rechaza los tipos de contorno que no conoce;
      - nunca lee `format_version`.

      Sirve tal cual:
      - `CommandStack`, que solo pide al objeto `execute` y `undo`;
      - el sistema de unidades, que guarda en kPa;
      - `LoadOrientation`;
      - el lector DXF, que aplana los arcos;
      - `Project.load`, para leer un `.ogr` de Slip2D;
      - el mallador.

      La huella de Slip2D (`ogr_api/snapshot.py`) está en Slip2D, no en el núcleo.
- [x] Mirado cómo lo hace la referencia (`M02` §5.2 y §6.2, `F01`). Cada programa tiene su archivo.
      El de elementos finitos guarda la malla y abre el archivo de equilibrio límite convirtiéndolo:
      trae contornos, agua, cargas y materiales, pone restricciones y valores elásticos por defecto
      y avisa de ellos. También exporta una fase al de equilibrio límite.
- [x] Fuentes: ninguna fórmula nueva. Las que se usan ya están leídas en la spec 002 (`plan.md`,
      «Formulación»).
- [x] Fichas STR-01, STR-04 y STR-09 releídas con su «Seguimiento». Las tres piden la malla general
      y los resultados por línea (`POST-LINEA`, que es de la 005).
- [x] Dudas convertidas en decisiones (D1–D16).

## Depende de

- Spec 002: la entrada del motor, las fases en totales, la tensión inicial por punto y la excavación
  por desactivación. El motor **no** admite que un elemento vuelva a activarse ni que cambie de
  material entre fases.
- Spec 003: la entrada del mallador y su salida, con el mapa segmento → nudos y lados y las notas.
- Spec 001, D1 y D2 (signos y totales); ADR-0002 (núcleo común); ADR-0003 (resultados aparte, con
  la huella).

## Contexto y objetivo

Hoy cada test escribe a mano la entrada del mallador y la del motor. Falta el **modelo**: lo que
define el ingeniero, guardado en un archivo, y su traducción determinista a la entrada del mallador
y a la del motor. Comprende la geometría, los materiales, las fases, la tensión de campo, las
condiciones y cargas sobre la geometría, los ajustes de malla y la malla.

Esta spec es esa capa, sin interfaz. La usarán la 005, que guarda los resultados con la huella que
se calcula aquí, y la 006, que dibuja y edita el modelo. El plan pide un modelo en los casos desde la
fase 1, y hoy ninguno lo tiene.

## Usuarios / actores

- **El ingeniero**, por la interfaz (006) o por un script.
- **Las operaciones, la línea de órdenes y el servidor MCP** (006).
- **Los resultados** (005), que necesitan la huella.
- **OGR Slip2D**: su `.ogr` se abre aquí convirtiéndolo.
- **Los casos de validación**.

## Historias de usuario

- H1: Como ingeniero quiero guardar un modelo y abrirlo otro día idéntico, malla incluida, para
  repetir el cálculo.
- H2: Como ingeniero quiero insertar, borrar y renombrar fases, y decir en cada una qué regiones están
  excavadas y qué cargas y condiciones actúan.
- H3: Como ingeniero quiero poner cargas y condiciones sobre los contornos dibujados y no sobre
  nudos, para que sobrevivan a un nuevo mallado.
- H4: Como ingeniero quiero abrir un modelo de OGR Slip2D o un DXF y saber qué se ha traído y qué no.
- H5: Como ingeniero quiero ver con el modelo cada valor por defecto que cambia el resultado, y
  saber por la huella si unos resultados son de este modelo.

## Requisitos funcionales (EARS)

**Geometría, fases y ajustes**

- RF-1: EL SISTEMA guarda contornos de cuatro tipos y resuelve de ellos las regiones de material
  (D15):
  - externo, uno y cerrado;
  - de material, abierto o cerrado;
  - de excavación, cerrado;
  - de fase, abierto o cerrado: el que parte una región para excavarla por partes.

  Una excavación es una región que alguna fase desactiva. SI los contornos no forman regiones
  cerradas, o se cortan fuera de sus vértices, ENTONCES lo dice nombrando el contorno culpable.
- RF-2: EL SISTEMA guarda en cada segmento lo que el mallador necesita de él: el arco (su centro) y
  el número de divisiones forzado (D2).
- RF-3: EL SISTEMA trata la fase como dimensión del modelo (D10):
  - es una lista ordenada de fases, cada una con id estable y nombre;
  - por fase guarda el estado de cada región (material o excavada), qué condiciones están activas y
    el factor de cada carga y de cada desplazamiento impuesto;
  - el total es factor × magnitud, y un factor 0 quiere decir que no actúa.
- RF-4: SI una región excavada vuelve a activarse, o una región cambia de material entre fases,
  ENTONCES EL SISTEMA lo rechaza con un error que lo explica, hasta que el motor lo admita (012).
- RF-5: EL SISTEMA guarda el tipo de análisis (deformación plana o axisimetría), el sistema de
  unidades que se muestra (D5), el resumen y las fases. Todo valor por defecto que cambia el
  resultado se escribe explícito y se puede listar (regla 12). SI el análisis es axisimétrico y un
  punto o un arco tiene x < 0, ENTONCES error (spec 002, RF-4).

**Materiales, tensión de campo, condiciones y cargas**

- RF-6: EL SISTEMA guarda materiales elásticos isótropos (E, ν) con su peso específico y su modo de
  carga inicial (D11), y su asignación por región y fase. SI un material no tiene E o ν, ENTONCES el
  modelo no se traduce al motor y el error lo nombra.
- RF-7: EL SISTEMA guarda la tensión de campo, que puede ser:
  - constante: σ1, σ3, σz y el ángulo;
  - gravitatoria: con superficie y estratos horizontales, cada estrato con su cota inferior, γ, K y
    Kz (D14).

  La lleva a cada punto de integración con los preprocesos de la spec 002 (D3 y su enmienda en
  axisimetría).
- RF-8: EL SISTEMA convierte de compresión positiva (la costumbre geotécnica) a tracción positiva en
  **un único sitio**, el mismo para la tensión de campo y para las cargas (D6, regla 10).
- RF-9: EL SISTEMA guarda, por segmento o por vértice (D7):
  - restricciones en X, en Y o en las dos;
  - liberaciones;
  - desplazamientos impuestos.

  Guarda también la condición por defecto del contorno externo, escrita explícita y listada
  (regla 12). La precedencia y la unión en los nudos compartidos son las de D16. SI dos condiciones
  piden valores distintos para el mismo grado de libertad, ENTONCES error que nombra las dos.
- RF-10: EL SISTEMA guarda:
  - cargas repartidas, lineales entre sus extremos (la uniforme es un caso), sobre un tramo de
    contorno entre dos vértices, normales o con una de las orientaciones de `LoadOrientation` del
    núcleo;
  - cargas puntuales en un vértice; en axisimetría, la del anillo entero, que es el convenio del
    motor y se muestra.

  Las lleva a la malla con el mapa de la 003. SI una carga cae, en una fase, sobre un segmento que no
  es exterior al dominio activo, ENTONCES error que nombra la carga, el contorno y la fase.

**Malla y traducción al motor**

- RF-11: EL SISTEMA guarda los ajustes de malla y **la malla entera** (D3), con la huella de la
  entrada del mallador de la que salió. SI la geometría o los ajustes de malla cambian después de
  mallar, ENTONCES la malla es de otro modelo y no se calcula con ella. Cambiar un material o una fase
  no invalida la malla.
- RF-12: CUANDO se pide la entrada del motor, EL SISTEMA la construye de forma determinista: el mismo
  modelo da la misma entrada bit a bit. SI el mallador o el motor la rechazan, ENTONCES el error nombra
  el objeto del modelo (contorno, región, material, fase, carga o condición), no solo el nudo o el
  elemento.

**Archivo, apertura de otros formatos, deshacer y huella**

- RF-13: EL SISTEMA guarda el modelo en un `.ogrfem2d` JSON (D1), con estas propiedades:
  - lleva la versión de formato y el programa que lo escribió;
  - lleva la malla y no lleva resultados (ADR-0003);
  - guardar y abrir es una identidad, hasta los bytes del archivo;
  - SI una sección no tiene la forma esperada, una clave no se conoce o la versión es posterior,
    ENTONCES da un error que la nombra; nada se pierde en silencio.
  - *Modificado el 2026-11-24 (spec 006, T11, OK de la propietaria)*: guarda y abre un modelo
    **válido como documento**, también a medio dibujar (sin externo, con contornos que se cruzan, con
    una región sin material), y dice lo que le falta; calcular sigue exigiendo el modelo entero
    válido.
- RF-14: EL SISTEMA abre un `.ogr` de OGR Slip2D (D16) y un DXF (D13) convirtiéndolos, y dice qué ha
  traído, qué no ha podido traer y por qué, y qué valores por defecto ha puesto.
- RF-15: EL SISTEMA permite deshacer y rehacer cada edición del modelo.
- RF-16: EL SISTEMA calcula dos huellas (D12):
  - la **del modelo**, que cambia con todo lo que cambia el resultado, malla incluida, y con nada
    más: ni la vista, ni el resumen, ni los nombres y colores, ni el sistema de unidades que se
    muestra (ADR-0003);
  - la **del documento**, que lo recoge todo.

## Validación numérica

Esta spec no calcula nada nuevo: valida que el paso del modelo al motor no cambia nada, y añade dos
casos con malla general (D4).

| Caso | Fuente científica | Qué se compara |
|---|---|---|
| `validacion/casos/005-kirsch-malla-general` (ficha `VER-STR-01`) con su `modelo.ogrfem2d` | Kirsch (1898), en Jaeger, Cook y Zimmerman (2007), §8.4, como el caso | El modelo da el mismo `MeshInput` que el caso escrito a mano, la malla guardada es la del mallador bit a bit, y la entrada del motor es la del caso escrito a mano en kPa. El caso cumple su 0.5 % |
| `validacion/casos/006-carga-en-faja-malla-general` (nuevo, ficha `VER-STR-04`) | Michell (1902), en Timoshenko y Goodier (1951), §34, ec. (f), como el caso 004 | σ1 y σ3 bajo el centro de la faja, con la malla general, la carga sobre un tramo de contorno y las restricciones por segmento. Tolerancia fijada antes de medir; malla fijada por su estudio de convergencia |
| `validacion/casos/007-cavidad-esferica-malla-general` (nuevo, ficha `VER-STR-09`) | Lamé (1852), en Timoshenko y Goodier (1951), §121, ecs. (197)–(198), como el caso 003 | σt y u_R(a) en axisimetría, con la malla general y los arcos de la cavidad. Tolerancia fijada antes de medir; malla fijada por su estudio |
| Casos 001 a 004 | Los de sus casos | Sin cambio, bit a bit: siguen con sus mallas de prueba (D4) |
| Ida y vuelta del `.ogrfem2d` | — (identidad) | Guardar y abrir da el mismo modelo, los mismos bytes, la misma huella y la misma entrada del motor |
| Unidades | — (homogeneidad dimensional) | El mismo modelo con las tensiones ×1000 da los mismos desplazamientos y las tensiones en la misma proporción, a redondeo |
| Signos | Spec 001, D1 | Una compresión de campo llega al motor negativa. Una presión normal positiva empuja hacia el terreno |
| Campo gravitatorio con peso propio | JCZ (2007), ecs. (13.1) y (13.5) | Superficie horizontal, estratos horizontales y la carga inicial «tensión de campo y peso propio»: el campo está en equilibrio y el desplazamiento es nulo. Cada modo de carga inicial mueve el número |
| Regiones | — (identidad) | La suma de las áreas de las regiones es el área del externo, y la característica de Euler cuadra |
| Huella | — | Mutar cada dato que mueve el resultado cambia la huella; el nombre, el color, el resumen o las unidades mostradas, no |
| Apertura de un `.ogr` de Slip2D | — | Las regiones y sus áreas son las que da el núcleo (`build_regions`) a redondeo, y el informe lista todo lo que no se trae |
| Regla 7 | — | Cada ajuste nuevo, con el test que demuestra que mueve el número |

## Fuentes por conseguir

- Ninguna para esta spec.
- La superficie real del terreno y K variable con la profundidad no tienen fuente leída; van a la
  009 (D14).
- Las caras de un grafo plano (D15) son un algoritmo de geometría computacional (de Berg et al.
  2008, cap. 2, que no está en la bibliografía). Se validan con identidades, no con la fuente.

## Requisitos no funcionales

- Sin Qt: el modelo se usa desde scripts, tests, la línea de órdenes y el servidor MCP.
- El `.ogrfem2d` es legible y comparable con git, con un nudo y un elemento por línea en la malla.
- Lo genérico se toma del núcleo (unidades, orientaciones, deshacer, lector DXF, mallador); aquí no
  se copia ni se rodea.
- Sin dependencias nuevas. Los mensajes llevan una clave traducible para la interfaz (regla 2).

## Casos límite

- Región sin material o con dos asignaciones; ningún externo o dos externos; contornos que se cortan
  fuera de sus vértices; un contorno abierto con un extremo suelto; dos regiones que se tocan en un
  punto (spec 003, RF-14).
- Fase sin cambios; fase que lo excava todo; nudo sin elementos activos (spec 002).
- Una carga sobre un contacto entre dos regiones activas; una condición que libera el segmento de al
  lado de una esquina fija.
- Un `.ogr` de Slip2D con contornos que aquí no tienen sentido (nivel freático, grieta, superficies),
  con cargas cuyos extremos no son vértices, o de una versión que el núcleo fijado no abre.
- Un `.ogrfem2d` de una versión de formato posterior, con una clave desconocida o con un campo de
  otro tipo.
- Cambiar el sistema de unidades o el tipo de análisis con el modelo ya definido; la malla de otra
  huella.

## Fuera de alcance

- La interfaz, los menús y las traducciones (006); los resultados y el `.h5` (005).
- Exportar una fase a OGR Slip2D (spec posterior) y que Slip2D abra un `.ogrfem2d` (su sesión).
- Mohr-Coulomb y las demás leyes, y los ajustes del cálculo (008, 007).
- Condiciones y cargas por nudo (006, si las pide).
- Relleno, cambio de material por fase, propiedades por fase y relajación de la tensión de campo
  (012).
- La tensión gravitatoria con la superficie real del terreno y K variable (009).
- Juntas e interfaz estructural (015, 016); soportes, agua, SSR, muelles, elementos infinitos y
  cuadriláteros.
- Tensión de campo propia de cada material y tensiones residuales, observadas en la referencia (D02,
  §3).

## Criterios de finalización

- [x] D1–D16 aprobadas por la propietaria y anotadas aquí (2026-11-23)
- [x] ADR-0004 escrito; AGENTS.md y ADR-0003 corregidos donde dicen `.ogr` (T0)
- [x] Todos los RF con su test en verde, y la regla 7 en cada ajuste nuevo
- [x] El caso 005 con su `modelo.ogrfem2d`, idéntico bit a bit al escrito a mano; los casos 006 y
      007 dentro de la tolerancia fijada antes de medir, con su estudio de convergencia
- [x] Las identidades de la tabla, en verde y con dientes
- [x] Los casos 001 a 004 dan lo mismo bit a bit
- [x] La petición al núcleo de los arcos en DXF, escrita (D13; no bloquea)
- [x] Changelog con lo encontrado; fichas STR-01, STR-04 y STR-09 con su «Seguimiento»

## Decisiones (2026-11-23)

Aprobadas el 2026-11-23. Las marcadas ✔ las eligió la propietaria al revisar la spec; las demás,
tal como se propusieron.
Las referencias D02, D03, D08, M04a, M05, M10, M23, P05, P11, P14 y P20 son del análisis de
interfaz (`../Referencias/Doc_Guia/Analisis_interfaz_funcionamiento/`); `M02` y `F01`, de su
documentación y de sus archivos.

| # | Duda del borrador | Decisión | Por qué |
|---|---|---|---|
| D1 ✔ | 2 y 3: qué clase es el modelo y qué quiere decir «compatible» | **Formato propio, `.ogrfem2d`** (JSON), con el modelo y la malla; los resultados, en el `.h5` aparte (ADR-0003). El modelo es una clase de FEM2D. Usa el código común del núcleo: unidades, orientaciones de carga, deshacer, lector DXF y mallador. FEM2D **abre el `.ogr` de Slip2D convirtiéndolo** (D16). Exportar una fase a Slip2D, en una spec posterior. Que Slip2D abra un `.ogrfem2d` es cosa de su sesión. ADR-0004 nuevo; AGENTS.md («Formato de proyecto») y ADR-0003 (`modelo.ogr`) se corrigen | Es lo que hace la referencia: dos archivos, y el programa FEM abre el de equilibrio límite (`M02` §5.2). Un archivo común pedía cambiar el `Project` del núcleo, que pierde al guardar lo que no conoce y rechaza los tipos de contorno que no conoce, y la spec habría esperado a una versión del núcleo. Lo que se comparte es el código, no el archivo |
| D2 | 1: el arco en la geometría | **El arco es un atributo del segmento** (su centro) en la geometría del `.ogrfem2d`, como en el `MeshInput`. Las divisiones forzadas, también | Con formato propio no cambia nada común. Reconocer arcos por los vértices sería adivinar (spec 003, D3) |
| D3 ✔ | 4: dónde viven la malla, la discretización y las ventanas | **Todo en el `.ogrfem2d`, la malla entera incluida**, con la huella del `MeshInput` del que salió. La malla lleva la región de cada elemento, no el material. Se rehace solo cuando se pide. Un nudo y un elemento por línea | Como la referencia, que guarda la malla (`F01`). La malla de un caso no cambia en silencio con una versión nueva del mallador (regla 9): lo dice la comparación con la guardada. Cambiar un material no obliga a rehacerla. El coste es que el archivo pesa (unos MB en el caso 005), y el ADR-0004 lo dice |
| D4 ✔ | 5: los casos con malla de prueba | Llevan modelo el **005** y **dos casos nuevos con malla general**: el 006 (STR-04, faja) y el 007 (STR-09, cavidad esférica, axisimétrico). Los dos fijan la tolerancia antes de medir y tienen su estudio de convergencia. Los casos 001 a 004 no cambian | El 005 no tiene cargas, ni restricciones por segmento, ni axisimetría; el 006 y el 007 sí, y son los que pide la fase 1. Cambiar la malla de un caso es cambiar el caso (regla 9): por eso son casos nuevos |
| D5 ✔ | 6: unidades | **Se guarda en m, kN, kPa y kN/m³**, como el núcleo. El sistema que se elige (de la lista del núcleo) solo cambia lo que se muestra; uno desconocido es un error, mientras que el núcleo lo sustituye en silencio. Cambiar de sistema no toca los valores. El motor recibe kPa | Es el patrón del núcleo y de Slip2D, y con él cambiar las unidades no puede romper un modelo. La comparación bit a bit del 005, escrito en MPa, se hace contra el mismo modelo escrito a mano en kPa: sus valores son enteros, así que ×1000 es exacto |
| D6 | 7: convenio dentro del archivo | **El del usuario**: tensión de campo en compresión positiva; carga normal positiva cuando empuja hacia el terreno (D08); desplazamientos según +x y +y. Lo convierte un único módulo, `ogr_fem2d/model/conventions.py`, que para las tensiones llama a `initial_stress` (spec 002) | Lo que se lee en el archivo es lo que escribió el usuario, y lo que se escribe es lo que ve. Un solo sitio, el mismo para el campo y para las cargas (regla 10). El motor sigue con tracción positiva y normal hacia fuera del elemento |
| D7 ✔ | 8: condiciones por nudo | **Solo sobre la geometría**, por segmento o por vértice. Por nudo, cuando lo pida la 006 | Sobreviven a un nuevo mallado, como en la referencia (P21). Un nudo es de una malla |
| D8 | 9: juntas e interfaz estructural | **A sus specs** (015 y 016). El formato lleva versión para añadirlas | Sin elemento en el motor serían ajustes que no hacen nada (regla 7) |
| D9 ✔ | 10: leyes y ajustes del cálculo | **Solo materiales elásticos.** Mohr-Coulomb, en la 008 con las demás leyes; la tolerancia, las iteraciones y los escalones, en la 007. La traducción usa los valores por defecto del motor | En elástico esos ajustes no mueven el número (regla 7), y la tolerancia por defecto la fija la 007 con STR-05 (S06, duda 8) |
| D10 | 11: semántica de las fases | Las fases tienen **id estable** y nombre; todo lo que depende de la fase se refiere al id. El archivo guarda la **tabla región × fase entera**: material o excavada. La propagación es cosa de la operación, no del archivo: asignar en la fase k escribe de k a N; con «solo esta fase», escribe k. **Una fase insertada copia la anterior**, y la primera si se inserta delante de ella. Cada carga lleva un factor por fase, y total = factor × magnitud (0 = no actúa); lo mismo cada desplazamiento impuesto. Cada restricción lleva si está activa en cada fase | El id estable lo propone M04a: borrar una fase no corre las referencias de las demás. La tabla explícita es la de M10, y deja el archivo listo para la 012. La propagación y «solo esta fase» son las observadas (P20, D03 §2). Que la fase insertada copie la anterior es **propuesta propia**: la referencia no lo documenta (M04a:278). El factor es lo observado (D08) |
| D11 | 11: modos de carga inicial | **Cuatro, por material**: solo tensión de campo, tensión de campo y peso propio, solo peso propio, o ninguna. Por defecto, el primero con campo constante y el segundo con gravitatorio. Se escribe explícito en cada material y se lista. En el motor, la tensión inicial es el campo o cero, y `Material.unit_weight` es γ o cero | Son los de la referencia, con su regla por defecto (D03, P05, M10). Cada modo mueve el número, y se prueba |
| D12 | 12: la huella | **Aquí**: SHA-256 de un JSON canónico, con claves ordenadas y separadores fijos. La del modelo excluye el resumen, los nombres, los colores y el sistema de unidades que se muestra, e incluye la malla. La del documento lo incluye todo. Si la versión del motor entra en la de los resultados, lo decide la 005 (su duda 7) | Con formato propio, la huella es de este archivo. La receta es genérica y corta. La de Slip2D vive en su `ogr_api`, no en el núcleo, así que no se copia nada del núcleo |
| D13 | 13: DXF y propiedades por fase | **DXF aquí**, con el lector del núcleo y un mapa de capas a los cuatro tipos de contorno (convenio de capas de `M02`). El lector aplana los arcos, y el informe lo dice. Se escribe la petición al núcleo de que los conserve, y no bloquea. Las propiedades por fase, a la 012 | El lector ya existe y es común. Un túnel aplanado da nudos intermedios fuera del arco, y eso se ve en el informe. La importación DXF real no se llegó a observar (S06) |
| D14 ✔ | 14: gravitatorio con la superficie real | **A la 009** (TI-GRAV), que ya lo recoge. Aquí, el campo constante y el gravitatorio con superficie y **estratos horizontales**: cota inferior, γ, K y Kz por estrato, como `initial_stress.Stratum` | Solo eso tiene fuente leída (JCZ ecs. 13.1 y 13.5). Bajo un talud, el campo de la superficie real no está en equilibrio, y pide su fuente. «K y Kz por material», como decía el borrador, solo tiene sentido con la superficie real |
| D15 | Nueva: de los contornos a las regiones | **Los contornos solo se tocan en vértices que comparten**; los cortes los pondrá la 006, como la referencia, que añade el vértice de intersección. Las regiones son las caras del grafo plano de los segmentos. El error nombra el contorno culpable: un corte fuera de los vértices, un extremo suelto de un contorno abierto, ningún externo o dos, o el mismo segmento en dos contornos con arcos distintos. **El material se asigna por un punto de la región**; una región sin asignar, o con dos asignaciones, es un error | La regla del mallador (spec 003: los segmentos solo se tocan en extremos compartidos) llevada a los contornos. Las regiones del núcleo (`build_regions`) no tienen arcos y fallan en silencio, y su asignación da el primer material a la región sin asignar. Aquí eso cambiaría el resultado sin decirlo (regla 12) |
| D16 | Nueva: condiciones por defecto y apertura de Slip2D | **Por defecto, el externo entero fijo en X e Y**, escrito explícito. Precedencia: vértice, después segmento, después el defecto. Un nudo compartido por dos segmentos toma la unión de sus restricciones, así que liberar un segmento no suelta la esquina del vecino. **Abrir un `.ogr` de Slip2D** trae: el externo y los de material, las asignaciones, y los materiales con nombre, color y γ, **sin E ni ν**, que no se inventan (el modelo no calcula hasta tenerlos). Trae también las cargas repartidas y puntuales, insertando vértices en sus extremos. Restricciones: laterales y fondo fijos y superficie libre. Tensión de campo: ninguna. El informe dice lo que no se trae (agua, grietas, soportes, sismo, búsquedas, resistencia) y lo que se ha puesto | El defecto es el observado (P11, M23); P05 vio otro y queda anotado. La unión es la propuesta de P14:82. Las restricciones de la apertura son las de la referencia (`M02` §5.2), que además pone E y ν por defecto: aquí no, porque sería un número que nadie ha dado. La gravitatoria del talud es la de la superficie real (009) |

### Consecuencias en el resto del proyecto

- `AGENTS.md`, «Stack»: la línea del formato de proyecto dice `.ogrfem2d` propio y que abre el
  `.ogr` de Slip2D (ADR-0004). Hecho en la T0, con el OK de la propietaria.
- ADR-0003, `tech-stack.md`, `plan_de_desarrollo.md` y `validacion/README.md`: `modelo.ogr` pasa a
  `modelo.ogrfem2d` (T0).
- Los borradores de las specs 005, 006 y 012 nombran el `.ogr` y estas dudas. Se corrigen cuando se
  abran (cada uno tiene su «reevaluar»).

### Lo que se encontró al hacerla (changelog v0.0.9)

Reportado y corregido durante las tareas, para revisar por la propietaria:

- **D10 precisada (T1)**: la asignación lleva un material por región, el del estado inicial
  también, y una bandera de excavada por fase; el material por fase, con la spec 012.
- **El cero negativo (T2)**: `atan2(−0.0, −1)` = −π ordenaba mal los lados en un vértice.
- **El K de un punto sobre el fondo de un estrato (T4)**: tomaba el del estrato de arriba; ahora, el
  del estrato de su elemento. El preproceso del motor no se tocó.
- **Un hueco lleno de dos regiones (T5)**: el mallador de la spec 003 lo tomaba por un vacío; una
  excavación partida por un contorno de fase no se podía mallar.
- **D12 precisada (T10)**: la huella del modelo nombra contornos, materiales y fases por su lugar, no
  por su id.
- **Los vértices de la subdivisión del núcleo (T12)**: vuelven movidos ~10⁻⁹; se toman los dibujados.
- **Un punto sobre la cuerda de un arco (T17)**: cuenta como fuera de la región; anotado, sin cambio.
- **Un modelo a medio dibujar no se podía guardar (spec 006, T11)**: `ogr_file.write` y `read`
  validaban el modelo entero. Corregido con el OK de la propietaria (2026-11-24): el archivo guarda un
  modelo válido como documento (`model.validate_document`, `model.DRAWING_RULES`), y calcular sigue
  exigiéndolo entero. RF-13 y el ADR-0004 lo dicen.
