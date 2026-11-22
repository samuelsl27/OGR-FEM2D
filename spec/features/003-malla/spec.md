# Spec 003 — Malla

> **Aprobada (2026-11-22)**, con D1–D13 tal como se propusieron y la enmienda de RF-5 (error
> propio, visto al escribir el plan). Segunda spec de la fase 1 del plan de desarrollo
> (`spec/constitution/plan_de_desarrollo.md`, «Spec 003 — Malla»). Solo el **qué** y el **porqué**;
> el cómo, en `plan.md`. Versión: **v0.0.8** (la v0.0.7 sube la fijación del núcleo, D1).

## Contexto y objetivo

El motor de la spec 002 resuelve cualquier malla de triángulos, pero nadie la genera: los casos usan
mallas estructuradas de prueba (`engine/mesh_structured.py`, `engine/mesh_radial.py`) hechas a
mano para cada geometría. Esta spec convierte una geometría (regiones de material, con huecos y con
arcos) en la entrada discreta del motor: nudos y elementos T3 o T6 con su material, y el mapa de qué
nudos y lados caen sobre cada contorno, que es lo que necesitará la spec 004 para poner cargas y
condiciones sobre la geometría y no sobre la malla.

Hace falta una malla **de calidad conocida**. El generador de `ogr_core.fem` (v0.2.2, igual en
0.2.3 y en `main`) solo hace T3 de tamaño uniforme, y su refinado no tiene fuente ni garantía. Un
sondeo del 2026-11-22 (fuera del repositorio) lo mide en la geometría de STR-01: un cuadrado de
20 m con un hueco circular de 40 lados da un ángulo mínimo de **4.9°** con h = 1 m y de 6.8° con
h = 2 m, frente a los 25° que el propio generador se pone de suelo. La causa es que discretiza los
contornos solo subdividiendo (las cuerdas del hueco, de 0.157 m, se quedan junto a elementos de
1–2 m) y no gradúa. El área, la conformidad y el respeto de los contornos salen bien en todos los
casos sondeados.

La fuente del mallado de calidad es el refinamiento de Delaunay de Ruppert (1995), en la
reformulación de Shewchuk (2002a): garantiza un ángulo mínimo, gradúa sola desde los rasgos
pequeños de la geometría y admite una cota de tamaño que depende de la posición. La calidad del
elemento se mide con las medidas de Shewchuk (2002b), derivadas del error de interpolación y del
condicionamiento; el elemento curvo, con el criterio del jacobiano de Zienkiewicz y Taylor (2000).

## Usuarios / actores

- **El modelo y la interfaz** (specs 004 y 006), que pasan la geometría y reciben la malla.
- **El motor** (spec 002), que la recibe ya convertida a su entrada (regla 11: no sabe de mallas).
- **OGR Slip2D**, a través del núcleo, si D2 lleva el generador a OGR-Core (lo usa su filtración).
- **El ingeniero**, que necesita saber qué malla ha calculado y si algún elemento es malo.

## Historias de usuario

- H1: Como ingeniero quiero mallar un modelo con excavaciones, capas y contornos curvos con un clic,
  con la malla fina junto a las excavaciones y gruesa lejos, para no dibujar la malla a mano.
- H2: Como ingeniero quiero ver los nudos de los contornos antes de mallar y cambiar el número de
  divisiones de un segmento, para controlar dónde está la malla fina.
- H3: Como ingeniero quiero densificar la malla en una ventana o un polígono (alrededor de un bulón,
  bajo una zapata) sin tocar el resto.
- H4: Como ingeniero quiero saber si la malla tiene elementos malos, cuáles y por qué criterio, y que
  el programa se niegue a calcular con un elemento degenerado.
- H5: Como ingeniero que verifica el programa quiero una malla radial reproducible alrededor de un
  hueco circular, para comparar con soluciones cerradas.

## Requisitos funcionales (EARS)

**Entrada y discretización (paso 1)**

