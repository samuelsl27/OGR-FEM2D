# Spec 007 — Tolerancia, colapso y escalones

> **Aprobada (2026-11-28)**, con D1–D14 tal como se propusieron. Fase 2 del plan de desarrollo
> (`spec/constitution/plan_de_desarrollo.md`, «Spec 007 — Tolerancia, colapso y escalones»). Solo el
> **qué** y el **porqué**; el cómo, en `plan.md`. Las dudas del borrador (2026-11-23) son ahora las
> decisiones D1–D14 (abajo). Versiones: **v0.0.16** (parte A, el motor y STR-05) y
> **v0.0.17** (parte B, el modelo, las operaciones y la interfaz).

## La revisión (2026-11-28)

- [x] Contrastada con el código y con las specs cerradas desde el borrador (004 a 006). **Ya está
  hecho**:
  - `engine/reference/solver.py`, `solve_stage`: escalones iguales, Newton completo con la tangente
    consistente, la (4.77) de de Souza Neto et al. (2008) dividida por la norma de la carga de la
    fase (no por ‖f_ext‖, que es cero al final de una excavación), la partición en dos del
    incremento que falla (§5.4.3) con `max_cuts` contado en toda la fase, el suelo de redondeo
    `NO_LOAD` (1e-12 de la mayor fuerza en juego) y `NotConvergedError` con la historia. **RF-3 está
    casi hecho**: falta que el error diga hasta qué factor de carga llegó la fase;
  - `engine/model.py`, `Stage`: los ajustes por fase, con `steps = 1`, `tolerance = 1e-8`,
    `max_iterations = 25` y `max_cuts = 0` por defecto. **Ninguno tiene fuente**: la spec 001 los
    dejó para aquí;
  - el modelo (004, D9) es **solo elástico** y no tiene ajustes del cálculo: la traducción usa los
    del motor, y `translate.deciding_values` ya los lista con el motivo «the engine's default (D9)».
    **El Mohr-Coulomb del modelo es de la 008** (004, D9): STR-05 se hace aquí en el motor, como los
    casos 001 a 004;
  - el `.h5` (005) ya guarda por fase la historia (escalón, iteración, residuo), los escalones, la
    tolerancia y las particiones; **no guarda** los incrementos (de qué factor a cuál, y por qué se
    partió cada uno);
  - el progreso (006, D9) lleva fase, escalón e iteración, pero solo se avisa al empezar y al
    terminar cada fase; la ventana de cálculo dice «escalones, última iteración». Cancelar es entre
    fases o matando el proceso;
  - el bucle es de Python para las dos variantes; Rust hace el trabajo por punto (una llamada por
    iteración). **Una estrategia nueva en `solve_stage` vale para las dos sin tocar `rust/`.** Desde
    el 2026-11-28 el motor por defecto es el de Rust.
- [x] Mirados el núcleo (v0.2.13) y OGR Slip2D: **ninguno tiene un bucle elastoplástico**. Lo de aquí
  es propio; `ogr_core.progress` ya basta para el progreso por iteración.
