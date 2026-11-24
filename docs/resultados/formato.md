# Los resultados: `modelo.h5` y lo que se interpreta de él

Spec 005 (`spec/features/005-resultados/`), ADR-0003. El código, en `ogr_fem2d/results/`. Este
documento sirve para leer el archivo con cualquier herramienta de HDF5 (h5py, MATLAB, HDFView…) sin
este programa, y para saber qué es cada número que entrega la capa de interpretación.

## El archivo

`<raíz>.h5`, junto a `<raíz>.ogrfem2d` y con la misma raíz. Lo escribe `results.calculate`, a
`<raíz>.h5.tmp`, y lo mueve sobre el anterior al terminar (`os.replace`): un corte a mitad de la
escritura deja el `.h5` de antes (RF-2, D13).

**Lo que va dentro es lo que dio el motor, y lo que se sigue de ello sin elegir nada** (D6):

- **el convenio del motor**: tensión positiva en tracción, deformación positiva en alargamiento;
- **las unidades guardadas**: m, kN, kPa.

No van los valores recuperados en los nudos ni el convenio del usuario: dependen de un método o de
una costumbre, y se calculan al leer.

### Atributos de la raíz

| Atributo | Qué es |
|---|---|
| `format` | `"ogr-fem2d-results"` |
| `format_version` | `1`. Un lector se niega con una posterior a la suya |
| `written_by` | `"OGR FEM2D <versión>"` |
| `core` | `"ogr-core <versión>"` |
| `engine_variant` | la variante del motor que resolvió (`reference`, `rust`) |
| `model_fingerprint` | la huella del modelo (`fingerprint.model_fingerprint`, spec 004, D12). Otra que la del `.ogrfem2d` hace los resultados **obsoletos** (RF-3) |
| `analysis` | `plane_strain` o `axisymmetric` |
| `units_stored` | `"m, kN, kPa"` |
| `sign_convention` | `"tension positive, lengthening positive (the engine's)"` |
| `status` | `complete`, `incomplete` (una fase no se resolvió) o `cancelled` (se paró entre fases) |
| `stopped_at` | la fase (desde 0) que no se resolvió; −1 si `complete` |
| `reason` | por qué se paró; vacío si `complete` |
| `n_stages` | cuántas fases hay escritas |

### `/deciding`

Tabla de texto (k × 3): lo que decidió el resultado y no se dibujó (`translate.deciding_values`,
regla 12): qué, el valor (en JSON) y por qué.

### `/mesh`

Copia de la malla del `.ogrfem2d` (la huella garantiza que es la misma), para leer el archivo solo.

| Campo | Forma | Qué es |
|---|---|---|
| `nodes` | N × 2, f8 | x, y de cada nudo (en axisimetría, r y z) |
| `elements` | E × 3 o E × 6, i8 | los nudos de cada elemento, esquinas antihorarias y, en T6, los intermedios de los lados 1-2, 2-3 y 3-1 |
| `element_region` | E, i8 | la región de cada elemento (spec 004, D3) |
| `element_material` | E, i8 | el material de cada elemento, por su lugar en el modelo |
| `points` | P × 2, f8 | x, y de cada punto de integración, elemento a elemento y en el orden de su regla (spec 002, D1) |
| `point_element` | P, i8 | el elemento de cada punto |

### `/stages/NNNN` (desde `0000`)

Atributos: `id` y `name` (los de la fase del modelo), `solved` (0 si la fase no cambiaba nada y no
se resolvió), `steps`, `tolerance` y `cuts` (los ajustes del motor y los cortes que hizo).

| Campo | Forma | Qué es |
|---|---|---|
| `displacement` | N × 2, f8 | u_x, u_y **totales** al final de la fase (los de un nudo retirado, los que tenía) |
| `stress` | P × 4, f8 | σxx, σyy, σzz, τxy (axisimetría: σr, σz, σθ, τrz), **totales**, tracción positiva; NaN en los puntos de los elementos inactivos |
| `strain` | P × 3 o P × 4, f8 | B u, con la B del motor: εx, εy, γxy en deformación plana; εr, εz, εθ, γrz en axisimetría; γ ingenieril; alargamiento positivo; NaN en los inactivos |
| `plastic` | P, u1 | 1 si el punto plastificó en el último escalón de la fase |
| `active` | E, u1 | 1 si el elemento está activo en la fase |
| `removed_nodes` | i8 | nudos sin ningún elemento activo |
| `axis_held` | i8 | nudos del eje sujetos en u_r por el motor (axisimetría; spec 002, D1 bis) |
| `reaction_nodes` | R, i8 | nudos con alguna componente restringida o impuesta |
| `reactions` | R × 2, f8 | R = f_int − f_ext en cada uno (kN por metro de espesor; en axisimetría, del anillo entero) |
| `history` | H × 3, f8 | escalón, iteración y residuo relativo de cada iteración |

Los campos grandes van con gzip y el filtro *shuffle*, los dos de cualquier HDF5.

## Calcular y abrir (`results.calculate`)

