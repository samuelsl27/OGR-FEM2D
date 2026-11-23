# Spec 006 — Interfaz, operaciones y cálculo

> **Borrador de alcance (2026-11-23), sin aprobar.** Fase 1 del plan de desarrollo
> (`spec/constitution/plan_de_desarrollo.md`, «Spec 006 — Interfaz, operaciones y cálculo (depende
> de P1)»). Solo el **qué** y el **porqué**, sin fórmulas ni decisiones tomadas. **Antes de abrirla
> hay que reevaluarla** (sección siguiente); después, plan y tareas con el OK de la propietaria.

## Antes de abrirla: reevaluar esta spec

Este borrador se escribió antes de que existieran las specs que lo preceden; el código, el núcleo y
OGR Slip2D habrán avanzado. Al abrirla, y antes de escribir el plan:

- [ ] Contrastarla con el código de este programa y con las specs cerradas desde el 2026-11-23: qué
      ya está hecho, qué cambió y qué se movió de sitio.
- [ ] Mirar qué tienen ya OGR Slip2D y `ogr_core` en la etiqueta fijada. Lo genérico se pide a la
      sesión de OGR-Core, no se copia (`AGENTS.md`, «Un núcleo y varios programas»). Puntos de
      partida vistos al escribir el borrador (Slip2D v0.1.484, solo lectura; para reevaluar P1):
      - `ogr_gui`: 77 archivos, **48 721 líneas** (el plan decía 42 000). Los 13 que importan el
        motor de equilibrio límite suman unas 23 200: `main_window.py` (7 500),
        `interpret_window.py` (4 821), `canvas/canvas_view.py` (4 378), `project_settings_dialog.py`,
        `grid_dialogs.py`, `labels.py`, `statistics_window.py`… Los otros 64 (unas 25 500) incluyen
        `i18n/__init__.py` (8 462: el diccionario, que mezcla textos genéricos y de equilibrio
        límite), `contours.py` (sin Qt), `themes/`, `widgets/legend.py`, `canvas/snap_engine.py`,
        `canvas/tool_mode.py`, `canvas/graphics_items.py`, los diálogos de DXF, anotaciones,
        preferencias y vista. **No importar el motor no lo hace genérico**:
        `material_properties_dialog.py` (2 607) no lo importa y es de criterios de equilibrio
        límite; y el lienzo y la ventana importan el `Project` del núcleo, que es de equilibrio
        límite (spec 004, duda 2).
      - `ogr_api`: 31 archivos, **10 158 líneas** (el plan: 9 700); los 14 que importan el motor
        suman unas 6 100 (`ops/model.py`, `ops/groundwater.py`, `results.py`, `settings_schema.py`,
        `catalog.py`, `jobs/worker.py`…). Genérico, unas 4 000: `workspace.py` (modelos por
        identificador), `errors.py`, `coerce.py`, `inventory.py`, `snapshot.py` (copias y huella),
        `bridge.py` (puente con la ventana abierta), `render.py`, `ops/project.py`, `ops/history.py`.
        `jobs/` (subproceso cancelable con archivos de progreso, resultado y estado) es genérico en
        su mecanismo; su `worker.py` llama al motor de equilibrio límite.
      - `ogr_mcp`: 8 archivos, 2 952 líneas; **no importa el motor**: servidor, OAuth, seguridad,
        perfiles y guía sobre `ogr_api.call`. Las herramientas salen del catálogo de `ogr_api`.
      - `ogr_cli`: 2 archivos, 395 líneas; de equilibrio límite (cálculo por lotes y `.h5`).
      - OGR-Core: su `AGENTS.md` («Capas») **prohíbe que `ogr_core` importe `PySide6`, `ogr_gui`,
        `ogr_api`, `ogr_cli`, `ogr_mcp` o `mcp`**. Llevar la interfaz al núcleo pide cambiar esa
        regla; un paquete hermano `ogr-gui`, no.
- [ ] Leer y comprobar las fuentes de «Validación numérica» y de «Fuentes por conseguir»; las fichas
      de los casos no son fuente.
- [ ] Releer las fichas de los casos que la cierran y su «Seguimiento».
- [ ] Convertir las «Dudas abiertas» en decisiones propuestas (D1, D2…) con su porqué, para el OK de
      la propietaria. **La primera, P1, con su ADR.**