- [x] Fuentes leídas (2026-11-28), con página en «Formulación» del plan:
  - **de Souza Neto, Perić y Owen (2008)** (dSN):
    - la (4.77) es un criterio en fuerza, sin valor recomendado («a sufficiently small specified
      tolerance»); sus ejemplos usan 1e-7 % o 1e-12, «far smaller than that required for
      engineering purposes» (§9.5);
    - **la definición de la carga de colapso con carga impuesta**: «the load above which
      equilibrium iterations can no longer converge for a sufficiently small load increment»
      (§7.5.3, pág. 251), sin decir qué es «suficientemente pequeño»;
    - **la zapata en faja de Tresca** (§8.4.3, págs. 346–349): rígida y lisa, con el asiento
      impuesto en 14 escalones, Newton completo; P_lim/c ≈ 5.19, «less than 1 % above» la de
      Prandtl y Hill, (2 + π) c (ec. 7.178, que cita Hill 1950). La meseta de la curva
      carga–asiento es como detecta el límite;
    - §5.4.1: el factor de carga de cada escalón es un **dato**. **No hay regla para el número ni
      para el reparto de los escalones** con carga impuesta; la regla de tamaño automático
      (ec. 5.3, l_next = l·n_des/n_act) es **solo de la longitud de arco** (§5.4.2);
    - la búsqueda lineal global **no la describe**: «not available in HYPLAS… (Crisfield, 1991)»
      (§5.4.3). La longitud de arco cilíndrica sí (§4.4, Box 4.4);
    - con φ = ψ = 0 los retornos de Mohr-Coulomb son los de Tresca (Remark 8.2), sin vértice.
  - **Clausen (2007)**: criterio en fuerza, «usually around 1e-3»; con desplazamiento impuesto, la
    tolerancia se mide sobre las reacciones (ec. 62). Con ψ = 0 no asociado, «with the denser
    meshes the calculation… needs an increased number of load steps… related to the
    non-uniqueness… not related to the stress return» (apéndice B, pág. 151). Cita Prandtl (1921),
    *ZAMM* 1(1), 15–20.
  - **Zienkiewicz y Taylor (2000), vol. 1**: solo §20.4.3 (Newton, tolerancia 1e-12 del residuo
    inicial en su programa docente). La solución no lineal está en el vol. 2, que no está.
  - Lo que **no hay en ninguna**: una tolerancia por defecto justificada, un criterio de energía o
    de desplazamiento, una regla para el número o el reparto de escalones, el algoritmo de la
    búsqueda lineal.
- [x] Ficha VER-STR-05 y su «Seguimiento» (vacío) releídos. **La ficha no fija** el dominio, los
  apoyos, los niveles de carga ni la tolerancia; sí fija la zapata (flexible, carga uniforme), la
  semianchura (b = 3 m) y el material (E = 250 MPa, ν = 0.2, c = 0.1 MPa, φ = 0). Lo de P13 (dominio
  de 15 × 10 m, ocho fases de 0.20 a 0.52 MPa, tracción de 100 MPa) es elección del análisis o
  comportamiento del programa de referencia. El programa de referencia itera con la **rigidez
  inicial** y un criterio de energía sin fuente: con 0.001 la fase de 0.52 MPa «convergía», con 1e-4
  no, tras 500 iteraciones. Su reparto geométrico (razón 0.7) y su regla de escalones (T05) no tienen
  fuente.
- [x] Las dudas, convertidas en decisiones (D1–D14), aprobadas el 2026-11-28.

## Depende de

- Specs 001 a 006, cerradas: el motor con Mohr-Coulomb, la malla estructurada de la faja (caso 004),
  el modelo, el `.h5` y su historia, la ventana de cálculo y su progreso.
- La 008 y la 009 dependen de esta: su criterio de no convergencia es el de aquí (D2), y la 008 trae
  el Mohr-Coulomb al modelo, con el que STR-05 tendrá su `modelo.ogrfem2d`.

## Contexto y objetivo

La spec 001 dejó un Newton completo con la tangente consistente, escalones iguales y la partición
automática del incremento, con una tolerancia estricta **solo para la prueba**: la tolerancia por
defecto del programa quedó para esta spec (enmienda 3 de la constitución). La razón es la
reproducción P13 de STR-05 (zapata de Prandtl): con la tolerancia por defecto del programa de
referencia, una fase cargada por encima del colapso «convergía»; con una diez veces menor fallaba
donde debía (duda 8 de S06). Si «no converge» no significa «no hay equilibrio», el SSR de la 009 no
tiene criterio de rotura.

Hay además tres pendientes de la spec 001 y de su changelog: Newton diverge con ψ = 0° en mallas
finas (anillo de 21 m con 16 × 48 divisiones; caso 002 con 16 × 64), y la partición, con los
ajustes de entonces, no lo arregló; el resultado de Mohr-Coulomb depende del número de escalones; y
el reparto de escalones es uniforme y fijado a mano. El objetivo es que una carga por encima del
colapso no se dé por convergida con los valores por defecto, que esos valores salgan de un estudio
escrito antes de medir y se muestren con el resultado, y que Newton sea robusto en los casos que hoy
fallan, o que se sepa por qué no.

