# Spec 028 — Análisis dinámico en el tiempo

> **Borrador de alcance (2026-11-23), sin aprobar.** Fase 7 del plan de desarrollo
> (`spec/constitution/plan_de_desarrollo.md`, «Fase 7 — Campos especiales»: dinámico). Solo el
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
      - Aquí, `ogr_fem2d/engine/`: motor estático. `interface.py` (una llamada por iteración,
        patrón de rigidez fijo, `stiffness_pattern`), `reference/solver.py` (`solve_stage`) y
        `docs/motor/entrada.md` (fases en totales). **No hay** masa, densidad, tiempo, velocidad
        ni aceleración.
      - Núcleo: `ogr_core/loads/seismic_record.py` (`SeismicRecord`: una aceleración horizontal a
        intervalo constante, guardada en g dentro del proyecto, con lectura de texto y conversión
        de g, cm/s² y m/s²). Se escribió para el bloque deslizante de Slip2D: no tiene velocidad,
        desplazamiento, dos componentes ni intervalo variable.
      - En Slip2D, solo lectura: `ogr_slip2d/newmark.py` y `spec/features/007-analisis-de-newmark/`
        son el **bloque rígido deslizante** (Newmark 1965, con el esquema que publica Jibson
        1993), otra teoría que el método de integración en el tiempo de Newmark (1959). Solo
        sirven como antecedente de cómo se guarda y se lee un acelerograma.
      - Specs vecinas: la 016 dejó aquí los muelles y los contornos absorbentes; la 021, los
        cuadriláteros que piden DYN-05 a -09; la 019 y la 018 piden funciones del tiempo
        (`C-TIEMPO`) antes que esta.
      - Lo observado: nada; la versión observada no tenía dinámico (carpeta B, `modelo/M26`).
        Documentación: carpeta B, `modelo/M26_dinamico.md` y `compute_interpret/I05` §4. Teoría:
        `C_teoria/T10`; erratas en `T00` §3.3 y fuentes incompletas en `T00` §3.4.
- [ ] Leer y comprobar las fuentes de «Validación numérica» y de «Fuentes por conseguir»; las fichas
      de los casos no son fuente.
- [ ] Releer las fichas de los casos que la cierran y su «Seguimiento».
- [ ] Convertir las «Dudas abiertas» en decisiones propuestas (D1, D2…) con su porqué, para el OK de
      la propietaria.

## Depende de

- Spec 002 (motor) y 007 (Newton, criterio de convergencia), con el **tiempo** y la **masa** como
  dimensiones nuevas; 008 (Mohr-Coulomb en DYN-17); 011 (miles de pasos por análisis).
- Specs `004-modelo-y-proyecto` (densidad por material, duración de fase, funciones del tiempo) y
  012 (fase estática previa; coacciones estáticas que se retiran en la dinámica).
- Specs `005-resultados` (historias y campos por instante) y `006-interfaz-y-calculo` (progreso por
  paso de tiempo).
- Para casos concretos: 013 (viga: DYN-03, -04, -15), 015 (junta: DYN-13), 021 (cuadriláteros:
  DYN-05 a -09) y 019 (funciones del tiempo, si llegan allí; no drenado para la licuefacción).

## Contexto y objetivo

Hasta aquí todo es estático: el motor busca el equilibrio al final de cada fase. En dinámica cuentan
la inercia y el amortiguamiento, y la respuesta es una historia en el tiempo: vibraciones, ondas que
viajan y se reflejan en los contornos, sismos. T10 describe la integración implícita de la familia
de Newmark (Newmark 1959), el amortiguamiento de Rayleigh, los contornos absorbentes de Lysmer y
Kuhlemeyer (1969), los de campo libre (Zienkiewicz, Bicanic y Shen 1989; Wolf 1988) y la base
flexible. Los casos piden también cargas y desplazamientos función del tiempo, acelerogramas,
historias en puntos, muelles y amortiguadores discretos y, en un caso, licuefacción.

Hay 18 casos `VER-DYN` y 2 `VER-XFM` dinámicos. Diez tienen solución analítica y dos aproximada;
DYN-09 no tiene referencia; DYN-06, -12, -16, -17 y -18 solo se comparan con otros programas. Los
dos casos de campo libre (DYN-16 y -17) son comparaciones: esa función solo se puede validar con
identidades. Es la spec más grande de la fase: la duda 1 propone cómo partirla.

