# ADR-0005 — La interfaz común: lo genérico sin Qt en OGR-Core, lo de Qt en `ogr-gui`

- **Estado:** ACEPTADA (2026-11-24, propietaria). Decisión D1 de la spec 006
  (`spec/features/006-interfaz-y-calculo/spec.md`), que concreta la decisión P1 del plan de
  desarrollo (opción (b), tomada el 2026-10-27).

## Contexto

P1 decidió no copiar la interfaz de OGR Slip2D ni escribirla de nuevo, sino **extraer lo genérico**
a una versión nueva de OGR-Core o a un paquete hermano `ogr-gui`, copiándolo desde Slip2D sin
tocarlo, como se hizo con el núcleo (ADR-0002). Cuál de los dos quedaba para el ADR de la spec de
la interfaz. Lo que se midió al abrirla (Slip2D v0.1.486, OGR-Core v0.2.7, solo lectura):

- `ogr_gui` tiene 77 archivos y 48 721 líneas; los 13 que importan el motor de equilibrio límite
  suman 23 308: la ventana principal (7 500), la de interpretación (4 821) y el lienzo (4 378) entre
  ellos. Esos tres, además, trabajan sobre el `Project` del núcleo, que es el modelo de equilibrio
  límite y no el de este programa (spec 004, D1). El diccionario de traducciones (8 462) mezcla los
  dos dominios, ordenado por versión.
- `ogr_api` tiene 31 archivos y 10 158 líneas, 6 087 en los 14 que importan el motor. Lo genérico
  (el registro de operaciones, los errores con código, la conversión de argumentos, los trabajos en
  subproceso y el puente con la ventana) son unas 1 200 líneas y no importan Qt ni `mcp`.
- Lo genérico con Qt (temas y colores por papel, iconos, leyenda, paletas y niveles, enganche, barra
  de estado, motivos de lo deshabilitado, tareas en hilo, preferencias, ayudas de diálogo, gráfico
  XY, el mecanismo de `tr()`) son del orden de 3 500 a 4 500 líneas, sin el motor ni el `Project`.
- La regla de capas del núcleo (`AGENTS.md` de OGR-Core, «Capas») prohíbe que `ogr_core` importe
  PySide6, `ogr_gui`, `ogr_api` o `mcp`, y un test lo vigila en el código y en `sys.modules`.
- **OGR Data ya copia el aspecto de Slip2D**, su `tr()` y su patrón de operaciones y de servidor
  MCP. La copia que diverge que P1 quería evitar ya existe una vez.
- Ni Slip2D ni OGR-Core tenían planeada ninguna extracción.

## Decisión

- **Lo genérico sin Qt va a una versión nueva de OGR-Core**: el registro de operaciones, los errores
  con código, la conversión de argumentos, los trabajos en subproceso y el protocolo del puente. No
  importa PySide6 ni `mcp`, así que cabe sin cambiar la regla de capas.
- **Lo genérico con Qt va a un paquete hermano, `ogr-gui`** (repositorio `samuelsl27/OGR-GUI`), que
  depende de `ogr-core` y que cada programa fija por etiqueta, como el núcleo. Lleva también el
  diccionario de sus propios textos y las comprobaciones de las reglas 2 y 3 (todo texto por `tr()`
  y traducido; toda acción en un menú), para que digan lo mismo en todos los programas.
- Las dos cosas **se copian de Slip2D sin tocarlo**. Slip2D, y OGR Data si quiere, las adoptan
  cuando su sesión lo decida.
- **No se extrae lo que no es genérico**: la ventana principal, la de interpretación, el lienzo
  completo y los diálogos de contenido. OGR FEM2D escribe los suyos sobre las piezas comunes, con la
  misma estética (`spec/constitution/guia-de-interfaz.md`).
- El servidor MCP de OGR FEM2D es propio y fino: sus herramientas salen de su catálogo de
  operaciones, sin OAuth en la fase 1.
- Lo pide este programa por escrito (spec 006, T1): a la sesión de OGR-Core, el armazón sin Qt; a la
  suite, el repositorio nuevo. Este programa no lo copia ni lo rodea mientras llega.

## Alternativas descartadas

- **Todo en OGR-Core**, cambiando su regla de capas: el núcleo dejaría de poder probarse sin pantalla
  y sin el SDK de MCP, y la línea de órdenes cargaría con Qt. Es caro y no hace falta.
- **Todo en `ogr-gui`**, también lo que no tiene Qt: el registro de operaciones quedaría en un
  paquete de interfaz, y la línea de órdenes y el servidor MCP dependerían de él. Queda como
  alternativa si OGR-Core no acepta el armazón.
- **Extraer también la ventana y el lienzo**: habría que separarlos del equilibrio límite y del
  `Project`, es decir, reescribir Slip2D, que no se toca. Copiarlos a medias sería otra copia que
  diverge.
- **Copiar lo que haga falta a este repositorio** (la opción (a) de P1): es la tercera copia.

## Consecuencias

- Este programa fija tres etiquetas: `ogr-core`, `ogr-gui` y, por él, la de `ogr-core` que pida
  `ogr-gui`. Subir cualquiera es un commit propio (`AGENTS.md`, «Un núcleo y varios programas»).
- La spec 006 se parte en cuatro partes (D2). La A no depende de nada de esto; la B espera a la versión
  de OGR-Core; la C y la D, a `ogr-gui` v0.1.0.
- `tech-stack.md`, `AGENTS.md` («Stack») y `plan_de_desarrollo.md` (P1) lo recogen.
