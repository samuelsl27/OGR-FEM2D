# Spec 005 — Resultados (`.h5`) y su interpretación sin interfaz

> **Cerrada (2026-11-24)**: criterios de finalización cumplidos (changelog v0.0.11, T18).
> **Aprobada (2026-11-24)**, con D1–D16 tal como se propusieron. Fase 1 del plan de desarrollo
> (`spec/constitution/plan_de_desarrollo.md`, «Spec 005 — Resultados (`.h5`) y su interpretación
> sin interfaz»). Solo el **qué** y el **porqué**; el cómo, en `plan.md`. Versión: **v0.0.11**.
> Las dudas del borrador son ahora las decisiones D1–D16 (abajo).

## La revisión (2026-11-24)

- [x] Contrastada con el código y con la spec 004, cerrada el 2026-11-23:
  - `engine/analysis.py`, `StageOutcome`: por fase da los desplazamientos (totales), las tensiones
    por punto (`None` en los elementos inactivos), las reacciones por nudo, el estado plástico, los
    nudos del eje sujetos, `solved`, la historia de convergencia, los escalones, la tolerancia, los
    cortes, los elementos activos y los nudos retirados. **No da deformaciones**, pero salen
    exactas de los desplazamientos con la B del motor (`solver.IntegrationPoint.strain`).
  - **`analysis.run` pierde las fases ya resueltas si una falla**: devuelve la lista al final, y
    una excepción en la fase k se lleva las k − 1 anteriores. Guardar resultados parciales (D7)
    pide un cambio pequeño en el motor, en Python.
  - El T6 en deformación plana integra en los **tres puntos medios de los lados** (spec 002, D1):
    los puntos están sobre los lados, también sobre los contornos y sobre el arco del hueco. En
    axisimetría, la regla de 7 puntos interiores.
  - El modelo ya guarda la malla entera (spec 004, D3) y su huella la incluye
    (`fingerprint.model_fingerprint`). Ya existen `translate.deciding_values` (lo que decide el
    resultado, regla 12), `initial_stress.integration_point_coordinates` y
    `reference/loads.local_coordinates` (invierte la transformación isoparamétrica: sirve para
    situar un punto en un T6 curvo).
  - El archivo es el `.ogrfem2d` (ADR-0004), no el `.ogr` que dice el borrador.
- [x] Mirados el núcleo en la etiqueta fijada (v0.2.7; su `main` solo cambia la versión) y Slip2D:
  - `ogr_core/project/results_io.py` es de equilibrio límite de punta a punta: escribe un
    `SearchResult` (superficies y dovelas) y lee su resumen. No guarda huella. Lo genérico que
    tiene es usar `h5py` con gzip, y eso no es una pieza que reutilizar.
  - La escritura segura (a un temporal, y después `os.replace`) está en Slip2D,
    `ogr_gui/background.py`, no en el núcleo.
  - `ogr_core.fem.mesh.Mesh` sitúa puntos, pero solo en T3 de lados rectos.
  - `ogr_gui/contours.py` (paletas, niveles, rango automático) y `ogr_api/results.py` (resúmenes
    para un agente) son del dibujo y de las operaciones: de la 006.
  - `h5py` 3.16 está en el `.venv` porque lo pide `ogr-core` (≥ 3.10), pero este programa no lo
    declara.
- [x] Mirado cómo lo hace la referencia (`I02` §2, §3 y §7; `I03` §1–§8; `00_arbol_menus_interpret`;
  P11 y P12):
  - presenta las tensiones en compresión positiva y guarda tracción positiva;
  - sus σ1 y σ3 son las del plano, y la diferencial es la 3D;
  - **promedia en los nudos sin separar materiales**: en P12 la pared de la cavidad dio
    σrr = 0.69 MPa en vez de 0;
  - las consultas interpolan de verdad, no toman el nudo más cercano; exportan
    `Material_Query_ID · Point_x · Point_y · Distance · Value`;
  - la consulta de la excavación tiene «dentro / fuera» a 0.1 m por defecto.
