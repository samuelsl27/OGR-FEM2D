# Spec 009 — Reducción de resistencia al corte (SSR)

> **Borrador de alcance (2026-11-23), sin aprobar.** Fase 2 del plan de desarrollo
> (`spec/constitution/plan_de_desarrollo.md`, «Spec 009 — Reducción de resistencia al corte
> (SSR)»). Solo el **qué** y el **porqué**, sin fórmulas ni decisiones tomadas. **Antes de abrirla
> hay que reevaluarla** (sección siguiente); después, plan y tareas con el OK de la propietaria.

## Antes de abrirla: reevaluar esta spec

Este borrador se escribió antes de que existieran las specs que lo preceden; el código, el núcleo y
OGR Slip2D habrán avanzado. Al abrirla, y antes de escribir el plan:

- [ ] Contrastarla con el código de este programa y con las specs cerradas desde el 2026-11-23: qué
      ya está hecho, qué cambió y qué se movió de sitio.
- [ ] Mirar qué tienen ya OGR Slip2D y `ogr_core` en la etiqueta fijada. Lo genérico se pide a la
      sesión de OGR-Core, no se copia (`AGENTS.md`, «Un núcleo y varios programas»). Puntos de
      partida vistos al escribir el borrador:
      ninguno para el algoritmo (Slip2D es de equilibrio límite). Para comparar: los casos de Slip2D
      `validacion/casos/001-acads-1a` (SLP-01) y `005-arai-tagyo-1985-ej3` (SLP-12), y su servidor
      MCP, que calcula el FS de equilibrio límite en el mismo modelo. Para la tensión inicial con
      superficie irregular: `ogr_core/loads/overburden.py` (columna de suelo sobre un punto) y
      `ogr_fem2d/engine/initial_stress.py` (hoy solo superficie y estratos horizontales, D3 de la
      spec 002). Para guardar las pruebas: `ogr_core/project/results_io.py` (ADR-0003).
- [ ] Leer y comprobar las fuentes de «Validación numérica» y de «Fuentes por conseguir»; las fichas
      de los casos no son fuente.
- [ ] Releer las fichas de los casos que la cierran y su «Seguimiento».
- [ ] Convertir las «Dudas abiertas» en decisiones propuestas (D1, D2…) con su porqué, para el OK de
      la propietaria.

## Depende de

- Spec 007: el criterio de no convergencia de cada prueba y la tolerancia por defecto.
- Spec 008: Mohr-Coulomb completo, Drucker-Prager, Hoek-Brown generalizado y la copia de la ley con
  la resistencia reducida.
- Spec `004-modelo-y-proyecto`: la casilla de aplicar el SSR por material, las áreas de búsqueda y
  de exclusión como geometría, los ajustes del SSR con sus valores por defecto, y la **tensión
  gravitatoria con la superficie real del terreno**, que 118 casos de SSR piden (`TI-GRAV`) y la
  spec 002 dejó para cuando hubiera geometría (su D3). Si la 004 no la trae, entra aquí.
- Spec `005-resultados`: los campos de cada prueba en `modelo.h5`, la deformación de corte máxima.
- Spec `006-interfaz-y-calculo`: progreso por factor de prueba, pestañas por prueba, gráfico.

## Contexto y objetivo

Es la función que más casos pide: 155 de los 274 exigen SSR y 123 tienen el SSR como área
principal. Ninguno de los 46 manuales de teoría describe el algoritmo; la única fuente científica
citada es Dawson, Roth y Drescher (1999) (T00 §3.1, duda 6 de S06). Lo observado en la reproducción
P05 da el comportamiento del programa de referencia (estimación inicial, subida, bisección hasta una
tolerancia, el mayor factor que converge como crítico; P10, la bajada cuando la primera prueba
falla), pero es una observación, no una fuente: el algoritmo tiene que ser una decisión propia,
documentada con su fuente.

El objetivo es obtener el factor de reducción crítico de un modelo, con un criterio de rotura fiable
(el de la 007), con control de qué resistencias se reducen (por material, y más adelante juntas e
interfaces, P21 y P22), con un área de búsqueda o de exclusión que piden 15 casos, y con los
resultados que permiten juzgar el mecanismo: deformación de corte máxima, desplazamientos y la curva
del factor frente al desplazamiento máximo.

## Usuarios / actores

- **Ingeniero de taludes**, que necesita el factor de seguridad y el mecanismo.
- **Docente**, que compara el SSR con el equilibrio límite de OGR Slip2D en el mismo modelo.
- **Agente vía MCP**, que lanza el SSR y lee la tabla de pruebas.

## Historias de usuario

- H1: Como ingeniero quiero el factor de reducción crítico de un talud y su mecanismo de rotura,
  para comparar con el factor de seguridad de equilibrio límite.
- H2: Como ingeniero quiero ver qué resistencias se han reducido y cuáles no, material por material,
  para no tomar por bueno un factor que dependa de una casilla olvidada (P21).
