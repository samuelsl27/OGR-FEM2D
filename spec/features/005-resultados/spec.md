# Spec 005 — Resultados (`.h5`) y su interpretación sin interfaz

> **Borrador de alcance (2026-11-23), sin aprobar.** Fase 1 del plan de desarrollo
> (`spec/constitution/plan_de_desarrollo.md`, «Spec 005 — Resultados (`.h5`) y su interpretación
> sin interfaz»). Solo el **qué** y el **porqué**, sin fórmulas ni decisiones tomadas. **Antes de
> abrirla hay que reevaluarla** (sección siguiente); después, plan y tareas con el OK de la
> propietaria.

## Antes de abrirla: reevaluar esta spec

Este borrador se escribió antes de que existieran las specs que lo preceden; el código, el núcleo y
OGR Slip2D habrán avanzado. Al abrirla, y antes de escribir el plan:

- [ ] Contrastarla con el código de este programa y con las specs cerradas desde el 2026-11-23: qué
      ya está hecho, qué cambió y qué se movió de sitio.
- [ ] Mirar qué tienen ya OGR Slip2D y `ogr_core` en la etiqueta fijada. Lo genérico se pide a la
      sesión de OGR-Core, no se copia (`AGENTS.md`, «Un núcleo y varios programas»). Puntos de
      partida vistos al escribir el borrador:
      - `ogr_core/project/results_io.py` (v0.2.6, 284 líneas): escribe y lee en HDF5 el resultado
        de una búsqueda de equilibrio límite (superficies, dovelas y un resumen), con
        `format_version` y `project_id` como atributos y compresión gzip en el resumen. **No guarda
        huella.** Ya no está «sin usar», como dice el ADR-0003: lo usan `ogr_gui/background.py`
        (escribe a un temporal y lo mueve) y `ogr_cli` de Slip2D. La disposición por fase de un
        cálculo FEM es nueva; lo reutilizable es la parte genérica.
      - `h5py` llega como dependencia de `ogr-core` (≥ 3.10), no de este programa.
      - En Slip2D: `ogr_gui/contours.py` (paletas, niveles y rango automático, sin Qt) y
        `ogr_api/results.py` (resúmenes para un agente).
      - En este programa: `engine/analysis.py`, `StageOutcome` (por fase: desplazamientos, tensiones
        por punto, reacciones, estado plástico, historia de convergencia, elementos activos, nudos
        retirados y del eje). **No da deformaciones.** Y `mesh/mesher.py`, `Mesh` con sus notas.
- [ ] Leer y comprobar las fuentes de «Validación numérica» y de «Fuentes por conseguir»; las fichas
      de los casos no son fuente.
- [ ] Releer las fichas de los casos que la cierran y su «Seguimiento».
- [ ] Convertir las «Dudas abiertas» en decisiones propuestas (D1, D2…) con su porqué, para el OK de
      la propietaria.

## Depende de

- Spec 002 (lo que devuelve el motor por fase), spec 003 (la malla y su mapa de contornos), spec 004
  (el modelo y su huella). ADR-0003 (resultados en `modelo.h5` con la huella).

## Contexto y objetivo

El motor devuelve sus resultados en memoria y nadie los guarda; los tests comparan a mano, en los
puntos de integración. Esta spec guarda cada cálculo en `modelo.h5`, junto al `.ogr` y con su
huella, para que abrir un modelo no obligue a recalcular y para que unos resultados nunca se tomen
por los de otro modelo. Encima, sin Qt, da lo que se interpreta: las magnitudes de campo, cada una
con su definición y su fuente; el paso a los nudos para dibujar, sin perder los valores en los
puntos, que son los que se validan; y las consultas por línea, por contorno y en todos los nudos,
con su evolución por fase. Así lo usan igual la interfaz (006), la línea de órdenes, un agente, un
informe y un test.

## Usuarios / actores