- RF-1: EL SISTEMA recibe regiones de material (polígonos cerrados con huecos, cada una con su
  material; las excavaciones también son regiones y se mallan), los segmentos de sus contornos, cada
  uno con un **arco opcional** (centro y radio, D3), y los parámetros de mallado: tipo de malla
  (graduada, uniforme o radial), tipo de elemento (T3 o T6), tamaños y ventanas de densidad.
- RF-2: EL SISTEMA discretiza los contornos en un paso aparte, que devuelve los nudos de cada
  segmento antes de mallar; CUANDO se fija el número de divisiones de un segmento, ese segmento se
  divide así (D10). Un arco se discretiza con sus nudos sobre la circunferencia.
- RF-3: EL SISTEMA malla respetando cada nudo y cada segmento de la discretización: todo segmento es
  una unión de lados de la malla y ningún elemento cruza un contorno (Shewchuk 2002a, §1). SI el
  refinado tiene que añadir nudos sobre un segmento, ENTONCES el resultado dice cuántos y dónde
  (D10).

**Mallado (paso 2)**

- RF-4: EL SISTEMA genera la malla por refinamiento de Delaunay (Ruppert 1995; Shewchuk 2002a, §3)
  con una cota B del cociente circunradio / lado más corto; por defecto **B = √2**, con la que todo
  ángulo queda entre arcsin(1/2B) = 20.7° y 138.6° (Shewchuk 2002a, §2, pág. 5) cuando ningún ángulo
  entre segmentos de la entrada baja de 60° (teorema 4, pág. 16). La cota usada se muestra con la
  malla (regla 12).
- RF-5: **Malla graduada**: el tamaño lo fija la discretización de los contornos y crece lejos de
  ellos por la graduación propia del refinado (tamaño local de rasgo, Shewchuk 2002a, §3.2, pág. 11),
  con una cota de tamaño máximo opcional (D5). La garantía de graduación (teorema 8, pág. 23) exige
  **B > √2 estrictamente**: con el B = √2 por defecto no está garantizada y se **mide**; el test
  del teorema 8 se hace con B = 1.93. *Enmendado el 2026-11-22: decía que la graduación tenía fuente
  con el B por defecto, y no es así (`plan.md`, «Anomalías»).*
- RF-6: **Malla uniforme**: una cota de tamaño constante, dada directamente o a partir de un número
  aproximado de elementos (D5).
- RF-7: **Densificación por ventana o polígono**: una cota de tamaño menor dentro de la zona, que se
  suma a la global como cota que depende de la posición (Shewchuk 2002a, pág. 11), no insertando
  centroides (D9).
- RF-8: **Malla radial**: malla estructurada de un anillo completo alrededor de un único hueco
  circular, con el número de divisiones del hueco, el radio exterior y una progresión geométrica en
  el radio (D8).
- RF-9: CUANDO la entrada tiene ángulos entre segmentos menores de 60°, EL SISTEMA termina siempre
  (Shewchuk 2002a, §5: el refinado de Ruppert puede no terminar), y el resultado dice dónde quedan
  ángulos por debajo de la cota y por qué (D6).

**Elementos**

- RF-10: CON elementos T6, EL SISTEMA añade el nudo intermedio de cada lado: en el punto medio en
  los lados rectos y **sobre el arco** en los lados de un segmento con arco (lección de la spec 001).
  Un nudo intermedio es único por lado, compartido por los dos elementos.
- RF-11: EL SISTEMA da los nudos de cada elemento en sentido antihorario y numeración estable: la
  misma entrada da la misma malla, bit a bit (D11).

**Calidad y comprobaciones**

- RF-12: EL SISTEMA calcula para cada elemento sus ángulos mínimo y máximo y las medidas de calidad
  de Shewchuk (2002b, tabla 4, pág. 44) que se decidan en D7, y da un resumen de la malla (peor valor
  y distribución de cada medida).
- RF-13: SI un elemento es degenerado o está invertido (área nula o negativa; en el T6, jacobiano que
  no conserva el signo en el elemento, Zienkiewicz y Taylor 2000, §9.2, págs. 205–206), ENTONCES EL
  SISTEMA no entrega la malla y dice qué elemento y por qué.
