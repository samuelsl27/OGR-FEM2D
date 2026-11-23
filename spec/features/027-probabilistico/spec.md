# Spec 027 — Análisis probabilístico y de sensibilidad

> **Borrador de alcance (2026-11-23), sin aprobar.** Fase 6 del plan de desarrollo
> (`spec/constitution/plan_de_desarrollo.md`, «Fase 6 — Probabilístico»). Solo el
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
      - `ogr_core/statistics/distributions.py`: siete distribuciones con truncamiento
        (`Distribution`, `DistributionType`), Monte Carlo e hipercubo latino (`SamplingMethod`,
        `uniform_samples`, `sample_variables`, con semilla y la opción de estratos compartidos),
        correlación de un par por reordenación de rangos (`correlate_pair`) y `SampleStatistics`
        (media, desviación, probabilidad de rotura como fracción de muestras bajo un umbral,
        índices de fiabilidad normal y lognormal, histograma, convergencia). **No hay estimas
        puntuales.**
      - `ogr_core/statistics/random_variables.py`: `RandomVariable` (tipo, objeto, parámetro,
        distribución, correlación) con `get_value`, `set_value`, `clone_project` y `apply_sample`
        sobre el `Project` **de equilibrio límite**. Sus tipos (resistencia y peso del material,
        hidráulicos, soporte, cargas, sismo, nivel freático) no tienen rigidez, junta ni tensión de
        campo. Generalizarlo depende de qué clase sea el modelo (spec 004, duda 2).
      - `ogr_core/statistics/__init__.py`: los ejecutores se fueron del núcleo al programa porque
        ejecutan el motor; aquí también serán de este programa.
      - En Slip2D, solo lectura: `ogr_slip2d/probabilistic.py` (muestras sobre copias del
        proyecto, recuento de muestras fallidas), `ogr_slip2d/sensitivity.py` (una variable cada
        vez entre su mínimo y su máximo, las demás en la media, intervalos fijos por defecto) y
        sus tests `tests/test_probabilistic_v135.py`, `test_sensitivity_v136.py` y
        `test_probabilistic_all_failed_v1169.py`.
      - Aquí: `ogr_fem2d/engine/` (cada muestra es un cálculo completo); la 011 (coste del bucle),
        la 006 (cálculo en subproceso con cola) y la 005 (`modelo.h5`).
      - Lo observado: `dialogos/D06` (variables de material, de junta y de tensión de campo) y
        `reproducciones/P06` (SLP-01 con dos variables); carpeta B, `modelo/M27_probabilistico.md`
        y `compute_interpret/I05` §5; teoría en `C_teoria/T08`.
- [ ] Leer y comprobar las fuentes de «Validación numérica» y de «Fuentes por conseguir»; las fichas
      de los casos no son fuente.
- [ ] Releer las fichas de los casos que la cierran y su «Seguimiento».
- [ ] Convertir las «Dudas abiertas» en decisiones propuestas (D1, D2…) con su porqué, para el OK de
      la propietaria.

## Depende de

- Spec 009 (SSR): el probabilístico con SSR repite una búsqueda entera por muestra.
- Spec 011 (rendimiento): el probabilístico multiplica el coste del bucle por el número de muestras.
- Specs `004-modelo-y-proyecto` (qué parámetros se pueden direccionar; las variables, el método y
  la semilla en el `.ogr` y en la huella), `005-resultados` (muestras y estadísticos en
  `modelo.h5`) y `006-interfaz-y-calculo` (cola, progreso, cancelación).
- Specs 008 (parámetros de cada ley), 012 (fases), 015 (variables de junta) y 020 (curva potencial
  de VER-SLP-91). Para EJ-SEE-03, además las 017 y 018.

## Contexto y objetivo

Un cálculo determinista da un número para unos datos que no se conocen con exactitud. El
probabilístico repite el cálculo con los datos inciertos y resume la dispersión de lo que sale:
media, desviación típica y coeficiente de variación de tensiones y desplazamientos, probabilidad de
plastificación por elemento y, con SSR, la distribución del factor crítico y la probabilidad de
rotura. La versión observada del programa de referencia solo tenía las estimas puntuales de
Rosenblueth (1975) (T08, D06); la actual añade Monte Carlo e hipercubo latino (carpeta B, M27), que
el núcleo ya tiene para el equilibrio límite. El análisis de sensibilidad barre un parámetro y
mira cómo responde el resultado.

Es un bucle externo sobre el motor: no lo toca (regla 11), pero multiplica su coste. Con estimas
puntuales el número de cálculos crece de forma exponencial con el número de variables (T08); con
SSR cada muestra es una búsqueda completa (009). Por eso esta spec se mide con la 011.