## Usuarios / actores

- **Ingeniero geotécnico sísmico**: respuesta de un talud, una presa o un túnel a un sismo.
- **Ingeniero de cimentaciones de máquinas y de voladuras**: vibraciones y ondas.
- **Investigador y docente**, que contrastan con soluciones clásicas de ondas y osciladores.

## Historias de usuario

- H1: Como ingeniero quiero aplicar un acelerograma en la base de un modelo, con contornos que no
  reflejen las ondas, y ver la historia de la aceleración en coronación.
- H2: Como ingeniero quiero cargas y desplazamientos que varían en el tiempo (armónicas, pulsos,
  escalones, tablas) sobre los contornos dibujados.
- H3: Como ingeniero quiero fijar el amortiguamiento y ver con el resultado cada parámetro del
  esquema temporal y del amortiguamiento, porque cambian el número.
- H4: Como investigadora quiero comprobar el periodo de una columna o la respuesta de un oscilador
  contra su solución cerrada.

## Requisitos funcionales (EARS)

**Integración en el tiempo**

- RF-1: EL SISTEMA resuelve el equilibrio dinámico en deformación plana y en axisimetría con la
  integración implícita de la familia de Newmark (Newmark 1959) y los parámetros que se decidan
  (duda 2), que se muestran con el resultado (regla 12).
- RF-2: EL SISTEMA forma la masa con la densidad de cada material, como se decida (duda 3); la
  gravedad con que se pasa de peso a masa se muestra con el resultado (regla 12).
- RF-3: EL SISTEMA admite fases dinámicas con su duración, después de fases estáticas que dan el
  estado inicial, y velocidades iniciales impuestas (DYN-02); cómo se pasa de una a otra, según la
  duda 6.
- RF-4: EL SISTEMA integra con el paso que fija el usuario y, si se decide, con control automático
  (duda 4); el paso usado se guarda y se muestra. Cada caso fija la malla, el orden del elemento
  y el paso de tiempo (regla 9).
- RF-5: CON leyes plásticas (008) o juntas (015), EL SISTEMA itera el equilibrio en cada paso con
  el Newton del motor (spec 001, D7: la rigidez inicial se descartó) y el criterio de la 007; SI un
  paso no converge, ENTONCES lo dice con el instante.

**Amortiguamiento y elementos discretos**

- RF-6: EL SISTEMA aplica amortiguamiento de Rayleigh dado por sus dos coeficientes o por dos
  frecuencias y una razón (duda 5); con cero, no hay amortiguamiento oculto.
- RF-7: EL SISTEMA admite muelles y amortiguadores discretos en nudos o vértices, por dirección
  (`MUELLE`, DYN-08; la 016 los dejó aquí).

**Cargas y contornos**

- RF-8: EL SISTEMA admite cargas y movimientos función del tiempo (`C-TIEMPO`): fuerza puntual o
  repartida, desplazamiento, velocidad y aceleración impuestos, en X, en Y o normales al contorno,
  dados por tabla o por las formas que se decidan (duda 7). Entran al motor en totales en cada
  instante (spec 001, D2).
- RF-9: EL SISTEMA lee un acelerograma o una historia de velocidades (`SISMO-REG`), convierte sus
  unidades en un único sitio y lo aplica donde se diga; SI el registro no empieza en cero o no es
  regular, ENTONCES lo dice (duda 8).
- RF-10: EL SISTEMA ofrece contornos absorbentes (`CC-ABS`, Lysmer y Kuhlemeyer 1969) calculados
  con las propiedades del material vecino; SI el segmento separa dos materiales, ENTONCES aplica
  la regla que se decida con fuente (T10 da una sin fuente).
- RF-11: EL SISTEMA ofrece contornos laterales de campo libre (`CC-LIBRE`) y base flexible, según
  la duda 9, y el contorno atado de DYN-16 si se decide (duda 11).

**Resultados**

- RF-12: EL SISTEMA registra en cada paso las historias en los puntos que el usuario declara antes
  de calcular (`POST-HIST`): desplazamiento, velocidad, aceleración, tensión y deformación,
  interpoladas en su elemento; y guarda los campos completos en los instantes que se decidan, en
  `modelo.h5` con la huella (ADR-0003).
