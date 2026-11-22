# OGR FEM2D

Análisis geotécnico 2D por elementos finitos: tensión-deformación, fases de construcción,
reducción de resistencia al corte, agua, sostenimiento y juntas.

**Dos niveles de nombre**: *OpenGeoRock* (u *OGR Suite*) es el paraguas de los programas de la
suite; **OGR FEM2D** es este programa (el 03 de la hoja de ruta). Hermano de **OGR Slip2D**
(equilibrio límite), con el que comparte filosofía, interfaz, formatos y reglas.

Autor y titular del copyright: Samuel Sáez López (UPCT). Licencia AGPL-3.0-or-later.

> Este archivo es el **contrato de trabajo** con cualquier agente de IA. Se consulta antes de cada
> acción. **Estado: APROBADO por el propietario (2026-10-27)**, derivado del `AGENTS.md` de OGR
> Slip2D. Las decisiones estructurales, con su motivo, están en `spec/constitution/tech-stack.md` y
> en `docs/decisiones/` (ADR).

---

## Antes de nada

- La especificación de partida y todo el análisis previo están **fuera del repositorio**, en
  `../Referencias/Doc_Guia/Analisis_interfaz_funcionamiento/` (empieza por su `00_LEEME.md`).
- Los casos de verificación, uno por carpeta con su ficha, en
  `../Referencias/Ejemplos/Casos_por_problema/00_INDICE.md`.
- Trabajo guiado por especificaciones (SDD): constitución en `spec/constitution/`, una carpeta por
  función en `spec/features/NNN-nombre/` con `spec.md`, `plan.md` y `tasks.md`.
- Repositorio público `samuelsl27/OGR-FEM2D`. Las contribuciones se aceptan con el CLA de la suite
  (`CLA.md`, `CONTRIBUTING.md`).

## Stack

- **Interfaz, modelo, orquestación**: Python 3.11+, PySide6, NumPy, SciPy, Shapely (como Slip2D).
- **Motor numérico**: Rust + PyO3 + maturin, **aceptado con condición** de que la prueba de concepto
  cumpla sus criterios (`docs/decisiones/ADR-0001-lenguaje-motor.md`). **Cada elemento y cada ley
  constitutiva tiene su implementación de referencia en Python**, que es el oráculo de los tests.
- **Núcleo**: `ogr_core`, del paquete `ogr-core` (repositorio OGR-Core, etiqueta `v0.2.2` desde la
  v0.0.4), con la malla y la filtración (`ADR-0002`). El paquete de este programa es `ogr_fem2d`.
  **El núcleo se cambia solo en OGR-Core** (abajo, «Un núcleo y varios programas»). El `.venv`
  tiene el núcleo **instalado desde la etiqueta fijada**, como la CI, y no en editable desde el
  árbol de OGR-Core (`../../Core/OGR-Core` desde este repositorio): ese árbol sigue al `main` del
  núcleo. OGR Slip2D adoptó el núcleo en su v0.1.473 (ya no lleva `ogr_core/` ni ningún paquete
  `ogr_fem2d`), fija su propia etiqueta y tiene su propio `.venv`; los dos programas pueden fijar
  versiones distintas.
- **Formato de proyecto**: `.ogr` (JSON), compatible con OGR Slip2D en la parte geométrica. Los
  resultados van aparte en `modelo.h5` con la huella del modelo (`ADR-0003`).
- **Tests**: el runner de la suite (`ogr_core.testing.runner`), a través de `tests/_runner.py`.

## Comandos

```bash
.venv/Scripts/python tests/_runner.py          # toda la suite (lo que corre la CI)
.venv/Scripts/python tests/_runner.py t6       # archivos que contengan eso
.venv/Scripts/python tests/_runner.py -k patch # tests con ese nombre
```

**Siempre con el `.venv` del proyecto.** Otro Python puede no tener el núcleo (el del sistema no lo
tiene, 2026-11-20) o tener otra versión, y el runner se niega («WRONG SHARED TREE»). La línea
`shared:` de la cabecera dice qué núcleo se mide, de dónde sale y qué versión es: en una corrida
normal, `shared: ogr_core 0.2.2 …\.venv\Lib\site-packages\ogr_core (installed, no git tree)`. Para
instalar algo más en el `.venv`, `--no-deps`: con sus dependencias, pip volvería a resolver el
núcleo por su cuenta. Una ejecución filtrada no es evidencia para cerrar una tarea: antes, la suite
entera.

## Un núcleo y varios programas

OGR Core es la biblioteca común de la suite y la usan varios programas a la vez. Desde el lado de
este programa (las reglas del núcleo, en el `AGENTS.md` de OGR-Core y en su `docs/consumidores.md`):

- **Solo vive `main`, y el trabajo normal va en commits directos en `main`** (decisión de la
  propietaria del 2026-11-22, con la misma lógica que OGR Slip2D), con **la suite entera en verde
  antes de cada commit**. El commit de cada tarea terminada se hace sin esperar; el push, solo
  cuando la propietaria lo pide.
- **Una rama corta `dev/…` solo cuando la propietaria la elige**; lo típico, cambios en `rust/` o
  en la CI, donde la suite local de Windows no predice Linux ni macOS. Cuando está en verde se
  fusiona en `main`, se sube y se borra, en GitHub y en local. Una rama sin fusionar no se borra
  sin el OK de la propietaria, y si lleva algo que `main` no tiene, antes se archiva con una
  etiqueta `archivo/<nombre>`.
