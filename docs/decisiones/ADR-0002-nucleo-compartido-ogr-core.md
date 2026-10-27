# ADR-0002 — Núcleo compartido con OGR Slip2D: paquete `ogr-core`

- **Estado:** ACEPTADA (2026-10-27, propietario) y **MODIFICADA el mismo día** (ver «Modificación»,
  al final): de momento OGR-Core es el núcleo de OGR FEM2D, y OGR Slip2D conserva el suyo sin
  cambios. Decisión D1 de
  `../Referencias/Doc_Guia/Analisis_interfaz_funcionamiento/D_sintesis/S06_pendientes_y_dudas.md`.
- **Contexto completo:** `S02_reutilizacion_OGR-Slip2D.md` (fuera del repositorio).

## Contexto

El `AGENTS.md` de OGR Slip2D dice que `ogr_core` «se extraerá a su propio paquete cuando exista un
segundo programa que lo use — no antes». OGR FEM2D es ese segundo programa. Comprobado en Slip2D
v0.1.370 (2026-10-27):

- `ogr_core` (89 archivos, ≈30 000 líneas) **no importa ningún otro paquete** de Slip2D; solo lo
  nombran algunos comentarios.
- Slip2D ya tiene un paquete **`ogr_fem2d`** (malla Delaunay y solvers de filtración estacionaria y
  transitoria, líneas de corriente; 10 archivos, ≈4 100 líneas) que solo importa `ogr_core` y que
  importan 52 archivos de Slip2D. Si este programa se llamara igual, los dos paquetes chocarían al
  instalarse en el mismo entorno.

## Decisión

1. Nuevo repositorio **OGR-Core**, distribución **`ogr-core`**, con el paquete de importación
   **`ogr_core`** sin cambiar de nombre (las importaciones de Slip2D siguen valiendo).
2. **La malla y la filtración de Slip2D (`ogr_fem2d`) pasan al núcleo**, porque las usan los dos
   programas. Destino: **`ogr_core/fem/`**, donde Slip2D ya había movido en v0.1.342 la malla y los
   datos de filtración; faltan el generador, el solver, las líneas de corriente y los códigos
   `seepage.*`. El núcleo pasa a contener ese solver compartido. La extracción completa está
   especificada en Slip2D, `spec/features/009-extraer-ogr-core/` (decisiones P1–P7 del
   2026-10-27: `ogr-core` con serie de versiones propia desde 0.1.0, dependencia git con etiqueta,
   runner de tests único en `ogr-core`, carpeta `C:\Samuel\OpenGeoRock_Core\OGR-Core`).
3. Slip2D y FEM2D dependen de una **versión fijada** de `ogr-core` en cada publicación; durante el
   desarrollo se instala en modo editable.
4. Liberado el nombre, el paquete de este programa es **`ogr_fem2d`** (distribución `ogr-fem2d`).

## Alternativas descartadas

- **Extraer solo `ogr_core`** y dar otro nombre a este programa: la malla quedaría duplicada o FEM2D
  dependería de Slip2D para usarla.
- **Depender de `ogr-slip2d`**: arrastra el motor de equilibrio límite, acopla las versiones y choca
  el nombre `ogr_fem2d`.
- **Copiar y divergir**: las reglas y la geometría acabarían diciendo cosas distintas en cada
  programa (lo que el `AGENTS.md` de Slip2D prohíbe).

## Consecuencias

- **Slip2D cambia** (otro repositorio, con su propia especificación y versión): empaquetado, las
  importaciones de `ogr_fem2d` pasan al núcleo, y los tests de `ogr_core` y de la filtración se
  mueven a OGR-Core. Hace falta el plan y el OK del propietario antes de tocarlo.
- La **fase 0** (prueba de concepto del motor) no necesita el núcleo y puede ir en paralelo; la
  **fase 1** sí, así que la extracción es requisito previo de la fase 1.
- **Riesgo de coexistencia**: una instalación con pip de un Slip2D anterior a la extracción (que aún
  trae `ogr_fem2d`) junto a este programa sobrescribiría archivos. Los instaladores congelados no
  comparten entorno y no lo sufren. Mitigación: documentar la versión mínima de Slip2D compatible.
- **La interfaz (`ogr_gui`) queda fuera** de esta decisión: cómo compartir sus partes genéricas
  (lienzo, herramientas, diálogos comunes) se decide en la especificación de la fase 1.

## Modificación (2026-10-27, propietario)

**OGR Slip2D no se toca por ahora.** OGR-Core se hace para OGR FEM2D; Slip2D sigue con su propio
`ogr_core` y su `ogr_fem2d`, independiente, y la integración de los dos núcleos se decidirá más
adelante.

Estado en el momento de la modificación:

- **OGR-Core v0.1.0 está publicado** (`samuelsl27/OGR-Core`, `main` y etiqueta `v0.1.0`, commit
  `ae1c83e`, CI en verde en Python 3.11–3.13). Es el `ogr_core` de Slip2D en su commit `2d68c29`:
  el de v0.1.370 con la malla y la filtración ya dentro de `ogr_core/fem/`. Incluye el runner de
  tests compartido y 34 tests movidos de Slip2D. **Es el núcleo del que dependerá este programa**,
  con la etiqueta fijada.
- En Slip2D solo quedó la rama local `dev/extraer-ogr-core` (F1 y la spec 009), sin integrar en
  `main` ni subir. Su `main` no ha cambiado.

Consecuencias:

- **Hay dos copias del núcleo, y pueden divergir.** Es justo la alternativa «copiar y divergir» que
  se descartó arriba; se acepta como estado temporal por decisión del propietario. Para que la
  integración futura sea posible: cada cambio de OGR-Core se anota en su changelog respecto a la
  base (`2d68c29` de Slip2D), y los changelogs de Slip2D ya registran sus cambios en `ogr_core`.
- **Slip2D y este programa no pueden compartir un entorno de Python.** Los dos instalan un paquete
  `ogr_core` (Slip2D el suyo, este el de OGR-Core) y los dos usarán el nombre `ogr_fem2d`. Cada
  repositorio se desarrolla en su propio entorno virtual (el de este, `OGR-FEM2D/.venv`), y los
  instaladores congelados no comparten entorno. En particular, la instalación editable de Slip2D
  del Python del sistema resuelve `ogr_core` y `ogr_fem2d` a su árbol: no se usa para este
  programa.
- El requisito de la fase 1 (fase 0b de la hoja de ruta) queda cumplido con OGR-Core v0.1.0; ya no
  depende de cambiar Slip2D.
