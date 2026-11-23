# Spec 015 — Juntas

> **Borrador de alcance (2026-11-23), sin aprobar.** Fase 3 del plan de desarrollo
> (`spec/constitution/plan_de_desarrollo.md`, «Spec 015 — Juntas»). Solo el **qué** y el
> **porqué**, sin fórmulas ni decisiones tomadas. **Antes de abrirla hay que reevaluarla** (sección
> siguiente); después, plan y tareas con el OK de la propietaria.

## Antes de abrirla: reevaluar esta spec

Este borrador se escribió antes de que existieran las specs que lo preceden; el código, el núcleo y
OGR Slip2D habrán avanzado. Al abrirla, y antes de escribir el plan:

- [ ] Contrastarla con el código de este programa y con las specs cerradas desde el 2026-11-23: qué
      ya está hecho, qué cambió y qué se movió de sitio.
- [ ] Mirar qué tienen ya OGR Slip2D y `ogr_core` en la etiqueta fijada. Lo genérico se pide a la
      sesión de OGR-Core, no se copia (`AGENTS.md`, «Un núcleo y varios programas»). Puntos de
      partida vistos al escribir el borrador (núcleo v0.2.6):
      - Aquí: la spec 003 dejó fuera las juntas con nudos duplicados; `ogr_fem2d/mesh/pslg.py`
        (segmentos forzados: una junta lo es antes de duplicar sus nudos) y `docs/malla/entrada.md`
        (`Mesh.boundaries`). La entrada del motor no tiene elementos de interfaz.
      - Núcleo: `geometry/boundary_type.py`, `WEAK_LAYER` (polilínea con resistencia propia, que
        en equilibrio límite no es geometría: aquí la junta sí lo es, se interseca y parte la
        malla); `materials/builtin_models.py` (envolventes `Hyperbolic` y de Barton-Bandis como
        resistencia en función de la tensión normal: sirven como envolvente, no como ley con
        rigidez); `statistics/` (variables aleatorias y distribuciones, para las redes, con
        semilla); `support/support.py`, `intersections_with_polyline` (cruce bulón-junta).
      - Lo observado: `dialogos/D07` (extremos, cuatro criterios y sus valores por defecto,
        presión interna, deslizamiento desde una fase, redes, *Apply SSR*, tabla de resultados),
        `reproducciones/P09` (STR-28), `P19` (JNT-23, sin dilatancia) y `P21` (redes y SSR);
        teoría en `C_teoria/T04`, `T02` §2 (bulón-junta) y `T07a` §9 (criterios de juntas).
- [ ] Leer y comprobar las fuentes de «Validación numérica» y de «Fuentes por conseguir»; las fichas
      de los casos no son fuente.
- [ ] Releer las fichas de los casos que la cierran y su «Seguimiento».
- [ ] Convertir las «Dudas abiertas» en decisiones propuestas (D1, D2…) con su porqué, para el OK de
      la propietaria.

## Depende de

- Spec 003 (malla con segmentos forzados), `004-modelo-y-proyecto` (el contorno de junta: su duda
  9), 007 y 008 (no linealidad y Mohr-Coulomb de la roca, que STR-06 necesita), 012 (instalación y
  deslizamiento por fase), 014 (para la interacción bulón-junta), 009 (para el SSR con juntas).

## Contexto y objetivo

Una junta es una discontinuidad: dos caras que se separan, se cierran y deslizan según su rigidez y
su resistencia. En elementos finitos convencionales es un elemento de espesor nulo entre dos filas
de nudos duplicados (Goodman et al. 1968, por comprobar). Ningún manual de teoría lo formula
(`C_teoria/T00`, §3.1): hay que ir a la literatura. Esta spec añade el elemento junta, sus
criterios de resistencia con dilatancia, las redes de juntas y la interacción con los bulones, y lo
valida con STR-28 y STR-06, los dos casos de la fase. Juntas es el área con más casos (27, más los
16 de XFEM que usan la misma ley), casi todos con SSR.

## Usuarios / actores

- **El ingeniero de rocas** (taludes y túneles en macizos con discontinuidades); **el ingeniero de
  suelos**, para interfaces muro-suelo; **el modelo** (004), **el mallador** (003) y **la
  interpretación** (016); **los casos de validación**.

## Historias de usuario

- H1: Como ingeniero quiero dibujar una junta con sus extremos abiertos o cerrados y que corte los
  contornos que cruza, para representar una falla.
- H2: Como ingeniero quiero elegir el criterio de la junta (ninguno, Mohr-Coulomb con residual,
  Barton-Bandis, hiperbólico) con dilatancia, y ver dónde desliza o se abre.
- H3: Como ingeniero quiero generar una red de juntas reproducible (misma semilla, misma red).
- H4: Como ingeniero quiero que un bulón que cruza una junta que desliza la resista.

## Requisitos funcionales (EARS)

**Elemento y malla**

- RF-1: EL SISTEMA malla cada junta como un segmento forzado y duplica sus nudos, con extremos
  abiertos o cerrados, y la interseca con los contornos y con otras juntas; SI una junta deja un
  elemento degenerado o un ángulo que el mallador no garantiza (spec 003), ENTONCES lo dice.
