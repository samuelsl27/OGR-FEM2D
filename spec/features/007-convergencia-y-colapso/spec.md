# Spec 007 — Tolerancia, colapso y escalones

> **Borrador de alcance (2026-11-23), sin aprobar.** Fase 2 del plan de desarrollo
> (`spec/constitution/plan_de_desarrollo.md`, «Spec 007 — Tolerancia, colapso y escalones»). Solo
> el **qué** y el **porqué**, sin fórmulas ni decisiones tomadas. **Antes de abrirla hay que
> reevaluarla** (sección siguiente); después, plan y tareas con el OK de la propietaria.

## Antes de abrirla: reevaluar esta spec

Este borrador se escribió antes de que existieran las specs que lo preceden; el código, el núcleo y
OGR Slip2D habrán avanzado. Al abrirla, y antes de escribir el plan:

- [ ] Contrastarla con el código de este programa y con las specs cerradas desde el 2026-11-23: qué
      ya está hecho, qué cambió y qué se movió de sitio.
- [ ] Mirar qué tienen ya OGR Slip2D y `ogr_core` en la etiqueta fijada. Lo genérico se pide a la
      sesión de OGR-Core, no se copia (`AGENTS.md`, «Un núcleo y varios programas»). Puntos de
      partida vistos al escribir el borrador:
      `ogr_fem2d/engine/reference/solver.py` (`solve_stage`: escalones iguales, Newton completo
      con la tangente consistente, partición del incremento con `max_cuts` contados en toda la
      fase, comprobación de la ec. 4.77 de de Souza Neto et al. 2008 y el suelo de redondeo
      `NO_LOAD` de la v0.0.2); `ogr_fem2d/engine/analysis.py` (fases en totales, D2 de la
      spec 001); `ogr_fem2d/engine/interface.py` y `rust/src/lib.rs` (una llamada por iteración).
      En el núcleo, `ogr_core/progress.py` (fase y puntos de control de un cálculo en curso). Ni el
      núcleo ni Slip2D tienen un bucle elastoplástico: lo de aquí es propio.
- [ ] Leer y comprobar las fuentes de «Validación numérica» y de «Fuentes por conseguir»; las fichas
      de los casos no son fuente.
- [ ] Releer las fichas de los casos que la cierran y su «Seguimiento».
- [ ] Convertir las «Dudas abiertas» en decisiones propuestas (D1, D2…) con su porqué, para el OK de
      la propietaria.

## Depende de

- Spec 002 (motor elástico general) y spec 003 (malla), cerradas: entrada discreta, fases en
  totales, cargas distribuidas, malla de calidad conocida para STR-05.
- Spec `004-modelo-y-proyecto`: las fases como dimensión del modelo y los ajustes del solver con sus
  valores por defecto a la vista (regla 12).
- Spec `005-resultados`: la historia por fase y escalón en `modelo.h5`, y la consulta en un punto.
- Spec `006-interfaz-y-calculo`: la ventana de cálculo, el registro de convergencia y los menús.
- La 008 y la 009 dependen de esta: su criterio de no convergencia es el de aquí.

## Contexto y objetivo

La spec 001 dejó un Newton completo con la tangente consistente, escalones iguales y la partición
automática del incremento, con una tolerancia estricta **solo para la prueba**: la tolerancia por
defecto del programa quedó para esta spec (enmienda 3 de la constitución). La razón es la
reproducción P13 de STR-05 (zapata de Prandtl): con la tolerancia por defecto del programa de
referencia, una fase cargada por encima del colapso «convergía»; con una diez veces menor fallaba
donde debía (duda 8 de S06). Si «no converge» no significa «no hay equilibrio», el SSR de la 009
no tiene criterio de rotura.

Hay además tres pendientes de la spec 001 y de su changelog: Newton diverge con ψ = 0° en mallas
finas (anillo de 21 m con 16 × 48 divisiones; caso 002 con 16 × 64), y la partición no lo arregla;
el resultado de Mohr-Coulomb depende del número de escalones; y el reparto de escalones es uniforme
y fijado a mano. El objetivo es que una carga por encima del colapso no se dé por convergida con
los valores por defecto, que el número y el reparto de escalones salgan de una regla con fuente y
se muestren con el resultado, y que Newton sea robusto en los casos que hoy fallan.

## Usuarios / actores

- **Ingeniero**, que necesita saber si una carga es admisible y si el programa le dice la verdad
  cuando no lo es.
- **Investigador**, que cambia la tolerancia, el criterio o los escalones y quiere ver cuánto mueven.
- **La spec 009**, que usa la no convergencia como criterio de rotura de cada factor de prueba.
- **Agente vía MCP**, que lanza el mismo cálculo a través de `ogr_api`.

## Historias de usuario

- H1: Como ingeniero quiero que una carga por encima de la de colapso no salga como convergida con
  los valores por defecto, para no tomar por estable lo que no lo es.