## Depende de

- **Decisión P1** del plan (tomada: opción (b); queda elegir entre OGR-Core y `ogr-gui` en el ADR
  que abre esta spec).
- Specs 002 a 005: motor, malla, modelo y resultados. ADR-0002 y ADR-0003.

## Contexto y objetivo

Es la spec que cierra la fase 1: dibujar un modelo, mallarlo, calcularlo y ver los resultados, todo
desde la interfaz, en elástico. Tiene tres capas, como Slip2D: las **operaciones** sin Qt
(`ogr_api`), con la línea de órdenes y el servidor MCP encima; el **modelador**, con los menús en el
orden del flujo de trabajo; y el **cálculo** y la **interpretación**. La interfaz se parece a la que
los ingenieros conocen, pero cada opción tiene que mover el número (regla 7) y cada valor por
defecto que lo cambia se ve con el resultado (regla 12). Reutilizar la de Slip2D sin tocarlo es P1.

## Usuarios / actores

- **El ingeniero**; **el docente y el estudiante**; **un agente** a través del servidor MCP; **un
  script** o la línea de órdenes; **el investigador** que lee los resultados.

## Historias de usuario

- H1: Como ingeniero quiero dibujar un túnel y su contorno exterior, mallarlo, darle la tensión de
  campo, calcular y ver σ1 alrededor del hueco sin salir del programa.
- H2: Como ingeniero que conoce la interfaz de referencia quiero los menús en el orden del flujo de
  trabajo y entrar vértices por clic, teclado, tabla, círculo o arco.
- H3: Como ingeniero quiero cancelar un cálculo largo y ver su progreso por fase, escalón e
  iteración, y su registro de convergencia.
- H4: Como ingeniero quiero una consulta por línea con su gráfico y exportarla a una tabla.
- H5: Como agente quiero construir y calcular el mismo modelo con las mismas operaciones que la
  interfaz.
- H6: Como usuario quiero toda la interfaz en español o en inglés.

## Requisitos funcionales (EARS)

**Operaciones y transporte**

- RF-1: EL SISTEMA ofrece cada acción de las specs 004 y 005 como una operación con nombre,
  argumentos tipados y respuesta serializable, sin Qt; la interfaz, la línea de órdenes y el
  servidor MCP la llaman, y ninguna sabe quién la llama.
- RF-2: SI una operación recibe un argumento desconocido o inválido, ENTONCES lo rechaza con un error
  que lo nombra; nunca lo acepta en silencio.
- RF-3: EL SISTEMA hace de cada edición un paso de deshacer, venga de donde venga.

**Cálculo**

- RF-4: CUANDO se pide calcular, EL SISTEMA lo hace en un subproceso cancelable y con cola, muestra el
  progreso por fase, escalón e iteración, y al terminar escribe el `.h5` (spec 005).
- RF-5: CUANDO se cancela, EL SISTEMA termina el proceso de verdad y no deja resultados que parezcan
  completos.
- RF-6: SI el cálculo falla (entrada rechazada, sistema singular, no convergencia), ENTONCES EL
  SISTEMA dice qué objeto del modelo lo causa y conserva el registro.
- RF-7: SI no hay malla, o la malla o los resultados son de otro modelo, ENTONCES calcular o
  interpretar no se ofrece como válido, y el motivo se dice.

**Modelador**

- RF-8: EL SISTEMA ordena los menús como el flujo de trabajo: Archivo, Edición, Vista, Análisis,
  Contornos, Malla, Cargas, Desplazamientos, Soporte, Agua, Estadística, Propiedades, Herramientas,
  Ventana, Ayuda (carpeta A, `menus_modelo/00_arbol_menus_modelo.md`); toda acción es alcanzable
  desde un menú (regla 3).
- RF-9: EL SISTEMA ofrece los diálogos de la fase 1: ajustes del proyecto, fases, tensión de campo,
  malla en dos pasos (discretizar y mallar), materiales, asignación por región y fase (con
  excavar), desplazamientos (restringir en X, en Y o en las dos, imponer, liberar, condición por
  defecto del externo) y cargas.
- RF-10: EL SISTEMA dibuja las fases como pestañas, el bloque de tensiones de campo, las condiciones y
  las cargas; la fase visible es la que se edita.
