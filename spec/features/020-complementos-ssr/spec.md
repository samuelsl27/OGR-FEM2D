# Spec 020 — Complementos del análisis de taludes por SSR

> **Borrador de alcance (2026-11-23), sin aprobar.** Fase 2. **No está en el plan de desarrollo**
> (`spec/constitution/plan_de_desarrollo.md`): recoge funciones de taludes que el índice de casos
> pide mucho y que el plan no coloca en ninguna spec. Hay que añadirla al plan, con el OK de la
> propietaria, antes de abrirla. Solo el **qué** y el **porqué**, sin fórmulas ni decisiones
> tomadas. **Antes de abrirla hay que reevaluarla** (sección siguiente); después, plan y tareas con
> el OK de la propietaria.

## Antes de abrirla: reevaluar esta spec

Este borrador se escribió antes de que existieran las specs que lo preceden; el código, el núcleo y
OGR Slip2D habrán avanzado. Al abrirla, y antes de escribir el plan:

- [ ] Contrastarla con el código de este programa y con las specs cerradas desde el 2026-11-23: qué
      ya está hecho, qué cambió y qué se movió de sitio.
- [ ] Mirar qué tienen ya OGR Slip2D y `ogr_core` en la etiqueta fijada. Lo genérico se pide a la
      sesión de OGR-Core, no se copia (`AGENTS.md`, «Un núcleo y varios programas»). Puntos de
      partida vistos al escribir el borrador:
      grieta: `ogr_core/geometry/tension_crack.py` (nivel del agua en la grieta: seca, llena, en
      porcentaje o bajo una cota), `ogr_core/geometry/boundary_type.py` (`TENSION_CRACK`), y en
      Slip2D `ogr_slip2d/slicer.py` (`tension_crack_boundary`, `apply_tension_crack_truncation`);
      sismo: `ogr_core/loads/loads.py` (`SeismicLoad`: coeficientes horizontal y vertical, solo
      sobre el peso del suelo) y `ogr_slip2d/external_forces.py` (`seismic_soil_weight` y
      siguientes); curva potencial: `ogr_core/materials/builtin_models.py` (`PowerCurve`, criterio
      de equilibrio límite sin regla de flujo); propiedades variables: el mismo archivo
      (`UndrainedDepthFromLayerTop`, `UndrainedDepthFromDatum`, `UndrainedDistanceToSlope`,
      `DiscreteFunction`) y `ogr_core/interpolation.py`; en este programa,
      `ogr_fem2d/engine/initial_stress.py` (`integration_point_coordinates`).
- [ ] Leer y comprobar las fuentes de «Validación numérica» y de «Fuentes por conseguir»; las fichas
      de los casos no son fuente.
- [ ] Releer las fichas de los casos que la cierran y su «Seguimiento».
- [ ] Convertir las «Dudas abiertas» en decisiones propuestas (D1, D2…) con su porqué, para el OK de
      la propietaria.

## Depende de

- Spec 008: la resistencia a tracción de Mohr-Coulomb (la grieta) y la conversión a Hoek-Brown
  generalizado (la curva potencial).
- Spec 009: el SSR, que reduce también las resistencias variables y las de la curva potencial.
- Spec 010: el agua dentro de la grieta y el nivel freático de los casos que los combinan.
- Spec `004-modelo-y-proyecto`: la zona de grieta como geometría, el sismo por fase, las propiedades
  que dependen de la posición.
- Spec `005-resultados` y `006-interfaz-y-calculo`: lo que se ve y los diálogos.

## Contexto y objetivo

El orden de desbloqueo del índice de casos (pasos 4, 5, 6 y 9) pone, justo después del SSR y del
agua, cuatro funciones de taludes que el plan no asigna: **grieta de tracción** (`GRIETA`, 11
casos), **coeficiente sísmico pseudoestático** (`SISMO-PS`, 7), **criterio de curva potencial**
(`PC`, 9) y **propiedades que varían con la profundidad o la posición** (`PROP-VAR`, 6). Todas
existen ya en OGR Slip2D como equilibrio límite; en elementos finitos cambian de naturaleza: la
grieta no es una superficie de rotura dada sino una zona del continuo, el sismo es una fuerza de
masa, la curva potencial necesita una regla de flujo, y la propiedad variable se evalúa en cada
punto de integración.