- RF-2: EL SISTEMA calcula el elemento junta compatible con T3 y con T6, con rigidez normal y
  tangencial, en deformación plana (duda 2 para la axisimetría).
- RF-3: EL SISTEMA da por elemento y fase la tensión normal y tangencial, los desplazamientos
  relativos normal y tangencial y el estado (elástico, deslizando, abierto), con el convenio
  interno (tracción positiva, regla 10); lo que no tiene valor (junta excavada) va como «sin dato»,
  no como un número enorme (la referencia escribe 1.79769e+308, D07).

**Leyes**

- RF-4: EL SISTEMA ofrece los criterios ninguno (elástico), Mohr-Coulomb con tracción, pico y
  residual, Barton-Bandis e hiperbólico, cada uno con su fuente.
- RF-5: EL SISTEMA admite dilatancia en las juntas (S06, duda 12) con el límite y la opción
  direccional que se decidan.
- RF-6: EL SISTEMA trata la junta en tracción como se decida (duda 4); cualquier factor de rigidez
  por defecto va con el resultado (regla 12).
- RF-7: Cada ley se prueba en un ensayo de corte de tensiones uniformes contra su fuente antes de
  usarse en un modelo, que es para la junta lo que la regla 8 es para el punto de Gauss.

**Fases, redes, bulones y SSR**

- RF-8: EL SISTEMA instala cada junta en una fase y permite que deslice desde otra (spec 012); SI
  uno de sus lados se excava, ENTONCES hace lo que se decida en la duda 7 de la 012.
- RF-9: EL SISTEMA genera redes de juntas en una región con los modelos que se decidan (duda 6), con
  semilla guardada en el modelo: misma semilla, misma red.
- RF-10: CUANDO un bulón adherido cruza una junta, EL SISTEMA puede añadir su resistencia de pasador
  (Dight 1982, modificada, por comprobar), opción que lleva su test (regla 7; duda 8).
- RF-11: EL SISTEMA deja que el SSR reduzca o no la resistencia de cada junta, y el resultado dice
  qué se ha reducido (la referencia no las reduce por defecto, P21; spec 009).
- RF-12: EL SISTEMA tiene el elemento y cada ley en la referencia en Python, oráculo de Rust, con su
  identidad (ADR-0001).

## Validación numérica

| Caso | Fuente científica (por comprobar) | Qué se compararía |
|---|---|---|
| `VER-STR-28`, junta que corta un túnel | Kirsch (1898), en Jaeger, Cook y Zimmerman (2007), §8.4; Deb y Das (2010) | σn, τ y τ/σn a lo largo de la junta. La solución es la del medio continuo: vale si la junta es lo bastante rígida para no perturbarlo, y hay que comprobarlo (regla 1). Las tensiones de la junta y las del terreno a lo largo de su traza, las dos (la ficha se contradice) |
| `VER-STR-06`, columna con una junta, compresión uniaxial | Jaeger y Cook (1979), plano de debilidad; Jaeger, Cook y Zimmerman (2007) lo trata y está en la bibliografía | Resistencia de la columna para cada inclinación; necesita Mohr-Coulomb en la roca (008). La ficha usa T3, y Mohr-Coulomb con T3 está rechazado (spec 002, D6): el caso fija su elemento (regla 9) |
| `VER-STR-26`, columnas con una y dos juntas | Deb y Das (2009) | Desplazamiento a lo largo del eje: la suma de la deformación de la roca y el salto de cada junta |
| `VER-STR-27`, columna con junta, carga triaxial | Deb y Das (2010) | Diferencia de tensiones principales que hace deslizar la junta, por inclinación |
| `VER-JNT-23`, corte directo, Mohr-Coulomb con residual y dilatancia | La de la ley que se adopte; la ficha cita Deb y Das (2010) y Esterhuizen, Filz y Duncan (2001) para otras cosas | Cierre, resistencia y pendiente desplazamiento normal-tangencial; con un ensayo de tensiones uniformes (P19 vio que el de la ficha gira) |
| `VER-JNT-22`, corte directo, hiperbólico con ablandamiento | Esterhuizen, Filz y Duncan (2001), experimental | Curvas tensión tangencial-desplazamiento frente a los ensayos |
| `VER-STR-24`, empuje pasivo sobre un muro | Chen (la ficha da 2007 en el texto y 2008 en la bibliografía) | Carga de colapso con tres adherencias muro-suelo; necesita 007 y 008 |
| Identidades | — | Parcela del elemento junta (σn y τ uniformes exactos); sólido rígido a través de la junta; junta muy rígida, igual al medio continuo; junta sin rigidez tangencial, caras lisas; referencia y Rust idénticas |

Los casos de SSR con juntas (`VER-JNT-01` a `-21`) necesitan además la 009 y casi todos las redes:
los de Goodman y Bray (1976) son **aproximados**, los de Alejano et al. y de Lorig y Varona,
**numérica publicada**, y los que solo tienen otro programa, **comparaciones**. Ninguno cierra la
fase según el plan. `VER-CON-02` (fase 4), `VER-DYN-13` y los `VER-XFM` (fase 7) usan la ley.

