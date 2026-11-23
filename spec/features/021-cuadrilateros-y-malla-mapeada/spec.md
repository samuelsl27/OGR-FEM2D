# Spec 021 — Cuadriláteros y malla mapeada

> **Borrador de alcance (2026-11-23), sin aprobar.** Transversal, **sin fase fija**. **No está en
> el plan de desarrollo** con este número (`spec/constitution/plan_de_desarrollo.md`): el plan los
> aplazó «cuando una spec los pida» (decisión P2 y viñeta de la spec 003). Solo el **qué** y el
> **porqué**, sin fórmulas ni decisiones tomadas. **Antes de abrirla hay que reevaluarla** (sección
> siguiente); después, plan y tareas con el OK de la propietaria.

> **Solo se abre si un caso lo exige.** Por la regla 9, cada caso de validación fija su malla y su
> elemento; la física del problema no depende del elemento que usó el programa de referencia.
> STR-01 y STR-02 ya se validaron con T6 (casos 001, 002 y 005), aunque sus fichas piden Q8 y Q4.
> Esta spec existe para que la necesidad no se pierda, no para abrirla por defecto.

## Antes de abrirla: reevaluar esta spec

Este borrador se escribió antes de que existieran las specs que lo preceden; el código, el núcleo y
OGR Slip2D habrán avanzado. Al abrirla, y antes de escribir el plan:

- [ ] Contrastarla con el código de este programa y con las specs cerradas desde el 2026-11-23: qué
      ya está hecho, qué cambió y qué se movió de sitio.
- [ ] Mirar qué tienen ya OGR Slip2D y `ogr_core` en la etiqueta fijada. Lo genérico se pide a la
      sesión de OGR-Core, no se copia (`AGENTS.md`, «Un núcleo y varios programas»). Puntos de
      partida vistos al escribir el borrador (núcleo v0.2.6):
      - Aquí: `docs/motor/entrada.md` (un tipo de elemento por modelo, T3 o T6: regla
        `element_kind`); `ogr_fem2d/engine/reference/` (T3, T6, cuadraturas de triángulo);
        `ogr_fem2d/mesh/radial.py` (la malla radial de la 003 es de triángulos) y
        `ogr_fem2d/engine/mesh_structured.py` (rejilla graduada partida en triángulos, de la 002).
      - Núcleo: `ogr_core/fem/generator.py` y `mesh.py` (triángulos de 3 nudos para la
        filtración); nada de cuadriláteros.
      - Lo observado: `dialogos/D02` (tipos de malla y de elemento de la referencia); `S06`, duda 3
        (P02: con malla gruesa, Q4 −11 % y Q8 −1.9 % en el desplazamiento plástico de STR-02, en la
        referencia).
- [ ] Leer y comprobar las fuentes de «Validación numérica» y de «Fuentes por conseguir»; las fichas
      de los casos no son fuente.
- [ ] Releer las fichas de los casos que la cierran y su «Seguimiento».
- [ ] Convertir las «Dudas abiertas» en decisiones propuestas (D1, D2…) con su porqué, para el OK de
      la propietaria.

## Depende de

- Spec 002 (motor, cuadraturas, axisimetría), 003 (mallador, discretización), 008 si los
  cuadriláteros van a plasticidad, y la spec del caso que la pida.

## Contexto y objetivo

La hoja de ruta ponía T3, T6, Q4 y Q8 en la fase 1; la decisión P2 dejó T6 y T3 y aplazó los
cuadriláteros y el mallado mapeado hasta que una spec los pida. El índice de casos los nombra a
menudo porque son los que usó el programa de referencia, no porque el problema los necesite. Esta
spec recoge lo que habría que hacer (Q4 y Q8 en deformación plana y axisimetría, y una malla
mapeada de regiones de cuatro lados) y, sobre todo, la lista de casos que podrían pedirlo, para
decidir con ellos.

**Qué casos los piden** (recuento del índice, `00_INDICE.md`):

- `EL-Q4`, 14 casos: `VER-STR-02`, `-03`, `-07`, `-15`, `-21`, `-30`; `VER-CON-10`, `-11`;
  `VER-DYN-05`, `-06`, `-07`, `-08`, `-09`; `VER-GW-09`.
- `EL-Q8`, 9 casos: `VER-STR-01`, `-05` (con T6 también), `-08`, `-11`, `-13`, `-18`, `-19`,
  `-29`; `VER-CON-07`.

**Si alguno no se puede hacer con triángulos sin cambiar el caso.** Con lo leído, ninguno lo
necesita por la física: se comparan con una solución analítica, publicada o con otro programa, y
la malla es nuestra. Los que hay que mirar al abrirla, porque el elemento es casi el problema:

- `VER-DYN-08` (un solo Q4 casi rígido como masa de un sistema de un grado de libertad) y
  `VER-DYN-09` (dos Q4 apilados, seis nudos): con dos triángulos por cuadrado los nudos son los
  mismos; por comprobar si el reparto de la masa cambia la comparación (fase 7).
