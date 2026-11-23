# Spec 004 — Modelo FEM y proyecto `.ogr`

> **Borrador de alcance (2026-11-23), sin aprobar.** Fase 1 del plan de desarrollo
> (`spec/constitution/plan_de_desarrollo.md`, «Spec 004 — Modelo FEM y proyecto `.ogr`»). Solo el
> **qué** y el **porqué**, sin fórmulas ni decisiones tomadas. **Antes de abrirla hay que
> reevaluarla** (sección siguiente); después, plan y tareas con el OK de la propietaria.

## Antes de abrirla: reevaluar esta spec

Este borrador se escribió antes de que existieran las specs que lo preceden; el código, el núcleo y
OGR Slip2D habrán avanzado. Al abrirla, y antes de escribir el plan:

- [ ] Contrastarla con el código de este programa y con las specs cerradas desde el 2026-11-23: qué
      ya está hecho, qué cambió y qué se movió de sitio.
- [ ] Mirar qué tienen ya OGR Slip2D y `ogr_core` en la etiqueta fijada. Lo genérico se pide a la
      sesión de OGR-Core, no se copia (`AGENTS.md`, «Un núcleo y varios programas»). Puntos de
      partida vistos al escribir el borrador (núcleo v0.2.6):
      - `ogr_core/project/project.py`: el `Project` del núcleo es el de equilibrio límite (métodos,
        búsquedas, grieta, soportes, sismo). Contornos como polilíneas (`geometry/boundary.py`,
        `geometry/boundary_type.py`: externo, material, nivel freático…; sin excavación, fase ni
        arco); material por punto semilla (`region_assignments`); guarda **dentro** del `.ogr` la
        malla de filtración (`fem_mesh`) y sus resultados (`seepage_result`, `transient_results`).
      - `project/file_shape.py` (forma de cada sección, comprobada al leer); `project/commands.py`
        (deshacer con órdenes, atadas a ese `Project`); `units/unit_system.py` (guarda en kPa,
        muestra en MPa, kPa, t/m² o imperiales); `project/rules.py`, `fe_model_signature` y
        `mesh_mismatch_reason` (huella de lo que se malla, malla de otro modelo); `dxf/`.
      - En Slip2D, `ogr_api/snapshot.py`: `model_hash` (lo que lee un análisis, sin anotaciones ni
        modo de cálculo) y `document_hash` (todo). Genérico, y fuera del núcleo.
      - Aquí: `docs/motor/entrada.md`, `docs/malla/entrada.md` (`MeshInput`, `Mesh.boundaries`,
        `to_engine`) y `engine/initial_stress.py`.
- [ ] Leer y comprobar las fuentes de «Validación numérica» y de «Fuentes por conseguir»; las fichas
      de los casos no son fuente.
- [ ] Releer las fichas de los casos que la cierran y su «Seguimiento».
- [ ] Convertir las «Dudas abiertas» en decisiones propuestas (D1, D2…) con su porqué, para el OK de
      la propietaria.

## Depende de

- Spec 002: la entrada del motor, las fases en totales, la tensión inicial por punto y la excavación
  por desactivación. El motor **no** admite que un elemento vuelva a activarse ni que cambie de
  material entre fases (un material por elemento para todo el cálculo).
- Spec 003: la entrada del mallador (regiones, arcos, divisiones forzadas, ventanas) y su salida
  (mapa segmento → nudos y lados; notas con cada valor que decidió la malla).
- Spec 001, D1 y D2 (signos y totales); ADR-0002 (núcleo común); ADR-0003 (huella).

## Contexto y objetivo

Hoy cada test escribe a mano la entrada del mallador y del motor. Falta el **modelo**: lo que define
el ingeniero (geometría, materiales, fases, tensión de campo, condiciones y cargas sobre la
geometría, ajustes de malla y de cálculo), guardado en un `.ogr`, y su traducción determinista a la
entrada del mallador y del motor. Esta spec es esa capa, sin interfaz: la usarán la 005, que guarda
los resultados con la huella que se calcula aquí, y la 006, que dibuja y edita el modelo. El plan
pide `modelo.ogr` en los casos desde la fase 1, y hoy ninguno lo tiene.

## Usuarios / actores

- **El ingeniero**, por la interfaz (006) o por un script; **las operaciones, la línea de órdenes y
  el servidor MCP** (006); **los resultados** (005), que necesitan la huella; **OGR Slip2D**, que
  comparte la parte geométrica del `.ogr`; **los casos de validación**.

## Historias de usuario