Solo dos casos piden `PROB`: VER-SLP-91 (sensibilidad de dos parámetros de la curva potencial,
sin resultados publicados de la sensibilidad) y EJ-SEE-03 (cien campos aleatorios de
permeabilidad generados con otro programa). Ninguno es una validación: la spec se cierra con
identidades y con un caso analítico propio.

## Usuarios / actores

- **Ingeniero de rocas y de taludes**, que necesita la dispersión del resultado y no solo un valor.
- **Investigador y docente**, que comparan estimas puntuales con Monte Carlo en el mismo modelo.
- **Agente vía MCP**, que lanza el análisis y lee la tabla de muestras.

## Historias de usuario

- H1: Como ingeniero quiero declarar como aleatorios parámetros de material, de junta y de tensión
  de campo, y obtener la media y la desviación de cualquier magnitud, para saber cuánto me fío.
- H2: Como ingeniero quiero la probabilidad de rotura de un talud por SSR, y saber cómo se ha
  calculado, para no tomar por buena una cifra que dependa de una hipótesis oculta (P06).
- H3: Como ingeniero quiero barrer un parámetro y ver dónde el factor crítico cruza 1.
- H4: Como investigadora quiero repetir un análisis exactamente: misma semilla, mismas muestras.
- H5: Como ingeniero quiero saber antes de lanzar cuántos cálculos hará y cuánto tardará.

## Requisitos funcionales (EARS)

**Variables y muestreo**

- RF-1: EL SISTEMA permite declarar como aleatorio un parámetro de material, de junta o de la
  tensión de campo de entre los que el modelo usa (lista según la duda 3), con su distribución,
  media, desviación y límites; SI el parámetro no lo usa el modelo, ENTONCES no se ofrece.
- RF-2: EL SISTEMA ofrece estimas puntuales de Rosenblueth (1975), Monte Carlo e hipercubo latino;
  los dos últimos con el muestreo del núcleo y la semilla guardada en el modelo.
- RF-3: SI una variable no tiene dispersión, o la combinación de método y distribución no es
  válida (las estimas puntuales no usan distribución, carpeta B), ENTONCES EL SISTEMA lo dice y no
  la trata en silencio como determinista.
- RF-4: EL SISTEMA aplica la correlación y el truncamiento que se decidan (duda 7) y lo escribe con
  el resultado.

**Cálculo**

- RF-5: CUANDO se pide un probabilístico, EL SISTEMA dice antes de empezar cuántos análisis hará
  (con el de las medias, según la duda 4) y una estimación del tiempo con la medida de la 011; SI
  pasan del umbral que se fije, ENTONCES avisa antes de lanzar.
- RF-6: EL SISTEMA calcula cada muestra sobre una copia del modelo, nunca sobre el del usuario, y
  el resultado no depende del orden ni del número de procesos con que se calculen.
- RF-7: SI una muestra no converge o falla, ENTONCES EL SISTEMA hace lo que se decida (duda 5) y el
  resultado dice cuántas fueron y cuáles.
- RF-8: EL SISTEMA calcula en subproceso, cancelable, con el progreso por muestra (006).

**Resultados**

- RF-9: EL SISTEMA da la media, la desviación típica y el coeficiente de variación de las
  magnitudes de campo donde se decida (duda 6), y la probabilidad de plastificación por elemento.
- RF-10: CON SSR, EL SISTEMA da el factor crítico de cada muestra, su media, su desviación, su
  histograma y la probabilidad de no llegar a un umbral (1 por defecto, editable), con el método
  con que se ha calculado esa probabilidad escrito junto a ella (duda 1; regla 12).
- RF-11: EL SISTEMA guarda en `modelo.h5` (ADR-0003) lo que se decida de cada muestra, con la
  huella del modelo, las variables, el método, el número de muestras y la semilla.

**Sensibilidad**

- RF-12: EL SISTEMA barre una variable cada vez entre su mínimo y su máximo, con las demás en su
  media, y da la curva del resultado elegido y dónde cruza un umbral; el número de puntos del
  barrido va con el resultado (regla 12).

**Reglas transversales**

- RF-13: El motor no sabe que hay un probabilístico: recibe una entrada como cualquier otra (regla
  11). Lo que genera y combina las muestras es Python; nada de esto va a Rust salvo que la 011 lo
  pida, y entonces con la referencia en Python como oráculo.
- RF-14: Las variables de tensión de campo se escriben en el convenio del usuario y pasan por la
  conversión única de la 004 (su RF-8; regla 10).
