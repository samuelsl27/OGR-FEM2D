# Tareas — Spec 005, resultados (`.h5`) y su interpretación sin interfaz

Pequeñas y verificables, ordenadas por dependencia. Al terminar cada una:
- este archivo y el changelog, al día;
- la suite entera en verde (`.venv/Scripts/python tests/_runner.py`);
- el commit directo en `main`, sin push hasta que la propietaria lo pida.

Cada test lleva su cabecera y tiene dientes: mutaciones sistemáticas
(`{etiqueta: (archivo, texto, sustituto)}`), anotadas aquí.

## Antes de programar

- [x] T0. **Spec, plan y tareas aprobados**, con D1–D16. Va en un commit propio.
  - ADR-0003, «Decisión»: ya no se parte de `ogr_core/project/results_io.py` (D8).
  - `plan_de_desarrollo.md`, «Spec 005»: el §14.2 pasa a §14.3–14.4, el factor de resistencia va a
    la 008 (D4) y `results_io.py` sale.
  - `pyproject.toml`: `h5py>=3.10` en las dependencias, con su licencia (BSD-3) en el comentario.
    No se instala nada: ya está en el `.venv` (3.16).

  *Hecho cuando:* la propietaria ha dado el OK, y las decisiones están anotadas como aprobadas en
  `spec.md` y `plan.md`. (Hecho el 2026-11-24: OK de la propietaria a D1–D16; corregidos ADR-0003,
  que ahora dice que el `.h5` se escribe aquí, y `plan_de_desarrollo.md`, en la 005 y en la 008;
  `h5py>=3.10` declarado, sin instalar nada.)

## Las magnitudes, las deformaciones y el motor

- [x] T1. **v0.0.11**, `results/quantities.py`, el catálogo (D16) y las magnitudes de tensión (D2).
  - Antes de programar, las ecuaciones de JCZ (2.37)–(2.44), (2.149), (2.153), (2.162)–(2.163) y
    (2.195), y la (6.111) de dSN, **leídas sobre la página**, no sobre el texto extraído. Lo que
    se vea de las tres erratas posibles, al changelog.
  - La conversión de salida en `model/conventions.py` (D1).
  - En axisimetría, los nombres de cada magnitud.
  - La versión pasa a 0.0.11 y empieza `CHANGELOG_v0.0.11.md`.

  *Hecho cuando:* los tests de invariantes, de convenio y de axisimetría de la «Estrategia» están en
  verde con tensores sueltos, y cada magnitud cita su fuente en el código.
  (Hecho el 2026-11-24: 16 tests; 12 mutaciones, 12 cazadas. **Tres erratas del libro** en JCZ,
  (2.149), (2.162) y (2.195), vistas sobre la página; ninguna se usa tal cual. θ1 en [0°, 180°), el
  intervalo de JCZ, changelog.)
- [x] T2. `results/strains.py` y las magnitudes de deformación (D3, D6): B u con la B del motor;
  εv y γmax.

  *Hecho cuando:* la prueba de la parcela (desplazamiento lineal impuesto) da la deformación exacta
  en todos los puntos con T3 y T6, en deformación plana y en axisimetría, y γmax tiene su factor 2.
  (Hecho el 2026-11-24: 7 tests; 7 mutaciones, 7 cazadas.)
- [x] T3. `engine/analysis.py`: `stages()`, el generador de fases (D7).

  *Hecho cuando:*
  - `run` y `list(stages())` dan lo mismo bit a bit en los casos 001 a 007;
  - una fase que falla entrega antes las anteriores y después lanza su error;
  - los tests del motor siguen sin un cambio.

  (Hecho el 2026-11-24: los casos 003 a 007 y un túnel de tres fases dan la misma huella de todos
  sus campos antes y después; los 001 y 002 no pasan por `analysis`. 3 tests; 4 mutaciones, 4
  cazadas.)

## El `.h5`

