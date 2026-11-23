# OGR FEM2D v0.0.9

**Fase 1, tercera parte: el modelo y su archivo** (spec 004). Lo que define el ingeniero, en un
`.ogrfem2d` propio con su malla (ADR-0004), y su traducción determinista a la entrada del mallador y
del motor. Este archivo cuenta lo que fue entrando, tarea a tarea.

## La spec, el plan y las tareas (2026-11-23)

Revisados contra el estado del código, del núcleo (`v0.2.6`) y de OGR Slip2D, y aprobados con D1–D16
(`spec/features/004-modelo-y-proyecto/`). Lo que se encontró al revisarla:

- **El `Project` del núcleo no sirve como modelo FEM ni como archivo común.** Es el modelo de
  equilibrio límite: no tiene E ni ν, ni contornos de excavación o de fase, ni arcos. Lee una lista
  fija de secciones y pierde al guardar las que no conoce. Un tipo de contorno desconocido hace que el
  archivo no se pueda abrir. Nunca lee `format_version`.
- **Los programas de referencia tienen dos formatos** (`M02` §5.2 y §6.2, `F01` del análisis de
  interfaz). El de elementos finitos guarda la malla y abre el de equilibrio límite convirtiéndolo.
  Decidido así (D1 y ADR-0004): FEM2D tiene su `.ogrfem2d` y abre el `.ogr` de Slip2D. Lo que se
  comparte es el código del núcleo.
- **La huella de Slip2D vive en su `ogr_api`, no en el núcleo**: aquí se escribe la de este archivo,
  sin copiar código del núcleo (D12).

## T0 — aprobación y ADR-0004 (2026-11-23)

ADR-0004 escrito. `AGENTS.md`, ADR-0003, `tech-stack.md`, `plan_de_desarrollo.md` y
`validacion/README.md` nombran el `.ogrfem2d`.

## T1 — el modelo y sus reglas (2026-11-23)

Paquete nuevo `ogr_fem2d/model/`, fuera del motor y del mallador (regla 11). `model.py`: el modelo
como valor (dataclasses congeladas), con contornos, materiales, fases, asignaciones, tensión de
campo, condiciones, cargas, ajustes de malla y malla guardada, y `problems()`/`validate()`, todos los
problemas a la vez, cada uno con su regla y su sitio. `docs/modelo/formato.md`: el modelo, el archivo,
la traducción y las reglas.

- **Hallazgo al escribir D10: la tabla región × fase necesita el material del estado inicial.** La
  tensión de campo es la del estado antes de la primera fase, y una región excavada en la primera
  fase necesita un material para ese estado; además, RF-4 no deja cambiar el material entre fases. Por
  eso la asignación lleva **un material por región** y, por fase, si está excavada. El material por
  fase llegará con la spec 012, que cambiará el formato con su versión.
- 17 reglas, cada una con su caso, y la tabla cubre exactamente `model.RULES`
  (`tests/test_model_input_v009.py`, 17 tests). 27 mutaciones: tres sobrevivían (el índice de un
  segmento fuera de rango, un modelo sin externo y una malla con un nudo que no existe) y llevaron a
  tres tests; al final, 27 de 27.