- RF-14: EL SISTEMA comprueba que la malla es conexa y conforme (cada lado en uno o dos elementos;
  los de un solo elemento son exactamente los del contorno) y avisa de dos regiones unidas solo por
  un nudo.

**Salida**

- RF-15: EL SISTEMA devuelve, además de nudos y elementos, la región y el material de cada elemento,
  el mapa segmento → nudos y lados de la malla en orden, y las notas de la malla con cada valor por
  defecto que la ha decidido (B, cotas de tamaño, nudos añadidos en segmentos), listo para construir
  un `EngineModel` de la spec 002.

## Validación numérica

| Caso | Fuente científica | Qué se compara |
|---|---|---|
| `validacion/casos/005-kirsch-malla-general` (ficha `VER-STR-01`), deformación plana, T6 con los nudos del hueco sobre el arco, malla graduada (D12) | Kirsch (1898), en Jaeger, Cook y Zimmerman (2007), §8.4, ecs. (8.90)–(8.92), págs. 216–218, como el caso 001 | **σθ en todos los puntos de integración sobre r = a** y **ur en todos los nudos sobre r = a**, el peor de cada uno, con tolerancia **0.5 %** (D12). Contorno cuadrado de semilado L = 100 m, fijo |
| Identidad de Kirsch con el desplazamiento exacto en el contorno, la **misma malla** del caso 005 | Las mismas ecuaciones, con el desplazamiento que causa la excavación impuesto en el contorno exterior (derivación propia, en `comprobaciones/`) | Lo mismo, con la misma tolerancia, en el campo hidrostático y en uno con p2 = p1/2. Mide solo la discretización; la diferencia con el caso 005 (misma malla) es el efecto del contorno cuadrado |
| Malla radial | Solución exacta del anillo con el exterior fijo (`lame_fixed_outer`, spec 001) | σθ(a) y ur(a) en un anillo completo hasta b = 100 m, 0.5 % (D8) |
| Identidades de la malla | — (propiedades exactas) | Área: la suma de las áreas de los elementos es la de las regiones a redondeo; con T6 sobre arcos, la del polígono más la de cada segmento parabólico, 2/3 · cuerda · flecha (Arquímedes; ya usada en la spec 001). Conformidad y característica de Euler. Cada segmento es unión de lados. Cada nudo intermedio sobre su arco (\|x − c\| = R) o en el punto medio de su lado |
| Garantías del refinado | Shewchuk (2002a), §2 (pág. 5), §3.1 (pág. 11) y teorema 4 (pág. 16) | Con ángulos de entrada ≥ 60°: todo triángulo con circunradio / lado más corto ≤ B; toda cota de tamaño cumplida; la malla final es de Delaunay (círculos circunscritos vacíos, pág. 9) |
| Prueba de la parcela sobre mallas generadas | Zienkiewicz y Taylor (2000), cap. 9–10 (el apartado, por localizar en el plan) | Un campo de desplazamientos lineal se reproduce exacto con T3 y con T6 de lados curvos, en deformación plana y en axisimetría |
| Casos 001 a 004 | Los de las specs 001 y 002 | Los mismos números bit a bit: esta spec no toca el motor |

Datos de la ficha STR-01: a = 1 m, E = 10 000 MPa, ν = 0.2, campo hidrostático de 30 MPa de
compresión, excavación sin presión interior. Valores de control: σθ(a) = 60 MPa, ur(a) = 0.0036 m.

**Lo que hay que tener en cuenta:**

- El contorno de la ficha (circular a 21 m) no sirve contra Kirsch: aparta la solución exacta un
  0.60 % en ur(a) (spec 001, D3 bis). Con un cuadrado no hay solución cerrada del dominio finito; por
  eso la identidad con el desplazamiento exacto en el contorno se calcula sobre la misma malla.
