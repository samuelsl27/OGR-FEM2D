# ADR-0003 — Los resultados se guardan en un archivo aparte con la huella del modelo

- **Estado:** ACEPTADA (2026-10-27, propietario). Decisión D3 de
  `../Referencias/Doc_Guia/Analisis_interfaz_funcionamiento/D_sintesis/S06_pendientes_y_dudas.md`.

## Contexto

OGR Slip2D no guarda resultados: los recalcula al abrir el modelo, para que el formato sea simple y
ningún resultado obsoleto sobreviva a un cambio del modelo (su `tech-stack.md`). Allí un cálculo dura
segundos. Aquí no: con fases, reducción de resistencia (se observaron 8–20 análisis completos por SSR
en las reproducciones P05 y P07) y probabilístico, un cálculo puede durar minutos u horas. El programa
de referencia guarda los resultados de cada fase dentro del archivo de proyecto (análisis de su
formato de archivos, fuera del repositorio: `../Referencias/Doc_Guia/Analisis_interfaz_funcionamiento/`,
`archivos/F01_formato_fez_fea_resultados.md`).

## Decisión

- **`modelo.ogr`** (JSON) sigue siendo la **única fuente de verdad** del modelo.
- Los resultados van en **`modelo.h5`**, al lado y con la misma raíz, organizados por fase.
- El `.h5` guarda la **huella** (hash) del contenido del modelo que los produjo. Al abrir, si la
  huella no coincide con la del modelo actual, los resultados se marcan **obsoletos** y no se
  presentan como válidos.
- Se parte del módulo HDF5 que Slip2D ya tiene sin usar (`ogr_core/project/results_io.py`).
  `h5py` es BSD-3-Clause, compatible con AGPL-3.0, y ya es dependencia de Slip2D.

## Alternativas descartadas

- **Recalcular siempre**: abrir un modelo podría costar minutos u horas.
- **Resultados dentro del `.ogr`**: el JSON crecería mucho y dejaría de ser legible y comparable con
  git.

## Consecuencias

- Se aparta de Slip2D en este punto; la preocupación de Slip2D (resultados obsoletos) la cubre la
  huella.
- La especificación correspondiente debe fijar: qué entra en la huella (todo lo que cambia el
  resultado; no la vista ni las anotaciones), qué se guarda (desplazamientos nodales, tensiones y
  deformaciones en puntos de Gauss, estado plástico, historia de convergencia, ensayos del SSR) y
  con qué compresión.
- Con un modelo sin `.h5`, o con un `.h5` obsoleto, el programa ofrece calcular; nunca muestra en
  silencio resultados de otro modelo.