- RF-11: EL SISTEMA muestra en cada campo de tensión o de carga el convenio en que se escribe, y
  convierte en un único sitio (regla 10; S06, duda 14).

**Interpretación**

- RF-12: EL SISTEMA ofrece un selector de magnitud (spec 005), contornos con leyenda (magnitud,
  unidad, convenio y si los valores son recuperados), pestañas de fase, consultas por línea, por
  contorno y en todos los nudos, con sus gráficos, y su exportación.
- RF-13: EL SISTEMA da un informe textual del modelo y de sus resultados (como el *Info Viewer* de la
  referencia, carpeta A, `interpret/01_info_viewer.md`).
- RF-14: EL SISTEMA muestra con cada resultado los valores por defecto que lo decidieron: la cota B y
  las notas del mallador (nudos añadidos, arcos sin prueba de terminación), los nudos del eje que
  restringió el motor, los ajustes del cálculo (regla 12).

**Idioma, ayuda y casos**

- RF-15: EL SISTEMA pasa todo texto visible por `tr()`, con su traducción española (regla 2), y una
  ayuda adaptada que enlaza los casos de validación; sin telemetría ni llamadas de red no pedidas.
- RF-16: EL SISTEMA abre, calcula y compara los casos de la fase con su `modelo.ogr` en un test que
  usa las operaciones, sin pantalla.

## Validación numérica

| Caso | Fuente científica (por comprobar) | Qué se compararía |
|---|---|---|
| Los casos de `VER-STR-01`, `VER-STR-04` y `VER-STR-09` con `modelo.ogr` (cuáles, spec 004, duda 5) | Kirsch (1898), en Jaeger, Cook y Zimmerman (2007), §8.4; Michell (1902) y Lamé (1852), en Timoshenko y Goodier (1951), §34 y §121 | Por la vía completa (abrir, mallar, calcular, consultar), los mismos números bit a bit que por el motor, y dentro de la tolerancia de su `esperado.json` |
| Identidad de transporte | — | La misma secuencia de operaciones por la interfaz, la línea de órdenes y el servidor MCP da el mismo modelo (huella) y los mismos resultados |
| Identidad de cancelación | — | Cancelar y volver a calcular da lo mismo que calcular una vez |
| Regla 7 | — | Cada opción de cada diálogo, con el test que demuestra que mueve el número |

El 0.6 % de error de σ1 en la ficha de `VER-STR-04` es del programa de referencia: no es valor
esperado. La duda 7 de S06 (el dominio finito de STR-04) quedó resuelta en la spec 002: el efecto
del contorno baja con la distancia, y el caso se fijó con un dominio mayor.

## Fuentes por conseguir

- Ninguna fórmula nueva. Si se ofrece el contorno externo automático (caja, círculo, envolvente),
  la relación entre su factor de expansión y el tamaño observada en la referencia es una hipótesis
  (carpeta A, `dialogos/D02_contornos_malla_tension_de_campo.md`, §1), no una fuente: la regla sería
  propia y documentada.

## Requisitos no funcionales

- **Dependencias nuevas para este repositorio**: PySide6 (LGPL, en el `tech-stack.md`) y el SDK del
  servidor MCP (licencia por comprobar); cada una con el OK de la propietaria.
- Tests de la interfaz sin pantalla y sin estado filtrado (regla 5), en Windows, macOS y Linux.
- El lienzo, fluido con la malla del caso 005 (28 066 elementos); el objetivo, medido en el plan.
- Instalador congelado con la interfaz, a partir del congelado de la spec 001.

## Casos límite

- Modelo sin malla; malla de otro modelo; resultados obsoletos.
- Cerrar la ventana o el programa con un cálculo en marcha.
- El servidor MCP editando un modelo que está abierto en la ventana (en Slip2D, `bridge.py`).
- Un texto sin traducción; una acción sin menú (los dos, fallo de un test).
- Axisimetría: el eje dibujado, la geometría al otro lado rechazada al dibujarla.
- Cambio de unidades o de tipo de análisis con el modelo ya definido.

## Fuera de alcance

