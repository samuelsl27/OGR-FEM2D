# Spec 030 — Térmico acoplado: cambio de fase, agua y mecánica

> **Borrador de alcance (2026-11-23), sin aprobar.** Fase 7 del plan de desarrollo
> (`spec/constitution/plan_de_desarrollo.md`, «Fase 7 — Campos especiales»: térmico, «conducción y
> después acoplamientos»). Solo el **qué** y el **porqué**, sin fórmulas ni decisiones tomadas.
> **Antes de abrirla hay que reevaluarla** (sección siguiente); después, plan y tareas con el OK de
> la propietaria.

## Antes de abrirla: reevaluar esta spec

Este borrador se escribió antes de que existieran las specs que lo preceden; el código, el núcleo y
OGR Slip2D habrán avanzado. Al abrirla, y antes de escribir el plan:

- [ ] Contrastarla con el código de este programa y con las specs cerradas desde el 2026-11-23: qué
      ya está hecho, qué cambió y qué se movió de sitio.
- [ ] Mirar qué tienen ya OGR Slip2D y `ogr_core` en la etiqueta fijada. Lo genérico se pide a la
      sesión de OGR-Core, no se copia (`AGENTS.md`, «Un núcleo y varios programas»). Puntos de
      partida vistos al escribir el borrador (núcleo v0.2.6):
      - Lo que deje la 029: el solver térmico, la malla térmica frente a la tensional y la
        temperatura en los puntos de integración.
      - `ogr_core/fem/seepage.py`: velocidades de Darcy por elemento (`element_fluxes`) del flujo
        estacionario y del transitorio, que la advección necesita; el transitorio no tiene término
        de flotabilidad (convección natural) ni succión añadida por el hielo. La eliminación de
        Dirichlet conserva la simetría; la advección hace la matriz no simétrica (T12 §1.4).
      - `ogr_core/hydraulic/hydraulic_properties.py`: **una sola curva de retención, la de van
        Genuchten, para todos los modelos** (018, duda 2), que condiciona el agua no congelada
        «a partir del contenido de agua» y el bloqueo de poros por hielo; `permeability_models.py`
        (los modelos k(ψ) que el bloqueo usaría).
      - Aquí: `ogr_fem2d/engine/` (la deformación inicial no existe en el motor: la térmica sería
        la primera) y lo que dejen las specs 008 (leyes plásticas), 010 (geosintéticos), 013
        (vigas), 015 (juntas) y 017–018 (agua).
      - Lo observado: nada (la versión observada no tenía térmico). Documentación: carpeta B,
        `modelo/M25_termico.md` (§2: la referencia excluye el térmico con dinámico, XFEM y
        consolidación), `M13`, `compute_interpret/I05`. Teoría: `C_teoria/T12` (bloques B a K);
        erratas en `T00` §3.3 («unidades de las tablas de constantes y radiación de onda larga»).
- [ ] Leer y comprobar las fuentes de «Validación numérica» y de «Fuentes por conseguir»; las fichas
      de los casos no son fuente.
- [ ] Releer las fichas de los casos que la cierran y su «Seguimiento».
- [ ] Convertir las «Dudas abiertas» en decisiones propuestas (D1, D2…) con su porqué, para el OK de
      la propietaria.

## Depende de

- **Spec 029** (conducción, contornos, condición inicial, tiempo): todo lo de aquí va encima.
- **Specs 017 y 018** (flujo estacionario, transitorio y no saturado): las velocidades para la
  advección, la retención para el agua no congelada y el bloqueo por hielo. La 018 dejó el hielo y
  el balance superficial para esta fase.
- Para la deformación térmica: 002 (motor), 008 (Hoek-Brown en EJ-THM-06), 012 (fases), 013 (viga:
  THM-16), 010 (geosintético: EJ-THM-08). Para el aislamiento de juntas: 015.
- Specs `005-resultados` y `006-interfaz-y-calculo`, y la 028 si define antes las funciones del
  tiempo.

## Contexto y objetivo

Sobre la conducción de la 029 quedan los fenómenos que hacen útil el térmico en geotecnia: el
**cambio de fase agua-hielo** con su calor latente y su curva de agua no congelada (`TER-CAMBIO`,
13 casos), con la capacidad calorífica de Jame y Newman (`OTRO`, 2) y las conductividades que
dependen de la saturación y del estado helado (`TER-K`, según la 029, duda 8); el **acoplamiento
con el agua**: la advección del calor por el flujo (`TER-ADV`, 6), la convección natural por la
densidad (`TER-NAT`, 1) y el bloqueo de poros por hielo (`OTRO`, 2); el **acoplamiento
termomecánico** en sólidos y en vigas (`TER-MEC`, 4); y dos **contornos especiales**: el balance
energético superficial con datos climáticos (`TER-SEB`, 4) y los termosifones (`TER-SIFON`, 2).
T12 da a este escalón dificultad alta, y le faltan piezas: el esquema de iteración, la
«compensación de entalpía» que la referencia usa para el cambio de fase y el esquema de
acoplamiento entre módulos no están documentados (T12 §1.4). Es demasiado para una spec: la duda 1
propone cómo partirla.

