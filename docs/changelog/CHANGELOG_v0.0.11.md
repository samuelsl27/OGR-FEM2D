# OGR FEM2D v0.0.11

**Fase 1, cuarta parte: los resultados** (spec 005). Cada cálculo se guarda en `modelo.h5`, junto al
`.ogrfem2d` y con su huella (ADR-0003). Encima, sin Qt, va lo que se interpreta: las magnitudes con
su fuente, los valores en los nudos y las consultas. Este archivo cuenta lo que fue entrando, tarea a
tarea.

## La spec, el plan y las tareas (2026-11-24)

Revisados contra el código, el núcleo (`v0.2.7`), OGR Slip2D, las fuentes y las fichas, y aprobados
con D1–D16 (`spec/features/005-resultados/`). Lo que se encontró al revisarla:

- **La cita de la recuperación estaba mal.** El §14.2 de Zienkiewicz y Taylor (2000) es el de los
  puntos de muestreo óptimos. La recuperación es el §14.3, donde dicen que el promedio en los nudos es
  inadecuado en triángulos, y el §14.4, la recuperación por parches (SPR).
- **`analysis.run` pierde las fases resueltas si una falla**: devuelve la lista al final. Guardar
  resultados parciales (D7) pide entregar las fases una a una.
- **Las fuentes que faltaban estaban en la bibliografía.** Jaeger, Cook y Zimmerman (2007), cap. 2,
  da las principales, los invariantes, J2, las deformaciones y la volumétrica; de Souza Neto et al.
  (2008), la tensión de von Mises (6.111) y Mohr-Coulomb en invariantes (6.119), que va a la 008 con
  el factor de resistencia (D4).
- **`results_io.py` del núcleo es de equilibrio límite** de punta a punta: el `.h5` se escribe aquí,
  con `h5py` declarado (D8).

## T0 — aprobación (2026-11-24)

D1–D16 aprobadas tal como se propusieron. ADR-0003 dice ahora que el `.h5` se escribe aquí;
`plan_de_desarrollo.md` cita el §14.3–14.4 y pasa el factor de resistencia a la 008; `h5py>=3.10`,
declarado en `pyproject.toml` (ya estaba en el `.venv`, que lo trae el núcleo).

## T1 — las magnitudes (2026-11-24)

Paquete nuevo `ogr_fem2d/results/`. `quantities.py`: el catálogo (D16), 22 magnitudes con su
definición, su fuente, su unidad, su convenio y su nombre en axisimetría, y su cálculo vectorizado
desde los tensores del usuario. `model/conventions.py` recibe la conversión de salida (D1): tensión y
deformación cambian de signo, el desplazamiento no. La versión pasa a 0.0.11.

- **Tres erratas del libro, no de la extracción** (JCZ 2007, leídas sobre la página renderizada):
  - (2.149), pág. 40: imprime (σ3 − σ3)² donde va (σ3 − σ1)²;
  - (2.162), pág. 41: imprime τ²xx + τ²yy + τ²zz donde va el desviador, s²xx + s²yy + s²zz (con τ,
    un estado hidrostático tendría J2 ≠ 0);
  - (2.195), pág. 47: el corchete de las principales de deformación va sin la raíz que sí lleva su
    gemela de tensiones, la (2.37).

  Ninguna se usa tal cual: J2 sale de la (2.163), que está bien, y las principales de deformación,
  con la raíz.
- **El ángulo de σ1 va de 0° a 180°**, el intervalo de JCZ (2.41)–(2.44), y no de −90° a 90° como
  decía el plan; el plan, corregido.
- `tests/test_results_quantities_v0011.py`, 16 tests: invariantes con 200 tensores al azar y siete
  giros, θ1 que gira con los ejes, (2.146), (2.163) = (2.164), estado hidrostático, las cuatro ramas
  del ángulo, el orden con σz mayor, intermedia y menor, el signo del usuario, la conversión en un solo
  sitio y el catálogo. 12 mutaciones, 12 cazadas tras añadir un test (la media sin σz sobrevivía a los
  giros y al estado hidrostático).

## T2 — las deformaciones (2026-11-24)

