# Spec 031 — Juntas no conformes con la malla (XFEM)

> **Borrador de alcance (2026-11-23), sin aprobar.** Fase 7 del plan de desarrollo
> (`spec/constitution/plan_de_desarrollo.md`, «Fase 7 — Campos especiales»: «XFEM al final, con la
> ley de junta ya validada en el elemento convencional»). Solo el
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
      - Aquí: `ogr_fem2d/engine/interface.py` (la frontera supone dos grados de libertad por nudo
        y un patrón de rigidez fijo, `stiffness_pattern`; el enriquecimiento añade grados a unos
        nudos), `engine/reference/` (T3 y T6, la base que se enriquecería), `mesh/pslg.py` (hoy
        una junta sería un segmento forzado: con XFEM deja de serlo) y `docs/motor/entrada.md`.
      - El elemento junta y sus leyes de la 015, que esta spec reutiliza sin copiarlas; sus redes
        de juntas con semilla (015, RF-9) y su SSR de juntas (015, RF-11).
      - Núcleo: intersecciones de polilíneas (`geometry/cleanup.py`, `find_intersections`;
        `geometry/regions.py`), punto de partida para cortar elementos con juntas; nada de
        enriquecimiento. Slip2D: nada (es equilibrio límite).
      - Lo observado: nada; la versión observada no tenía XFEM (carpeta B, `modelo/M04a` §3.4).
        Documentación: carpeta B, `modelo/M04a` §3.4 y `modelo/M20` §2.7. Teoría: `C_teoria/T13`;
        errata en `T00` §3.3.
- [ ] Leer y comprobar las fuentes de «Validación numérica» y de «Fuentes por conseguir»; las fichas
      de los casos no son fuente.
- [ ] Releer las fichas de los casos que la cierran y su «Seguimiento».
- [ ] Convertir las «Dudas abiertas» en decisiones propuestas (D1, D2…) con su porqué, para el OK de
      la propietaria.

## Depende de

- **Spec 015** (juntas): la ley de junta validada en el elemento convencional, las redes y el SSR
  de juntas. Es la condición del plan, y la referencia de casi todas las comparaciones.
- Specs 002 y 003 (motor y malla), 007 y 008 (no linealidad, Mohr-Coulomb, Hoek-Brown en
  XFM-16), 009 (SSR: once casos), 011 (coste de las redes).
- Para casos concretos: 010 (rejilla y agua embalsada: XFM-12), 012 (excavación: XFM-10, -13,
  -16), 013 y 016 (revestimiento compuesto: XFM-16), 017 (flujo: XFM-11), 018 y 019 (transitorio y
  consolidación: XFM-13) y 028 (dinámico: XFM-14, -15).

## Contexto y objetivo

En la 015 una junta es un elemento de espesor nulo entre dos filas de nudos duplicados, y la malla
tiene que seguirla. Con una red de muchas juntas eso da mallas enormes y ángulos pequeños, que el
mallador no garantiza (spec 003). El método de elementos finitos extendido deja que la junta corte
los elementos: los nudos de los elementos cortados reciben grados de libertad enriquecidos que
permiten un salto del desplazamiento dentro del elemento, con funciones de unión donde dos juntas
se cruzan y subdivisión de los elementos cortados para integrar (T13; Belytschko y Black 1999;
Moës, Dolbow y Belytschko 1999). La ley de la junta es la misma; cambia la cinemática.

Hay 16 casos `VER-XFM`: trece con redes de juntas, once con SSR, y los demás con flujo,
consolidación con drenes, dinámico y un revestimiento. **Los dieciséis comparan con el mismo modelo
calculado por el programa de referencia con juntas convencionales**: ninguno es una validación. Por
eso esta spec se apoya en los casos ya validados de la 015, repetidos con juntas XFEM.

## Usuarios / actores

- **Ingeniero de rocas**, con taludes y túneles en macizos con familias de juntas densas.
- **El mallador** (003), que deja de seguir las juntas, y **el motor**, con grados de libertad
  variables por nudo.
- **Los casos de validación** de la 015, que sirven aquí de referencia.

## Historias de usuario