## Usuarios / actores

- **Ingeniero de congelación artificial, permafrost y obras en climas fríos.**
- **Ingeniero de almacenamientos y obras con calor** (EJ-THM-06), que necesita las tensiones
  térmicas en un modelo elastoplástico.
- **El SSR de la 009**, si se decide un SSR con temperaturas (EJ-THM-08).

## Historias de usuario

- H1: Como ingeniero quiero activar el calor latente y elegir la curva de agua no congelada de cada
  material, para ver avanzar un frente de congelación o de deshielo.
- H2: Como ingeniero quiero que el flujo de agua transporte calor, y que el hielo frene el flujo,
  para estudiar una pared helada con agua que la rodea.
- H3: Como ingeniero quiero que un cambio de temperatura dilate el terreno y los soportes, y ver
  las tensiones y esfuerzos que eso produce.
- H4: Como ingeniero quiero imponer en superficie el clima de un año o un termosifón, y ver con el
  resultado cada constante y parámetro que el programa tomó por defecto.

## Requisitos funcionales (EARS)

**Cambio de fase y propiedades**

- RF-1: CUANDO un material tiene calor latente, EL SISTEMA lo incluye con el método que se decida
  con su fuente (duda 2) y con la curva de agua no congelada que elija el usuario (duda 3).
- RF-2: EL SISTEMA ofrece la capacidad calorífica constante (helada y no helada), por tabla y la de
  Jame (1977) y Newman (1995), y las conductividades que se decidan (029, duda 8; duda 5), cada una
  probada en un punto contra su fuente antes de usarse en un modelo (regla 8).
- RF-3: EL SISTEMA da con el resultado la posición del frente (la isoterma de congelación) y su
  evolución, y el balance de energía por etapa con el calor latente incluido.

**Acoplamiento con el agua**

- RF-4: CUANDO se activa la advección, EL SISTEMA transporta el calor con las velocidades del flujo
  de la 017 o la 018, con el esquema de acoplamiento que se decida (duda 6); SI el número de Péclet
  de un elemento pasa el límite que dé la fuente, ENTONCES lo avisa con el elemento.
- RF-5: CUANDO se activa la convección natural, EL SISTEMA añade al flujo de agua la fuerza por la
  densidad dependiente de la temperatura, con la relación que dé una fuente (duda 7).
- RF-6: CUANDO se activa el bloqueo de poros por hielo, EL SISTEMA añade la succión que da la
  temperatura y la lleva a la permeabilidad del modelo no saturado (duda 8); SI el material no tiene
  modelo no saturado, ENTONCES lo dice y no lo aplica en silencio.

**Acoplamiento termomecánico**

- RF-7: EL SISTEMA añade la deformación térmica, con su coeficiente de dilatación por material y
  por elemento estructural, al análisis tensional de cada fase, desde la temperatura de referencia
  que se decida, con la hipótesis fuera del plano a la vista (duda 9).
- RF-8: La deformación térmica entra al motor como deformación inicial discreta por punto, en el
  convenio de tracción positiva (regla 10); el motor no sabe de temperaturas ni de unidades (regla
  11).

**Contornos especiales**

- RF-9: EL SISTEMA aplica el balance energético superficial con series climáticas por etapa, cada
  término con su fuente y cada constante a la vista (regla 12), según la duda 10.
- RF-10: EL SISTEMA aplica termosifones con la regla de activación y el método de conductancia que
  se decidan con su fuente (duda 11), y el aislamiento de juntas si se decide (duda 12).

**Reglas transversales**

- RF-11: Cada ley nueva (agua no congelada, capacidad, conductividad, succión criogénica) tiene su
  referencia en Python, oráculo de Rust si va al motor (ADR-0001).
- RF-12: Las constantes del agua, el hielo y el aire salen de una fuente, no de la tabla de T12 con
  sus erratas de unidades, y se muestran con el resultado (regla 12; duda 13).
- RF-13: Cada opción nueva lleva su test que mueve el número (regla 7); los textos pasan por `tr()`
  y las acciones están en un menú (reglas 2 y 3).