- [x] Fuentes leídas (detalle en `plan.md`, «Formulación»):
  - **Zienkiewicz y Taylor (2000)**: el §14.2 que cita el borrador es el de los puntos de muestreo
    óptimos. La recuperación es el **§14.3** (pág. 376: el promedio en los nudos «no es lo mejor
    para triángulos» y es «inadecuado» con elementos de orden alto) y el **§14.4**, la
    recuperación por parches (SPR): ecs. (14.27)–(14.31), figs. 14.8–14.10, págs. 375–380.
  - **Jaeger, Cook y Zimmerman (2007)**, cap. 2, dan las tensiones principales, los invariantes,
    la media, J2, las deformaciones, las principales de deformación y la volumétrica. No hace falta
    Davis y Selvadurai. Su convenio es compresión y acortamiento positivos.
  - **de Souza Neto, Perić y Owen (2008)** dan la tensión de von Mises, ec. (6.111). También dan
    **Mohr-Coulomb en invariantes**, ec. (6.119), que es la forma publicada que el borrador echaba
    en falta para el factor de resistencia (D4).
  - Tres erratas posibles en el texto extraído de JCZ, (2.149), (2.162) y (2.195), se comprueban
    sobre la página antes de programar (T1).
- [x] Fichas STR-01, STR-04 y STR-09 releídas con su «Seguimiento»: las tres piden `POST-LINEA`. La
  de STR-09 ya avisa de que, con la esfera fija a 21 m, la línea hasta 5 m se aparta de la solución
  del medio infinito; aquí se compara con la de la esfera finita (D10).
- [x] Dudas convertidas en decisiones (D1–D16), aprobadas el 2026-11-24.

## Depende de

- Spec 002: lo que devuelve el motor por fase, la B de cada punto y la regla de cada elemento (D1).
- Spec 003: la malla, sus lados y el mapa segmento → nudos y lados.
- Spec 004: el modelo, su malla, su huella, `deciding_values` y el único cambio de signo
  (`model/conventions.py`, D6).
- ADR-0003: resultados en `modelo.h5`, aparte y con la huella.

## Contexto y objetivo

El motor devuelve sus resultados en memoria y nadie los guarda; los tests los comparan a mano, en
los puntos de integración. Esta spec hace dos cosas.

La primera es guardar cada cálculo en `modelo.h5`, junto al `.ogrfem2d` y con su huella. Así abrir
un modelo no obliga a recalcular, y unos resultados nunca se toman por los de otro modelo.

La segunda, sin Qt, es dar lo que se interpreta:

- las magnitudes de campo, cada una con su definición, su fuente y su convenio;
- los valores en los nudos para dibujar, sin perder los de los puntos, que son los que se validan;
- las consultas por línea, por contorno y en todos los nudos, con su evolución por fase.

Lo usan igual la interfaz (006), la línea de órdenes, un agente, un informe y un test.

## Usuarios / actores

- **El ingeniero**, que abre unos resultados, los consulta y los exporta.
- **La interfaz, las operaciones, la línea de órdenes y el servidor MCP** (006).
- **El investigador**, que lee el `.h5` con sus herramientas.
- **Los tests y los casos**, que comparan con soluciones cerradas.

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

- RF-1: CUANDO termina un cálculo, EL SISTEMA escribe `modelo.h5` junto al `.ogrfem2d`, con la misma
  raíz (D13). El archivo lleva:
  - la huella del modelo;
  - las versiones del formato, del programa y del núcleo, y la variante del motor;
  - lo que decidió el resultado (`deciding_values`, regla 12);
  - una copia de la malla con las coordenadas de los puntos de integración (D6);
  - por fase, todo lo que devuelve el motor y las deformaciones en los puntos (D6).
- RF-2: EL SISTEMA escribe el archivo de forma que un corte a mitad de la escritura deje el `.h5`
  anterior intacto. Un cálculo que falla o se cancela entre fases deja un `.h5` que **dice** que está
  incompleto, con las fases resueltas, la que no se resolvió y por qué (D7).
- RF-3: CUANDO se abren unos resultados, EL SISTEMA dice su estado:
  - válidos;
  - **obsoletos**, porque la huella no es la del modelo, y entonces no los presenta como válidos;
  - incompletos o cancelados;
  - sin resultados, y entonces ofrece calcular (ADR-0003);
  - o sin modelo con el que comprobarlos.

  Que los escribiera otra versión del programa o del núcleo no los hace obsoletos, pero se dice
  (D7).
