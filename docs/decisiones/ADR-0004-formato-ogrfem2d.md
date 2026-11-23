# ADR-0004 — Formato propio `.ogrfem2d`, con la malla, que abre el `.ogr` de Slip2D

- **Estado:** ACEPTADA (2026-11-23, propietaria). Decisiones D1 y D3 de la spec 004
  (`spec/features/004-modelo-y-proyecto/spec.md`). Modifica la fila «Formato `.ogr` compartido con
  Slip2D» de `spec/constitution/tech-stack.md` y el nombre del archivo del modelo del ADR-0003.

## Contexto

`AGENTS.md` y `tech-stack.md` decían que el proyecto sería un `.ogr` (JSON) «compatible con OGR
Slip2D en la parte geométrica». Al abrir la spec 004 se miró qué haría falta para eso (núcleo
`ogr-core` v0.2.6):

- El `Project` del núcleo es el modelo de equilibrio límite: métodos, búsquedas, grieta, soportes,
  sismo. No tiene E ni ν, ni contornos de excavación o de fase, ni arcos en los segmentos.
- Lee una lista fija de secciones. Las que no conoce las acepta al leer, **pero las pierde al
  guardar**. Un tipo de contorno que no conoce hace que el archivo no se pueda abrir. Nunca lee
  `format_version`.
- Que los dos programas abran el mismo archivo pedía cambiar el núcleo (conservar secciones, leer la
  versión, arcos, contornos nuevos) y Slip2D, y la spec habría esperado a esa versión del núcleo.

Los programas de referencia tienen dos formatos. El de elementos finitos guarda su archivo con el
modelo, la malla y los resultados. Al abrir el archivo del de equilibrio límite, lo convierte: trae
contornos, agua, cargas y materiales, pone restricciones y valores elásticos por defecto, y lo dice.
También exporta una fase al de equilibrio límite. Es lo documentado en el análisis de interfaz, fuera
del repositorio: `B_RS2_documentacion/modelo/M02_menu_file_e_import_export.md`, §5.2 y §6.2, y
`A_Phase2_8_observado/archivos/F01_formato_fez_fea_resultados.md`.

## Decisión

- El modelo de OGR FEM2D se guarda en un archivo propio, **`modelo.ogrfem2d`**, en JSON. Lleva
  `format`, `format_version` y `written_by`. Una versión posterior, una clave desconocida o un tipo
  erróneo dan un error que los nombra; nada se pierde en silencio.
- **Lleva la malla entera**, con la huella de la entrada del mallador de la que salió (spec 004, D3).
  Va un nudo y un elemento por línea, para que git pueda comparar el archivo.
- Los resultados siguen aparte, en `modelo.h5`, con la huella del modelo (ADR-0003).
- OGR FEM2D **abre el `.ogr` de OGR Slip2D convirtiéndolo** (spec 004, D16). Lo lee con
  `Project.load` del núcleo fijado y dice qué trae, qué no trae y qué pone por defecto. Exportar una
  fase a Slip2D va en una spec posterior. Que Slip2D abra un `.ogrfem2d` es cosa de su sesión.
- **Lo que se comparte es el código, no el archivo.** El núcleo pone las unidades (se guarda en kPa),
  las orientaciones de carga, el deshacer, el lector DXF y el mallador.

## Alternativas descartadas

- **Un `.ogr` común con una sección por programa**: pide cambiar el `Project` del núcleo y Slip2D,
  y la spec 004 quedaría parada hasta esa versión del núcleo. Puede volver si algún día los dos
  programas necesitan editar el mismo modelo.
- **Todo tipado en el `Project` del núcleo**: cada spec de FEM con algo nuevo en el modelo pediría un
  PR al núcleo y una subida de la fijación en Slip2D, y Slip2D cargaría con clases que no usa.
- **La malla fuera del archivo, rehecha al abrir**: una versión nueva del mallador cambiaría la malla
  de un caso sin que se viera (regla 9).

## Consecuencias

- El archivo pesa: la malla del caso 005 son unos 28 000 elementos de 6 nudos, varios MB. Se mide en
  la spec 004 (T15).
- Las condiciones y cargas van sobre la geometría (spec 004, D7), y sobreviven a un nuevo mallado.
- `AGENTS.md`, `tech-stack.md`, el ADR-0003, `plan_de_desarrollo.md` y `validacion/README.md`
  pasan a nombrar `.ogrfem2d`.