Se comprobó en el índice qué otras funciones de taludes quedan sin spec: los demás criterios de
resistencia del catálogo (Barton-Bandis, hiperbólico, función por puntos, razón de tensión vertical,
SHANSEP…) **no los pide ningún caso** (`CRIT-OTROS`, cero casos); los clavos (`CLAVO`, SLP-99) son
soporte de la fase 3; los que piden flujo, la fase 4; el probabilístico (SLP-91), la fase 6. El
área de búsqueda y la curva del SSR (`POST-HIST`) son de la 009, y el peso saturado, de la 010.

## Usuarios / actores

- **Ingeniero de taludes**, que pasa a elementos finitos un modelo que ya calculaba en equilibrio
  límite con grieta, sismo o resistencias no lineales.
- **OGR Slip2D**, a través del núcleo y del formato `.ogr`: un modelo con estas entidades debe pasar
  de un programa al otro.

## Historias de usuario

- H1: Como ingeniero quiero definir una zona de grietas de tracción, seca o con agua, para estudiar
  su efecto en el factor crítico como en equilibrio límite.
- H2: Como ingeniero quiero aplicar un coeficiente sísmico horizontal y vertical en una fase, para el
  análisis pseudoestático de un talud.
- H3: Como ingeniero quiero usar la curva potencial ajustada a mis ensayos, sabiendo cómo la ha
  convertido el programa en un criterio con regla de flujo.
- H4: Como ingeniero quiero una resistencia no drenada o un módulo que crece con la profundidad,
  para modelar una arcilla normalmente consolidada o un suelo de Gibson.

## Requisitos funcionales (EARS)

**Grieta de tracción**

- RF-1: CUANDO el usuario define una zona de grietas, EL SISTEMA la modela como se decida (duda
  abierta) y la muestra con el resultado; la opción vista en las fichas (SLP-78) es anular la
  resistencia a tracción en la zona.
- RF-2: CUANDO la grieta lleva agua, EL SISTEMA aplica su presión hidrostática según el nivel dado
  (los modos del núcleo), con la superficie de agua de la 010.

**Sismo pseudoestático**

- RF-3: EL SISTEMA aplica, en la fase indicada, una fuerza de masa proporcional al peso con un
  coeficiente horizontal y otro vertical, con su convenio de signos documentado y dibujado.
- RF-4: EL SISTEMA dice sobre qué actúa la fuerza sísmica (suelo, agua, cargas exteriores), con la
  regla que se decida y su fuente.

**Curva potencial**

- RF-5: EL SISTEMA admite la curva potencial en un análisis elastoplástico y en el SSR, con la
  conversión que se decida (a Hoek-Brown generalizado por la 008, o como Mohr-Coulomb instantáneo,
  T07c §4), y guarda la curva original y los parámetros que resultan.

**Propiedades variables**

- RF-6: EL SISTEMA admite parámetros de resistencia y de rigidez que varían linealmente con la
  profundidad (desde la cima del estrato o desde una cota) o con la distancia al talud, evaluados en
  cada punto de integración, y el SSR reduce el valor de cada punto.

**Reglas transversales**

- RF-7: Cada opción tiene su test que mueve el número (regla 7) y su valor por defecto a la vista
  con el resultado (regla 12); las leyes que resulten se prueban en un punto de Gauss (regla 8).
- RF-8: Lo que el núcleo ya sabe hacer (geometría de la grieta, coeficientes sísmicos, parámetros de
  la curva, perfiles con la profundidad) se usa desde el núcleo; lo que falte se pide a OGR-Core.

## Validación numérica

| Caso | Fuente científica (por comprobar) | Qué se compararía |
|---|---|---|
| `VER-STR-25`, carga en faja sobre suelo de Gibson | Gibson (1967), **analítica** | Asiento bajo la carga con el módulo lineal con la profundidad |
| `VER-SLP-03` (y su par `VER-SLP-72`), ACADS 1(d) con sismo | Giam y Donald (1989) | Factor crítico frente a FS de equilibrio límite publicado |
| `VER-SLP-70`, ACADS 1(b) con grietas llenas de agua | Giam y Donald (1989); profundidad según Craig (1997) | Ídem |
| `VER-SLP-30`, curva potencial | Perry (1993) | Factor crítico frente a la superficie publicada |
| `VER-SLP-94` y `VER-SLP-31`, curva potencial y Mohr-Coulomb | Baker (2003): FS y tensión normal máxima | Factor crítico de cada criterio |
| `VER-SLP-45`, `46` y `119`, resistencia no drenada variable | Duncan y Wright (2005), rangos de referencia | Factor crítico y mecanismo somero o profundo |
| Identidades | — | Sismo horizontal en un modelo sin peso de agua frente a la gravedad girada y escalada; propiedad variable con pendiente nula frente a la constante; curva potencial en su caso lineal frente a Mohr-Coulomb, si la fuente lo permite |

