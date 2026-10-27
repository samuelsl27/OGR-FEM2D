# Stack y convenciones

> **Aprobado por el propietario (2026-10-27).** Las convenciones de trabajo están en
> [`AGENTS.md`](../../AGENTS.md); aquí solo las decisiones estructurales y su motivo. Cada decisión
> nueva va con su ADR en [`docs/decisiones/`](../../docs/decisiones/).

## Decisiones y su motivo

| Decisión | Origen | Motivo |
|---|---|---|
| **Python 3.11+ para interfaz, modelo y orquestación** | heredada de Slip2D | Legibilidad, ecosistema científico y reutilización directa del código de Slip2D |
| **PySide6** | heredada | Licencia LGPL compatible |
| **Formato `.ogr` (JSON)** compartido con Slip2D | heredada | Un modelo debe poder pasar de un programa de la suite a otro |
| **Motor numérico en Rust (PyO3 + maturin)** | ADR-0001, **aceptada** (2026-10-27, tras la prueba de concepto de la spec 001) | Rendimiento compilado para *return mapping*, SSR, probabilístico y, a futuro, métodos explícitos y DEM; seguridad de memoria y de concurrencia comprobada por el compilador; una rueda por plataforma sin dependencias nativas. La prueba de concepto cumplió los criterios 1 a 4 y dio ≈ ×9.6 sobre NumPy vectorizado en el 5, que el propietario dio por suficiente |
| **Implementación de referencia en Python de todos los elementos y leyes constitutivas** | ADR-0001 | Oráculo de los tests del núcleo compilado; código legible para auditar |
| **Solver lineal inicial: SuperLU (SciPy)**; faer tras medir | ADR-0001 | Sin problemas de licencia ni de distribución; el solver disperso en Rust es el riesgo principal |
| **Sin PARDISO/MKL** | ADR-0001 | Licencia propietaria incompatible con distribuir AGPL; no existe en macOS ARM |
| **Malla sin `triangle`** | heredada | Licencia incompatible con AGPL (se usa Delaunay de SciPy; en Rust, `spade`) |
| **Núcleo `ogr_core` del paquete `ogr-core`** (repositorio OGR-Core, etiqueta `v0.1.0` fijada), con la malla y la filtración | ADR-0002, modificada | Sale del núcleo de Slip2D. **De momento Slip2D conserva el suyo** y la integración se decide más adelante: hasta entonces hay dos copias, y Slip2D y este programa no comparten entorno de Python |
| **Resultados en `modelo.h5` aparte, con la huella del modelo** | ADR-0003 | Un cálculo con fases y SSR puede durar horas; la huella impide presentar resultados obsoletos como válidos |
| **AGPL-3.0-or-later y el CLA de la suite** | decisión D4 | Igual que Slip2D: el CLA está redactado para toda la suite y conserva la opción de un servicio alojado con otras condiciones |
| **Repositorio público `samuelsl27/OGR-FEM2D`** | decisión D5 | Igual que Slip2D; la constitución y las decisiones se publican desde el principio |
| **Tracción positiva dentro del motor; cargas y desplazamientos de cada fase en totales** | spec 001, D1 y D2 | El convenio de los textos de elementos finitos y plasticidad que se siguen; un solo convenio para cargas y desplazamientos, sin errores acumulados |
| **Rust: `pyo3`, `numpy` (crate) y `ndarray`; PyInstaller para el congelado** | spec 001, D6 | MIT/Apache-2.0, BSD-2-Clause y GPL-2.0+ con excepción de distribución: compatibles con AGPL-3.0 |

## Separaciones que no deben romperse

- **Motor ↔ interfaz**: el motor recibe una descripción discreta (nudos, elementos, propiedades,
  tensiones iniciales, restricciones, fases) y devuelve campos; no conoce contornos, unidades de
  usuario, idiomas ni normas.
- **Cálculo ↔ presentación**: los contornos y gráficos no dependen de Qt para poder probarlos y
  usarlos en informes.
- **Operaciones ↔ transporte**: como en Slip2D, `ogr_api` no sabe si le llama la interfaz, un script
  o un agente.
- **Modelo ↔ resultados**: el `.ogr` es la única fuente de verdad; el `.h5` solo vale si su huella
  coincide con la del modelo.
