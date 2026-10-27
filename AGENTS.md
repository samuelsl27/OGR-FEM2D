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
- **Núcleo**: `ogr_core`, del paquete `ogr-core` (repositorio OGR-Core, etiqueta `v0.1.0`), con la
  malla y la filtración (`ADR-0002`). El paquete de este programa es `ogr_fem2d`. **De momento OGR
  Slip2D conserva su propio núcleo**: hay dos copias, cada cambio de OGR-Core se anota en su
  changelog, y este programa **no comparte entorno de Python con Slip2D** (se desarrolla en
  `OGR-FEM2D/.venv`).
- **Formato de proyecto**: `.ogr` (JSON), compatible con OGR Slip2D en la parte geométrica. Los
  resultados van aparte en `modelo.h5` con la huella del modelo (`ADR-0003`).
- **Tests**: el runner propio de la suite (`tests/_runner.py`, heredado de Slip2D).

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
