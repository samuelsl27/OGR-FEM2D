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