- **El `main` de este repositorio tiene que estar verde**: la CI de OGR-Core lo coge y corre esta
  suite en cada commit del núcleo. Después de cada push se mira la CI (Linux, Windows y macOS), y
  un rojo se arregla antes de seguir.
- **En OGR-Core no cambia nada**: allí cada cambio sigue en una rama corta con su PR.
- **El código de `ogr_core` solo se cambia en OGR-Core, y aquí no se copia.** Lo que este programa
  necesite del núcleo se pide a la sesión de OGR-Core, con lo que se encontró y la evidencia; aquí
  no se rodea.
- **La fijación se sube a propósito, en un commit suyo**, a una etiqueta (nunca a una rama): el
  `pyproject.toml`, el entorno y lo que el changelog de esa versión del núcleo pida a los programas.
  El entorno no se entera solo:

  ```bash
  .venv/Scripts/python -m pip install --no-deps --force-reinstall "ogr-core @ git+https://github.com/samuelsl27/OGR-Core@vX.Y.Z"
  ```

  Después, la suite entera: la cabecera nombra la versión nueva.
- **Cuando se sube la fijación, la fila de este programa en `docs/consumidores.md` de OGR-Core se
  corrige allí**, no aquí: se le dice al propietario, y lo hace la sesión de OGR-Core.
- **Un núcleo sin etiquetar se prueba sin instalar nada**, con el árbol o el worktree de OGR-Core
  por delante del instalado:

  ```bash
  PYTHONPATH=<árbol o worktree de OGR-Core> .venv/Scripts/python tests/_runner.py --dev-core
  ```

  Acepta solo una `X.Y.Z.devN` de una versión posterior a la fijada, dice `DEV CORE` antes y
  después de los totales y **no es evidencia para publicar** este programa. Mientras dura deja
  `OGR_DEV_CORE=1` en el entorno: un test pregunta con `ogr_core.testing.runner.dev_core_run()` en
  qué corrida está, y la suite tiene que salir entera en verde también así (la CI de OGR-Core la
  corre contra el núcleo de cada PR).

## Las siete reglas (heredadas de OGR Slip2D, sin cambios)

1. **El trabajo numérico se valida contra algo EXTERNO**: solución analítica, caso publicado o
   identidad. Nunca contra una captura de lo que el código imprime hoy. Un resultado que coincide sin
   una razón física, matemática y geotécnica **no se da por válido**.
2. **Todo texto visible pasa por `tr()`** y tiene su traducción española.
3. **Toda acción debe ser alcanzable desde un menú.**
4. **Cada archivo lleva su cabecera de licencia** (SPDX AGPL-3.0-or-later y copyright).
5. **Los tests no filtran estado.**
6. **Las anomalías se reportan ANTES de corregirlas.**
7. **Ningún ajuste puede no hacer nada**: toda opción lleva el test que demuestra que mueve el número.

## Reglas propias de un motor de elementos finitos

8. **Cada ley constitutiva se prueba en un punto de Gauss** contra su fuente (trayectoria de
   tensiones conocida) antes de usarse en un modelo.
9. **Convergencia de malla**: un caso de validación fija la malla y el orden de elemento con los que
   se establece su tolerancia; cambiar la malla de un caso es cambiar el caso.
10. **Un único convenio de signos interno**, documentado (las fuentes usan convenios distintos):
    **tracción positiva** dentro del motor; la interfaz convierte a compresión positiva donde sea la
    costumbre geotécnica, en un único sitio. Las cargas y los desplazamientos impuestos de cada fase
    entran al motor **en totales**, y el motor calcula el incremento (spec 001, D1 y D2).
11. **El motor no conoce la interfaz**: recibe nudos, elementos, propiedades, tensiones iniciales,
    restricciones y secuencia de fases; no sabe de contornos, menús ni unidades de usuario.
12. **Un valor por defecto que cambia el resultado se muestra junto al resultado.** En las
    reproducciones del programa de referencia, la cara de filtración (P18), la reducción de las
    juntas en el SSR (P21), la rigidez del geosintético (P22) y la tolerancia de convergencia (P13)
    cambiaban el número sin que el resultado lo dijera.

## Flujo de trabajo

- Antes de una tarea no trivial, plan y OK del propietario. Una tarea a la vez.
- Si no estás seguro al 80 %, pregunta. **No inventes**, sobre todo fórmulas.
- Cada versión con su changelog en `docs/changelog/` registrando **qué se encontró**.

## Documentación de referencia

La documentación y los programas comerciales de referencia se usan para entender **qué** hace una
función y **cómo** se comporta su interfaz. **El código no puede contener ninguna referencia a esos
productos ni a sus marcas**, ni copiar su texto. Las fórmulas se citan por su fuente científica
original (autor y año).

Lo que el programa de referencia calcula cuando lo reproducimos nosotros sirve para entender su
comportamiento, **nunca como valor esperado de un caso de validación**. Un valor publicado en su
manual se puede usar citando la fuente; si es el resultado de ese programa, el caso es una
`comparacion`, no una validación (`validacion/README.md`).

## No hagas

- No instales dependencias sin preguntar, y comprueba su licencia (compatible con AGPL-3.0).
- No toques los casos de validación para hacer pasar un cambio.
- No cambies `LICENSE` ni las cabeceras SPDX sin pedirlo.
- No añadas telemetría ni llamadas de red no pedidas.

---

© 2026 Samuel Sáez López — UPCT — AGPL-3.0-or-later