- [x] T4. `results/store.py` y `docs/resultados/formato.md` (D6, D13) — RF-1, RF-2 y RF-4.
  - El formato del plan, con gzip.
  - La escritura a `<raíz>.h5.tmp` y `os.replace`.
  - La lectura perezosa de una fase o de un campo.
  - La comprobación de la forma y de la versión.

  *Hecho cuando:*
  - la ida y vuelta es bit a bit, con los NaN de los inactivos en su sitio;
  - un archivo dañado, sin un campo o de un formato posterior da un error que lo nombra;
  - un fallo a mitad de la escritura deja el `.h5` anterior intacto y ningún temporal.

  (Hecho el 2026-11-24: 10 tests; 9 mutaciones, 9 cazadas.)
- [x] T5. `results/calculate.py`: `calculate` y `open_results` (D7, D13) — RF-1, RF-2 y RF-3.

  *Hecho cuando:*
  - cada estado (`valid`, `stale`, `incomplete`, `cancelled`, `missing`, `damaged`) tiene su test;
  - un `.h5` de otra versión del programa es válido, y lo dice;
  - en el caso 005 están medidos el tamaño (con y sin gzip, con y sin la copia de la malla), el
    tiempo de escritura y el de B u, y el nivel de gzip está decidido y anotado en el changelog.

  (Hecho el 2026-11-24: 6 tests; 7 mutaciones, 7 cazadas. Caso 005, una fase: 6.45 MB con gzip 4, de
  ellos 2.13 MB la copia de la malla; 10.50 MB sin comprimir; escribir, 0.24 s; la B de los 84 198
  puntos, 0.84 s, y B u, 0.02 s. Se queda gzip 4.)

## Los nudos y las consultas

- [x] T6. `results/locate.py`: situar un punto (D11) — RF-10.

  *Hecho cuando:* tienen su test un punto en el interior, uno sobre un lado común, uno sobre un
  contacto (sus dos elementos), uno entre la cuerda y el arco de un T6 curvo, uno en una excavación
  y uno fuera del modelo.
  (Hecho el 2026-11-24: 4 tests; 5 mutaciones, 5 cazadas.)
- [x] T7. **Las figuras de Z&T, sobre la página**: la 14.6 (qué puntos óptimos da para el T6) y las
  14.8 y 14.9 (los parches y los bordes). Lo que se vea, al plan («Formulación») y, si no es lo
  esperado, reportado antes de seguir (regla 6).

  *Hecho cuando:* las tres figuras están descritas en el changelog, con su página.
  (Hecho el 2026-11-24. **Hallazgo**: para el T6 los puntos óptimos no son los medios de los lados,
  que son los de la cuadratura mínima; y la fig. 14.8 precisa D5: un parche determina su nudo central
  y los intermedios de sus radios, no todos los nudos que contiene. Changelog.)
- [x] T8. `results/recovery.py`: SPR material a material (D5) — RF-8 y RF-9.
  - Los parches de los nudos interiores del material, en coordenadas locales escaladas.
  - Los bordes del material desde los parches interiores.
  - Los nudos intermedios del T6.
  - La salida sin parche, dicha.
  - Solo los elementos activos de la fase.

  *Hecho cuando:*
  - el campo gravitatorio con T6, sin excavar, sale exacto en todos los nudos, bordes incluidos;
  - un campo constante con T3 sale exacto;
  - con dos materiales de distinto peso, exacto a cada lado del contacto, y con la mutación que
    los mezcla, no;
  - un material de un elemento de espesor da la salida extrapolada, y la procedencia lo dice;
  - el tiempo en el caso 005 está medido y anotado.

  (Hecho el 2026-11-24: 6 tests; 8 mutaciones, 8 cazadas. Caso 005: 2.2 s, 13 089 parches, ninguno
  rechazado, 16 nudos por el campo del elemento.)
- [x] T9. `results/queries.py`: la línea y la polilínea, todos los nudos y todos los puntos (D9) —
  RF-11 y RF-13.

  *Hecho cuando:*
  - N puntos repartidos y los vértices dan sus distancias acumuladas;
  - un contacto da dos filas;
  - un punto fuera o excavado da su fila sin valor y con la razón;
  - el desplazamiento interpolado en un nudo es el nodal.

  (Hecho el 2026-11-24: 7 tests; 8 mutaciones, 8 cazadas.)