- RF-15: Cada ajuste nuevo (método, número de muestras, semilla, correlación, truncamiento, umbral,
  puntos del barrido) lleva su test que mueve el número (regla 7); los textos pasan por `tr()` y
  las acciones están en el menú de estadística (reglas 2 y 3).

## Validación numérica

| Caso | Fuente científica (por comprobar) | Qué se compararía |
|---|---|---|
| Kirsch con tensión de campo incierta (el ejemplo de T08, sobre la malla del caso 005) | Kirsch (1898), en Jaeger, Cook y Zimmerman (2007), §8.4; Rosenblueth (1975) | La tensión en el contorno del hueco es lineal en las tensiones de campo: con entradas normales independientes, las estimas puntuales deben dar la media y la desviación exactas de esa combinación (T08 lo da como observación propia: comprobarlo en Rosenblueth 1975). La cifra del ejemplo del manual es de otro programa y no es valor esperado |
| Monte Carlo e hipercubo latino, mismo caso | Las mismas | Media y desviación convergen a las exactas al crecer el número de muestras; tolerancia estadística fijada antes de medir, con el número de muestras y la semilla fijados por el caso, como la malla (regla 9) |
| Probabilidad de rotura de una salida de distribución conocida | — (identidad con la función de distribución) | La probabilidad que da el sistema con el método que declara |
| Desviación nula | — (identidad) | Todas las muestras iguales al determinista, bit a bit |
| Semilla, orden y procesos | — (identidad) | Misma semilla, mismos resultados; otro orden u otro número de procesos, también |
| Sensibilidad de una carga en elástico | — (linealidad) | El barrido de la magnitud de una carga da una recta exacta en desplazamientos |
| `VER-SLP-91`, talud con curva potencial | Perry (1993), factor publicado sobre una superficie prefijada (spec 020) | El factor crítico es de la 020; la sensibilidad no tiene resultados publicados: **comparación** con lo que dé el equilibrio límite de OGR Slip2D en el mismo barrido |
| `EJ-SEE-03`, desembalse con permeabilidad aleatoria | Ninguna: campos e histograma de otro programa | **Comparación**; necesita además permeabilidad variable (017, duda 12) y no saturado (018) |
| Regla 7 | — | Cada ajuste de RF-15 mueve el número |

La reproducción P06 (SLP-01 con dos variables) se hizo para recorrer los menús: lo que dio el
programa de referencia **no es un valor esperado**. Se propone que cierren la spec el caso de
Kirsch y las identidades; los dos casos del índice quedan como comparaciones.

## Fuentes por conseguir

- Rosenblueth (1975), *PNAS* 72(10), la fuente del método según T08 y la carpeta B (I05). La
  carpeta B (M27) cita «Rosenblueth (1972)»: comprobar si hay dos trabajos o una errata.
- Valley, Kaiser y Duff (2010): estimas puntuales frente a Monte Carlo, y su fallo cuando las
  muestras caen en mecanismos distintos (T08). Hoek (1992), citada por T08 para la incertidumbre.
- Iman, Davenport y Zeigler (1980) y Startzman y Wattenbarger (1985), para el hipercubo latino
  (carpeta B); Law y Kelton (1991), para los parámetros de las distribuciones beta y gamma; Duncan
  (2000), regla de las tres sigmas. La reordenación de rangos que el núcleo atribuye a Iman y
  Conover no lleva referencia completa.
- Perry (1993), para SLP-91 (lo pide también la 020).
- Ninguna está en `Referencias/Bibliografia`.

## Requisitos no funcionales

- Coste: el de un determinista por el número de muestras; con SSR, también por el de pruebas y
  escalones (P05: ocho pruebas de diez escalones). Medirlo con la 011 en un SSR de la fase 2 antes
  de fijar umbrales y avisos.
- Las muestras son independientes: se pueden calcular en procesos en paralelo, con memoria acotada
  y resultado reproducible (RF-6).
- Guardar todos los campos de todas las muestras puede no caber en `modelo.h5`: medirlo.
- Sin dependencias nuevas.

## Casos límite

- Una sola variable; muchas (las estimas puntuales se vuelven inviables, carpeta B M27).
- Variable que el modelo no usa: material sin asignar, cohesión de un material elástico (M27 §4).
- Muestra con un parámetro sin sentido físico (cohesión negativa, ν de 0.5 o más, rigidez nula).
- Ninguna muestra converge; todas fallan (Slip2D tiene su test).
- Muestras en mecanismos distintos, elástico y plástico: T08 advierte que las estimas puntuales
  fallan y que la salida deja de ser normal.
- Variables en un modelo con fases; propiedades por fase (012).
- Modelo cambiado después del cálculo: resultados obsoletos (ADR-0003).

## Fuera de alcance

