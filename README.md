# OGR FEM2D

**Análisis geotécnico 2D por elementos finitos de código abierto** — programa 03 de la suite
[OpenGeoRock](https://opengeorock.org).

> **Estado: en preparación.** Todavía no hay código. La constitución del proyecto está aprobada; el
> siguiente paso es la prueba de concepto del motor
> ([ADR-0001](docs/decisiones/ADR-0001-lenguaje-motor.md)).

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

## Contribuir

Las contribuciones se aceptan con el [CLA](CLA.md) de la suite; antes, lee
[CONTRIBUTING.md](CONTRIBUTING.md).

## Licencia

AGPL-3.0-or-later. © 2026 Samuel Sáez López — Universidad Politécnica de Cartagena.
