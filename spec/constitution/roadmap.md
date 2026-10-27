# Hoja de ruta

> **Aprobada por el propietario (2026-10-27).** El orden sale del catálogo teórico
> (`../Referencias/.../C_teoria/T00_indice_teoria.md`) y de qué funciones desbloquean más casos de
> verificación (`../Referencias/Ejemplos/Casos_por_problema/00_INDICE.md`).

| Fase | Contenido | Casos de validación que la cierran |
|---|---|---|
| **0. Prueba de concepto** | Triángulo de 6 nudos, elasticidad y Mohr-Coulomb en Python de referencia, NumPy y Rust; ruedas multiplataforma. Criterios de aceptación de ADR-0001 (entre ellos ×10 sobre NumPy vectorizado); si no se cumplen, se reabre el ADR | STR-01, STR-02 |
| **0b. Núcleo `ogr-core`** (ADR-0002) | **Hecha (2026-10-27)**: OGR-Core v0.1.0 publicado, con `ogr_core` y la malla y la filtración de Slip2D. Slip2D conserva su propio núcleo por ahora; integrar los dos es una decisión futura | 34 tests de Slip2D movidos sin cambios y los propios del núcleo: 499 de 499 en la CI |
| **1. Primer análisis elástico de principio a fin** | Núcleo FEM (deformación plana y axisimetría, T3/T6/Q4/Q8), tensión de campo, contorno fijo, interpretación de contornos y consultas, resultados en `.h5` con huella (ADR-0003). **Su especificación fija, antes de escribir el motor, el convenio de signos interno y si las cargas y los desplazamientos impuestos de cada fase van en totales o en incrementos** (S06, dudas 12 y 14) | STR-01 (Kirsch), STR-04 (carga en faja), STR-09 (cavidad esférica) |
| **2. No linealidad y plasticidad básica** | **Empieza fijando la tolerancia de convergencia por defecto y el criterio de colapso con STR-05 (Prandtl)**: en la reproducción P13, con la tolerancia por defecto del programa de referencia, la carga de 0.52 MPa «convergía» por encima del colapso (0.514 MPa). Después: rigidez inicial, criterios de convergencia, escalones automáticos; MC, DP, HB/GHB; factor de resistencia; **SSR** | STR-05, STR-02, STR-03, SLP-01, SLP-12 |
| **3. Estructuras y discontinuidades** | Revestimientos (viga), bulones, juntas, **fases de construcción**, elementos infinitos | STR-07, STR-21, STR-28, STR-06 |
| **4. Agua** | Reutilizar y ampliar el FEM de filtración (ya en `ogr-core`); tensiones efectivas; no drenado; consolidación | GW-03, GW-04, GW-15, CON-01 |
| **5. Modelos constitutivos avanzados** | Cam-Clay/MCC, Hardening Soil, ablandamiento, roca diaclasada… (cada uno con su oráculo en Python, ADR-0001) | STR-13, CNS-01 |
| **6. Probabilístico** | Estimas puntuales, Monte Carlo, LHS | — |
| **7. Campos especiales** | Dinámico, térmico, XFEM | DYN, THM, XFM |
| **Después del FEM** | Diferencias finitas explícitas, DEM de partículas y de bloques | — |