## Validación numérica

| Caso | Fuente científica (por comprobar) | Qué se compararía |
|---|---|---|
| `VER-THM-05`, deshielo de una columna | Solución de Neumann, en Carslaw y Jaeger (la ficha cita 1986) | Perfiles de temperatura a 10, 50 y 100 días; necesita Jame-Newman y una curva muy empinada |
| `VER-THM-07`, advección en una columna | Bredehoeft y Papadopulos (1965) | Perfil estacionario con flujo descendente, ascendente y horizontal; la ficha anota una errata de signo en la ecuación impresa y que el convenio de signo del caudal no se documenta |
| `VER-THM-08`, deshielo con advección | Lunardini (1998), aproximada (cuasiestacionaria); condiciones de Kurylyk et al. (2014) | Profundidad del frente en 20 días; α, velocidad y número de Stefan sin documentar en la ficha |
| `VER-THM-15`, dilatación en sólidos | Deformación térmica libre (la ficha no cita fuente; Jaeger, Cook y Zimmerman 2007, §7.8, está en la carpeta) | Desplazamiento vertical en dos fases; la ficha avisa de que en deformación plana estricta con laterales libres no saldría la deformación libre que publica el manual (duda 9) |
| `VER-THM-16`, dilatación de una viga | Deformación térmica libre (sin fuente en la ficha) | Desplazamiento a lo largo de la viga; necesita la 013 |
| `VER-THM-11`, conductividad de Côté y Konrad | Côté y Konrad (2005), forma cerrada; Kersten (1949), ensayos | Conductividad frente a saturación, helado y no helado; es una prueba de la ley en un punto (regla 8) |
| `VER-THM-12`, conductividad de Johansen y de Lu | Johansen (1975, tesis; traducción de 1977); Lu et al. (2007); Tarnawski et al. (2009), ensayos | Conductividad frente a contenido de agua en cuatro suelos; prueba de la ley en un punto |
| `VER-THM-06`, tubería enterrada que congela | Coutts y Konrad (1994), numérica publicada | Extensión del frente bajo la tubería y a su lado a 730 días (la ficha no dice desde dónde se mide) |
| `VER-THM-09`, convección natural | Yang, Feng, Luo y Chen (2010), numérica, comparación cualitativa | Mapas de temperatura y vectores; la ficha dice que los parámetros se ajustaron para parecerse: no valida |
| `VER-THM-10`, balance energético superficial | Hwang (1976), numérica, y medidas de campo | Temperatura frente al tiempo en un punto que la ficha no documenta |
| `VER-THM-13`, `-14`, termosifones | Solo otro programa (el montaje de la -13 sigue a Haynes y Zarling 1988, sin sus datos) | **Comparaciones**, no validaciones |
| `EJ-THM-01`, `-04`, `-05`, `-06` | Yan et al. (2019); McKenzie, Voss y Siegel (2007); Carvalho y Zivković (2018): numéricas publicadas | Frentes, isotermas, historias y zona plástica; ejemplos, no casos de cierre |
| `EJ-THM-02`, `-03`, `-07`, `-08` | Sin referencia | Ninguna validación posible |
| Sin calor latente, sin advección, sin dilatación | — (identidad) | El mismo campo que la 029 y el mismo análisis tensional que sin térmico |
| Barra coaccionada | — (identidad, derivación propia a comprobar con la fuente) | Calentada sin poder dilatar: la tensión que da la ley elástica, sin desplazamiento |
| Péclet nulo | — (identidad) | Advección con caudal nulo igual a conducción pura |
| Contornos especiales degenerados | — (identidad) | Balance superficial con solo el término convectivo, o termosifón con coeficiente manual: lo mismo que la convección de la 029 |
| Balance de energía con cambio de fase | — (identidad) | Calor almacenado, latente incluido, igual al flujo neto en cada etapa |
| Convergencia en malla y en tiempo | — | Con el paso y la malla fijados por caso (regla 9): la referencia presume de capturar el frente con pasos grandes (THM-05, -08), y eso no es un valor esperado |

Se proponen como los que la cierran **THM-05** (cambio de fase), **THM-07** (advección),
**THM-15** y **THM-16** (termomecánico), y **THM-11** y **THM-12** como pruebas de las leyes en un
punto; THM-08 según la duda 2. El balance superficial, los termosifones y la convección natural no
tienen caso validable: solo identidades y comparaciones.

## Fuentes por conseguir

- En `Referencias/Bibliografia` no hay ninguna térmica. Está Jaeger, Cook y Zimmerman (2007), con
  un §7.8 de termoelasticidad (pág. 197 del libro), por leer para RF-7. Timoshenko y Goodier está
  escaneado y no se ha buscado en él.