- RF-4: SI el `.h5` está dañado, le falta algo o es de una versión de formato posterior, ENTONCES EL
  SISTEMA da un error que lo nombra y no lee nada a medias. EL SISTEMA lee una fase o una magnitud
  sola, sin leer el resto.

**Magnitudes de campo**

- RF-5: EL SISTEMA da, por fase y en los puntos de integración, las magnitudes de D2 y D3:
  - las tensiones cartesianas y la de fuera del plano;
  - las principales en el plano y su orientación;
  - las tres principales ordenadas;
  - la media, la de von Mises y la diferencial;
  - los desplazamientos horizontal, vertical y total;
  - las deformaciones cartesianas, la volumétrica y la de corte máxima.

  Cada una lleva su definición escrita y su fuente, y su unidad (tensión, longitud o
  adimensional).
- RF-6: EN axisimetría, EL SISTEMA nombra cada magnitud por su sentido (radial, axial,
  circunferencial). La tensión y la deformación fuera del plano son las circunferenciales
  (spec 002).
- RF-7: EL SISTEMA entrega las magnitudes en el convenio del usuario: tensiones en compresión
  positiva, deformaciones en acortamiento positivo, desplazamientos según +x y +y. El `.h5` guarda
  el del motor. Cada magnitud declara su convenio, y la conversión ocurre en un único sitio, el de
  la spec 004 (D1, regla 10).

**De los puntos a los nudos**

- RF-8: EL SISTEMA recupera las tensiones y las deformaciones en los nudos por parches (SPR,
  Zienkiewicz y Taylor 2000, §14.4) **material a material**, sin tocar los valores en los puntos.
  Un nudo en el contacto de dos materiales tiene un valor por material. Cada valor dice de dónde
  sale: punto de integración, nudo recuperado con su método, o campo de los elementos
  (desplazamientos) (D5).
- RF-9: EL SISTEMA no usa los elementos inactivos de una fase; un nudo retirado no tiene valor de
  tensión ni de deformación.

**Consultas**

- RF-10: EL SISTEMA sitúa un punto en el elemento activo que lo contiene, también junto a un arco;
  SI el punto cae en una excavación o fuera del modelo, ENTONCES lo dice y no inventa un valor (D11).
- RF-11: EL SISTEMA consulta una magnitud a lo largo de una línea o una polilínea, en N puntos
  repartidos a lo largo de toda ella o en sus vértices, con la distancia acumulada desde el primero.
  Dentro de un elemento interpola los desplazamientos con sus funciones de forma, y las tensiones y
  las deformaciones con los valores recuperados (Z&T, ec. 14.27). Donde la línea cruza un contacto
  entre materiales da el valor de cada lado (D9).
- RF-12: EL SISTEMA consulta sobre un contorno del modelo, o a una distancia dada de él hacia un
  lado, sobre la geometría (con sus arcos) y no sobre la malla. Con distancia 0, sobre el contorno
  (D12).
- RF-13: EL SISTEMA da el valor en todos los nudos (un valor por material en los nudos de un
  contacto) y en todos los puntos de integración, con sus coordenadas.
- RF-14: EL SISTEMA exporta cualquier consulta a una tabla CSV. La tabla declara la magnitud, la
  unidad del sistema que se muestra, el convenio, la fase, el método y la huella, y lleva una fila
  por punto: identificador, x, y, distancia, valor, elemento, material y procedencia (D15).
- RF-15: EL SISTEMA da la evolución por fase de una magnitud en un punto o a lo largo de una
  consulta, y un resumen por fase (D14):
  - los extremos de cada magnitud, dónde se dan y si son de un punto o de un nudo;
  - las reacciones totales y por contorno del modelo.

## Validación numérica