- `VER-STR-13` y `VER-STR-29` (un solo Q8 axisimétrico, ensayo de laboratorio de estado
  homogéneo): cualquier elemento completo debería dar el estado homogéneo exacto; por comprobar.
- `VER-CON-07` (Q8, sin referencia) y `VER-GW-09` (Q4, aproximada y otro programa): sin
  referencia externa fuerte, el elemento no se puede «validar» con ellos.

## Usuarios / actores

- **El ingeniero** que quiere una malla estructurada de cuadriláteros (un terraplén, una columna,
  una probeta); **los casos de validación** que lo exijan; **el motor**, que pasaría a admitir
  otros elementos.

## Historias de usuario

- H1: Como ingeniero quiero mallar una región de cuatro lados con una malla mapeada de
  cuadriláteros, con divisiones por lado.
- H2: Como ingeniero quiero reproducir con el mismo elemento un caso que solo se entiende con él.

## Requisitos funcionales (EARS)

- RF-1: SI un caso lo exige y se abre esta spec, EL SISTEMA calcula Q4 y Q8 en deformación plana y
  en axisimetría, con la regla de integración de su fuente, en la referencia en Python y en Rust.
- RF-2: EL SISTEMA malla con una malla mapeada una región de cuatro lados con divisiones dadas, y
  SI la región no tiene cuatro lados o las divisiones opuestas no casan, ENTONCES lo dice.
- RF-3: EL SISTEMA comprueba la calidad de los cuadriláteros con un criterio con fuente (jacobiano
  positivo en todo el elemento, como el T6 de la spec 003).
- RF-4: EL SISTEMA rechaza la mezcla de triángulos y cuadriláteros mientras no se decida (duda 2).

## Validación numérica

| Caso | Fuente científica (por comprobar) | Qué se compararía |
|---|---|---|
| El caso que la pida | La de su ficha | Lo que ese caso compare, con la malla y el elemento que fije (regla 9) |
| Identidades de elemento | Zienkiewicz y Taylor (2000), caps. 8 y 9 (en la bibliografía) | Parcela en deformación plana y axisimetría; sólido rígido; equilibrio de reacciones |
| Regresión | Kirsch (1898), en Jaeger, Cook y Zimmerman (2007), §8.4 | El caso 005 con Q8: mismo criterio de tolerancia, otro estudio de malla |
| Variantes | — | Referencia y Rust idénticas a redondeo |

## Fuentes por conseguir

- Zienkiewicz y Taylor (2000), vol. 1, está en la bibliografía: elementos de la familia
  *serendipity* y de Lagrange, transformación isoparamétrica e integración (caps. 8 y 9, por
  comprobar las secciones). El mallado mapeado no lo trata (cap. 15 declara el mallado fuera de su
  alcance, según la bibliografía de la spec 003).
- El comportamiento del Q4 en plasticidad (bloqueo): fuente por localizar; de Souza Neto et al.
  (2008), en la bibliografía, por comprobar si lo trata.

## Requisitos no funcionales

- Un caso ya validado no cambia de elemento: cambiar el elemento es cambiar el caso (regla 9).
- Sin dependencias nuevas.

## Casos límite

- Cuadrilátero casi triangular o cóncavo; nudos intermedios del Q8 sobre un arco; región de cuatro
  lados con un lado curvo; malla mapeada junto a una no estructurada.

## Fuera de alcance

- Abrirla sin un caso que lo exija.
- Elementos de nueve nudos, de orden superior o incompatibles; refinamiento adaptativo.

## Criterios de finalización

- [ ] Un caso que lo exige, nombrado y aprobado por la propietaria antes de abrirla
- [ ] Dudas convertidas en decisiones y aprobadas
- [ ] Todos los RF con su test en verde, y la regla 7 en cada ajuste nuevo
- [ ] El caso que la pidió dentro de la tolerancia fijada antes de medir, con su estudio de malla
- [ ] Changelog con lo encontrado

## Dudas abiertas

- [NECESITA ACLARACIÓN] **1. ¿Hay algún caso que la exija?** Mirar primero `VER-DYN-08` y `-09`
  (fase 7) y `VER-STR-13` y `-29` (fase 5): si dan lo mismo con triángulos, esta spec no se abre.
- [NECESITA ACLARACIÓN] **2. Mezcla de elementos**: hoy el motor admite un tipo por modelo
  (`element_kind`). ¿Cuadriláteros solos, o mezclados con triángulos (T6 con Q8)?
- [NECESITA ACLARACIÓN] **3. Malla mapeada sin cuadriláteros**: una malla mapeada de triángulos (una
  rejilla partida, como la de la spec 002) podría bastar para los casos con `MALLA-GRAD`. ¿Entra
  aquí, en la 003 o en ninguna?
- [NECESITA ACLARACIÓN] **4. El dato de P02** (S06, duda 3): es lo que dio la referencia con sus
  cuadriláteros, no un valor esperado; sirve solo para saber que el elemento importa con malla
  gruesa.