## Usuarios / actores

- **Ingeniero**, que necesita saber si una carga es admisible y si el programa le dice la verdad
  cuando no lo es.
- **Investigador**, que cambia la tolerancia, los escalones o las particiones y quiere ver cuánto
  mueven.
- **La spec 009**, que usa la no convergencia como criterio de rotura de cada factor de prueba.
- **Agente vía MCP**, que lanza el mismo cálculo a través de `ogr_fem2d.api`.

## Historias de usuario

- H1: Como ingeniero quiero que una carga por encima de la de colapso no salga como convergida con
  los valores por defecto, para no tomar por estable lo que no lo es.
- H2: Como ingeniero quiero ver junto al resultado la tolerancia, el criterio de convergencia, el
  número máximo de iteraciones, el número y reparto de escalones y las particiones usadas, para saber
  qué he calculado (regla 12).
- H3: Como ingeniero quiero la curva carga–asiento de una zapata, con la meseta donde la da la
  solución de Prandtl, para fiarme del criterio de colapso.
- H4: Como investigador quiero cambiar los escalones y las particiones y ver en el registro cuántas
  veces se partió un incremento y hasta qué carga llegó la fase, para juzgar la robustez.

## Requisitos funcionales (EARS)

**Convergencia y colapso**

- RF-1: EL SISTEMA tiene un criterio de convergencia (D1), una tolerancia, un número máximo de
  iteraciones y un número máximo de particiones por defecto, fijados con STR-05 y el caso 002 por un
  estudio escrito antes de medir (D1, D3) y documentados con él.
- RF-2: SI una fase se carga por encima de la carga de colapso, ENTONCES EL SISTEMA, con los valores
  por defecto, no la da por convergida (en STR-05, la fase por encima de la banda de tolerancia de la
  carga de Prandtl, D6).
- RF-3: CUANDO un incremento no alcanza la tolerancia en el número máximo de iteraciones después de
  las particiones permitidas, EL SISTEMA declara la fase no convergida con la fase, el incremento, las
  iteraciones, la historia del residuo y **el factor de carga que alcanzó** (D2), y no presenta el
  estado como resultado válido (amplía el RF-6 de la spec 001).
- RF-4: CUANDO un incremento converge por el suelo de redondeo y no por la tolerancia, EL SISTEMA lo
  dice en el resultado (D12).

**Escalones**

- RF-5: MIENTRAS el usuario no fije los escalones, EL SISTEMA usa el modo por defecto de D3
  (escalones iguales o el tamaño automático de Crisfield 1991, ec. 9.40, el que elija el estudio),
  partidos donde haga falta (§5.4.3); el modo, el número, el reparto y las particiones van con el
  resultado (regla 12). *Modificado el 2026-11-28* (D3).
- RF-6: CUANDO el usuario fija el número de escalones o su reparto (la lista de factores de carga,
  dSN §5.4.1), EL SISTEMA los usa y lo dice.

**Robustez**

- RF-7: CUANDO un incremento no converge, un punto no se puede actualizar o la tangente es
  singular, EL SISTEMA aplica la estrategia de D5 (la partición del incremento y, si el estudio la
  elige, la búsqueda lineal de Crisfield 1991, §9.2) y el resultado dice cuántas veces y en qué
  incremento actuó.
- RF-8: EL SISTEMA resuelve el caso 002 con ψ = 0° en la malla de 16 × 64 y el anillo de 21 m con
  16 × 48 divisiones, que hoy no convergen, o el changelog documenta por qué no puede, con el
  diagnóstico de D5.

**Fases e historia**

- RF-9: EL SISTEMA resuelve una secuencia de fases de carga en totales (D2 de la spec 001) y guarda
  por fase sus incrementos (factor inicial y final, estado y motivo de cada partición) y por
  iteración el residuo; la curva carga–desplazamiento se hace con las fases (D11).