## Fuentes por conseguir

- Goodman, Taylor y Brekke (1968), el elemento junta (volumen por comprobar: el catálogo da «14» y
  «R.D.»). La regla de integración del elemento, con fuente.
- Bandis, Lumsden y Barton (1983); Barton y Choubey (1977). Jaeger, Cook y Zimmerman (2007), en la
  bibliografía, trata la rigidez normal y la resistencia de juntas (por comprobar si basta).
- La dilatancia de la junta y su límite: la ficha de JNT-23 la describe, sin fuente propia.
- Esterhuizen, Filz y Duncan (2001); Deb y Das (2009, 2010); Jaeger y Cook (1979); Chen (2007 u
  2008); Goodman y Bray (1976).
- Dight (1982), tesis, y Grasselli (2005), para el bulón-junta (T02 §2 marca una transcripción
  dudosa de la fórmula).
- Baecher, Lanney y Einstein (1978) y Dershowitz (1985) para las redes; la formulación original de
  Veneziano no se cita; la regularización de Voronoi no se describe (T04).

## Requisitos no funcionales

- El motor recibe pares de nudos y la ley de cada elemento junta, sin contornos (regla 11).
- Una red con miles de juntas tiene que mallarse y calcularse en un tiempo razonable (a medir con la
  011). Sin dependencias nuevas.

## Casos límite

- Juntas que se cortan en T y en X; junta que termina dentro de un material; junta sobre un
  contorno de material o sobre el exterior; junta que entra en una excavación.
- Juntas muy cortas o casi paralelas (ángulos de entrada pequeños: spec 003); muchas juntas.
- Rigidez muy alta (condicionamiento) o nula; junta abierta en toda su longitud (bloque suelto:
  modelo sin sujetar, spec 002).
- Inversión del sentido de corte con dilatancia direccional; presión normal que cambia por fase.

## Fuera de alcance

- La presión de agua dentro de la junta (fase 4); XFEM (fase 7).
- Juntas ubicuas o roca diaclasada como ley del material (fase 5): STR-06 es una junta discreta y
  queda aquí (duda 9).
- La interfaz estructural (016) y los gráficos de juntas en la interpretación (016).

## Criterios de finalización

- [ ] Dudas convertidas en decisiones y aprobadas por la propietaria
- [ ] Cada ley probada en el ensayo de corte uniforme contra su fuente (RF-7)
- [ ] Todos los RF con su test en verde, y la regla 7 en cada ajuste nuevo
- [ ] STR-28 y STR-06 dentro de la tolerancia fijada antes de medir, con la malla y el estudio de
      convergencia que la justifican (regla 9); los demás de la tabla, según se decida
- [ ] Las identidades, en verde y con dientes; referencia y Rust idénticas
- [ ] Changelog con lo encontrado; fichas con su «Seguimiento»

## Dudas abiertas

- [NECESITA ACLARACIÓN] **1. Dilatancia** (S06, duda 12): la referencia observada no la tiene y
  JNT-23 la pide. ¿Con límite por desplazamiento, opción direccional (dmín, dmáx) y en qué
  criterios? La parte de totales e incrementos ya está fijada (spec 001, D2).
- [NECESITA ACLARACIÓN] **2. Formulación del elemento**: espesor nulo en desplazamientos relativos
  (Goodman et al. 1968) u otra; regla de integración; axisimetría, sí o no.
- [NECESITA ACLARACIÓN] **3. Nudos duplicados**: en el mallador de este programa o pedidos al núcleo;
  qué pasa en un extremo cerrado y en un cruce de juntas.
- [NECESITA ACLARACIÓN] **4. Junta en tracción**: la referencia multiplica la rigidez por 0.01 cuando
  se abre (ajuste del proyecto, P19). ¿Se adopta, con otro valor o sin rigidez?
- [NECESITA ACLARACIÓN] **5. «Deformación inicial de la junta»**, marcada por defecto en la
  referencia (D07): qué hace y si mueve el número.
- [NECESITA ACLARACIÓN] **6. Redes**: cuáles de los seis modelos observados (paralelas deterministas
  y estadísticas, cruzadas, Baecher, Veneziano, Voronoi); medida de intensidad; recorte; aquí o en
  una spec propia.
- [NECESITA ACLARACIÓN] **7. SSR de las juntas**: qué por defecto (spec 009, su duda de juntas).
- [NECESITA ACLARACIÓN] **8. Bulón-junta**: ningún caso del índice lo valida y la fórmula tiene una
  transcripción dudosa. ¿Aquí con un test de la fórmula, o se aplaza hasta tener un caso?
- [NECESITA ACLARACIÓN] **9. STR-06**: el plan lo llama «roca diaclasada», pero la ficha es una sola
  junta discreta (`JUNTA`), no la ley de roca diaclasada de la fase 5. Se propone dejarlo aquí.
- [NECESITA ACLARACIÓN] **10. Barton-Bandis**: solo como resistencia, o también con la rigidez
  normal que depende de la tensión (Bandis et al. 1983).