- `calculate(modelo, ruta_del_ogrfem2d)` traduce el modelo (spec 004), resuelve fase a fase
  (`analysis.stages`) y escribe el `.h5`. Su estado:
  - `complete`;
  - `incomplete`: una fase no se resolvió (no convergió, un punto no se actualizó, las restricciones
    dejan libre el modelo, una carga cae fuera de su elemento). Las fases anteriores quedan escritas;
  - `cancelled`: `should_stop()`, consultado entre fases, lo pidió.

  Un modelo que no se traduce, o una entrada que el motor rechaza, no escribe nada.
- `open_results(ruta)` da el estado:
  - `valid`;
  - `stale`: otra huella; el modelo cambió después de calcular;
  - `incomplete` o `cancelled`;
  - `missing`: no hay `.h5`;
  - `damaged`: no se lee, y dice por qué.

  Solo los válidos se entregan tal cual (`.results`); los demás que se pueden leer, con
  `.read_anyway()`. Otra versión del programa o del núcleo no los hace obsoletos, pero se dice
  (`other_version`).

## Lo que se interpreta

### Las magnitudes (`results.quantities`)

Todas en el **convenio del usuario**: tensiones en compresión positiva, deformaciones en acortamiento
positivo y desplazamientos según +x y +y. El cambio de signo está en `model/conventions.py` y en
ningún otro sitio (regla 10). Cada entrada del catálogo tiene id, clave traducible
(`results.quantity.<id>`), unidad, convenio, nombre en deformación plana y en axisimetría,
definición y fuente:

| id | Qué es | Fuente |
|---|---|---|
| `sigma_xx`, `sigma_yy`, `sigma_z`, `tau_xy` | cartesianas; en axisimetría, radial, axial, circunferencial y rz | — |
| `sigma_1`, `sigma_3` | principales **en el plano** (en axisimetría, en el plano meridiano) | JCZ (2007) ecs. (2.37)–(2.38) |
| `theta_1` | ángulo de σ1 desde +x, antihorario, 0° ≤ θ < 180° | JCZ ecs. (2.33), (2.41)–(2.44) |
| `sigma_I`, `sigma_II`, `sigma_III` | las tres principales ordenadas (σ1, σ3 y σz) | JCZ §2.5 |
| `p` | tensión media, (σxx + σyy + σzz)/3 | JCZ ec. (2.153) |
| `q` | von Mises, √(3 J2) | de Souza Neto et al. (2008) ec. (6.111); J2, JCZ ec. (2.163) |
| `sigma_diff` | diferencial, σI − σIII | JCZ cap. 6, pág. 151 |
| `u_x`, `u_y`, `u` | desplazamientos y su módulo | — |
| `eps_xx`, `eps_yy`, `eps_z`, `gamma_xy` | deformaciones; γ ingenieril; εz = 0 en deformación plana, εθ = u/r en axisimetría | JCZ ecs. (2.181)–(2.185); Z&T ecs. (5.5)–(5.6) |
| `eps_v` | volumétrica, εxx + εyy + εz | JCZ ec. (2.231) |
| `gamma_max` | corte máxima ingenieril en el plano, ε1 − ε3 | JCZ ec. (2.195) y pág. 46 |

Tres erratas del libro de JCZ, vistas sobre la página: (2.149), (2.162) y (2.195) (changelog
v0.0.11, T1).

### Los nudos (`results.recovery`)

Recuperación por parches (SPR) de Zienkiewicz y Taylor (2000), §14.4, **material a material** y
solo con los elementos activos:

- el polinomio de grado p (1 en T3, 2 en T6) se ajusta a los puntos de integración del parche de
  cada nudo de esquina interior (ecs. 14.28–14.31);
- cada parche determina su nudo, los intermedios de sus radios (fig. 14.8) y los nudos del borde del
  material que tiene (fig. 14.9);
- la media, donde lo determinan varios;
- un nudo que no alcanza ningún parche toma el campo propio de sus elementos (grado p − 1), y lo dice
  (`element`).

Se recupera el tensor, y la magnitud se calcula del tensor. El resultado va por (elemento, nudo
local): un valor por material en un contacto.

### Las consultas (`results.queries`) y la tabla (`results.table`)

- `line`: n puntos a la misma distancia en toda una polilínea, o sus vértices, con la distancia
  acumulada.
- `on_boundary`: sobre un contorno del modelo, con sus arcos, o a una distancia de él hacia un lado
  (dentro o fuera; izquierda o derecha). En los vértices, por la bisectriz. La distancia por defecto es
  0.
- `all_nodes`, `all_points`, `history` (un punto en cada fase) y `summary` (extremos, desplazamiento
  máximo y reacciones totales y por contorno).
- Dentro de un elemento, los desplazamientos salen de las funciones de forma, y las tensiones y las
  deformaciones, de los valores recuperados interpolados (Z&T ec. 14.27). Un punto sobre un contacto
  da una fila por material; uno fuera o en una excavación, una fila sin valor con la razón.
- Cada fila dice su procedencia: `point`, `fe`, `spr`, `element` o `spr+element`.
- Cada consulta lleva su método y sus ajustes (`settings`, regla 12).

La tabla CSV declara en su cabecera (`#`) el programa, la magnitud, la unidad, el convenio, la fase,
los ajustes, el método y la huella. Sus columnas son fijas: `query_id, point, x, y, distance, value,
element, material, source`. Va en las unidades del sistema que se muestra.