- Cambio de fase: Carslaw y Jaeger (solución de Neumann); el método de calor latente efectivo de T12
  y la «compensación de entalpía», sin fuente ni formulación publicadas (por localizar); Lunardini
  (1998); Kurylyk et al. (2014).
- Agua no congelada: Mackenzie, Voss y Siegel (T12: 2006, incompleta, escrito «Mackenze»; la ficha
  de EJ-THM-04 cita McKenzie, Voss y Siegel 2007); Lebeau y Konrad (2009); Anderson y Tice (1972)
  (T12 cita también un «Tice y Anderson 1976» que no está en su lista).
- Capacidad: Jame (1977), tesis; Newman (1995), tesis de máster.
- Conductividad: Johansen (T12: 1977; THM-12: tesis de 1975 y traducción de 1977); Farouki (1981)
  (Johansen y De Vries); Lu et al. (2007) (T12 lo cita como «1977»); Côté y Konrad (2005);
  Tarnawski et al. (2009); Kersten (1949).
- Agua y calor: Frivik y Comini (1982), advección; Frind (1982), convección natural, escrita para
  solutos con una concentración media (T12 no da la relación densidad-temperatura); Kurylyk y
  Watanabe (2013), succión por el hielo; Bredehoeft y Papadopulos (1965).
- Balance superficial: Hwang (1976), incompleta; Allen et al. (1998); Dingman (2008); Saito y
  Šimůnek (2009). Termosifones: Haynes y Zarling (1988); la fórmula atribuida a Yarmak (1983) es una
  comunicación personal y no se cita.
- Las de los casos: Coutts y Konrad (1994), Yang et al. (2010), Yan et al. (2019), Carvalho y
  Zivković (2018), McKenzie, Voss y Siegel (2007).

## Requisitos no funcionales

- Transitorios muy largos (THM-14: 4 años; THM-09: 206 años; EJ-THM-06: 1000 años) cancelables y
  con el tamaño de `modelo.h5` medido.
- Temperatura en kelvin donde la fuente lo pida (relación de Clapeyron, radiación), convertida en
  un único sitio.
- Lo que se pida al núcleo (succión por hielo, flotabilidad) deja a Slip2D bit a bit.

## Casos límite

- Curva de agua no congelada casi vertical (THM-05: sólido total a −0.001 °C); temperatura
  exactamente en la de congelación; frente más fino que un elemento; paso que salta el frente.
- Péclet grande (T12: inestable por encima de un límite, sin estabilización por defecto).
- Material sin modelo no saturado con bloqueo activado; material seco con calor latente.
- Columna libre en deformación plana (THM-15); viga con extremos coaccionados; geosintético que
  pasa su resistencia por contracción (EJ-THM-08).
- Clima con nieve y sin ella; termosifón que se apaga por la regla de activación.

## Fuera de alcance

- Radiación salvo dentro del balance superficial; dispersividad térmica (T12 §1.2.D, con una duda
  de dimensiones y ningún caso que la pida); el factor N del contorno de temperatura (ningún caso
  leído lo pide; sin fuente en T12).
- Levantamiento por helada y presión de hinchamiento del hielo; transporte de solutos; gases.
- Térmico con dinámico, XFEM o consolidación (la referencia los excluye, M25 §2; duda 14); SSR con
  temperaturas, según la duda 15.

## Criterios de finalización

- [ ] Dudas convertidas en decisiones y aprobadas por la propietaria; la spec, partida o no
- [ ] Todos los RF con su test en verde, y la regla 7 en cada opción nueva
- [ ] Cada ley, probada en un punto contra su fuente (regla 8), con su oráculo en Python
- [ ] Los casos que la cierran dentro de tolerancia, con su malla y su paso fijados (regla 9)
- [ ] Las identidades de la tabla, en verde y con dientes
- [ ] Lo pedido a OGR-Core, en una versión etiquetada y fijada aquí
- [ ] Todo texto nuevo con traducción española y toda acción nueva en un menú
- [ ] Changelog con lo encontrado; fichas con su «Seguimiento»

## Dudas abiertas

- [NECESITA ACLARACIÓN] **1. Partir la spec.** Opciones vistas: (a) cuatro: 030a, cambio de fase y
  leyes de propiedades, sin agua (THM-05, -06, -11, -12); 030b, agua y calor (advección, convección
  natural, bloqueo por hielo: THM-07, -08, -09); 030c, termomecánico en sólidos y vigas (THM-15,
  -16, EJ-THM-06); 030d, contornos especiales (balance superficial, termosifones, aislamiento:
  THM-10, -13, -14); (b) por dependencias: la 030c solo necesita la 029, el motor y la 013, y
  podría ir primero; (c) una sola spec con tareas por bloques.