- [x] T10. La consulta sobre un contorno, con distancia y lado (D12) — RF-12.

  *Hecho cuando:*
  - sobre un arco, los puntos están en el arco;
  - en un círculo, hacia dentro y hacia fuera dan el círculo concéntrico;
  - en un vértice cóncavo, el punto va por la bisectriz;
  - un punto que sale del modelo queda sin valor;
  - la distancia por defecto es 0.

  (Hecho el 2026-11-24: 5 tests; 7 mutaciones, 7 cazadas.)
- [x] T11. El punto frente a la fase y el resumen por fase (D14) — RF-15.

  *Hecho cuando:*
  - la evolución de un punto da una fila por fase, con el estado `solved` de cada una;
  - los extremos dicen dónde y de qué tipo son;
  - las reacciones por contorno suman la total, y la total equilibra las cargas y el peso de la
    fase.

  (Hecho el 2026-11-24: 3 tests; 6 mutaciones, 6 cazadas.)
- [x] T12. `results/table.py`: la tabla CSV (D15) — RF-14.

  *Hecho cuando:* la cabecera lo declara todo, la tabla en MPa es la de kPa entre 1000, las columnas
  son las fijas y los números vuelven iguales al leerlos (`repr`).
  (Hecho el 2026-11-24: 3 tests; 6 mutaciones, 6 cazadas.)

## Los casos

- [x] T13. **Las tolerancias antes de medir** (D10): `comparaciones_consulta` en los `esperado.json`
  del 005, el 006 y el 007, con la línea (sus extremos, N, la fase), la magnitud, la referencia y la
  tolerancia. Va en un commit propio, antes de que la consulta exista sobre los casos.

  *Hecho cuando:* el commit está hecho y los casos no se han consultado todavía.
  (Hecho el 2026-11-24, antes de consultar ningún caso.)
- [x] T14. **Caso 005 por la consulta**: σr, σθ y ur a lo largo de un radio, de r = a a 5a, y σθ
  sobre el contorno del hueco, contra Kirsch.

  *Hecho cuando:* cumple la tolerancia de la T13, o el hallazgo está reportado (regla 6). La ficha
  STR-01 tiene su «Seguimiento».
  (Hecho el 2026-11-24, dentro de la tolerancia: σ1 = σθ 0.0022 p0, σ3 = σr 0.0020 p0, u 0.0008 u_r(a); la pared, 0.0035 p0.)
- [x] T15. **Caso 006 por la consulta**: σ1 y σ3 en x = 0, de z = 0.25 a 5 m, contra Michell.

  *Hecho cuando:* lo mismo, y la ficha STR-04 tiene su «Seguimiento».
  (Hecho el 2026-11-24, dentro de la tolerancia: σ1 0.00006 q, σ3 0.00449 q.)
- [x] T16. **Caso 007 por la consulta**: σR, σt y uR a lo largo del radio a 45°, de R = a a 5 m,
  contra la esfera con u(b) = 0, y σt sobre el contorno de la cavidad.

  *Hecho cuando:* lo mismo, y la ficha STR-09 tiene su «Seguimiento».
  (Hecho el 2026-11-24, dentro de la tolerancia: σt 0.0004 y 0.0003 P0, σR 0.0015 P0, u 0.00006 uR(a); el arco, 0.0015 y 0.0008 P0.)

## El cierre

- [ ] T17. El barrido de las reglas 7 y 12:
  - una tabla de cada opción nueva (N, modo, lado, distancia, fase, magnitud, unidades), con el test
    que demuestra que mueve el número;
  - los valores por defecto que cambian el resultado (el método de recuperación, la distancia 0, el
    convenio), dichos con él.

  *Hecho cuando:* la tabla está en el changelog y no le falta ninguna opción.
- [ ] T18. El cierre.
  - Cada fórmula de «Formulación», citada en el código.
  - Los casos 001 a 007, bit a bit.
  - `CHANGELOG_v0.0.11.md`, completo.
  - Avisar a la propietaria de lo que reciben la 006 (el catálogo, los estados, `calculate`, el
    valor absoluto como opción de dibujo) y la 008 (el factor de resistencia con dSN 6.119).

  *Hecho cuando:* todos los criterios de finalización de `spec.md` están marcados.