- H1: Como ingeniero quiero guardar un modelo y abrirlo otro día idéntico, para repetir el cálculo.
- H2: Como ingeniero quiero insertar, borrar y renombrar fases y decir en cada una qué regiones están
  excavadas y qué cargas y condiciones actúan.
- H3: Como ingeniero quiero poner cargas y condiciones sobre los contornos dibujados y no sobre
  nudos, para que sobrevivan a un nuevo mallado.
- H4: Como ingeniero quiero traer la geometría de un modelo de OGR Slip2D o de un DXF.
- H5: Como ingeniero quiero ver con el modelo cada valor por defecto que cambia el resultado, y
  saber por la huella si unos resultados son de este modelo.

## Requisitos funcionales (EARS)

**Geometría, fases y ajustes**

- RF-1: EL SISTEMA guarda contornos externo, de material, de excavación y de fase (el que parte una
  región para excavarla por partes) y resuelve de ellos las regiones de material; una excavación es
  una región que alguna fase desactiva. SI no forman regiones cerradas, ENTONCES lo dice con el
  contorno culpable.
- RF-2: EL SISTEMA conserva lo que el mallador necesita de cada segmento (arco, divisiones forzadas)
  donde se decida (dudas 1 y 4).
- RF-3: EL SISTEMA trata la fase como dimensión del modelo: lista ordenada con nombre, y por fase el
  estado de cada región, las condiciones y las cargas, estas **en totales**; un factor por fase
  multiplica la magnitud y da el total (como lo observado en la referencia, D08).
- RF-4: SI una región excavada vuelve a activarse, o una región cambia de material entre fases,
  ENTONCES EL SISTEMA lo rechaza con un error que lo explica, hasta que el motor lo admita (012).
- RF-5: EL SISTEMA guarda el tipo de análisis (deformación plana o axisimetría), el sistema de
  unidades, el resumen, las fases y los ajustes del cálculo; todo valor por defecto que cambia el
  resultado se escribe explícito y se puede listar (regla 12). SI el análisis es axisimétrico y un
  punto tiene x < 0, ENTONCES error (spec 002, RF-4).

**Materiales, tensión de campo, condiciones y cargas**

- RF-6: EL SISTEMA guarda materiales elásticos isótropos, con su peso específico y su modo de carga
  inicial, y su asignación por región y fase.
- RF-7: EL SISTEMA guarda la tensión de campo constante (σ1, σ3, σz y ángulo) o gravitatoria
  (superficie y estratos horizontales, K y Kz por material) y la lleva a cada punto con los
  preprocesos de la spec 002 (D3 y su enmienda en axisimetría).
- RF-8: EL SISTEMA convierte de compresión positiva (la costumbre geotécnica) a tracción positiva en
  **un único sitio**, el mismo para la tensión de campo y para las cargas (regla 10).
- RF-9: EL SISTEMA guarda restricciones en X, en Y o en las dos, desplazamientos impuestos y
  liberaciones por segmento o vértice, y la condición por defecto del contorno externo, que se
  muestra (regla 12).
- RF-10: EL SISTEMA guarda cargas repartidas (uniformes y lineales, normales o en componentes) y
  puntuales sobre la geometría y las lleva a la malla con el mapa de la 003; SI una cae sobre un
  contorno que no es exterior en esa fase, ENTONCES error que nombra el contorno y la fase.

**Malla y traducción al motor**

- RF-11: EL SISTEMA guarda los ajustes de malla (tipo, elemento, cota B, tamaños, ventanas,
  divisiones por segmento) y la malla según la duda 4; SI la geometría, la asignación o los ajustes
  cambian después de mallar, ENTONCES la malla es de otro modelo y no se calcula con ella.
- RF-12: CUANDO se pide la entrada del motor, EL SISTEMA la construye de forma determinista (mismo
  modelo, misma entrada bit a bit), y SI el mallador o el motor la rechazan, ENTONCES el error nombra
  el objeto del modelo (contorno, región, material, fase), no solo el nudo o el elemento.

**Archivo, importación, deshacer y huella**

- RF-13: EL SISTEMA guarda el modelo en un `.ogr` JSON con versión de formato y sin resultados
  (ADR-0003); guardar y abrir es una identidad; SI una sección no tiene la forma esperada, ENTONCES
  error que la nombra.
- RF-14: EL SISTEMA importa la geometría de un `.ogr` de OGR Slip2D y de un DXF, y dice qué no ha
  podido traer y por qué.