- H3: Como ingeniero quiero restringir el SSR a una zona o excluir otra, para estudiar un mecanismo
  concreto o evitar uno superficial sin interés.
- H4: Como ingeniero quiero la curva del factor frente al desplazamiento máximo, con las pruebas
  convergidas y las que no, para juzgar si el colapso está bien definido.

## Requisitos funcionales (EARS)

**Algoritmo**

- RF-1: CUANDO se pide SSR, EL SISTEMA busca el factor crítico resolviendo el modelo con las
  resistencias de los materiales marcados divididas por factores de prueba, con un algoritmo
  documentado con su fuente (Dawson et al. 1999, o la que se decida).
- RF-2: EL SISTEMA ofrece búsqueda automática con tolerancia y barrido con paso fijo hasta un factor
  final, desde una estimación inicial, y encuentra factores menores que 1 (SLP-24, SLP-56).
- RF-3: Cada prueba usa el criterio de no convergencia de la 007; el resultado dice el criterio, la
  tolerancia, las iteraciones, los escalones y la tolerancia de la búsqueda (regla 12).
- RF-4: SI ninguna prueba converge, ni la de menor factor, ENTONCES EL SISTEMA lo dice y no da un
  factor; SI todas convergen hasta el factor máximo, ENTONCES da una cota inferior y lo dice.

**Qué se reduce**

- RF-5: EL SISTEMA reduce, por material, los parámetros de resistencia de cada ley de la 008 con la
  regla de su fuente; los materiales elásticos o no marcados no se reducen (SLP-23 tiene una zona
  elástica que no puede romper); el resultado lista qué se redujo.
- RF-6: Las opciones que cambian qué se reduce (dilatancia, resistencia a tracción, resistencias
  variables de la 020) tienen su test que mueve el número (regla 7) y su defecto a la vista.
- RF-7: Las presiones intersticiales de la 010 se mantienen fijas durante la búsqueda (SLP-12).

**Áreas**

- RF-8: CUANDO el usuario define un área de búsqueda o de exclusión, EL SISTEMA la aplica según la
  regla que se decida (duda abierta) y la dibuja con el resultado (15 casos: `OTRO` del índice).

**Resultados**

- RF-9: EL SISTEMA guarda el factor crítico y la tabla de pruebas (factor, convergida o no,
  desplazamiento máximo, iteraciones), y los campos de cada prueba en `modelo.h5` con la huella.
- RF-10: EL SISTEMA dibuja la deformación de corte máxima, los vectores de desplazamiento y la curva
  del factor frente al desplazamiento máximo; esa curva es la `POST-HIST` de SLP-59, 61, 63 y 65.

**Reglas transversales**

- RF-11: El algoritmo tiene su referencia en Python; el cálculo es cancelable y muestra el progreso
  por prueba (006). El motor recibe el factor como dato y no conoce la interfaz (regla 11).

## Validación numérica

| Caso | Fuente científica (por comprobar) | Qué se compararía |
|---|---|---|
| `VER-SLP-21` y `VER-SLP-87`, carga de hundimiento de Prandtl sin peso | Prandtl (1921): con la carga teórica, factor exacto 1 | Factor crítico; mecanismo |
| `VER-SLP-20` y `VER-SLP-86`, carga vertical en el borde de un talud sin peso | Prandtl (1921), con los datos de Chen y Shao (1988) | Factor crítico; la 86 con área de exclusión |
| `VER-SLP-01`, ACADS 1(a) | Giam y Donald (1989), valor del árbitro y medias de la encuesta | Factor crítico frente a un FS **de equilibrio límite** publicado |
| `VER-SLP-12`, Arai y Tagyo (1985), ej. 3 | Arai y Tagyo (1985), Bishop | Ídem, con nivel freático (necesita la 010) |
| `VER-SLP-74`, ACADS 2(b), círculo prefijado | Giam y Donald (1989) | Área de búsqueda |
| `VER-SLP-60`, Hoek-Brown generalizado | Li, Merifield y Lyamin (2008), ábacos: **aproximada** | Factor crítico con una ley no lineal |
| `VER-SLP-56` a `58`, Mohr-Coulomb y Drucker-Prager | Pruska (2003) publica resultados de otros programas: **comparación** | Diferencia entre las dos leyes |
| Identidad de escala | — | Un modelo con la resistencia ya dividida por un factor da el factor crítico dividido por él |
| Convergencia de malla (duda 5) | — | El factor crítico con tres mallas; la tolerancia de cada caso se fija con la elegida (regla 9) |

Se proponen como los que la cierran **SLP-21 y SLP-20** (analíticos) y **SLP-01 y SLP-12** (los del
plan). Ojo: en SLP-01 y SLP-12 la referencia publicada es un factor de equilibrio límite, no de
SSR; los dos métodos no tienen por qué coincidir, así que la tolerancia tiene que justificarse. El
factor de OGR Slip2D en el mismo modelo es una **comparación independiente**, no una validación.
Cálculo propio sobre la tabla maestra del índice: con la fase 1 y las specs 007 a 009 se desbloquean
unos 45 casos (40 de taludes); el núcleo del SSR sin agua, 21.