- RF-13: EL SISTEMA dibuja y exporta las historias; el espectro de respuesta, según la duda 10.

**Motor y reglas transversales**

- RF-14: El motor recibe nudos, elementos, densidades, coeficientes de amortiguamiento,
  amortiguadores y muelles discretos, historias discretas por grado de libertad, paso y parámetros
  del esquema; no sabe de contornos, registros ni unidades de usuario (regla 11).
- RF-15: Cada término nuevo (masa, amortiguamiento, contorno viscoso, esquema) tiene su referencia
  en Python, que es el oráculo de Rust, con su identidad (ADR-0001).
- RF-16: Un único convenio: tracción positiva dentro del motor; velocidades y aceleraciones del
  registro en el sentido de los ejes del modelo, convertidas en un único sitio (regla 10).
- RF-17: Cada parámetro nuevo (esquema, paso, amortiguamiento, tipo de masa, contornos, muelles)
  lleva su test que mueve el número (regla 7); los textos pasan por `tr()` y las acciones están en
  un menú (reglas 2 y 3; duda 14).

## Validación numérica

| Caso | Fuente científica (por comprobar) | Qué se compararía |
|---|---|---|
| `VER-DYN-01`, periodo de una columna (T3) | Barra elástica fija-libre; la ficha la toma del manual de otro programa: fuente científica por localizar | Periodo del desplazamiento de coronación con el peso aplicado de golpe |
| `VER-DYN-02`, barra con velocidad inicial (T3) | Smith y Griffiths (2004), analítica y numérica publicada | Periodo y amplitud junto al apoyo; la ficha anota que su cálculo propio no da el periodo del manual |
| `VER-DYN-08`, elemento sobre muelles | Oscilador de un grado de libertad (la ficha no cita fuente; DYN-04 y -07 citan Chopra 1995 para el oscilador: por comprobar) | Historia sin amortiguar, con amortiguadores y con Rayleigh proporcional a la masa; la ficha anota una errata en su ec. 8.3. Necesita la 021 o dos triángulos (021, duda 1) |
| `VER-DYN-10`, onda S en una columna | Propagación de una onda de corte (fuente por localizar) | Llegada al punto medio, con contorno fijo y absorbente; la ficha anota una posible errata de unidades |
| `VER-DYN-11`, problema de Lamb (axisimétrico) | Lamb, sin referencia en la ficha: por localizar | Llegada de las ondas P y S; posible errata de unidades en la ficha |
| `VER-DYN-14`, voladura interior | Blake (1952) | Onda esférica; la ficha duda del tipo de análisis atribuido |
| `VER-DYN-13`, onda armónica y junta | Miller (1978) | Coeficientes de transmisión, reflexión y absorción; necesita la 015 |
| `VER-DYN-03`, `-04`, `-05`, vigas | Chopra (1995) para la -04 y la -05; la -03 cita el manual de otro programa | Respuesta modal; necesitan la 013 (viga) o la 021 (cuadriláteros) |
| `VER-DYN-07`, `-15` | Chopra (1995), aproximada; Gazetas y Roesset (1979), aproximada | Respuesta de un grado de libertad; flexibilidad de una zapata (la ficha anota una errata de unidades) |
| `VER-DYN-09`, dos elementos | Sin referencia | **Identidad**: fuerza nodal, aceleración impuesta y desplazamiento impuesto dan el mismo movimiento relativo |
| `VER-DYN-06`, `-12`, `-16`, `-17`, `-18` | Solo otros programas | **Comparaciones**, no validaciones |
| Límite cuasiestático | — (identidad) | Una carga aplicada muy despacio da la solución estática de la 002 |
| Propiedades del esquema | Newmark (1959); Bathe (1982) | La estabilidad incondicional que T10 atribuye a la aceleración media, y las demás propiedades que dé la fuente para el caso lineal sin amortiguamiento |
| Absorción con incidencia normal | Lysmer y Kuhlemeyer (1969) (T10 §1.6) | Una onda plana sale por el contorno sin reflejarse |
| Campo libre | — (identidad) | Un estrato horizontal con campo libre en los laterales responde como la columna sola; contorno atado y campo libre dan lo mismo en ese estrato (DYN-16) |
| Convergencia en el tiempo | — | El resultado con tres pasos; la tolerancia se fija con el elegido (regla 9) |
| Referencia y Rust | — (identidad) | Mismas historias hasta el redondeo |