- **El ingeniero**, que abre unos resultados, los consulta y los exporta; **la interfaz, las
  operaciones, la línea de órdenes y el servidor MCP** (006); **el investigador**, que lee el `.h5`
  con sus herramientas; **los tests y los casos**, que comparan con soluciones cerradas.

## Historias de usuario

- H1: Como ingeniero quiero abrir un modelo calculado ayer y ver sus resultados sin recalcular, y
  que el programa me diga si he cambiado el modelo desde entonces.
- H2: Como ingeniero quiero σ1, σ3 y los desplazamientos a lo largo de una línea, para compararlos
  con una solución cerrada o con una medida.
- H3: Como ingeniero quiero los valores sobre el contorno de una excavación, o a una distancia de él.
- H4: Como ingeniero quiero exportar el valor de una magnitud en todos los nudos a una tabla.
- H5: Como ingeniero quiero ver cómo cambia una magnitud en un punto de una fase a otra.
- H6: Como investigador quiero saber, de cada valor, si es de un punto de integración o recuperado
  en un nudo, y con qué método.

## Requisitos funcionales (EARS)

**El archivo de resultados**

- RF-1: CUANDO termina un cálculo, EL SISTEMA escribe `modelo.h5` junto al `.ogr` con la huella del
  modelo, la versión del formato, del programa y del núcleo, la malla con la que se calculó (o lo que
  se decida, duda 6) y, por fase, todo lo que devuelve el motor y los ajustes que decidieron el
  cálculo (regla 12).
- RF-2: EL SISTEMA escribe el archivo de forma que un cálculo interrumpido o cancelado no deje un
  `.h5` que parezca completo.
- RF-3: CUANDO se abre un modelo cuyo `.h5` tiene otra huella, EL SISTEMA marca los resultados
  obsoletos y no los presenta como válidos; sin `.h5`, ofrece calcular (ADR-0003).
- RF-4: SI el `.h5` está dañado o es de una versión de formato desconocida, ENTONCES EL SISTEMA lo
  dice con un error y no lee nada a medias. EL SISTEMA lee una fase o una magnitud sola.

**Magnitudes de campo**

- RF-6: EL SISTEMA da, por fase, en los puntos de integración: tensiones cartesianas y la de fuera
  del plano, tensiones principales y su orientación, tensión media, de von Mises y diferencial;
  desplazamientos horizontal, vertical (con y sin valor absoluto) y total; deformaciones
  volumétrica y de corte máxima. Cada una con su definición escrita y su fuente.
- RF-7: EN axisimetría, EL SISTEMA nombra cada magnitud por su sentido (radial, axial,
  circunferencial), y la tensión fuera del plano es la circunferencial (spec 002).
- RF-8: EL SISTEMA da el factor de resistencia (T05) solo cuando el material tiene los parámetros
  de resistencia que pide, y SI no los tiene, ENTONCES dice que no está disponible (duda 4).
- RF-9: EL SISTEMA declara el convenio de signos de cada magnitud que entrega; la conversión de
  tracción positiva a compresión positiva ocurre en un único sitio (regla 10; duda 1).

**De los puntos a los nudos**

- RF-10: EL SISTEMA recupera valores en los nudos para dibujar contornos (Zienkiewicz y Taylor 2000,
  §14.2, por comprobar), sin tocar los de los puntos de integración; cada valor dice de dónde sale.
- RF-11: EL SISTEMA no usa los elementos inactivos de una fase, y un nudo retirado no tiene valor.
- RF-12: CUANDO un nudo está en el contacto de dos materiales, EL SISTEMA trata el salto según la
  duda 5, y lo dice.

**Consultas**

- RF-13: EL SISTEMA consulta una magnitud a lo largo de una línea o polilínea, con su distancia, en
  los puntos que se pidan; SI un punto cae fuera del dominio activo, ENTONCES lo dice y no inventa un
  valor.
- RF-14: EL SISTEMA consulta sobre el contorno de una excavación, o a una distancia dada dentro o
  fuera de él (como lo observado en la referencia, carpeta A, `interpret/00_arbol_menus_interpret.md`).