- H1: Como ingeniero quiero dibujar o generar una red de juntas y mallar sin que la malla la siga,
  para modelar macizos con muchas discontinuidades en un tiempo razonable.
- H2: Como ingeniero quiero elegir, junta a junta, malla conforme o XFEM, y ver que el resultado de
  la junta (tensiones, saltos, estado) se lee igual que en la 015.
- H3: Como investigadora quiero comparar el mismo modelo con juntas convencionales y XFEM, para
  saber cuánto cambia el resultado y por qué.

## Requisitos funcionales (EARS)

**Cinemática**

- RF-1: EL SISTEMA representa juntas que cortan elementos sin que la malla las siga, con el
  enriquecimiento que se decida con sus fuentes originales (T13 y duda 1).
- RF-2: EL SISTEMA trata los cruces de dos juntas en los tres casos de T13 (completo, parcial y en
  el extremo); SI en un elemento hay una configuración que no está decidida (tres juntas, cruce y
  extremo a la vez), ENTONCES lo dice con el elemento y las juntas, y no calcula.
- RF-3: EL SISTEMA trata el extremo de una junta dentro de un elemento según la duda 2 (XFM-09
  tiene juntas que no atraviesan el modelo).
- RF-4: SI una junta pasa por un nudo, coincide con un lado o corta un elemento en una astilla,
  ENTONCES EL SISTEMA aplica la regla que se decida (duda 4) y nunca resuelve en silencio un sistema
  mal condicionado.
- RF-5: EL SISTEMA integra los elementos cortados por subdivisión (T13) y la junta con la regla que
  se decida con fuente (T13 no la da).

**Ley y resultados**

- RF-6: EL SISTEMA usa en la junta XFEM las mismas leyes de la 015 (criterios, dilatancia,
  tracción, rigidez), con la misma implementación y su mismo oráculo en Python.
- RF-7: EL SISTEMA da a lo largo de cada junta lo mismo que la 015 (tensión normal y tangencial,
  saltos normal y tangencial, estado), con el convenio interno (tracción positiva, regla 10).
- RF-8: EL SISTEMA dibuja las juntas sobre la malla y deja ver qué nudos están enriquecidos.

**Uso en el modelo**

- RF-9: EL SISTEMA aplica XFEM a las juntas sueltas y a las redes de la 015, con la misma semilla,
  y deja elegir por junta malla conforme o XFEM (duda 6).
- RF-10: CON SSR, EL SISTEMA reduce o no la resistencia de las juntas XFEM con la misma regla y el
  mismo valor por defecto que las convencionales (015, RF-11), y el resultado lo dice (regla 12).
- RF-11: EL SISTEMA admite excavaciones y revestimientos cortados por juntas XFEM (XFM-10, -13,
  -16) según la 012 y la 013.
- RF-12: SI se combina XFEM con flujo, consolidación o dinámico y la duda 7 no lo admite, ENTONCES
  EL SISTEMA lo rechaza con un error que lo explica.

**Motor y reglas transversales**

- RF-13: El motor recibe nudos, elementos, los grados enriquecidos y, por elemento cortado, la
  geometría discreta del corte; no sabe de contornos ni de redes (regla 11). La referencia en Python
  es el oráculo de Rust, con su identidad (ADR-0001).
- RF-14: La elección entre conforme y XFEM lleva su test que demuestra que cambia la discretización
  y el número, dentro de la tolerancia de comparación que se fije (regla 7); los textos pasan por
  `tr()` y la opción está en un menú (reglas 2 y 3).

## Validación numérica