Se proponen como los que la cierran **DYN-01, DYN-02, DYN-08 y DYN-10** (analíticos y con
elementos que ya hay o que pide la 021), **DYN-14** para la axisimetría con absorbentes, y las
identidades de campo libre, que no tiene otra validación.

## Fuentes por conseguir

- Newmark (1959) y Bathe (1982): el esquema y su linealización. Las erratas de T10 (T00 §3.3: el
  término de masa de la ec. 1.4, la ec. 1.11 y el arranque de la iteración) solo se resuelven con
  ellas. Nelson y Mak (1982), estabilidad del implícito no lineal.
- Lysmer y Kuhlemeyer (1969); Kuhlemeyer y Lysmer (1973), tamaño de elemento frente a la longitud
  de onda (carpeta B, M26 §10); Cohen y Jennings (1983), contornos silenciosos (incompleta).
- Zienkiewicz, Bicanic y Shen (1989) y Wolf (1988), campo libre; T10 no describe cómo se
  discretiza la columna lateral.
- Zienkiewicz y Xie (1991), control del paso, y Hudson et al. (1994), elección de las frecuencias
  de Rayleigh: **solo autor y año** (T00 §3.4); completarlas antes de citarlas.
- Las de los casos: Smith y Griffiths (2004), Chopra (1995), Miller (1978), Blake (1952), Gazetas
  y Roesset (1979), la solución de Lamb.
- Si entra el tratamiento del registro: Arias (1970); la corrección de línea base de T10 sale de un
  informe técnico de software (Jones, Kalkan y Stephens 2017).
- En `Referencias/Bibliografia` no hay ninguna. Zienkiewicz y Taylor (2000), vol. 1, está; no se
  ha comprobado si sus capítulos del tiempo bastan.

## Requisitos no funcionales

- Miles de pasos por análisis, cada uno con su sistema: el coste se mide con la 011 (reutilizar la
  factorización cuando la matriz no cambia es su duda 4).
- Registros largos (DYN-16: 25 s) y muchas historias: el tamaño de `modelo.h5` se mide.
- Unidades de tiempo, de densidad y de aceleración convertidas en un único sitio.

## Casos límite

- Paso grande frente al periodo de interés; elementos grandes frente a la longitud de onda.
- Base rígida con contornos absorbentes (la carpeta B dice que la base rígida anula su efecto).
- ν = 0 (DYN-01) y ν cercano a 0.5; región sin densidad; elemento casi rígido (DYN-08).
- Junta que se abre o desliza durante el sismo; junta que corta un contorno de campo libre (la
  carpeta B exige extremo cerrado en él).
- Carga puntual en axisimetría (DYN-11: la ficha reparte la carga por radián).
- Registro con otra unidad o con otro intervalo que el paso del cálculo.

## Fuera de alcance

- **Licuefacción** (`LICUEF`, DYN-18): necesita la ley de Finn (T07c §3, con erratas en las
  constantes según T00 §3.3 y la propia ficha), el no drenado de la 019 y presión intersticial en
  dinámico; su único caso es una comparación. Se propone una spec propia después de esta.
- Amortiguamiento histerético (DYN-12): es elasticidad no lineal (T07, fase 5); solo comparación.
- Masa hidrodinámica (Westergaard 1933): ningún caso, fórmula incompleta en T10.
- Frecuencias naturales por autovalores y el tratamiento del registro (filtro, línea base,
  intensidad de Arias), salvo lo que decida la duda 10.
- Método lineal equivalente (T10 lo describe para no usarlo); bloque deslizante (es de Slip2D);
  sismo pseudoestático (020); integración explícita (después del FEM).
- Dinámico con SSR, con flujo en fases dinámicas o con térmico; grandes deformaciones.

## Criterios de finalización

- [ ] Dudas convertidas en decisiones y aprobadas por la propietaria
- [ ] Todos los RF con su test en verde, y la regla 7 en cada parámetro nuevo
- [ ] Referencia en Python y Rust con su identidad (ADR-0001)
- [ ] Los casos que la cierran dentro de tolerancia, con su malla y su paso fijados (regla 9)
- [ ] Las identidades de la tabla, en verde y con dientes
- [ ] Todo texto nuevo con traducción española y toda acción nueva en un menú
- [ ] Changelog con lo encontrado; fichas con su «Seguimiento»