- [NECESITA ACLARACIÓN] **2. Método del cambio de fase**: capacidad aparente con la pendiente de la
  curva (lo que escribe T12), entalpía u otro, con fuente. La «compensación» de la referencia no
  tiene formulación publicada: no se puede reproducir ni conviene imitarla sin fuente.
- [NECESITA ACLARACIÓN] **3. Curvas de agua no congelada**: cuáles (la exponencial de T12, la de
  Anderson y Tice, la derivada del modelo hidráulico, la instantánea, la tabla). T12 duda del signo
  del exponente de Anderson y Tice, de una temperatura mal escrita en la exponencial y de las
  unidades de la conversión a succión; la derivada del modelo hidráulico hereda la retención única
  del núcleo (018, duda 2).
- [NECESITA ACLARACIÓN] **4. Jame-Newman**: T12 la escribe con pesos unitarios y la ficha de THM-05
  da el calor específico en kJ/t/°C; las dimensiones se fijan con la fuente original.
- [NECESITA ACLARACIÓN] **5. Conductividades de estado**: ¿todas (Johansen, Johansen para turbas,
  Johansen-Lu, De Vries, Côté y Konrad) o las que pide un caso? ¿La saturación sale del flujo
  (THM-11, -12) o se da?
- [NECESITA ACLARACIÓN] **6. Esquema de acoplamiento** agua-calor: secuencial por paso, iterado o
  monolítico, y cada cuánto se intercambian; la referencia no lo documenta. ¿Estabilización contra
  Péclet grande, con fuente, o solo el aviso?
- [NECESITA ACLARACIÓN] **7. Convección natural**: un solo caso (THM-09), sin validación posible y
  con la relación densidad-temperatura sin fuente. ¿Entra?
- [NECESITA ACLARACIÓN] **8. Bloqueo por hielo**: es un cambio en el flujo no saturado del núcleo
  (petición a OGR-Core); sus dos casos (EJ-THM-03 sin referencia; EJ-THM-04 numérica). ¿Entra, y
  con qué identidad?
- [NECESITA ACLARACIÓN] **9. Deformación térmica**: la componente fuera del plano en deformación
  plana (en THM-15 la referencia da la deformación libre, no la de la deformación plana estricta); la
  temperatura de referencia (la inicial de cada fase, la de la primera, o una por material); con
  leyes plásticas (EJ-THM-06, Hoek-Brown); en vigas y geosintéticos (013 y 010). ¿Y el modo sin
  transferencia, con la temperatura dada, de la 029, duda 4?
- [NECESITA ACLARACIÓN] **10. Balance superficial**: T12 anota erratas (el exponente de la constante
  de Stefan-Boltzmann, un factor que con el valor de la referencia anula la onda larga, unidades
  inglesas, un calor latente incoherente, referencias cruzadas erróneas) y su fuente principal
  está incompleta. Cuatro casos, ninguno validable. ¿Entra, y con qué términos?
- [NECESITA ACLARACIÓN] **11. Termosifones**: dos casos, los dos comparaciones; los títulos de las
  dos tablas de T12 están cruzados y las unidades del viento no se dan. ¿Entran?
- [NECESITA ACLARACIÓN] **12. Aislamiento en juntas** (solo elementos de junta, 015): ¿aquí o en la
  015? Ningún caso lo pide.
- [NECESITA ACLARACIÓN] **13. Constantes térmicas**: T12 da la densidad del hielo con una unidad que
  no cuadra y calores específicos con magnitudes de otra unidad (T00 §3.3). Valores con fuente,
  ¿constantes o dependientes de la temperatura?, y siempre a la vista (regla 12).
- [NECESITA ACLARACIÓN] **14. Incompatibilidades**: la referencia no deja combinar el térmico con el
  dinámico, el XFEM ni la consolidación. ¿Las mismas aquí, y con qué mensaje?
- [NECESITA ACLARACIÓN] **15. SSR con temperaturas** (EJ-THM-08, sin referencia): ¿se ofrece, con las
  temperaturas de un instante fijas, como el agua en la 009, o queda fuera?

Las referencias T00 y T12 son de la carpeta C del análisis de interfaz
(`../Referencias/Doc_Guia/Analisis_interfaz_funcionamiento/C_teoria/`); M13, M25 e I05, de la
carpeta B (`modelo/` y `compute_interpret/`).