- El contenido de los menús de Soporte, Agua y Estadística (fases 2 a 6), SSR, juntas y soportes.
- Animación y grabación, datos de usuario, juntas ubicuas, isolíneas, líneas de flujo de tensiones.
- Importar o exportar modelos de otros programas que no sean de la suite; informes en PDF.

## Criterios de finalización

- [ ] P1 decidida en su ADR; lo genérico, en la versión etiquetada que fije la decisión
- [ ] Dudas convertidas en decisiones y aprobadas por la propietaria
- [ ] Todos los RF con su test en verde; todo texto nuevo traducido; toda acción en un menú
- [ ] Los casos de la fase, por la vía completa, dentro de su tolerancia e idénticos al motor
- [ ] La CI en verde en las tres plataformas, con la interfaz y el congelado
- [ ] Changelog con lo encontrado; fichas con su «Seguimiento»; la fase 1 cerrada en la hoja de ruta

## Dudas abiertas

- [NECESITA ACLARACIÓN] **1. P1: OGR-Core o `ogr-gui`.** (a) Una versión nueva de OGR-Core, que pide
  cambiar su regla de capas (hoy no admite PySide6); (b) un paquete hermano `ogr-gui`, con
  repositorio, versiones y CI propios, y una tercera etiqueta fijada en cada programa. Y qué entra:
  el plan nombra lienzo, herramientas, diálogos de proyecto, vista y preferencias, contornos,
  idioma, trabajos en subproceso y deshacer; ¿también lo genérico de `ogr_api` y el transporte MCP?
- [NECESITA ACLARACIÓN] **2. El `Project` del núcleo**: el lienzo y la ventana de Slip2D lo importan;
  lo que se extraiga depende de la clase del modelo que elija la spec 004 (duda 2).
- [NECESITA ACLARACIÓN] **3. Traducciones**: un diccionario común y uno por programa, o uno por
  programa con copia de los textos comunes (la «copia que diverge» del ADR-0002).
- [NECESITA ACLARACIÓN] **4. Menús de fases futuras** (Soporte, Agua, Estadística): (a) visibles y
  deshabilitados con su motivo (Slip2D tiene `disabled_reasons.py`); (b) ocultos hasta su fase.
- [NECESITA ACLARACIÓN] **5. Valores por defecto de los diálogos.** Los observados (carpeta A,
  `dialogos/D01`–`D04` y `D08`: MPa, malla graduada de T3, 75 nudos por excavación, campo de 10 MPa,
  E = 20 000 MPa, ν = 0.3, peso 0.027 MN/m³…) son comportamiento, no obligación (regla 12). Las specs
  002 y 003 midieron que el T3 converge con orden 1 y no cumple STR-04 ni STR-09: ¿T6 por defecto?
- [NECESITA ACLARACIÓN] **6. Interpretación en otra ventana o en la misma**: la referencia la abre
  como otro programa; Slip2D, como otra ventana del mismo. Y una ventana por modelo o varias.
- [NECESITA ACLARACIÓN] **7. Pendientes de S06**: menús contextuales, *Page Setup* e impresión;
  ¿en esta spec o después?
- [NECESITA ACLARACIÓN] **8. El puente en vivo** entre el servidor MCP y la ventana abierta (Slip2D,
  `bridge.py` y `agent_bridge.py`): ¿en la fase 1?
- [NECESITA ACLARACIÓN] **9. Cómo partir esta spec** (se propone, no se parte aquí). Es la más grande
  de la fase. Una partición posible, en este orden:
  - **006a, operaciones y transporte**: `ogr_api` del modelo y de los resultados, la línea de
    órdenes, el servidor MCP, el cálculo en subproceso y los casos con `modelo.ogr` por operaciones.
    No necesita Qt ni P1, y cierra numéricamente la fase.
  - **006b, extracción P1**: el ADR, el paquete o la versión de OGR-Core con lo genérico, fijada
    aquí, con Slip2D sin tocar. Puede ir en paralelo a la 006a.
  - **006c, modelador**: menús, lienzo, entrada de geometría, fases y diálogos de la fase 1.
  - **006d, cálculo e interpretación en la interfaz**: ventana de cálculo, contornos y leyenda,
    consultas y gráficos, informe, exportación; y el cierre de la fase.
  Alternativa: dos specs (operaciones; interfaz) si P1 se resuelve pronto.