- Las mallas de Delaunay no están anidadas: al refinar, el error puede no bajar de forma monótona.
  El estudio de convergencia se hace con el número de divisiones del hueco (16, 32, 64, 128), y si
  no baja en cada paso es un hallazgo que se reporta, no una malla que se elige a dedo.

## Requisitos no funcionales

- La referencia en Python se escribe para leerse. El mallado no pasa a Rust en esta spec (plan de
  desarrollo: solo si se mide que hace falta).
- Sin dependencias nuevas: el Delaunay de SciPy (Qhull, BSD). Ruppert parte de una triangulación de
  Delaunay sin restricciones y recupera los segmentos que faltan partiéndolos (Shewchuk 2002a, §3.1,
  pág. 7), y la malla final es de Delaunay (pág. 9): no hace falta un Delaunay restringido.
- Toda fórmula y todo criterio comprobado contra su fuente y citado en el código.
- Un tiempo de mallado razonable para los casos de la fase 1, medido; el objetivo se fija en el plan.

## Casos límite

- Ángulos entre segmentos de la entrada menores de 60° (pie de un talud, capa que se acuña): RF-9.
- Vértices muy próximos o segmentos casi paralelos (capas delgadas): elementos pequeños inevitables;
  el resumen de calidad los señala.
- Un arco con pocas divisiones: el nudo intermedio se aparta mucho de la cuerda; el jacobiano lo
  juzga (RF-13).
- Dos regiones que se tocan en un solo punto (RF-14).
- Una cota de tamaño muy pequeña frente al dominio: tope de elementos con error que lo dice, no un
  cálculo que no acaba.
- Axisimetría: el eje es un segmento de la entrada y sus nudos quedan con x = 0 exacto.
- Una región sin área, o segmentos que se cortan fuera de sus extremos: error de entrada (la
  geometría limpia es de `ogr_core.geometry`).

## Fuera de alcance

- Cuadriláteros (Q4, Q8) y mallado mapeado (plan de desarrollo, P2).
- Juntas con nudos duplicados (spec 015) y elementos infinitos (spec 016).
- Guardar la malla, la discretización personalizada y las ventanas en el `.ogr` (spec 004); la
  conectividad por fase con elementos excavados (spec 004, que conoce las fases).
- Malla radial alrededor de un hueco elíptico; refinamiento adaptativo por estimación de error
  (Zienkiewicz y Taylor 2000, cap. 15); suavizado y mallas anisótropas.
- La interfaz, los menús y las traducciones (spec 006).
- Mallado en Rust.

## Criterios de finalización

- [x] D1–D13 decididas por la propietaria y anotadas aquí (2026-11-22)
- [ ] Cada fórmula y criterio comprobado contra su fuente (tabla «Formulación» de `plan.md`) y
      citado en el código
- [ ] Caso 005 dentro de la tolerancia fijada antes de medir, con la malla y el estudio de
      convergencia que la justifican
- [ ] Las identidades de la tabla, en verde y con dientes
- [ ] Los casos 001 a 004 dan lo mismo bit a bit
- [ ] Lo que se pida a OGR-Core (D2), en una versión etiquetada y fijada aquí
- [ ] Changelog con lo encontrado; ficha STR-01 con su «Seguimiento»

## Decisiones de la propietaria (2026-11-22)

Aprobadas las trece tal como se propusieron; la columna «Propuesta» es la decisión. D6 y D7 se
concretaron al leer las fuentes para el plan (ver sus filas), y D13 salió del plan.