| Caso | Fuente científica (por comprobar) | Qué se compararía |
|---|---|---|
| `VER-STR-28` con la junta en XFEM | Kirsch (1898), en Jaeger, Cook y Zimmerman (2007), §8.4; Deb y Das (2010) | Lo mismo que en la 015: σn, τ y τ/σn a lo largo de la junta, con la junta rígida |
| `VER-STR-06` con la junta en XFEM | Jaeger y Cook (1979), plano de debilidad; Jaeger, Cook y Zimmerman (2007) | Resistencia de la columna por inclinación de la junta |
| `VER-STR-26` y `-27` con XFEM | Deb y Das (2009, 2010) | Desplazamiento a lo largo del eje; tensión que hace deslizar la junta |
| Parcela con junta oblicua | — (identidad) | Tensión uniforme a través de una junta que corta elementos en ángulo: σn y τ exactos |
| Sólido rígido y junta rígida | — (identidad) | Sin tensiones; junta muy rígida igual al medio continuo |
| Referencia y Rust | — (identidad) | Mismos resultados hasta el redondeo |
| `VER-XFM-01` a `-08` | Los de su caso convencional (`VER-JNT-03`, `-05`, `-06`, `-07`, `-08`, `-15`, `-17`, `-18`): Lorig y Varona (2004) y Alejano et al. (2011), numérica publicada; los demás, otros programas | **Comparación** del factor crítico con el valor publicado del caso convencional, si su ficha lo da; y con nuestra junta convencional en el mismo modelo |
| `VER-XFM-09`, `-10` | Yan, Elmo y Stead (2007), sin valores en la ficha; la -10, otro programa | **Comparación** |
| `VER-XFM-11` a `-16` | Ninguna externa | **Comparación** con nuestra junta convencional; la -15 es la versión XFEM de DYN-13 (Miller 1978), con otros datos: comprobar si la solución adimensional de Miller vale |

Nuestro modelo con juntas convencionales de la 015 es un cálculo independiente, no una validación.
Se proponen como los que la cierran **STR-28 y STR-06 con XFEM** (las de la 015) y las identidades;
de los `VER-XFM`, XFM-01 y XFM-03 como comparaciones, si las fichas de JNT-03 y JNT-06 dan el
valor publicado de Lorig y Varona (2004). **XFM-06 no
sirve como identidad**: allí el programa de referencia da factores distintos con juntas
convencionales y XFEM, sin comentarlo.

## Fuentes por conseguir

- Belytschko y Black (1999); Moës, Dolbow y Belytschko (1999); Belytschko, Moës, Usui y Parimi
  (2001), discontinuidades arbitrarias; Wells y Sluys (2001) y Moës y Belytschko (2002), grietas
  cohesivas. La errata de la función de unión de la ec. 2 de T13 (T00 §3.3) se resuelve con ellas.
- La rigidez y las fuerzas de la junta: T13 remite a Moallemi, Curran y Yacoub (2018), congreso
  sin páginas y de autores vinculados al programa de referencia (comprobar si contiene la
  formulación y si es citable), y a Khoei, Vahab, Haghighat y Moallemi (2014).
- An, Fu y Ma (2011), comparación con el método de la variedad numérica: incompleta en T13.
- Las de los casos de la 015 que se repiten aquí, y Yan, Elmo y Stead (2007); Lorig y Varona
  (2004); Alejano et al. (2011); Miller (1978).
- Ninguna está en `Referencias/Bibliografia`.

## Requisitos no funcionales

- Grados de libertad variables por nudo: el patrón de rigidez sigue fijo dentro de un análisis si
  las juntas no cambian (frontera del ADR-0001); medirlo con la 011.
- Robustez geométrica: los cortes de juntas casi paralelas o casi tangentes a un lado, con una
  tolerancia única y documentada.
- Una red de miles de juntas tiene que caber y calcularse en un tiempo razonable. Sin dependencias
  nuevas.

## Casos límite

- Junta por un nudo, sobre un lado o a una distancia mínima de un nudo; astilla de elemento.
- Dos juntas casi paralelas en un elemento; tres juntas en un elemento; cruce en un nudo.
- Junta que termina sobre un lado, en un nudo o dentro de un elemento.
- Junta que corta el contorno externo, una excavación o un revestimiento; elemento cortado que se
  excava.
- T6 cortado: subdivisión con nudos intermedios; lado curvo cortado (arcos de la 003).
- Junta abierta en toda su longitud: bloque suelto (modelo sin sujetar, spec 002).

## Fuera de alcance

- Propagación de grietas (de lo que tratan Belytschko y Black 1999 y Moës et al. 1999): aquí las
  juntas son fijas.
