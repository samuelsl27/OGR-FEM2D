# OGR FEM2D

**Análisis geotécnico 2D por elementos finitos de código abierto** — programa 03 de la suite
[OpenGeoRock](https://opengeorock.org).

> **Estado: en preparación; fase 0 cerrada (2026-10-27).** La prueba de concepto del motor
> ([spec 001](spec/features/001-prueba-de-concepto/spec.md)) decidió que el motor se escribe en
> Rust ([ADR-0001](docs/decisiones/ADR-0001-lenguaje-motor.md), aceptada), con la implementación de
> referencia en Python como oráculo: triángulo de 6 nudos, Mohr-Coulomb con su tangente consistente
> y escalones con Newton, validados contra Kirsch y Salençon, y ruedas para Windows, macOS ARM y
> Linux. Todavía no hay interfaz.

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

Hace falta:

- **Python 3.11 o posterior** (la CI corre 3.11, 3.12 y 3.13 en Linux, Windows y macOS) y **git**:
  pip trae `ogr-core` de su etiqueta.
- **Rust**, la cadena estable (`rustup`). En Windows, la de MSVC
  (`stable-x86_64-pc-windows-msvc`), que necesita las Build Tools de Visual Studio con la carga
  «Desarrollo para el escritorio con C++».

En Windows, con Git Bash:

```bash
python -m venv .venv
.venv/Scripts/pip install numpy scipy maturin "ogr-core @ git+https://github.com/samuelsl27/OGR-Core@v0.2.3"
VIRTUAL_ENV=.venv .venv/Scripts/python -m maturin develop --release --skip-install
.venv/Scripts/python tests/_runner.py
```

Lo mismo en PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install numpy scipy maturin "ogr-core @ git+https://github.com/samuelsl27/OGR-Core@v0.2.3"
$env:VIRTUAL_ENV = "$PWD\.venv"
.venv\Scripts\python -m maturin develop --release --skip-install
.venv\Scripts\python tests\_runner.py
```

En Linux y macOS el intérprete del entorno es `.venv/bin/python`.

El tercer paso compila el motor en Rust (`rust/`, hace falta `cargo`) y deja el módulo
`ogr_fem2d._engine` dentro del árbol, sin reinstalar nada; hay que repetirlo cada vez que cambia
`rust/`, y un test avisa si el módulo es más viejo que sus fuentes. El programa no se instala en
su entorno: corre desde el árbol.

El congelado de los casos de validación necesita además PyInstaller, que es solo una herramienta
del entorno, en la versión que fija la CI:

```bash
.venv/Scripts/pip install "pyinstaller==6.22.3"
.venv/Scripts/python poc/freeze/build.py
```

Para trabajar en la suite entera (este programa, OGR-Core y OGR Slip2D a la vez, cada uno con su
entorno), este repositorio vive dentro de la carpeta de trabajo `OGR_Suite`, y el `DESARROLLO.md`
de su raíz dice qué instalar en un PC con Windows y cómo se monta todo (desde esta carpeta,
`../../DESARROLLO.md`).

El núcleo (`ogr-core`) va fijado a una etiqueta e instalado desde ella, y el runner de tests se
niega a medir contra cualquier otra versión
([ADR-0002](docs/decisiones/ADR-0002-nucleo-compartido-ogr-core.md)). Para probar este programa
contra un núcleo que se está cambiando no se instala nada: con su árbol por delante,
`PYTHONPATH=<árbol de OGR-Core> .venv/Scripts/python tests/_runner.py --dev-core`, una corrida que
lo dice antes y después de sus totales y que no vale para publicar (`AGENTS.md`, «Un núcleo y
varios programas»).

## Contribuir

Las contribuciones se aceptan con el [CLA](CLA.md) de la suite; antes, lee
[CONTRIBUTING.md](CONTRIBUTING.md).

## Licencia

AGPL-3.0-or-later. © 2026 Samuel Sáez López — Universidad Politécnica de Cartagena.