- H2: Como ingeniero quiero ver junto al resultado la tolerancia, el criterio de convergencia, el
  número máximo de iteraciones y el número y reparto de escalones usados, para saber qué he
  calculado (regla 12).
- H3: Como ingeniero quiero la curva carga–asiento de una zapata cargada por fases, con la meseta
  donde la da la solución de Prandtl, para fiarme del criterio de colapso.
- H4: Como investigador quiero cambiar la estrategia de control de Newton y ver en el registro
  cuántas veces actuó, para juzgar la robustez.

## Requisitos funcionales (EARS)

**Convergencia y colapso**

- RF-1: EL SISTEMA tiene un criterio de convergencia, una tolerancia y un número máximo de
  iteraciones por defecto, fijados con STR-05 antes de cerrar esta spec y documentados con su fuente.
- RF-2: SI una fase se carga por encima de la carga de colapso, ENTONCES EL SISTEMA, con los valores
  por defecto, no la da por convergida (en STR-05, la fase por encima de la carga de Prandtl).
- RF-3: CUANDO un escalón no alcanza la tolerancia en el número máximo de iteraciones, EL SISTEMA lo
  declara no convergido con la fase, el escalón, las iteraciones y la historia del residuo, y no
  presenta el estado como resultado válido (amplía el RF-6 de la spec 001).
- RF-4: SI la tolerancia no es alcanzable por redondeo, ENTONCES EL SISTEMA lo distingue de una no
  convergencia física y lo dice (el suelo de redondeo de la v0.0.2 se revisa aquí).

**Escalones**

- RF-5: MIENTRAS el usuario no fije el número de escalones, EL SISTEMA lo elige con una regla con
  fuente y reparte la carga de la fase entre ellos con otra; el número y el reparto van con el
  resultado (regla 12).
- RF-6: CUANDO el usuario fija el número de escalones o su reparto, EL SISTEMA los usa y lo dice.

**Robustez**

- RF-7: CUANDO Newton diverge u oscila dentro de un escalón, EL SISTEMA aplica la estrategia de
  control elegida con fuente (búsqueda lineal, longitud de arco o partición del incremento) y el
  resultado dice cuántas veces y dónde actuó.
- RF-8: EL SISTEMA resuelve el caso 002 con ψ = 0° en la malla de 16 × 64 y el anillo de 21 m con
  16 × 48 divisiones, que hoy no convergen, o el plan documenta por qué no puede.

**Fases e historia**

- RF-9: EL SISTEMA resuelve una secuencia de fases de carga en totales (D2 de la spec 001) y guarda
  por fase, escalón e iteración el residuo y el desplazamiento de los puntos de control, para la
  curva carga–desplazamiento y el registro de convergencia.

**Reglas transversales**

- RF-10: Cada ajuste nuevo (criterio, tolerancia, iteraciones, escalones, reparto, estrategia) tiene
  un test que demuestra que mueve el número (regla 7).
- RF-11: Mohr-Coulomb con φ = 0° (Tresca, el material de STR-05) se prueba en un punto de Gauss
  contra su fuente antes de usarse en el modelo (regla 8).
- RF-12: La referencia en Python va primero y es el oráculo; si la estrategia vive en Rust, la
  identidad entre las dos se comprueba (ADR-0001). El motor no conoce la interfaz (regla 11).

## Validación numérica

| Caso | Fuente científica (por comprobar) | Qué se compararía |
|---|---|---|
| `VER-STR-05`, zapata en faja sobre material puramente cohesivo, por fases | Prandtl (1921); la ficha la cita a través de Terzaghi y Peck (1967) | Carga de colapso; la curva carga–asiento en el eje y su meseta; que la fase por encima no converja |
| `validacion/casos/002` con ψ = 0° y la malla de 16 × 64 | Salençon (1969) con la zona de arista (D8 de la spec 001) | Que converja con la estrategia elegida y cumpla la tolerancia del caso |
| Anillo de 21 m, Mohr-Coulomb, 16 × 48, ψ = 0° | Identidad: solución exacta del anillo finito (`salencon_edge_finite`, spec 001) | Robustez en la malla que hoy falla |
| Identidades | — | Una fase elástica converge en una iteración con cualquier tolerancia; el resultado elástico no depende de los escalones; equilibrio global de reacciones en cada fase |
| Convergencia de malla de STR-05 | — | Tres mallas cada vez más finas; la tolerancia del caso se fija con la elegida (regla 9) |

Los asientos y cargas de la reproducción P13 **no son valor esperado** (`validacion/README.md`):
solo explican el comportamiento del programa de referencia. La carga de Prandtl es la referencia.
STR-05 la cierra; STR-02 (caso 002) y el anillo de 21 m comprueban la robustez.

## Fuentes por conseguir

- Prandtl (1921), el original, o la cita de Terzaghi y Peck (1967), *Soil Mechanics in Engineering
  Practice*, 2.ª ed., por comprobar.
- Crisfield (1991), para la búsqueda lineal: de Souza Neto et al. (2008) la remiten ahí. No está.
- Griffiths y Lane (1999), por comprobar, para la no convergencia como criterio de rotura (el
  análisis la cita en P05 y en D01). No está.