- RF-15: EL SISTEMA da el valor en todos los nudos y exporta cualquier consulta a una tabla con sus
  columnas, unidades y convenio declarados.
- RF-16: EL SISTEMA da la evolución por fase de una magnitud en un punto o a lo largo de una
  consulta, y un resumen por fase (máximos y reacciones totales).

## Validación numérica

| Caso | Fuente científica (por comprobar) | Qué se compararía |
|---|---|---|
| `validacion/casos/005-kirsch-malla-general` (ficha `VER-STR-01`) | Kirsch (1898), en Jaeger, Cook y Zimmerman (2007), §8.4, ecs. (8.90)–(8.92) | σr, σθ y ur a lo largo de un radio desde r = a: la consulta por línea que pide la ficha (`POST-LINEA`), en puntos y en nudos por separado, con tolerancias fijadas antes de medir |
| `validacion/casos/004-carga-en-faja-elastica` (ficha `VER-STR-04`), o el que la sustituya (spec 004, duda 5) | Michell (1902), en Timoshenko y Goodier (1951), §34, ec. (f) | σ1 y σ3 bajo el centro de la faja, de 0.25 a 5 m, por la consulta; en los puntos, ya validados en la spec 002 |
| `validacion/casos/003-cavidad-esferica-elastica` (ficha `VER-STR-09`), o su sucesor | Lamé (1852), en Timoshenko y Goodier (1951), §121, ecs. (197)–(198) | σR, σt y ur a lo largo de un radio. Con la esfera fija a 21 m, la diferencia con el medio infinito crece como R³ (0.5 % hacia R = 3.6 m, spec 002): llegar a 5 m pide otro contorno, y otro caso |
| Identidades de las magnitudes | — (propiedades exactas) | Las principales y los invariantes no cambian al girar los ejes; von Mises y la diferencial son nulas en un estado hidrostático; la suma de las principales en el plano es la de las cartesianas |
| Deformaciones | Zienkiewicz y Taylor (2000), cap. 2 (spec 002) | Un desplazamiento lineal impuesto (prueba de la parcela) da la deformación exacta en todo punto |
| Recuperación a nudos | Zienkiewicz y Taylor (2000), §14.2, por comprobar | Un campo que los elementos representan exacto se recupera exacto en los nudos |
| Ida y vuelta del `.h5` | — (identidad) | Escribir y leer da los mismos números bit a bit; una mutación del modelo los marca obsoletos |

Las tablas de errores de las fichas son del programa de referencia: no son valor esperado. La de
`VER-STR-01` (tabla 1.2) no dice si sus errores son absolutos o relativos.

## Fuentes por conseguir

- **Definiciones de las magnitudes**: principales e invariantes, en Jaeger, Cook y Zimmerman (2007),
  cap. 2, por comprobar; deformaciones, Davis y Selvadurai, que el catálogo teórico (T01) fecha en
  2002 y en otro punto (T07a) en 2005, por conseguir.
- **Factor de resistencia**: el catálogo (T00 y T05) no le da ninguna fuente científica; el manual
  del programa de referencia no lo es. Hace falta una forma publicada del criterio en invariantes.
- **Recuperación de tensiones**: Zienkiewicz y Taylor (2000), §14.2 (está en la bibliografía; el
  apartado no se ha leído).

## Requisitos no funcionales

- Sin Qt (separación cálculo ↔ presentación, `tech-stack.md`).
- Formato del `.h5` documentado campo a campo, para leerlo con otras herramientas.
- Tamaño medido en el caso 005 (28 066 elementos); la compresión, decidida (ADR-0003).
- Sin dependencias nuevas: `h5py` ya llega con el núcleo; usarlo directamente se pregunta.

## Casos límite

- Fase que no cambia nada (`solved` falso), que no converge, o cálculo cancelado a mitad.
- Nudo sobre el eje en axisimetría; nudo retirado; elemento inactivo.
- Punto de consulta en un contorno entre dos elementos o dos materiales, dentro de una excavación o
  fuera del modelo.
