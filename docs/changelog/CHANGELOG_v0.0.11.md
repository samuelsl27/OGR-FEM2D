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