- RF-10: CUANDO se calcula un modelo, EL SISTEMA avisa del progreso por escalón e iteración, con el
  residuo, y se puede cancelar entre dos iteraciones (D10).

**Reglas transversales**

- RF-11: Cada ajuste (tolerancia, iteraciones, escalones, reparto, particiones) tiene un test que
  demuestra que mueve el número (regla 7).
- RF-12: Mohr-Coulomb con φ = ψ = 0 (Tresca, el material de STR-05) se prueba en un punto de Gauss
  contra el retorno de Tresca de su fuente antes de usarse en el modelo (regla 8; D14).
- RF-13: La referencia en Python va primero y es el oráculo; la identidad con Rust se comprueba
  (ADR-0001). El motor no conoce la interfaz (regla 11): el progreso y la cancelación entran como
  funciones.

## Validación numérica

| Caso | Fuente científica | Qué se compara |
|---|---|---|
| `validacion/casos/008-prandtl-zapata-tresca` (nuevo, ficha `VER-STR-05`), **zapata rígida y lisa con el asiento impuesto** | Prandtl (1921) y Hill (1950), en dSN (2008), ec. (7.178): P_lim = (2 + π) c | La meseta de la reacción media bajo la zapata frente a (2 + π) c, con la tolerancia de D6 escrita antes de medir; la curva carga–asiento (H3) |
| El mismo caso, **zapata flexible con carga uniforme por fases** (la de la ficha) | La misma (D6) | Que las fases por debajo de la banda converjan y la de encima no, con los valores por defecto (RF-2) |
| `validacion/casos/002` con ψ = 0° y la malla de 16 × 64 | Salençon (1969) con la zona de arista (D8 de la spec 001) | Que converja con la estrategia de D5 y cumpla la tolerancia del caso, o el hallazgo (RF-8) |
| Anillo de 21 m, Mohr-Coulomb, 16 × 48, ψ = 0° | Identidad: la solución exacta del anillo finito (`salencon_edge_finite`, spec 001) | Lo mismo (RF-8) |
| Punto de Gauss, Tresca | dSN §8.1 (retorno de Tresca) y Remark 8.2 | Mohr-Coulomb con φ = ψ = 0 frente al retorno de Tresca, en el plano y en las dos aristas; nunca pide el vértice (RF-12) |
| Identidades | — | Una fase elástica converge en una iteración con cualquier tolerancia; el resultado elástico no depende de los escalones; una fase que descarga a la zona elástica converge en una iteración; equilibrio global de las reacciones en cada fase; con y sin el aviso de progreso, bit a bit |
| Estudio de dominio y de malla de STR-05 | — | Tres mallas anidadas cada vez más finas y el dominio doblado; la tolerancia, antes de medir (regla 9; D7) |

Los asientos y cargas de la reproducción P13 **no son valor esperado** (`validacion/README.md`):
solo explican el comportamiento del programa de referencia. El 5.19 de dSN tampoco: es lo que da su
malla de Q8, y aquí el valor esperado es (2 + π) c.

## Fuentes por conseguir

- ~~Crisfield (1991)~~: **conseguido el 2026-11-28** (la propietaria). Leídos §2.4, ec. (2.30)
  (criterio en fuerza, «typical values for β lie between 0.001 and 0.01»), §9.2 (búsqueda lineal,
  subrutinas SEARCH y LSLOOP), §9.5 (tamaño automático, ec. 9.40; partición, ec. 9.42) y §9.5.4
  (criterios: los de energía, «with great caution»). Libro = PDF − 15.
- **Hill (1950)**, *The Mathematical Theory of Plasticity*, o **Prandtl (1921)**, *ZAMM* 1(1),
  15–20: la fuente original de (2 + π) c, y la que diría si la zapata flexible con carga uniforme
  tiene la misma carga límite que la rígida y lisa (D6). Mientras no estén, el valor se cita por dSN
  (ec. 7.178), como los demás casos citan por un libro.