- RF-15: EL SISTEMA permite deshacer y rehacer cada edición del modelo.
- RF-16: EL SISTEMA calcula la huella del modelo, que cambia con todo lo que cambia el resultado y con
  nada más (no la vista ni las anotaciones, ADR-0003), y aparte la del documento entero.

## Validación numérica

Esta spec no calcula nada nuevo: valida que el paso del modelo al motor no cambia nada.

| Caso | Fuente científica (por comprobar) | Qué se compararía |
|---|---|---|
| `validacion/casos/005-kirsch-malla-general` (ficha `VER-STR-01`) con su `modelo.ogr` | Kirsch (1898), en Jaeger, Cook y Zimmerman (2007), §8.4, como el caso | El `.ogr` da al motor la misma entrada, bit a bit, que el caso escrito a mano; los números, idénticos |
| Casos 001, 003 y 004 (fichas `VER-STR-01`, `-09` y `-04`) | Las de sus casos | Según la duda 5: usan mallas de prueba que el mallador de la 003 no hace |
| Ida y vuelta del `.ogr` | — (identidad) | Guardar y abrir: mismo modelo, misma huella, misma entrada del motor |
| Unidades | — (homogeneidad dimensional) | El mismo modelo en MPa y en kPa: desplazamientos iguales, tensiones en la proporción de las unidades, a redondeo |
| Signos | Spec 001, D1 | Una compresión de campo llega al motor negativa; una presión hacia el terreno, con la normal hacia dentro |
| Huella | — | Mutar cada dato que mueve el resultado cambia la huella; mover la vista, no |
| Importación de Slip2D | — | La geometría importada da las mismas regiones y áreas, a redondeo |
| Regla 7 | — | Cada ajuste nuevo, con el test que demuestra que mueve el número |

## Fuentes por conseguir

- Ninguna fórmula nueva entra aquí. La superficie del terreno irregular y K variable con la
  profundidad (la 002 los dejó para cuando hubiera geometría) no tienen fuente: la spec 002 (D3)
  dejó escrito que K = a + b·zᶜ no la tiene y que la ec. (13.10) de Jaeger, Cook y Zimmerman (2007)
  es otra forma. Sin fuente leída, se quedan fuera.

## Requisitos no funcionales

- Sin Qt: el modelo se usa desde scripts, tests, la línea de órdenes y el servidor MCP.
- El `.ogr` sigue siendo legible y comparable con git (ADR-0003).
- Lo genérico (formato común, huella, deshacer, unidades) se pide a OGR-Core; aquí no se rodea.
- Sin dependencias nuevas. Los mensajes llevan una clave traducible para la interfaz (regla 2).

## Casos límite

- Región sin material; dos contornos externos; contornos que se cortan fuera de sus vértices; dos
  regiones que se tocan en un punto (spec 003, RF-14).
- Fase sin cambios; fase que lo excava todo; nudo sin elementos activos (spec 002).
- Un `.ogr` de Slip2D con contornos que aquí no tienen sentido (nivel freático, grieta, superficies).
- Un `.ogr` de una versión de formato posterior; un campo de otro tipo.
- Cambiar las unidades o el tipo de análisis con el modelo ya definido; malla de otra huella.

## Fuera de alcance

- La interfaz, los menús y las traducciones (006); los resultados y el `.h5` (005).
- Relleno, cambio de material por fase y relajación de la tensión de campo (spec 012).
- Juntas, soportes, agua, SSR, muelles, elementos infinitos y cuadriláteros.
- Propiedades por fase o dependientes de la cota; tensión de campo propia de cada material y
  tensiones residuales, observadas en la referencia (D02, §3).

## Criterios de finalización

- [ ] Dudas convertidas en decisiones y aprobadas por la propietaria
- [ ] Todos los RF con su test en verde, y la regla 7 en cada ajuste nuevo
- [ ] El caso 005 con su `modelo.ogr`, idéntico bit a bit al escrito a mano; los demás, según la
      duda 5
- [ ] Las identidades de la tabla, en verde y con dientes
- [ ] Lo pedido a OGR-Core, en una versión etiquetada y fijada aquí
- [ ] Changelog con lo encontrado; fichas con su «Seguimiento»

## Dudas abiertas

- [NECESITA ACLARACIÓN] **1. El arco en la geometría y en el `.ogr` común** (spec 003, D3): (a) un
  atributo del segmento en la geometría del núcleo, que Slip2D leería como su poligonal; (b) solo en
  la parte FEM del `.ogr`, y Slip2D ve las cuerdas; (c) sin arco, reconocido por los vértices (la
  003 lo descartó por adivinar). (a) cambia el formato común: petición a OGR-Core.