| Caso | Fuente científica | Qué se compara |
|---|---|---|
| `validacion/casos/005-kirsch-malla-general` (ficha `VER-STR-01`) | Kirsch (1898), en Jaeger, Cook y Zimmerman (2007), §8.4, ecs. (8.90)–(8.92), como el caso | σr, σθ y ur por la **consulta por línea** a lo largo de un radio, de r = a a 5a; σθ por la **consulta sobre el contorno** del hueco. Tolerancias de D10, escritas antes de medir |
| `validacion/casos/006-carga-en-faja-malla-general` (ficha `VER-STR-04`) | Michell (1902), en Timoshenko y Goodier (1951), §34, ec. (f), como el caso | σ1 y σ3 por la consulta por línea en x = 0 (un contorno del modelo), de z = 0.25 a 5 m, con la tolerancia del caso |
| `validacion/casos/007-cavidad-esferica-malla-general` (ficha `VER-STR-09`) | Lamé (1852), en Timoshenko y Goodier (1951), §121, ecs. (197)–(198): la esfera hueca con u(b) = 0, que es el modelo (comprobaciones de la spec 002, `sphere_fixed_outer`) | σR, σt y uR por la consulta por línea a 45°, de R = a a 5 m; σt sobre el contorno de la cavidad. Tolerancias de D10 |
| Invariantes | — (propiedades exactas; JCZ ecs. 2.137–2.146) | Las principales, la media, J2, von Mises y la diferencial no cambian al girar los ejes; von Mises y la diferencial son nulas en un estado hidrostático; σ1 + σ3 = σxx + σyy; z es dirección principal |
| Convenio | Regla 10; spec 001, D1 | Una compresión uniaxial da σ1 > 0 y un acortamiento positivo; el `.h5` guarda el signo del motor; la conversión está en un solo sitio |
| Deformaciones | Zienkiewicz y Taylor (2000), cap. 2 (spec 002); JCZ ecs. (2.181)–(2.186) | Un desplazamiento lineal impuesto (prueba de la parcela) da la deformación exacta en todo punto, en deformación plana y en axisimetría |
| Recuperación | Zienkiewicz y Taylor (2000), §14.4, págs. 377–379 | Un campo que la malla representa exacto se recupera exacto en todos los nudos, contornos incluidos: la tensión gravitatoria (lineal) con T6, y un campo constante con T3. Con dos materiales de distinto peso, exacto a cada lado del contacto; mezclándolos, no |
| Equilibrio | — (identidad; spec 002, RF-5) | Las reacciones por contorno suman la total, y la total equilibra las cargas y el peso de la fase |
| Ida y vuelta del `.h5` | — (identidad) | Escribir y leer da los mismos números bit a bit; mutar el modelo marca los resultados obsoletos; un `.h5` dañado, incompleto o de un formato posterior lo dice |
| Unidades | — (homogeneidad) | La tabla exportada en MPa es la de kPa entre 1000 |
| Regla 7 | — | Cada opción de consulta y de exportación, con el test que demuestra que mueve el número |

Las tablas de errores de las fichas son del programa de referencia y no son valor esperado. La de
`VER-STR-01` (tabla 1.2) no dice si sus errores son absolutos o relativos.

## Fuentes por conseguir

- Ninguna imprescindible. Moan (1974), al que remite la fig. 14.6 de Z&T para los puntos óptimos de
  los triángulos, no está en la bibliografía: se lee lo que dice la figura (T1) y basta.
- La forma del factor de resistencia (el cociente) no tiene fuente leída: va a la 008 con
  Mohr-Coulomb (D4).

## Requisitos no funcionales

- Sin Qt: todo se usa desde scripts, tests, la línea de órdenes y el servidor MCP.
- El formato del `.h5` está documentado campo a campo (`docs/resultados/formato.md`), para leerlo
  con otras herramientas sin este programa.
- El tamaño y el tiempo de escritura y de recuperación, medidos en el caso 005 (28 066 T6); la
  compresión, decidida con esa medida (D6).
- `h5py` se usa directamente y se declara en `pyproject.toml`. Ya está en el `.venv`, que lo trae el
  núcleo; BSD-3, compatible con AGPL-3.0. No se instala nada (D8).
- Los nombres de las magnitudes y los mensajes llevan una clave traducible para la interfaz
  (regla 2). Las columnas de la tabla son identificadores fijos, no texto traducido (D15).

## Casos límite

- Una fase que no cambia nada (`solved` falso), que no converge, o un cálculo cancelado entre fases.
- Un nudo sobre el eje en axisimetría; un nudo retirado; un elemento inactivo.
- Un material con pocos elementos, sin ningún nudo interior que dé un parche (D5).
- Un punto de consulta sobre un lado entre dos elementos del mismo material, sobre un contacto entre
  dos materiales, entre la cuerda y el arco de un lado curvo, dentro de una excavación o fuera del
  modelo.