- **Sloan y Randolph (1982)**, *Int. J. Numer. Anal. Methods Geomech.* 6, 47–76, sobre las cargas
  de colapso con triángulos de seis nudos en deformación plana: el riesgo de bloqueo del T6 con flujo
  incompresible (plan, «Riesgos»).
- Griffiths y Lane (1999), para la 009; Z&T (2000) vol. 2, cap. 2; Bathe (1996). No hacen falta
  para cerrar esta spec.

## Requisitos no funcionales

- El coste por fase no debe crecer sin medida: cualquier cambio del bucle se mide A/B en el mismo
  proceso, como en la spec 001; el bucle en Rust es cosa de la 011.
- La ventana de cálculo (006) sigue el progreso por fase, escalón e iteración y se puede cancelar sin
  congelarse.
- Python ≥ 3.11 y las tres plataformas de la CI. No se toca `rust/` ni la CI: commits en `main`.

## Casos límite

- Carga exactamente en la de colapso, y una fracción mínima por encima.
- Una fase que descarga (de vuelta a la zona elástica): converge en una iteración.
- Retorno al vértice con ψ = 0°, que la fuente no admite: un incremento que lo pide se parte (D5).
- Puntos que cambian de región del retorno en cada iteración (la oscilación de la T8 de la 001).
- Tolerancia inalcanzable por redondeo frente a carga pequeña sobre fuerzas grandes (v0.0.2).
- Particiones agotadas (`max_cuts`) y número máximo de iteraciones igual a 1.
- Fase sin cambios: no se resuelve y el resultado lo dice (spec 002).
- Cancelar dentro de una fase: la fase no se escribe y las anteriores quedan (D10).

## Fuera de alcance

- El Mohr-Coulomb en el modelo y las leyes nuevas (008); la reducción de resistencia (009).
- **La longitud de arco** (D5): cambia qué es una fase en totales; hará falta con el ablandamiento
  (024). Su fuente (dSN §4.4 y §5.4.2) está.
- Un criterio de energía o de desplazamiento (D1): Crisfield (1991, §9.5.4) desaconseja el de
  desplazamiento solo y el de energía «should be used with great caution».
- Llevar el bucle al código compilado (011). Fases de construcción completas (012).
- Grandes deformaciones, análisis dinámico, rigidez inicial (descartada en la spec 001, D7).

## Criterios de finalización

- [ ] Todos los RF con su test en verde
- [ ] STR-05 dentro de la tolerancia fijada antes de medir, con su estudio de dominio y de malla
- [ ] Los dos casos de robustez convergen o el incumplimiento queda reportado como hallazgo
- [ ] Valores por defecto fijados por su estudio, documentados y mostrados con el resultado (regla 12)
- [ ] Cada ajuste con su test que mueve el número (regla 7)
- [ ] Todo texto nuevo con traducción española y toda acción nueva en un menú
- [ ] Los casos 001 a 007, dentro de su tolerancia (bit a bit los que no usan los valores por
      defecto nuevos)
- [ ] Un changelog por parte registrando qué se encontró; la ficha STR-05 con su «Seguimiento»

## Decisiones (2026-11-28)

Aprobadas el 2026-11-28, tal como se propusieron. dSN es de Souza Neto, Perić y Owen (2008); las referencias
P13, T01, T05 y S06 son del análisis de interfaz (`../Referencias/Doc_Guia/Analisis_interfaz_funcionamiento/`).