- Campos aleatorios espaciales: EJ-SEE-03 los genera con otro programa y ninguna fuente leída
  describe cómo; el caso solo se podría reproducir cargando campos dados.
- Variables de soporte, de cargas, de agua y de geometría, salvo que la duda 3 las traiga.
- Estadística de bulones y revestimientos (carpeta B, I05 §5.6), salvo que la duda 6 la traiga.
- Variantes de las estimas puntuales con correlación o asimetría: T08 no las describe.
- Análisis inverso y optimización.

## Criterios de finalización

- [ ] Dudas convertidas en decisiones y aprobadas por la propietaria
- [ ] Todos los RF con su test en verde, y la regla 7 en cada ajuste nuevo
- [ ] El caso de Kirsch y las identidades de la tabla, dentro de tolerancia y con dientes
- [ ] Coste medido con la 011 y umbrales fijados con esa medida delante
- [ ] Lo pedido a OGR-Core, en una versión etiquetada y fijada aquí
- [ ] Todo texto nuevo con traducción española y toda acción nueva en un menú
- [ ] Changelog con lo encontrado; fichas con su «Seguimiento»

## Dudas abiertas

- [NECESITA ACLARACIÓN] **1. Probabilidad de rotura (S06, duda 2).** En P06 el programa de
  referencia dio 35.21 % con media 1.03 y desviación 0.1095; una normal daría ≈ 39 %. La carpeta B
  (I05 §5.8) dice que la calcula con una normal. Opciones vistas: (a) con estimas puntuales, solo
  momentos, y la probabilidad con una distribución declarada y mostrada; (b) la probabilidad solo
  como fracción de muestras, con Monte Carlo o hipercubo (lo que hace el núcleo); (c) las dos, cada
  una con su nombre. Lo que no se sabe de P06 (redondeo de la media mostrada, si entra el cálculo
  de las medias) no se copia.
- [NECESITA ACLARACIÓN] **2. Métodos**: los tres desde el principio, o primero las estimas
  puntuales (lo único que describe T08) y después los del núcleo.
- [NECESITA ACLARACIÓN] **3. Qué variables.** D06 y M27: módulo, Poisson, tracción, rozamiento y
  cohesión de pico y residuales, dilatancia; rigideces y resistencia de junta; razones de
  tensión de campo y tensiones horizontales fijas. ¿Cuáles? ¿Se generaliza `RandomVariable` del
  núcleo (petición a OGR-Core) o se escribe aquí una propia? ¿La media es siempre el valor
  determinista del modelo (D06 no la deja editar)?
- [NECESITA ACLARACIÓN] **4. El cálculo con las medias** («archivo base» de la carpeta B, M27 §2 e
  I05 §5.1): ¿se hace?, ¿entra en la media y en la desviación? En P06 solo se vieron los cálculos
  de las combinaciones.
- [NECESITA ACLARACIÓN] **5. Muestras que no convergen** (T08: no documentado): se excluyen y se
  cuentan, se toman como rotura en el SSR, o se detiene el análisis.
- [NECESITA ACLARACIÓN] **6. Qué se guarda y dónde se combina**: en puntos de integración, en
  elementos o en nudos (T08 no lo dice); todos los campos de cada muestra o solo los estadísticos y
  unas magnitudes elegidas.
- [NECESITA ACLARACIÓN] **7. Correlación y truncamiento**: la pareja cohesión–rozamiento que tiene
  el núcleo, la casilla «residual igual a pico» (D06), y los límites relativos de la carpeta B.
- [NECESITA ACLARACIÓN] **8. Sensibilidad**: aquí o en la 020; el número de puntos (Slip2D usa
  intervalos fijos) es un valor por defecto que se muestra.
- [NECESITA ACLARACIÓN] **9. SSR probabilístico**: una búsqueda completa por muestra es lo directo y
  lo caro. ¿Se acepta ese coste, o se espera a la 011 para fijar el número máximo de muestras?
- [NECESITA ACLARACIÓN] **10. Tolerancia estadística** de las identidades con Monte Carlo: con qué
  número de muestras y semilla, y con qué criterio se fija antes de medir.
- [NECESITA ACLARACIÓN] **11. Cuándo**: T00 §4 dice que el probabilístico «puede hacerse en
  cualquier momento después de la fase 2»; el plan lo pone en la fase 6. ¿Se mantiene?

Las referencias D06 y P06 son de la carpeta A del análisis de interfaz
(`../Referencias/Doc_Guia/Analisis_interfaz_funcionamiento/`, `dialogos/` y `reproducciones/`);
M27 e I05, de la carpeta B (`modelo/` y `compute_interpret/`); T00 y T08, de `C_teoria/`.