- Un `.h5` sin `.ogrfem2d`; un `.ogrfem2d` renombrado o movido sin su `.h5`; un `.h5` de otra
  versión del programa o de un formato posterior; un `.h5` abierto por otro programa al
  sobrescribirlo.
- Una consulta sobre un contorno con un vértice cóncavo, con distancia que la saca del modelo.

## Fuera de alcance

- El dibujo: contornos, leyenda, paletas, deformada, vectores, valor absoluto como opción de
  dibujo, menús de interpretación (006).
- El factor de resistencia (008, D4). Resultados de SSR, agua, soportes y juntas; la plastificación
  como resultado propio (fase 2). El estado plástico se guarda, pero no se interpreta aquí.
- Datos de usuario por expresión, juntas ubicuas, líneas de flujo de tensiones, isolíneas,
  animación, fase de referencia (diferencias entre fases), informes en PDF.
- Las tensiones normal y tangencial sobre la línea de una consulta (`I03` §7): 006, si las pide.

## Criterios de finalización

- [x] D1–D16 aprobadas por la propietaria y anotadas aquí (2026-11-24)
- [x] `plan_de_desarrollo.md` y ADR-0003 corregidos donde dicen que se parte de `results_io.py` y
      citan el §14.2 (T0)
- [x] Todos los RF con su test en verde, y la regla 7 en cada opción nueva
- [x] Cada magnitud con su definición comprobada contra su fuente y citada en el código
- [x] Las consultas de los casos 005, 006 y 007 dentro de la tolerancia fijada antes de medir
- [x] Las identidades de la tabla, en verde y con dientes
- [x] Los casos 001 a 007 dan lo mismo bit a bit (el motor solo cambia en cómo entrega las fases, D7)
- [x] `docs/resultados/formato.md` completo; tamaño y tiempos del caso 005 en el changelog
- [x] Changelog con lo encontrado; fichas STR-01, STR-04 y STR-09 con su «Seguimiento» (`POST-LINEA`)

## Decisiones (2026-11-24)

Aprobadas el 2026-11-24, tal como se propusieron. Las referencias I02, I03, P11 y P12 son del análisis de interfaz
(`../Referencias/Doc_Guia/Analisis_interfaz_funcionamiento/`). JCZ es Jaeger, Cook y Zimmerman
(2007); Z&T, Zienkiewicz y Taylor (2000); dSN, de Souza Neto, Perić y Owen (2008).