- Un criterio de convergencia por energía con fuente: el del programa de referencia (T01 §1) no cita
  ninguna. Bathe (1982), citado en T10, puede tenerlo; por comprobar.
- Regla del número automático de escalones: la de T05 es empírica y **sin fuente**; el reparto
  geométrico observado en P13 no está documentado en ningún manual. Hay que encontrar una con fuente.
- Disponible: de Souza Neto, Perić y Owen (2008), cap. 4 (Box 4.4, longitud de arco) y §5.4.3
  (partición del incremento, ya usada).

## Requisitos no funcionales

- El coste por fase no debe crecer sin medida: cualquier estrategia nueva se mide A/B en el mismo
  proceso, como en la spec 001; el bucle en Rust es cosa de la 011.
- La ventana de cálculo (006) sigue el progreso por fase, escalón e iteración y se puede cancelar.
- Python ≥ 3.11 y las tres plataformas de la CI.

## Casos límite

- Carga exactamente en la de colapso, y una fracción mínima por encima.
- Una fase que descarga (de vuelta a la zona elástica): converge en una iteración.
- Retorno al vértice con ψ = 0°, que la fuente no admite (spec 001, T5): un escalón que lo pide.
- Puntos que cambian de región del retorno en cada iteración (oscilación de la T8 de la spec 001).
- Tolerancia inalcanzable por redondeo frente a carga pequeña sobre fuerzas grandes (v0.0.2).
- Partición agotada (`max_cuts`) y número máximo de iteraciones igual a 1.
- Fase sin cambios: no se resuelve y el resultado lo dice (spec 002).

## Fuera de alcance

- La reducción de resistencia (009) y las leyes nuevas (008).
- Llevar el bucle al código compilado (011).
- Fases de construcción completas, relleno y *load split* (fase 3, spec 012).
- Grandes deformaciones, análisis dinámico, rigidez inicial (descartada en la spec 001, D7).

## Criterios de finalización

- [ ] Todos los RF con su test en verde
- [ ] STR-05 dentro de la tolerancia fijada antes de medir, con su estudio de malla
- [ ] Los dos casos de robustez convergen o el incumplimiento queda reportado como hallazgo
- [ ] Valores por defecto documentados con su fuente y mostrados con el resultado (regla 12)
- [ ] Cada ajuste con su test que mueve el número (regla 7)
- [ ] Todo texto nuevo con traducción española y toda acción nueva en un menú
- [ ] Changelog registrando qué se encontró

## Dudas abiertas

- [NECESITA ACLARACIÓN] **Duda 8 de S06: tolerancia por defecto y criterio de colapso.** Opciones:
  (a) una tolerancia en fuerza lo bastante estricta para que «no converge» sea colapso; (b) un
  criterio de energía como el del programa de referencia, que no tiene fuente; (c) detectar el
  colapso por la meseta de la curva carga–desplazamiento o por un punto límite con longitud de arco;
  (d) combinar fuerza y desplazamiento. El valor del programa de referencia no se traslada: él itera
  con rigidez inicial y este motor con Newton (D7), y sus residuos no se comparan.
- [NECESITA ACLARACIÓN] **Reparto de escalones** (también en la duda 8): iguales (hoy); la
  progresión geométrica observada en P13 (no documentada); la regla del factor de resistencia de T05
  (sin fuente, choca con «fórmula sin fuente no entra»); un control adaptativo por número de
  iteraciones (fuente por localizar).
- [NECESITA ACLARACIÓN] **Estrategia de robustez**: búsqueda lineal (Crisfield 1991, por
  conseguir), longitud de arco (de Souza Neto et al. 2008, disponible) o mejorar la partición. La
  longitud de arco cambia qué es una «fase en totales» (la carga deja de ser dato): ¿solo para STR-05
  y para buscar colapsos, o en todo cálculo?
- [NECESITA ACLARACIÓN] **El número de escalones mueve el resultado plástico** (changelog v0.0.1:
  0.31 % en ur(a) con 8 escalones frente a 1). ¿Se fija por caso como la malla (regla 9), o se busca
  un criterio de independencia de escalones?
- [NECESITA ACLARACIÓN] **Cómo se carga STR-05**: la ficha no dice si son fases de un modelo o
  modelos separados ni qué niveles; P13 usó ocho fases. ¿Qué niveles, qué dominio (la ficha no lo
  da; P13 usó uno propio) y qué punto de control del asiento?
- [NECESITA ACLARACIÓN] **Duda 3 de S06** (convergencia de malla): el plan la da por resuelta en la
  spec 001 como método. Confirmar que STR-05 sigue el mismo (tres mallas, tolerancia antes de medir).
- [NECESITA ACLARACIÓN] **Duda 6 de S06**: la integración de tensiones y el control del bucle no
  tienen manual; ¿basta con de Souza Neto et al. (2008) o hace falta otra fuente para el criterio?