- Enriquecimiento singular de punta de grieta, salvo que la duda 2 lo traiga.
- Enriquecimiento de la presión del agua y presión dentro de la junta, salvo que la duda 7 lo
  traiga; drenes (`DREN`), según la duda 8.
- Juntas ubicuas como ley de material (fase 5).

## Criterios de finalización

- [ ] Dudas convertidas en decisiones y aprobadas por la propietaria
- [ ] Todos los RF con su test en verde, y la regla 7 en la opción nueva
- [ ] STR-28 y STR-06 con XFEM dentro de la tolerancia de su caso de la 015, con la malla fijada
      por su estudio de convergencia (regla 9)
- [ ] Las identidades, en verde y con dientes; referencia y Rust idénticas
- [ ] Las comparaciones elegidas, anotadas con su diferencia y su porqué
- [ ] Todo texto nuevo con traducción española y toda acción nueva en un menú
- [ ] Changelog con lo encontrado; fichas con su «Seguimiento»

## Dudas abiertas

- [NECESITA ACLARACIÓN] **1. Enriquecimiento y errata** (T00 §3.3): la ec. 2 de T13 escribe la
  función de unión en el nudo de otro conjunto; se resuelve con Belytschko et al. (2001) o Moës et
  al. (1999), no con el manual.
- [NECESITA ACLARACIÓN] **2. Extremos dentro de un elemento** (XFM-09; T13 no los trata).
  Opciones vistas: (a) llevar el extremo al lado más cercano; (b) un enriquecimiento de punta con
  fuente; (c) rechazar juntas que acaban dentro de un elemento.
- [NECESITA ACLARACIÓN] **3. Elemento base**: T3, T6 o los dos (T13 no lo dice y su figura muestra
  cuadriláteros); cómo se subdivide un T6 cortado.
- [NECESITA ACLARACIÓN] **4. Junta cerca de un nudo**: quitar el enriquecimiento, mover la junta o
  aceptar el mal condicionamiento; T13 no lo documenta.
- [NECESITA ACLARACIÓN] **5. Integración sobre la junta**: número y posición de los puntos; T13 no
  los da.
- [NECESITA ACLARACIÓN] **6. Redes con XFEM**: trece casos las piden, pero la carpeta B se
  contradice (M20 §2.7: «malla conforme» no se aplica a redes; su tabla final: «redes siempre
  conformes»). ¿Redes siempre XFEM, siempre conformes, o a elección?
- [NECESITA ACLARACIÓN] **7. Combinaciones**: T13 dice que funciona con flujo y dinámico, y XFM-11,
  -13, -14 y -15 lo combinan; la carpeta B (M04a §3.4, M26 §2) dice que activar XFEM desactiva el
  dinámico. ¿Qué se admite, y con qué fuente para la presión enriquecida?
- [NECESITA ACLARACIÓN] **8. Drenes** (`DREN`, XFM-13): son agua, no XFEM, y los necesita también
  el modelo convencional de comparación; ninguna spec los tiene (la 017 los dejó para la fase 7).
  ¿Aquí, en la 018 o 019, o fuera con XFM-13?
- [NECESITA ACLARACIÓN] **9. Tolerancia de comparación** entre XFEM y convencional: no es una
  validación; ¿qué diferencia se acepta y cómo se justifica con la malla?
- [NECESITA ACLARACIÓN] **10. Ley de junta en XFEM**: confirmar con la fuente que la ley del
  elemento convencional sirve tal cual con el salto del elemento enriquecido.
- [NECESITA ACLARACIÓN] **11. Bulón que cruza una junta XFEM** (015, RF-10) y revestimiento cortado
  (XFM-16): ¿entran?
- [NECESITA ACLARACIÓN] **12. Orden**: el orden de desbloqueo del índice de casos pone `XFEM` en el
  paso 2, junto a las juntas, porque sus casos no piden nada más; el plan lo deja al final por su
  dificultad. ¿Se mantiene al final o va justo después de la 015?

Las referencias T00 y T13 son de la carpeta C del análisis de interfaz
(`../Referencias/Doc_Guia/Analisis_interfaz_funcionamiento/C_teoria/`); M04a, M20 y M26, de la
carpeta B (`modelo/`).