- `.h5` sin `.ogr`; `.ogr` renombrado o movido; `.h5` de otra versión del programa.
- Magnitud sin sentido en el modelo (factor de resistencia de un material sin resistencia).

## Fuera de alcance

- El dibujo, la leyenda y los menús de interpretación (006).
- Resultados de SSR, agua, soportes y juntas; plastificación como resultado propio (fase 2).
- Datos de usuario por expresión, juntas ubicuas, líneas de flujo de tensiones, isolíneas,
  animación; informes en PDF.

## Criterios de finalización

- [ ] Dudas convertidas en decisiones y aprobadas por la propietaria
- [ ] Todos los RF con su test en verde
- [ ] Cada magnitud con su definición comprobada contra su fuente y citada en el código
- [ ] La consulta por línea de los casos de la fase, dentro de la tolerancia fijada antes de medir
- [ ] Las identidades de la tabla, en verde y con dientes
- [ ] Formato del `.h5` documentado; lo pedido a OGR-Core, etiquetado y fijado
- [ ] Changelog con lo encontrado; fichas con su «Seguimiento» (`POST-LINEA`)

## Dudas abiertas

- [NECESITA ACLARACIÓN] **1. Convenio de lo que entrega esta capa** (S06, duda 14): tracción positiva,
  como el motor, y la conversión en la 006; o compresión positiva ya aquí, para que la línea de
  órdenes y un agente vean lo mismo que la interfaz. Igual con las deformaciones (en la referencia,
  positivas en acortamiento).
- [NECESITA ACLARACIÓN] **2. σ1 y σ3: en el plano o en 3D.** En la referencia son las del plano (σ1
  puede ser la intermedia si σz es mayor), y la diferencial es la de 3D. ¿Igual, o principales 3D
  con σz? El nombre tiene que decirlo.
- [NECESITA ACLARACIÓN] **3. Deformación de corte máxima**: la documentación de la referencia es
  ambigua entre la ingenieril y su mitad (carpeta B, `compute_interpret/I02`, §2.1). Lo decide la
  fuente.
- [NECESITA ACLARACIÓN] **4. Factor de resistencia** (plan: T05): necesita parámetros de resistencia
  en un material que en la fase 1 es elástico, y no tiene fuente leída. Opciones: (a) aquí, con
  Mohr-Coulomb y su fuente; (b) a la spec 008, con las leyes.
- [NECESITA ACLARACIÓN] **5. Método de paso a nudos**: promedio de los elementos que comparten el
  nudo, recuperación por parches (§14.2) o por material. La referencia promedia sin separar
  materiales (carpeta B, `I02`, §7), y en P12 su media nodal de T3 dio en la pared de la cavidad
  σrr = 0.69 MPa en vez de 0.
- [NECESITA ACLARACIÓN] **6. Qué se guarda y con qué compresión** (ADR-0003): deformaciones guardadas
  o derivadas al leer; la malla en el `.h5`, o solo su huella si la guarda el `.ogr` (spec 004,
  duda 4).
- [NECESITA ACLARACIÓN] **7. Versiones y resultados parciales**: ¿un `.h5` de otra versión del motor
  o del núcleo es obsoleto, o solo si cambia el modelo? Con una fase que no converge o un cálculo
  cancelado, ¿se guardan las fases anteriores, marcadas, o nada?
- [NECESITA ACLARACIÓN] **8. Dónde vive el escritor**: un escritor HDF5 genérico en el núcleo
  (petición a OGR-Core, junto al de Slip2D) y la disposición FEM aquí, o todo aquí.
- [NECESITA ACLARACIÓN] **9. La consulta dentro de un elemento**: interpolar desde los nudos
  recuperados o desde los puntos de integración; y el formato de la tabla exportada (en la
  referencia, texto con identificador, x, y, distancia y valor).
- [NECESITA ACLARACIÓN] **10. Tolerancias de `POST-LINEA`**, fijadas antes de medir, para puntos y
  para nudos (que en zonas de gradiente fuerte se apartan más).