## Dudas abiertas

- [NECESITA ACLARACIÓN] **1. Partir la spec.** Opciones vistas: (a) 028a, dinámico lineal (masa,
  Newmark, Rayleigh, muelles, funciones del tiempo, historias: DYN-01, -02, -07, -08, -09); 028b,
  contornos (absorbente, campo libre, base flexible, atado, acelerograma: DYN-10, -11, -14, -16,
  -17); 028c, no lineal y estructuras en dinámico (DYN-03, -04, -05, -13, -15; XFM-14 y -15 con la
  031); (b) partir por dependencias (lo que no necesita la 013, la 015 ni la 021, primero); (c)
  una sola spec con tareas por bloques.
- [NECESITA ACLARACIÓN] **2. Esquema.** T10 usa la regla de aceleración media y cita otros
  parámetros para amortiguar altas frecuencias. ¿Fijos o editables? T10 deja sin decir si linealiza
  con rigidez inicial o tangente; aquí el motor usa la tangente (spec 001, D7).
- [NECESITA ACLARACIÓN] **3. Masa** consistente o concentrada; con T6, la concentrada necesita una
  regla con fuente.
- [NECESITA ACLARACIÓN] **4. Paso de tiempo**: fijo, o automático según Zienkiewicz y Xie (1991),
  cita incompleta y con dos símbolos sin definir en T10; la tolerancia fija del programa de
  referencia sería un valor por defecto a la vista (regla 12).
- [NECESITA ACLARACIÓN] **5. Rayleigh**: global o por material (T10 no lo dice); frecuencias en Hz
  o en rad/s (T10 mezcla las dos); notación que choca con la de Newmark.
- [NECESITA ACLARACIÓN] **6. Paso de estático a dinámico**: las coacciones estáticas se cambian por
  sus reacciones (T10 §1.4; la carpeta B tiene «impedir el giro de la base»). DYN-01, en cambio,
  aplica el peso de golpe desde tensión nula. ¿Las dos cosas?
- [NECESITA ACLARACIÓN] **7. Funciones del tiempo**: tabla con interpolación lineal o con otra
  (carpeta B: no documentado); formas armónicas, pulso y escalón como tablas o como tipos. Totales
  en cada instante: la misma pregunta que la duda 7 de la 019 (S06, duda 12).
- [NECESITA ACLARACIÓN] **8. Acelerograma**: ampliar `SeismicRecord` del núcleo (velocidad,
  desplazamiento, dos componentes, intervalo variable: petición a OGR-Core) o un tipo propio.
- [NECESITA ACLARACIÓN] **9. Campo libre y base flexible**: T10 no dice cómo se resuelve la columna
  lateral ni qué longitud multiplica las fuerzas de la base flexible, que solo vale con velocidad o
  aceleración. ¿Con qué fuente?
- [NECESITA ACLARACIÓN] **10. Espectro de respuesta y frecuencias naturales**: DYN-16 compara un
  espectro; las frecuencias ayudan a elegir Rayleigh. ¿Entran?
- [NECESITA ACLARACIÓN] **11. Contorno atado** (DYN-16): pide nudos emparejados a la misma cota en
  los dos laterales; es una petición al mallador (003).
- [NECESITA ACLARACIÓN] **12. `C-TIEMPO` antes de esta spec**: CON-01, -04, -05 y -06 (019) lo
  piden como rampa o velocidad de carga, y la 018 pregunta por condiciones dentro de una etapa. Si
  entra antes, aquí se amplía (velocidad, aceleración, registro) y no se define.
- [NECESITA ACLARACIÓN] **13. Datos de los casos con erratas** (DYN-02, -08, -10, -11, -15): los
  datos se fijan con la fuente científica, no con la tabla del manual; ¿y si la fuente no da todos?
- [NECESITA ACLARACIÓN] **14. Menú**: la 006 no tiene menú dinámico; la versión actual del
  programa de referencia lo añade (S01 §4). ¿Uno propio o repartido entre Análisis, Cargas y
  Contornos?

Las referencias T00, T07c y T10 son de la carpeta C del análisis de interfaz
(`../Referencias/Doc_Guia/Analisis_interfaz_funcionamiento/C_teoria/`); M26 e I05, de la carpeta B
(`modelo/` y `compute_interpret/`); S01 y S06, de `D_sintesis/`.