- [NECESITA ACLARACIÓN] **2. Qué clase es el modelo**: (a) el `Project` del núcleo ampliado con
  secciones FEM; (b) una clase propia que comparte geometría, materiales y formato; (c) una base
  común en el núcleo con una especialización por programa. Decide si el deshacer del núcleo sirve, y
  condiciona la 006: el lienzo de Slip2D importa ese `Project`.
- [NECESITA ACLARACIÓN] **3. «Compatible en la parte geométrica»**: un mismo archivo que abren los
  dos programas sin tocar las secciones del otro (por comprobar si `file_shape` acepta secciones que
  no conoce), o importar y exportar entre dos formatos.
- [NECESITA ACLARACIÓN] **4. Dónde se guardan la malla, la discretización personalizada y las
  ventanas** (lo dejó la 003). Los ajustes, en el `.ogr`; la malla: (a) en el `.ogr`, como la de
  filtración del núcleo; (b) en el `.h5`; (c) no se guarda y se rehace (bit a bit por la 003, D11,
  pero una versión nueva del mallador cambiaría la malla de un caso: regla 9).
- [NECESITA ACLARACIÓN] **5. Los casos con malla de prueba.** El 001 y el 003 (cuarto de corona) y el
  004 (rectángulo con progresión geométrica) usan mallas que el mallador no hace (su malla radial es
  un anillo completo). Opciones: (a) admitir en el `.ogr` una malla dada; (b) casos nuevos con malla
  general y su estudio de convergencia (regla 9); (c) en la fase 1, `modelo.ogr` solo en el 005.
- [NECESITA ACLARACIÓN] **6. Unidades**: el núcleo guarda en kPa; los casos de roca, en MPa; el motor
  no sabe de unidades. ¿En cuáles recibe el motor? ¿Cambiar las unidades convierte los valores?
- [NECESITA ACLARACIÓN] **7. Convenio dentro del `.ogr`** (S06, dudas 12 y 14): compresión positiva,
  como lo escribe el usuario, o tracción positiva, como el motor.
- [NECESITA ACLARACIÓN] **8. Condiciones por nudo** (el plan: «segmento, vértice o nudo»): un nudo es
  de una malla y se pierde al rehacerla. ¿Solo geometría en la fase 1, o nudos ligados a una malla
  guardada, que se invalidan si cambia?
- [NECESITA ACLARACIÓN] **9. Contornos de junta e interfaz estructural** (en el plan): sin elemento en
  el motor hasta las specs 015 y 016 serían ajustes que no hacen nada (regla 7). ¿Se guardan ya y se
  rechaza calcular con ellos, o pasan a sus specs?
- [NECESITA ACLARACIÓN] **10. Leyes y ajustes del cálculo**: el motor ya calcula Mohr-Coulomb con T6
  en deformación plana (caso 002): ¿entra aquí, o solo elástico, como el plan? Tolerancia,
  iteraciones y escalones: el motor tiene los suyos por fase; en elástico no mueven el número, y la
  tolerancia por defecto la fija la 007 con STR-05 (S06, duda 8).
- [NECESITA ACLARACIÓN] **11. Semántica de las fases**: qué hereda una fase insertada; si un cambio
  vale solo para la fase visible o también para las siguientes (la referencia tiene «solo esta
  fase», D03 §2); qué modos de carga inicial por material se ofrecen y cuál por defecto (la
  referencia: «solo tensión de campo», con el peso inhabilitado).
- [NECESITA ACLARACIÓN] **12. La huella**: dónde vive (la de Slip2D es genérica: ¿petición al
  núcleo?) y qué entra además del modelo: la malla o solo sus ajustes, la versión del motor.
- [NECESITA ACLARACIÓN] **13. Pendientes de S06** que tocan aquí: la importación DXF real y las
  propiedades por fase con varias fases. ¿Aquí o en su spec?
- [NECESITA ACLARACIÓN] **14. Tensión gravitatoria con la superficie real del terreno** (visto al
  redactar la 009): la piden 118 casos de SSR (`TI-GRAV`); la spec 002 (D3) la mandó aquí y este
  borrador la deja fuera por falta de fuente. Si no entra aquí, tiene que entrar en la 009 o antes;
  si no, la fase 2 no desbloquea los casos que el plan le atribuye.

Las referencias D02, D03 y D08 son de la carpeta A del análisis de interfaz
(`../Referencias/Doc_Guia/Analisis_interfaz_funcionamiento/`, `dialogos/`).