| # | Duda del borrador | Decisión propuesta | Por qué |
|---|---|---|---|
| D1 | 1: convenio de lo que entrega esta capa | **Esta capa entrega el convenio del usuario**: tensiones en compresión positiva, deformaciones en acortamiento positivo (JCZ ecs. 2.169 y 2.231) y desplazamientos según +x y +y (spec 004, D6; no el x* = x − u de JCZ, ec. 2.168). **El `.h5` guarda lo que da el motor**, en tracción positiva, y lo dice en sus atributos. La conversión de salida se añade a `model/conventions.py`, junto a la de entrada | Con la conversión aquí, la interfaz, la línea de órdenes, un agente y un test ven el mismo número, como pide la regla 10 («en un único sitio»). En el `.h5`, el número del motor sin tocar: el investigador lo lee tal cual, y la ida y vuelta es bit a bit |
| D2 | 2: σ1 y σ3, en el plano o en 3D | **Las dos, con nombres que lo dicen.** `sigma_1` y `sigma_3` son las principales **en el plano** (JCZ ecs. 2.37–2.38), con `theta_1`, el ángulo de σ1 desde +x en sentido antihorario (ecs. 2.33 y 2.41–2.44). `sigma_z` es la de fuera del plano, que también es principal. `sigma_I` ≥ `sigma_II` ≥ `sigma_III` son las tres ordenadas. La media es p = I1/3 (JCZ ec. 2.153); la de von Mises, q = √(3 J2) (dSN ec. 6.111, con J2 de JCZ ec. 2.163); la diferencial, σI − σIII (JCZ cap. 6, pág. 151) | Las del plano son las que comparan las fichas (Michell da σ1 y σ3 en el plano) y las que muestra la referencia. Las 3D son las que entran en la media, von Mises y la diferencial. Con el nombre, una σ1 que es la intermedia (σz mayor) no engaña a nadie |
| D3 | 3: deformación de corte máxima | **La ingenieril en el plano**: `gamma_max` = ε1 − ε3, con las principales de deformación en el plano (JCZ ec. 2.195). El nombre y la definición dicen que es el doble de la tensorial, que es la que JCZ prefiere (pág. 46: γ = 2ε) | Es la que se usa en geotecnia y la que muestra la referencia (`I02` §7: «los cortantes que muestra son ingenieriles»). La duda del factor 1/2 la resuelve la definición escrita, no la fuente: las dos están en JCZ |
| D4 | 4: factor de resistencia | **A la spec 008**, con las leyes. Su borrador ya lo pide (T05), y allí el material tiene c y φ. dSN, ec. (6.119), da Mohr-Coulomb en invariantes (tracción positiva, según Owen y Hinton 1980). El cociente que define el factor es una definición sin fuente leída, y se decide allí | En la fase 1 el material es elástico: añadir c y φ solo para un resultado adelantaría la 008 a medias. La forma en invariantes ya está localizada, y la 008 no empieza de cero |
| D5 | 5: el paso a los nudos | **Recuperación por parches (SPR), material a material** (Z&T §14.4, ecs. 14.28–14.31). En cada nudo de esquina interior del material, un polinomio del grado de los desplazamientos (1 en T3, 2 en T6) se ajusta por mínimos cuadrados a los valores de los puntos de integración del parche. Cada parche determina su nudo y, en T6, los intermedios de los lados que salen de él (fig. 14.8, precisado en la T7); un nudo que determinan varios toma la media (pág. 379). Los nudos del borde del material (contornos, excavación, contactos) toman los valores de los parches interiores vecinos (fig. 14.9). Un nudo intermedio del T6, los de los parches de las esquinas de su lado. **Sin parche posible** (un material de un elemento de espesor), el campo del propio elemento extrapolado, y el valor lo dice. **Sin promedio simple** | Z&T §14.3, pág. 376: el promedio es inadecuado en triángulos y en orden alto. En P12, la referencia promediaba y daba σrr = 0.69 MPa en la pared, donde vale 0. Por material, porque las tensiones tangenciales y las principales saltan en un contacto (`I02` §7; Z&T fig. 14.9: «on interfaces where stresses are discontinuous»). La salida de los parches que faltan es **propuesta propia**: Z&T no trata el caso |
| D6 | 6: qué se guarda y con qué compresión | **En el `.h5` va lo que dio el motor y lo que se sigue de ello sin elegir nada**: por fase, desplazamientos, tensiones, deformaciones (B u, con la B del motor), estado plástico, elementos activos, nudos retirados y del eje, reacciones, historia y ajustes. **Va también una copia de la malla** con las coordenadas de los puntos, aunque el `.ogrfem2d` ya la tiene; la huella garantiza que es la misma. **No van los valores recuperados**, que dependen de un método y se calculan al leer. *Modificada el 2026-11-27 por la propietaria (spec 006, T36): una fase **puede** llevar los valores recuperados, escritos al calcular y marcados con su método y su versión (`recovery.METHOD`); un lector solo los usa si la marca es la de su método, y si no los recupera otra vez. Se cumple el motivo de esta decisión (un método mejor se ve en los resultados viejos), y el primer dibujo de una fase deja de esperar a la recuperación (spec 006, D15: 1.3 s con el caso 005, 0.6 s ahora). El `.h5` del caso 005 pasa de 6.1 a 8.9 MB.* Compresión gzip, la de HDF5 que cualquier lector abre, con el nivel fijado midiendo el caso 005 | Las deformaciones guardadas son las que pide el ADR-0003, y el investigador las lee sin reconstruir la B. La copia de la malla deja el `.h5` completo por sí mismo, por H6 y por el investigador, por unos MB en el caso 005 (se mide). Lo que depende de un método no se congela en el archivo: si el método mejora, los resultados viejos se ven con el nuevo |
| D7 | 7: versiones y resultados parciales | **Solo la huella del modelo hace obsoletos unos resultados.** Las versiones del programa, del núcleo y del formato y la variante del motor se guardan y se muestran con el resultado (regla 12). Un formato posterior al que se conoce, error. **Si una fase falla o se cancela el cálculo, se guardan las fases resueltas**, con el estado `incomplete` o `cancelled`, la fase y el porqué. Para eso `analysis.py` entrega las fases una a una (un generador; `run` sigue igual, bit a bit) | Obsoleto por versión obligaría a recalcular horas en cada actualización, y un cambio de número entre versiones lo vigilan los casos, no el `.h5`. Las fases resueltas de un cálculo largo valen, y el estado impide tomarlas por un cálculo completo. El cambio en el motor es de orquestación, en Python: no toca leyes, elementos ni `rust/` |
| D8 | 8: dónde vive el escritor | **Todo aquí**, en un paquete nuevo `ogr_fem2d/results/`, con `h5py` directamente, **declarado en `pyproject.toml`**. No se pide nada al núcleo | Lo que el núcleo tiene es de equilibrio límite, y lo genérico serían unas 20 líneas (atributos, gzip, escritura a un temporal). Si Slip2D quiere compartirlo algún día, se pide entonces con lo que haya en los dos. Un import directo de un paquete no declarado dependería de que el núcleo lo siga pidiendo |
| D9 | 9: el valor dentro de un elemento y la tabla | **Desplazamientos**: las funciones de forma del elemento (el campo de elementos finitos). **Tensiones y deformaciones**: los valores recuperados de D5, interpolados con las funciones de forma (Z&T ec. 14.27), que dentro de un material son continuos. **En un contacto entre materiales**, una fila por lado, con la misma distancia. Los valores en los puntos, aparte (RF-13), con sus coordenadas. Tabla: D15 | La consulta da un campo continuo y definido en todo punto, como la referencia, que interpola de verdad (`I03` §1). El salto en un contacto existe (`I02` §7), y dos filas lo enseñan en vez de esconderlo. Los puntos, que son lo que se valida, siguen al alcance |
| D10 | 10: tolerancias de `POST-LINEA` | **Antes de medir**, en `esperado.json`. **Tensiones**: error absoluto ≤ 0.01 de la tensión de campo (p0 o P0). En el 005 es el mismo 0.3 MPa que el 0.5 % del caso sobre σθ(a) = 2 p0, y vale también donde σr → 0. **Desplazamientos**: error absoluto ≤ 0.005 del de la pared, ur(a) o uR(a). **Caso 006**: la del caso, 0.01 q. **Caso 007**: contra la esfera de 21 m fija, que es el modelo, y no contra el medio infinito | Medir el error relativo al valor local no significa nada donde la tensión pasa por cero. Las de puntos, las de los casos, siguen igual. En el 007, la ficha y el caso 003 ya miden que el medio infinito se aparta un 0.5 % hacia R = 3.6 m: la comparación con la esfera finita no lleva ese error del contorno. **En el 006 el margen es pequeño**: el efecto del dominio ya es 0.0045 q, y en los puntos se midió 0.0053 q. Si no cumple, es un hallazgo y no se afloja |
| D11 | Nueva: situar un punto | **Aquí**: una rejilla de cajas de los elementos activos, ampliadas para que quepan los lados curvos, y la inversa isoparamétrica de `reference/loads.local_coordinates`. Un punto sobre un lado común a dos elementos del mismo material toma el de menor índice, y da igual cuál, porque el campo recuperado es continuo. Sobre un contacto, los dos (D9) | El localizador del núcleo es de T3 rectos: un punto entre la cuerda y el arco quedaría fuera. Con T6 curvos hace falta la transformación del elemento, que el motor ya tiene |
| D12 | Nueva: la consulta sobre un contorno | Sobre la geometría del modelo, con los arcos. Toma los vértices, o N puntos por segmento sobre el segmento o el arco. Con distancia d ≠ 0, cada punto se mueve d por la normal del contorno hacia el lado pedido; en un vértice, por la bisectriz de las dos normales. Lado: dentro o fuera en los cerrados, izquierda o derecha en los abiertos. **Distancia por defecto: 0**, sobre el contorno | Sobre la geometría, porque los puntos de un arco tienen que estar en el arco (`I03` §3). La regla del desplazamiento es **propia**, porque la referencia no la documenta. La distancia por defecto de la referencia (0.1 m) cambiaría el número sin pedirlo (regla 12) |
| D13 | Nueva: dónde y cómo se escribe | `results.calculate(modelo, ruta)` traduce, resuelve fase a fase y escribe `<raíz>.h5` junto a `<raíz>.ogrfem2d`. Escribe a `<raíz>.h5.tmp` y lo mueve con `os.replace` al terminar, también si el cálculo acaba incompleto. Un fallo de escritura borra el temporal y deja el `.h5` anterior | Es el patrón de Slip2D (`ogr_gui/background.py`). Un corte deja el `.h5` de antes, que su huella juzga |
| D14 | Nueva: el resumen por fase | Por magnitud, el máximo y el mínimo en los puntos y en los nudos, cada uno con dónde y de qué tipo. El desplazamiento total máximo, con su nudo. Las reacciones, totales y por contorno del modelo (con el mapa segmento → nudos de la 003) | Es lo que pide RF-15 y lo que la 006 enseña como resumen. Que las reacciones sean por contorno las hace legibles («el fondo soporta…») y da la identidad del equilibrio |
| D15 | Nueva: unidades y tabla | La capa entrega en las unidades guardadas (m, kN, kPa) y lo declara. **La tabla, en las del sistema que se muestra** (`ogr_core.units`, `to_user`). CSV en UTF-8, punto decimal, cabecera de comentarios (`#`) con magnitud, unidad, convenio, fase, método y huella. Columnas: `query_id, point, x, y, distance, value, element, material, source`. Las cinco primeras, como las de la referencia | La tabla la lee una persona en las unidades que ve; la API, un programa, que necesita un solo sistema. Identificadores fijos, porque una columna traducida rompería los scripts que la leen |
| D16 | Nueva: el catálogo | Cada magnitud es una entrada con id, clave traducible, unidad, convenio, nombre en axisimetría, si es de tensión, deformación o desplazamiento, su definición y su fuente. La 006 lo usa para el selector | Un sitio para cada definición y su fuente, como piden los criterios. La interfaz no inventa nombres |