`results/strains.py`: B u en cada punto con la B que construye el propio motor
(`solver.integration_points`), escrita con NumPy; NaN en los puntos de los elementos inactivos. En el
signo del motor (alargamiento positivo); el del usuario lo pone `conventions.py` (D1).

- `tests/test_results_strains_v0011.py`, 7 tests: la prueba de la parcela (desplazamiento lineal
  impuesto, deformación exacta en todos los puntos) con T3 y T6, en deformación plana y en
  axisimetría (εθ = u/r en el punto) y en los T6 curvos de un túnel; el producto es
  `IntegrationPoint.strain` del motor punto a punto; los inactivos sin deformación; γmax es la
  ingenieril (un corte puro γ da γmax = γ). 7 mutaciones, 7 cazadas tras completar un test (εv sin
  εθ sobrevivía en deformación plana, donde εz = 0).

## T3 — el motor fase a fase (2026-11-24)

`engine/analysis.py`: `stages(m, variant)`, el cuerpo de `run` con `yield` en lugar de acumular, y
`run` = `list(stages(...))`. Una fase que falla lanza su error después de haber entregado las
anteriores (D7). `docs/motor/entrada.md` lo dice.

- **Bit a bit**: una huella (SHA-256 del `repr` de desplazamientos, tensiones, reacciones, plástico,
  eje, `solved`, historia, ajustes, activos y retirados) de los casos 003 a 007 y de un túnel de tres
  fases, antes y después del cambio, idéntica en los seis. Los casos 001 y 002 llaman a
  `solver.solve_stage` directamente y no pasan por aquí.
- `tests/test_analysis_stages_v0011.py`, 3 tests: `run` es la lista de las fases; una fase sin
  restricciones suficientes deja entregada la anterior y lanza su error con su índice; la entrada se
  comprueba antes de la primera fase. 4 mutaciones, 4 cazadas.

## T4 — el archivo de resultados (2026-11-24)

`results/store.py` y `docs/resultados/formato.md`: el `.h5` campo a campo. `Writer` escribe a
`<raíz>.h5.tmp`, añade las fases según llegan y, en `finish`, pone el estado y lo mueve con
`os.replace`. Si algo falla, o el escritor se queda sin `finish`, borra el temporal y deja el `.h5`
anterior. `read` comprueba la forma entera al abrir (formato, versión, atributos, cada campo con su
tamaño) y después lee una fase o un campo sueltos. Las tensiones de los inactivos van como NaN y
vuelven como `None`; los grandes, con gzip y *shuffle*.

- `tests/test_results_store_v0011.py`, 10 tests: cada fase leída es la `StageOutcome` del motor (`==`),
  y las deformaciones y la malla, los mismos bits; lo que decidió el resultado vuelve; un campo se lee
  solo; un archivo que no es HDF5, de otro programa, de un formato posterior, sin un campo o con un
  campo de otro tamaño dan `ResultsError` con lo que falla; un error a mitad o un escritor sin
  `finish` dejan el anterior y ningún temporal; el estado es coherente. 9 mutaciones, 9 cazadas.

## T5 — calcular y abrir (2026-11-24)

`results/calculate.py`. `calculate(modelo, ruta)` traduce, resuelve fase a fase y escribe
`<raíz>.h5` junto a `<raíz>.ogrfem2d`:

- **completo**;
- **incompleto**, si una fase no se resuelve: no converge, un punto no se actualiza, las
  restricciones dejan libre el modelo o una carga cae fuera de su elemento. Las fases anteriores
  quedan escritas, con el error del motor;
- **cancelado**, si `should_stop()`, consultado entre fases, lo pide.

Un modelo que no se traduce, o un error de entrada, no escribe nada y deja el `.h5` anterior.
`open_results` da el estado: `valid`, `stale`, `incomplete`, `cancelled`, `missing` o `damaged`.
Solo los válidos se dan tal cual; los demás, con `read_anyway`. Otra versión del programa o del
núcleo no los hace obsoletos, pero se dice (D7).