## Fuentes por conseguir

- Dawson, Roth y Drescher (1999), *Géotechnique* 49(6), 835–840: la única citada. No está.
- Griffiths y Lane (1999), por comprobar, que el análisis cita para la no convergencia como
  criterio de rotura (P05, D01). No está.
- Zienkiewicz, Humpheson y Lewis (1975), por comprobar: no lo cita el análisis; se propone buscarlo
  como origen del método.
- La reducción de un criterio no lineal (Hoek-Brown generalizado): por localizar.
- Prandtl (1921); Chen y Shao (1988); Giam y Donald (1989) y Arai y Tagyo (1985) (Slip2D los tiene
  leídos); Li, Merifield y Lyamin (2008); Pruska (2003).

## Requisitos no funcionales

- Un SSR son decenas de análisis no lineales (P05: ocho pruebas de diez escalones): el coste se mide
  antes de la 011 y se usa para decidirla.
- Las pruebas son independientes del orden en que se calculan: el resultado no depende de si una
  prueba parte del estado de la anterior, o se decide y se documenta que sí.

## Casos límite

- Modelo estable para cualquier factor (sin peso ni carga) o inestable sin reducir (SRF < 1).
- Material con cohesión nula y rozamiento nulo a la vez; Tresca puro (φ = 0°).
- Rotura local superficial que no es el mecanismo de interés (lo que motiva el área de exclusión).
- Dos factores de prueba que redondean al mismo valor (P05 redondea a dos decimales).
- Modelo con varias fases: en cuál se aplica el SSR.

## Fuera de alcance

- Reducción de juntas, interfaces y soporte (fase 3; aquí solo se deja prevista en el resultado).
- Presiones del flujo FEM en el SSR (fase 4); las hidrostáticas son de la 010.
- Grieta de tracción, sismo, curva potencial y propiedades variables (spec 020).
- SSR probabilístico (fase 6).

## Criterios de finalización

- [ ] Todos los RF con su test en verde
- [ ] Los casos que la cierran dentro de la tolerancia fijada antes de medir, con su estudio de malla
- [ ] Algoritmo y regla de reducción documentados con su fuente
- [ ] Lo que se reduce y lo que no, mostrado con el resultado (regla 12)
- [ ] Todo texto nuevo con traducción española y toda acción nueva en un menú
- [ ] Changelog registrando qué se encontró

## Dudas abiertas

- [NECESITA ACLARACIÓN] **Duda 6 de S06: el algoritmo no tiene manual.** Opciones: la bisección
  observada en P05 y P10, documentada como decisión propia; el procedimiento de Dawson et al. (1999)
  si difiere; barrido con paso fijo. ¿Qué tolerancia de búsqueda por defecto?
- [NECESITA ACLARACIÓN] **Criterio de rotura de cada prueba** (duda 8, vía la 007): no convergencia,
  salto del desplazamiento máximo, o continuidad de la zona plástica; el «mayor factor convergido» de
  P05 resuelve una contradicción de la documentación del programa de referencia, pero no es fuente.
- [NECESITA ACLARACIÓN] **Duda 5 de S06: sensibilidad del factor a la malla** (P05: 1.03 con 201
  triángulos frente a 0.995 del manual). La tolerancia de cada caso depende del estudio de malla.
- [NECESITA ACLARACIÓN] **Dilatancia y tracción en el SSR**: el programa de referencia reduce la
  dilatancia de alguna forma (T07c §4) y por defecto también la resistencia a tracción (D01). ¿Qué
  se reduce, con qué fuente y con qué defecto?
- [NECESITA ACLARACIÓN] **Área de búsqueda y de exclusión**: qué hacen exactamente (¿restringir dónde
  se reduce la resistencia, dónde se mide el desplazamiento, o dónde se admite el mecanismo?). Las
  fichas no lo documentan; hay que decidirlo y justificarlo.
- [NECESITA ACLARACIÓN] **Parámetros que las fichas no dan** (E, ν, dilatancia, resistencia a
  tracción; SLP-01): cambian el factor. ¿Qué defectos y cómo se muestran?
- [NECESITA ACLARACIÓN] **Tensión inicial antes del SSR**: gravedad con la superficie real y qué K
  (P05 usó 1), o cargar el peso desde cero; en materiales plásticos el estado de partida importa.
- [NECESITA ACLARACIÓN] **Opción de «acelerar tras la rotura»** del programa de referencia (D01, por
  defecto activa): ¿existe aquí? Si cambia el número, regla 7 y regla 12.
- [NECESITA ACLARACIÓN] **Juntas e interfaces** (P21, P22): por defecto el programa de referencia no
  reduce las juntas. Cuando lleguen (fase 3), ¿qué defecto y cómo se muestra?
