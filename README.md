# OGR FEM2D

**Análisis geotécnico 2D por elementos finitos de código abierto** — programa 03 de la suite
[OpenGeoRock](https://opengeorock.org).

> **Estado: en preparación, fase 0.** La constitución está aprobada y está en curso la prueba de
> concepto del motor ([spec 001](spec/features/001-prueba-de-concepto/spec.md),
> [ADR-0001](docs/decisiones/ADR-0001-lenguaje-motor.md)): ya existe la implementación de
> referencia en Python del triángulo de 6 nudos y del Mohr-Coulomb. Todavía no hay interfaz.

## Qué será

Tensión-deformación en deformación plana y axisimetría, fases de construcción, reducción de
resistencia al corte (SSR), flujo de agua, sostenimiento (bulones, revestimientos) y juntas, con la
misma interfaz y el mismo formato de proyecto que [OGR Slip2D](https://github.com/samuelsl27/OGR-Slip2D),
y validado contra soluciones analíticas y casos publicados.

## Estructura

| Ruta | Contenido |
|---|---|
| `spec/constitution/` | Misión, stack y hoja de ruta |
| `spec/features/` | Una carpeta por función: `spec.md`, `plan.md`, `tasks.md` |
| `validacion/` | Casos de validación: modelo, valor esperado y su fuente |
| `docs/decisiones/` | Registro de decisiones de arquitectura (ADR) |
| `docs/changelog/` | Qué cambió y qué se encontró en cada versión |

## Desarrollo

```bash
python -m venv .venv
.venv/Scripts/pip install numpy scipy maturin "ogr-core @ git+https://github.com/samuelsl27/OGR-Core@v0.1.0"
.venv/Scripts/python tests/_runner.py
```

El núcleo (`ogr-core`) va fijado a una etiqueta, y el runner de tests se niega a medir contra
cualquier otra versión. OGR Slip2D conserva por ahora su propia copia del núcleo: los dos programas
no comparten entorno de Python ([ADR-0002](docs/decisiones/ADR-0002-nucleo-compartido-ogr-core.md)).

## Contribuir

Las contribuciones se aceptan con el [CLA](CLA.md) de la suite; antes, lee
[CONTRIBUTING.md](CONTRIBUTING.md).

## Licencia

AGPL-3.0-or-later. © 2026 Samuel Sáez López — Universidad Politécnica de Cartagena.