- **La medida del caso 005** (56 367 nudos, 28 066 T6, 84 198 puntos, una fase):

  | gzip | tamaño | la copia de la malla | escribir |
  |---|---|---|---|
  | sin comprimir | 10.50 MB | 4.72 MB | 0.05 s |
  | 1 | 6.49 MB | 2.15 MB | 0.22 s |
  | **4** | **6.45 MB** | **2.13 MB** | **0.24 s** |
  | 9 | 6.42 MB | 2.13 MB | 0.37 s |

  Abrir y leer las tensiones de la fase, 0.02 s. La B de todos los puntos, 0.84 s, y B u, 0.02 s;
  resolver la fase con el motor de referencia, 26 s. **Se queda gzip 4**: más nivel no gana nada. La
  copia de la malla es un tercio del archivo con una fase, menos con más fases; se queda (D6).
- `tests/test_results_calculate_v0011.py`, 6 tests: los resultados son los del motor; cada estado,
  con el incompleto (una liberación de todo el externo en la fase 2) y el cancelado; otra versión,
  válida y dicha; un modelo sin malla no escribe nada. 7 mutaciones, 7 cazadas.

## T6 — situar un punto (2026-11-24)

`results/locate.py`: una rejilla de las cajas de los elementos (ampliadas un 1 % de su diagonal) y,
en cada candidato, la inversa isoparamétrica del motor (`loads.local_coordinates`). El punto está en
el elemento si sus coordenadas de área son ≥ −10⁻⁹ y el mapa las devuelve al punto. Da todos los
elementos activos que lo contienen, en orden de índice, o dice si el punto está en una excavación o
fuera del modelo.

- `tests/test_results_locate_v0011.py`, 4 tests: dentro de un elemento; sobre un lado y sobre un nudo,
  todos los que lo tienen; entre la cuerda y el arco de un T6 curvo, en el elemento del arco (en el
  hueco: con el hueco excavado no hay elemento activo, aunque el triángulo de esquinas del vecino lo
  contiene) y, justo fuera del arco, en la roca; excavado y fuera, por separado. 5 mutaciones, 5
  cazadas (entre ellas, situar con el triángulo de esquinas).

## T7 — las figuras de Zienkiewicz y Taylor, sobre la página (2026-11-24)

Leídas sobre las páginas renderizadas, porque el texto extraído pierde los dibujos.

- **Fig. 14.6, pág. 375** (puntos de muestreo óptimos y de cuadratura mínima, según Moan). En el T3
  coinciden: el centroide. **En el T6, no** (hallazgo, regla 6):
  - los óptimos, con error O(h⁴), son puntos interiores;
  - los tres medios de los lados, que es la regla del motor en deformación plana (spec 002, D1), son
    los de la **cuadratura mínima**, con O(h³).

  La recuperación se hace igual, como ajuste por mínimos cuadrados sobre los puntos de integración, y
  la regla del motor no se toca. Se pierde la superconvergencia que promete el texto, pero no la
  exactitud con un campo que la malla representa, que es la identidad que se prueba. La regla de 7
  puntos de la axisimetría tampoco es la óptima.
- **Fig. 14.8, pág. 378** (los parches). En los triángulos, el parche se monta en un nudo de esquina
  interior con los elementos que lo tienen. **Determina el nudo central y, en el T6, los intermedios de
  los lados que salen de él** (los puntos negros). Los nudos del borde exterior del parche (blancos)
  los determinan otros parches. Esto **precisa D5**: decía que cada nudo toma la media de todos los
  parches que lo contienen. Ahora un nudo de esquina interior sale solo de su parche, y un intermedio
  interior, de los dos parches de los extremos de su lado.
- **Fig. 14.9, pág. 379** (bordes y contactos). Los nudos de un contorno o de un contacto entre
  materiales salen de los parches interiores vecinos de su material, cada material con los suyos. Es
  lo que decía D5.

El plan («Decisiones de diseño» y «Formulación») está corregido con las tres.

## T8 — la recuperación por parches, material a material (2026-11-24)

`results/recovery.py`. Por fase y por material, con los elementos activos:

- en cada nudo de esquina interior, el polinomio de grado p (1 en T3, 2 en T6) ajustado por mínimos
  cuadrados a los puntos de integración del parche (Z&T ecs. 14.28–14.31), en coordenadas centradas
  en el nudo y escaladas por el tamaño del parche;
- cada parche determina su nudo, los intermedios de sus radios en T6 (fig. 14.8) y los nudos de su
  parche que están en el borde del material (fig. 14.9). Un nudo que determinan varios parches toma
  la media;