Se proponen como los que la cierran **STR-25** (analítica), **SLP-03**, **SLP-70**, **SLP-30** y
**SLP-45**. Salvo STR-25, las referencias son factores de equilibrio límite publicados: se compara
con tolerancia justificada, y el factor de OGR Slip2D en el mismo modelo es una comparación
independiente. En SLP-78 la zona de grietas del caso 2 es una variante del programa de referencia:
**comparación**. Cálculo propio sobre la tabla maestra: con la fase 1 y las specs 007 a 010, esta
spec añade unos 28 casos (sin los geosintéticos de la 010).

## Fuentes por conseguir

- Craig (1997), para la profundidad de la grieta (la cita la ficha de SLP-70).
- Una fuente de la grieta de tracción en un análisis continuo por elementos finitos: por localizar.
- Una fuente del método pseudoestático: el análisis no la trae; por localizar.
- Perry (1993), Baker (2003) y Miller (1988), para la curva potencial; Balmer (1952), para la
  conversión (008).
- Gibson (1967), para STR-25; Duncan y Wright (2005), para SLP-45, 46 y 119.

## Requisitos no funcionales

- Un `.ogr` de Slip2D con grieta, sismo, curva potencial o perfiles variables se importa sin perder
  datos (`tech-stack.md`: formato compartido), y lo que no tiene sentido en elementos finitos se
  dice al importar.

## Casos límite

- Zona de grieta que corta todo el talud, o que no corta la superficie.
- Grieta con agua por encima del nivel freático.
- Coeficiente sísmico que, solo, ya hace inestable el talud (factor menor que 1).
- Curva potencial con tensión normal nula o de tracción (el exponente no está definido).
- Propiedad variable que se hace negativa en el dominio (gradiente negativo): error, no un recorte.

## Fuera de alcance

- Sismo dinámico, acelerogramas y Newmark (fase 7; Slip2D tiene Newmark para equilibrio límite).
- Los criterios de equilibrio límite que ningún caso pide (Barton-Bandis, hiperbólico, SHANSEP…).
- Clavos de suelo (fase 3) y análisis probabilístico (fase 6).
- Juntas reales para la grieta (fase 3), salvo que se decida modelarla así.

## Criterios de finalización

- [ ] La spec añadida al plan de desarrollo con el OK de la propietaria
- [ ] Todos los RF con su test en verde
- [ ] Los casos que la cierran dentro de la tolerancia fijada antes de medir, con su malla
- [ ] Todo texto nuevo con traducción española y toda acción nueva en un menú
- [ ] Changelog registrando qué se encontró

## Dudas abiertas

- [NECESITA ACLARACIÓN] **Cómo es la grieta en elementos finitos**: (a) zona de material sin
  resistencia a tracción (lo visto en SLP-78); (b) un corte en la malla con la presión del agua en
  sus caras; (c) elementos junta (fase 3). Las fichas dicen que su tratamiento en el programa de
  referencia no está documentado.
- [NECESITA ACLARACIÓN] **Convenio del sismo**: el núcleo da el coeficiente horizontal como magnitud
  en el sentido de la rotura y el vertical positivo hacia abajo; el programa de referencia usa x a la
  derecha e y hacia arriba (P10 usó un coeficiente negativo). En elementos finitos no hay un sentido
  de rotura dado. Liga con la **duda 14 de S06**: un convenio, documentado, en un único sitio.
- [NECESITA ACLARACIÓN] **Sismo sobre el agua**: el núcleo no lo aplica a las cargas ni al agua
  embalsada; ¿y a la masa del agua intersticial (peso saturado)?
- [NECESITA ACLARACIÓN] **Curva potencial**: conversión a GHB (T07a §8, rango por fijar), Mohr-Coulomb
  instantáneo (T07c §4, con la iteración por la dependencia de la tensión sin documentar), o una ley
  propia. SLP-31 muestra que el programa de referencia usa un material de Hoek-Brown generalizado.
- [NECESITA ACLARACIÓN] **Propiedades variables**: ¿desde qué referencia se mide la profundidad
  (cima del estrato, cota, superficie del terreno)? ¿También para la rigidez? STR-25 es elástico y
  podría adelantarse a la fase 1: ¿se queda aquí?
- [NECESITA ACLARACIÓN] **Geosintéticos** (duda 13 de S06): varios casos de grieta los llevan
  (SLP-90); si salen de la 010, ¿vienen aquí o a la fase 3?