| # | Pregunta | Propuesta | Por qué |
|---|---|---|---|
| D1 | **Fijación del núcleo antes de empezar.** FEM2D fija `ogr-core` v0.2.2; la v0.2.3 está publicada y su subida pendiente (`Promts_desarrollo/2026_11_20_subir_a_ogr_core_0.2.3.md`) | Subirla primero, en una versión propia (v0.0.7), como la v0.0.3 y la v0.0.4; esta spec pasa a la v0.0.8 | Es compatible y no toca el cálculo (`ogr_core.fem` es igual), pero trae lo que la v0.0.5 dejó pendiente en el runner. Una subida de fijación va en un commit suyo, y mezclarla con la spec emborrona las dos |
| D2 | **Dónde vive cada pieza.** El generador del núcleo lo usa la filtración de Slip2D (24 archivos): cambiar su comportamiento movería sus números | (a) **Petición a OGR-Core**: una función nueva que malla un grafo de segmentos (PSLG) por refinamiento de Ruppert con cota B y cota de tamaño función de la posición, más las medidas de calidad de RF-12. `generate_mesh` no se toca, y Slip2D sigue bit a bit. (b) **En FEM2D**: la discretización (con arcos), las ventanas convertidas en cota de tamaño, el T6, el jacobiano, la malla radial y la conversión al motor | Es mallado genérico, que Slip2D también necesita (el 4.9° de arriba es su malla de filtración); copiarlo aquí sería la «copia que diverge» que el ADR-0002 descarta. Inconveniente: la spec espera a una versión del núcleo; mientras, se prueba con `--dev-core`. Alternativa: escribirlo aquí y proponerlo al núcleo después, que contradice «aquí no se rodea» |
| D3 | **Los arcos.** La geometría del núcleo solo tiene polilíneas: un círculo es un polígono | En esta spec, la entrada del mallador lleva un arco opcional (centro y radio) por segmento. Si el arco entra en la geometría y en el `.ogr` común con Slip2D se decide en la spec 004 | Sin el arco verdadero el nudo intermedio no puede ir sobre él. Reconocer círculos a partir de los vértices sería adivinar |
| D4 | **Qué punto del arco** recibe el nudo intermedio | El punto medio del arco (sobre la bisectriz del ángulo que abarca el lado): su proyección sobre la cuerda es el punto medio, dentro del «tercio central» de Zienkiewicz y Taylor (2000), fig. 9.6 | Es lo que hacía la malla radial de la spec 001, validada; la fig. 9.6 habla de la posición a lo largo del lado, y la flecha la juzga el jacobiano (RF-13) |
| D5 | **Los controles de tamaño de la malla graduada y de la uniforme** | Graduada: el número de nudos de las excavaciones (o del contorno exterior, si no hay excavaciones) y una cota de tamaño máximo opcional; la graduación es la del refinado, sin factor de graduación. Uniforme: una cota constante h, o h a partir de un número de elementos N, con h² = 4A/(√3 N) (área del triángulo equilátero, la misma cuenta que `generate_mesh`) | El factor de graduación del programa de referencia es una ley de tamaño con la distancia que su documentación no da; inventarla sería inventar. La graduación por tamaño local de rasgo sí tiene fuente (Shewchuk 2002a, §3.2, pág. 11, que remite su cota a la §4.3: por leer en el plan) |
| D6 | **Ángulos pequeños de la entrada** | El «Terminator» de Shewchuk (2002a, §6.3, págs. 33–35), con la división en capas concéntricas de §6.2: siempre termina (teorema 11) y ningún ángulo baja de arcsin(sin(φ/2)/√2), con φ el menor ángulo de la entrada (teorema 12). Los triángulos que quedan por debajo de la cota B se señalan en el resultado | En geotecnia son frecuentes (pie de talud, capa acuñada). La pág. 27 demuestra que no siempre existe una malla sin ángulos nuevos pequeños, y que el refinado puede no terminar |
| D7 | **Qué medidas de calidad se dan y qué umbral es «malo»** | Por elemento: ángulos mínimo y máximo, y dos medidas invariantes con la escala de la tabla 4 de Shewchuk (2002b): una del error del gradiente y otra del condicionamiento, normalizadas a 1 en el equilátero (la propiedad 3 de una medida «justa», §6.3, pág. 51). Las variantes **exactas**: A/(ℓmáx ℓmed (ℓmín + 4\|r_in\|))^(2/3) y A/(3ℓ²rms + √((3ℓ²rms)² − 48A²)), no las suaves, que la fuente da por menos precisas (pág. 46) (notación en su tabla 1, pág. 3). «Malo» es por debajo de la garantía del refinado (B, 20.7° con B = √2); sin otros umbrales | Ninguna fuente leída da umbrales; los del programa de referencia (30, 2° y 175°) salen de su manual. Shewchuk (2002b, §5, págs. 42–43): un ángulo muy cercano a 180° puede estropear la solución en toda la malla, y un solo elemento malo sube el autovalor máximo de la rigidez global. Las dos cosas son distintas: por eso se dan las dos medidas |
| D8 | **La malla radial** | Anillo completo alrededor de un hueco circular; parámetros: divisiones del hueco, radio exterior y crecimiento radial (progresión geométrica, como `mesh_radial.quarter_annulus`); el exterior circular lo genera ella; sin otros contornos | Es para verificar (lo dice la documentación del programa de referencia) y la de la spec 001 ya está validada como estructura |
| D9 | **La densificación por ventana o polígono** | Una cota de tamaño local (RF-7) y no la inserción de un nudo en el centroide de cada elemento | Shewchuk (2002b, §6.2, pág. 49): el refinamiento jerárquico no puede quitar un ángulo pequeño; la cota local la admite el refinado sin perder la terminación (Shewchuk 2002a, pág. 11) |
| D10 | **Los dos pasos y la discretización personalizada** | La discretización es un resultado explícito (nudos por segmento), con número de divisiones forzable por segmento. El refinado conserva todos sus nudos, pero puede añadir más en un segmento invadido (§3.1), y lo dice | Sin partir segmentos, Ruppert no garantiza nada: prohibirlo dejaría elementos malos junto a los contornos. Guardar la discretización en el modelo es de la spec 004 |
| D11 | **Determinismo** | Misma entrada, misma malla bit a bit (orden de inserción fijado, sin azar) | La huella del modelo (ADR-0003) y la regla 9: la malla que fija la tolerancia de un caso tiene que poder rehacerse |
| D12 | **El caso 005 (STR-01 con malla general)** | Caso **nuevo**; el 001 no se toca. Contorno cuadrado de semilado 100 m, fijo; modelo completo, sin simetría; T6, malla graduada; **0.5 %** en σθ(a) y ur(a), como D3 de la spec 001, fijado antes de medir; malla fijada por estudio (16 a 128 divisiones del hueco); identidad con el desplazamiento exacto en el contorno, hidrostática y con p2 = p1/2 | Cambiar la malla de un caso es cambiar el caso (regla 9). Con 100 m el contorno circular apartaba la solución un 0.027 %; el cuadrado, sin solución cerrada, se mide con la identidad sobre la misma malla. El campo no hidrostático hace que la malla general no se beneficie de ninguna simetría |
| D13 | **Vértices que el refinado añade sobre las cuerdas de un arco** (salió al escribir el plan) | Después de mallar, se llevan al arco (radialmente desde el centro); se comprueba el jacobiano de los elementos afectados (RF-13) y el resultado dice cuántos se movieron (regla 12) | Un arco entra al refinado como cadena de cuerdas: el vértice nuevo caería sobre la cuerda y el T6 representaría mal el lado. Prohibir partir las cuerdas dejaría sin garantía de calidad los elementos junto al arco (D10) |

## Otras cosas encontradas al escribir el borrador

- **Para la sesión de OGR-Core** (no se toca aquí): el generador actual se queda muy por debajo de su
  propio suelo de 25° cuando un contorno tiene vértices mucho más próximos que el tamaño pedido (el
  sondeo de arriba). Va en la petición de D2 si se elige (a), o como nota aparte si no.
- Las fuentes de mallado son nuevas en la bibliografía (`../Referencias/Bibliografia/00_LEEME.md`,
  «Para la spec 003»). Babuška y Aziz (1976) y Zlámal (1968), que establecieron las condiciones del
  ángulo máximo y mínimo, no se han conseguido; lo que se usa de ellas se toma de Shewchuk (2002b).