- un nudo que no alcanza ningún parche toma el campo de sus propios elementos, de grado p − 1, y su
  procedencia lo dice (`ELEMENT`).

El resultado va por (elemento, nudo local), con un valor por material en los contactos y NaN en los
inactivos.

- **Lo que no alcanza ningún parche** no es solo un material de un elemento de espesor. También es un
  elemento con sus tres esquinas en el contorno, como la esquina de un cuadrado, y los nudos que
  comparte con sus vecinos. Ahí el valor es el del propio elemento: exacto con un campo de grado
  p − 1, no con uno de grado p. Es la salida de D5, sin cambio.
- **El caso 005** (84 198 puntos): 2.2 s, 13 089 parches, ninguno rechazado por el número de
  condición, y 16 nudos por el campo del elemento.
- `tests/test_results_recovery_v0011.py`, 6 tests:
  - un campo cuadrático con T6 en la malla curva de un túnel, exacto en todos los nudos que alcanza
    un parche, contornos y hueco incluidos;
  - el campo gravitatorio de dos estratos, exacto a cada lado del contacto, con el salto de la
    tensión horizontal;
  - un campo constante con T3;
  - la regla de la fig. 14.8, con datos al azar;
  - un material de un elemento de espesor, con su procedencia;
  - un elemento inactivo con basura en sus puntos, que no entra.

  8 mutaciones, 8 cazadas, entre ellas mezclar los materiales en un parche.

## T9 — la línea, todos los nudos y todos los puntos (2026-11-24)

`results/queries.py`. `View(resultados, fase)` reúne lo que comparten las consultas de una fase: el
localizador (guardado en el propio objeto de resultados, sin estado global, regla 5), los tensores
del usuario y los valores recuperados.

- `line`: n puntos a la misma distancia en toda la polilínea, o sus vértices, con la distancia
  acumulada. Los desplazamientos salen del campo de elementos finitos. Las tensiones y las
  deformaciones salen de los valores recuperados, interpolados **como tensor**: la magnitud (σ1, q…)
  se calcula del tensor en el punto. Sobre un contacto hay una fila por material, y fuera o en una
  excavación la fila va sin valor y con la razón.
- `all_nodes`: un desplazamiento por nudo; una tensión por nudo y material, sin valor en un nudo
  retirado.
- `all_points`: el valor del motor en cada punto, sin valor en los excavados.
- Cada fila dice su procedencia: `point`, `fe`, `spr`, `element` o `spr+element` (H6).

`tests/_results.py` calcula los modelos de las pruebas: dos estratos con una sobrecarga y el túnel
excavado. `tests/test_results_queries_v0011.py`, 7 tests: dónde caen los puntos; el salto en un
contacto; sin valor fuera y en la excavación; el desplazamiento y la tensión en un nudo son el nodal y
el recuperado; todos los nudos, con dos filas en el contacto y ninguna en los retirados; todos los
puntos, los del motor. 8 mutaciones, 8 cazadas.

## T10 — la consulta sobre un contorno (2026-11-24)

`queries.on_boundary` y `boundary_points`: sobre la geometría del modelo, con sus arcos (D12). Toma
los vértices, o n puntos por segmento sobre el segmento o el arco, con la distancia a lo largo del
contorno (longitud de arco en los arcos). Con una distancia d, cada punto se mueve por la normal hacia
el lado pedido: dentro o fuera en un contorno cerrado, izquierda o derecha en uno abierto. En un
vértice va por la bisectriz de las dos normales. Qué lado es dentro lo dice el área con signo del
contorno, con los arcos incluidos: la mitad de ∮ x dy − y dx. La distancia por defecto es 0, y una
distancia sin lado es un error.

- `tests/test_results_boundary_v0011.py`, 5 tests:
  - sobre el círculo de un túnel, los puntos en el círculo y a su longitud de arco;
  - dentro y fuera, los círculos concéntricos, también con el contorno en sentido horario;
  - el área con signo de un círculo de cuatro arcos es πr²;
  - izquierda, derecha y la bisectriz en una esquina;
  - en el hueco excavado no hay valor, fuera sí, y fuera del externo tampoco.

  7 mutaciones, 7 cazadas.