### Consecuencias en el resto del proyecto

- ADR-0003, «Decisión»: dice que se parte de `ogr_core/project/results_io.py`; con D8, no. Se
  corrige en la T0, con el OK de la propietaria.
- `plan_de_desarrollo.md`, «Spec 005»: el §14.2, a §14.3–14.4; el factor de resistencia, a la 008;
  `results_io.py`, fuera. En la T0.
- El borrador de la 008 recibe el factor de resistencia con la forma de dSN (6.119) localizada (D4).
- La 006 recibe el catálogo (D16), los estados de RF-3, `calculate` (D13) para su subproceso, y el
  valor absoluto como opción de dibujo.

### Lo que se encontró al hacerla (changelog v0.0.11)

Reportado y resuelto durante las tareas, para revisar por la propietaria:

- **Tres erratas del libro en JCZ (T1)**: (2.149), (2.162) y (2.195), vistas sobre la página. Ninguna
  se usa tal cual.
- **Los puntos del T6 no son los óptimos de Z&T (T7)**: los tres medios de los lados son los de la
  cuadratura mínima (fig. 14.6). La recuperación se hace igual; la superconvergencia no está
  asegurada.
- **D5 precisada por la fig. 14.8 (T7)**: un parche determina su nudo central, los intermedios de sus
  radios y los nudos del borde del material que tiene; no todos los nudos que contiene.
- **Lo que no alcanza ningún parche (T8)** no es solo un material de un elemento de espesor: también
  un elemento con sus tres esquinas en el contorno (la esquina de un cuadrado). Toma la salida de D5.
- **Las tolerancias de los casos no distinguen los parches del promedio (T14–T16)**: con el campo
  propio de los elementos promediado, los tres casos también cumplen, y en la pared del 005 sale algo
  mejor. Lo que fija los parches son las identidades de la T8.
- **Las consultas no llevaban sus ajustes (T17)**: ahora sí (`Query.settings`), y la tabla los
  escribe (regla 12).
- **Un sistema de unidades desconocido** en la tabla es un error; el núcleo lo sustituiría en
  silencio (T12).