| # | Duda del borrador | Decisión | Por qué |
|---|---|---|---|
| D1 | Duda 8: el criterio y la tolerancia por defecto | **El criterio en fuerza de ahora**: ‖r‖ / ‖carga de la fase‖ ≤ tol (dSN, ec. 4.77, con el denominador de la v0.0.1). **El valor por defecto sale de un estudio escrito antes de medir** (T6): se barre tol = 1e-3, 1e-4, …, 1e-10 en STR-05 (las dos variantes) y en el caso 002, y se toma la mayor que cumple (i) la fase de 0.95 (2 + π) c converge y la de 1.05 (2 + π) c no; (ii) la carga de la meseta y el ur(a) del 002 se apartan de los de 1e-10 menos de 1/10 de la tolerancia de su caso. **El defecto es esa tolerancia dividida por 100** (con Newton cuadrático, el margen cuesta una iteración). Ningún criterio de energía ni de desplazamiento | Ninguna fuente da un valor por defecto (dSN, Z&T, Clausen: «usually around 1e-3»). El de energía del programa de referencia no tiene fuente (T01), y su 0.001 no se traslada: él itera con la rigidez inicial, que converge despacio y deja «converger» por encima del colapso (P13); con Newton completo el residuo cae cuadráticamente donde hay equilibrio y se estanca donde no. Que esto se cumpla es lo que mide el estudio, no se supone |
| D2 | Duda 8 (c, d): el criterio de colapso | **El de dSN (§7.5.3)**: la carga de colapso es aquella por encima de la cual las iteraciones ya no convergen con un incremento suficientemente pequeño. En el programa: **una fase no converge cuando un incremento sigue sin converger después de las particiones permitidas** (§5.4.3), y el error dice **hasta qué factor de carga llegó** (el último convergido), que acota el colapso. «Suficientemente pequeño» es el incremento más pequeño que las particiones permiten, y el resultado lo dice. La meseta de la curva carga–asiento se usa **para validar** (H3), no como criterio automático | Es la única definición con fuente. Con carga impuesta no hay meseta que mirar (la fase falla antes); con el asiento impuesto sí, y es como valida dSN. Dar el factor alcanzado convierte el fallo en información útil para la 009 |
| D3 | Reparto y número de escalones | *Modificada el 2026-11-28 por la propietaria, al leer Crisfield (1991): **se programan los dos modos**, los escalones iguales de abajo y **el tamaño automático de Crisfield (1991), ec. (9.40)**, Δλ_nuevo = Δλ_viejo · (I_d / I_viejo)^(1/2) (n = 1/2, de Ramm), con I_d las iteraciones deseadas («I_d ≃ 3») y un incremento inicial, un máximo y, si se quiere, un mínimo; los dos con su test de la regla 7. **El estudio de la T7, con su protocolo escrito antes de medir, elige cuál va por defecto y con qué parámetros.** La partición sigue igual. La premisa de abajo («no hay regla con fuente») era falsa: lo que sigue queda como estaba aprobado.* **Escalones iguales, partidos donde haga falta**; el número por defecto, fijado en el mismo estudio (T6): el menor de 5, 10 y 20 con el que STR-05 y el 002 convergen y se apartan del doble de escalones menos de 1/4 de la tolerancia de su caso. **El usuario puede dar el número o la lista de factores de carga** (dSN §5.4.1). Sin progresión geométrica, sin la regla de T05, sin tamaño adaptativo | No hay regla con fuente para la carga impuesta: dSN da los factores como dato (§5.4.1) y su regla adaptativa (ec. 5.3) es de la longitud de arco; T05 y la razón 0.7 de P13 no tienen fuente. Una regla extendida a otro método que el de su fuente sería propia |
| D4 | El número de escalones mueve el resultado plástico | **Como la malla (regla 9)**: cada caso fija sus escalones en su `esperado.json`; el programa usa los de D3 y los muestra. Sin criterio de independencia de escalones | Ninguna fuente da uno. El 0.31 % de la v0.0.1 viene de la proyección de Euler implícito, exacta solo dentro de una región: es del método, y se acota con el estudio |
| D5 | La estrategia de robustez | **(1) Primero el diagnóstico** (regla 6, T3): en el 002 con 16 × 64 y en el anillo de 16 × 48 con ψ = 0°, en qué incremento falla, por qué (puntos que piden el vértice, regiones que oscilan) y qué pasa con más escalones y más particiones; se reporta antes de cambiar nada. **(2) La estrategia de esta spec es la partición del incremento** (dSN §5.4.3), **activa por defecto** (`max_cuts` > 0, del estudio de D1), y más escalones (Clausen 2007, apéndice B: con ψ = 0 y mallas densas hacen falta más). **(3) La búsqueda lineal, solo con Crisfield (1991) leído**; si (2) no basta y la fuente no está, RF-8 queda como hallazgo. *Al cerrar la T2 (2026-11-28): (2) no basta (barrera de nivel de carga), y la propietaria pasó Crisfield (1991): la búsqueda lineal de su §9.2 entra en la T9, medida A/B; si tampoco basta, RF-8 queda como hallazgo. Y una tangente singular cuenta como incremento que falla (la anomalía de la T2, corregida en la T3 con el OK de la propietaria).* **(4) La longitud de arco, fuera** | La partición es la única estrategia con fuente que este motor ya tiene, y la que usa el programa de los autores. La v0.0.1 la probó con pocas particiones y sin diagnóstico. La longitud de arco cambia la fase en totales (la carga deja de ser dato) y no hace falta para STR-05, que se valida con el asiento impuesto, como dSN |
| D6 | Cómo se carga STR-05 | **Un caso nuevo en el motor**, `008-prandtl-zapata-tresca` (`caso.md` y `esperado.json`, como 001 a 004; el `modelo.ogrfem2d` llega con el Mohr-Coulomb de la 008). Material de la ficha (E = 250 MPa, ν = 0.2, c = 0.1 MPa, φ = ψ = 0, sin peso ni tensión inicial) y su semianchura (b = 3 m). **Dos variantes**: (a) **zapata rígida y lisa con el asiento impuesto** en escalones (la de dSN §8.4.3): la presión media es la suma de las reacciones bajo la zapata dividida por b; (b) **la de la ficha, carga uniforme por fases en totales** a 0.4, 0.8, 0.9 y 0.95 (2 + π) c, y una fase a 1.05 (2 + π) c que no debe converger. Medio modelo por simetría, rodillos en los lados y base fija; **dominio propio**, empezando por la proporción de dSN (5 B de ancho y de fondo, B = 2b) y con su estudio. Malla estructurada graduada de T6 (la del caso 004), fina junto al borde de la zapata. **Tolerancia, antes de medir: \|P_lim / ((2 + π) c) − 1\| ≤ 2 %**, con el error bajando al refinar. Punto de control: el asiento en el eje | La ficha deja libres el dominio, los apoyos y los niveles. Con el asiento impuesto la meseta existe y es la validación de la fuente; con la carga impuesta se prueba lo que pide RF-2. Que la carga uniforme tenga la misma carga límite (el campo de Prandtl es uniforme bajo la faja y su cuña central baja como un sólido) **está por comprobar en Hill o Prandtl** (Fuentes): por eso la variante (b) se juzga con la banda de ±5 % y no con la meseta. El 2 % es el del caso 002; dSN da menos del 1 % con 135 Q8 |
| D7 | Duda 3 de S06: convergencia de malla | **El mismo método de la spec 001**: tres mallas anidadas, la tolerancia antes de medir, la malla del caso la primera que cumple; más el estudio de dominio (spec 002, D4) | Ya funcionó en 001 a 007 |
| D8 | Duda 6 de S06: ¿basta dSN? | **Sí, para todo lo que entra**: Newton, el criterio, la partición, la definición de colapso, Tresca y la zapata. La búsqueda lineal pide Crisfield (1991); el original de Prandtl o Hill, preferible (Fuentes) | Lo leído el 2026-11-28 (la revisión) |
| D9 | De la 004 (su D9): los ajustes del cálculo en el modelo | **Un bloque de ajustes del cálculo por proyecto** en el `.ogrfem2d` (`format_version` 2, que lee el 1 con los valores por defecto): tolerancia, iteraciones máximas, escalones (número o lista de factores) y particiones máximas, los mismos para todas las fases. Con su edición pura, su operación, su diálogo en Análisis → Ajustes del cálculo, y los `deciding_values` leídos del modelo con el motivo «estudio de la spec 007» | Por fase lo admite el motor, pero nada lo pide todavía (la 012, con el *load split*, puede pedirlo). Un bloque por proyecto es lo que el usuario reconoce del programa de referencia y de Slip2D. En elástico estos ajustes no mueven el número; se exponen ya porque la 008 los necesita y la regla 12 pide verlos |
| D10 | Nueva: el progreso y la cancelación dentro de la fase | `solve_stage` recibe dos funciones opcionales: **`progress`**, avisada en cada iteración (escalón, iteración, residuo, factor de carga, partición), y **`should_stop`**, preguntada entre dos iteraciones. `calculate` las pasa; el trabajo en subproceso las escribe y las lee; la ventana de cálculo dice «escalón i de n, iteración k de máx., residuo» y guarda el registro. Cancelar dentro de una fase no escribe esa fase: quedan las anteriores y el `.h5` dice `cancelled` | Es lo que la 006 dejó a esta (su D9). Dos funciones no hacen que el motor conozca la interfaz (regla 11). Cancelar entre iteraciones para de verdad una fase larga sin matar el proceso |
| D11 | Nueva: lo que guarda el `.h5` | **Por fase, sus incrementos** (factor inicial y final, estado y motivo de la partición) además de la historia que ya guarda; el informe y la interpretación los muestran. **Sin campos por escalón**: la curva carga–desplazamiento se hace con las fases, que van en totales (spec 001, D2), y se consulta con la de la 005 frente a la fase | Guardar los campos de cada escalón multiplicaría el archivo sin que nada lo pida; con fases en totales, cada punto de la curva es una fase |
| D12 | RF-4: el suelo de redondeo | **Se queda** (`NO_LOAD`, 1e-12 de la mayor fuerza en juego), pero **el incremento que converge por el suelo y no por la tolerancia queda marcado** en sus incrementos, y el resultado lo dice | Distingue el redondeo de una convergencia física sin cambiar ningún número de los casos (la v0.0.2 ya midió que donde la tolerancia se alcanza el suelo no actúa) |
| D13 | Nueva: cómo partirla | **Dos partes**: **A, v0.0.16**, el motor y STR-05 (Tresca en un punto, diagnóstico, progreso, incrementos, el caso, los estudios y los valores por defecto); **B, v0.0.17**, el modelo, las operaciones, el `.h5`, la interfaz y el cierre. Sin rama: no se toca `rust/` ni la CI | Los valores por defecto los fija la A; la B los lleva al modelo y a la pantalla. Cada parte queda cerrada y en verde |
| D14 | RF-12: Tresca en un punto de Gauss | **Mohr-Coulomb con φ = ψ = 0 frente al retorno de Tresca de dSN §8.1**, escrito aparte en el test desde sus boxes (Remark 8.2 dice que deben coincidir), en el plano y en las dos aristas, con estados aleatorios y en una trayectoria de corte simple en deformación plana (τ llega a c); con φ = 0 el vértice nunca se pide. Y la identidad con Rust | Es una comparación con la fuente por otro camino, no consigo mismo (regla 1). Que el vértice no se pida es lo que hace usable el código actual con φ = 0 |

### Consecuencias en el resto del proyecto

- `engine/model.py`, `Stage`: los valores por defecto cambian con el estudio de D1 y D3. Los casos
  001 a 007 fijan los suyos o usan los del motor: los que usan los del motor (005 a 007, elásticos)
  no cambian de número (en elástico, una iteración); se comprueba.
- `ogr_file.py`: `format_version` 2 (D9). `store.py`: el esquema del `.h5` gana los incrementos
  (D11); un `.h5` de antes se sigue leyendo.
- La 004 (su D9) queda cumplida aquí en lo que toca a los ajustes; el Mohr-Coulomb sigue en la 008.
- La 009 hereda D2: cada factor de prueba que no converge dice hasta dónde llegó.
- `Referencias/Bibliografia/00_LEEME.md`: Crisfield (1991), con lo leído.
- Ficha VER-STR-05: su «Seguimiento» con el caso 008.
