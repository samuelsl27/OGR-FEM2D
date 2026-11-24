# OGR FEM2D v0.0.13

**Fase 1, sexta parte: operaciones y transporte** (spec 006, parte B). El catálogo de operaciones de
este programa, sin Qt, sobre el armazón del núcleo (`ogr_core.api`, ADR-0005); el cálculo como trabajo
en subproceso; la línea de órdenes y el servidor MCP. Este archivo cuenta lo que fue entrando, tarea a
tarea.

## T10 — la fijación sube a OGR-Core v0.2.9 (2026-11-24)

En su propio commit (`AGENTS.md`, «Un núcleo y varios programas»): `pyproject.toml` a `@v0.2.9`, el
`.venv` reinstalado desde la etiqueta con `--no-deps --force-reinstall`, y los tests de la fijación con
sus listas de versiones movidas. La versión del programa pasa a 0.0.13.

La v0.2.9 trae `ogr_core.api`, lo que se pidió en la T1 de la spec 006: `Registry`, los errores con
código (`OgrApiError` y los suyos, `did_you_mean`), `Workspace` con `WorkspaceNames`, los trabajos en
subproceso (`JobContext`, `JobCancelled`, `JobHooks`, `cancel_grace_s`), el puente (`BridgeConfig`,
`BridgeSession`) y sus mensajes codificados (`API_MESSAGES`, que la interfaz traduce con
`ogr_core.messages.render`). Su §2 no pide nada obligatorio a este programa; la sesión del núcleo ya
había corrido esta suite contra él con `--dev-core` (660 de 660).
