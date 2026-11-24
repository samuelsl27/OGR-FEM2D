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
