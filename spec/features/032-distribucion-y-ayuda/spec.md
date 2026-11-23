# Spec 032 — Distribución, ayuda y páginas de los casos

> **Borrador de alcance (2026-11-23), sin aprobar.** Trabajo transversal del plan de desarrollo
> (`spec/constitution/plan_de_desarrollo.md`, «Trabajo transversal (en todas las fases)»:
> distribución y documentación). Solo el **qué** y el **porqué**, sin fórmulas ni decisiones
> tomadas. **Antes de abrirla hay que reevaluarla** (sección siguiente); después, plan y tareas con
> el OK de la propietaria.

## Antes de abrirla: reevaluar esta spec

Este borrador se escribió antes de que existieran las specs que lo preceden; el código, el núcleo y
OGR Slip2D habrán avanzado. Al abrirla, y antes de escribir el plan:

- [ ] Contrastarla con el código de este programa y con las specs cerradas desde el 2026-11-23: qué
      ya está hecho, qué cambió y qué se movió de sitio.
- [ ] Mirar qué tienen ya OGR Slip2D y `ogr_core` en la etiqueta fijada. Lo genérico se pide a la
      sesión de OGR-Core, no se copia (`AGENTS.md`, «Un núcleo y varios programas»). Puntos de
      partida vistos al escribir el borrador (núcleo v0.2.6):
      - Aquí, el congelado de la spec 001 (RF-10, tarea T15; D6: PyInstaller 6.22 en el `.venv`
        como herramienta, GPL-2.0-or-later con excepción para distribuir): `poc/freeze/build.py`
        congela `poc/freeze/casos.py` en una carpeta, con los `esperado.json` dentro, y lo ejecuta
        fuera del árbol sin `PYTHONPATH` ni `PYTHONHOME`; sale en `build/freeze/` (ignorado). Es el
        programa de los casos, sin interfaz.
      - `.github/workflows/wheels.yml`: una rueda abi3 por plataforma (Windows x64, macOS ARM,
        Linux x86_64) con maturin; la suite entera sobre cada rueda con Python 3.11, 3.12 y 3.13; un
        trabajo que congela y ejecuta los casos en las tres. `.github/scripts/wheel_check.py`.
      - `pyproject.toml` (v0.0.8): el núcleo como dependencia `git+…@v0.2.6`; sin PySide6 ni h5py
        todavía. `validacion/README.md` (estructura de un caso y qué se publica). `docs/changelog/`.
        Este repositorio no tiene todavía su orden de publicación (`release`).
      - Spec `006-interfaz-y-calculo`: RF-15 (ayuda adaptada que enlaza los casos, sin telemetría),
        su requisito no funcional «instalador congelado con la interfaz» y el criterio «la CI en
        verde con la interfaz y el congelado» (duda 1).
      - En OGR Slip2D, solo lectura: **no tiene instalador**; se instala clonando y con
        `pip install -e .` (`README.es.md`, «Instalación»; `docs/quickstart.md`), y su CI
        (`.github/workflows/tests.yml`) no congela. **Ayuda**: `ogr_gui/documentation.py`
        (v0.1.250): F1 abre en el navegador la documentación del sitio del proyecto en el idioma de
        la interfaz (es o en), con una sola tabla de direcciones, nada al arrancar y la razón
        escrita de por qué no es la llamada de red que prohíbe su `AGENTS.md`; «Buscar
        actualizaciones» no contacta con ningún servidor. El fuente del sitio no está en ese
        repositorio (no visto dónde está).
      - En Slip2D, la traducción: `ogr_gui/i18n/__init__.py` (diccionarios en Python, con la puerta
        abierta a otro formato sin tocar las llamadas a `tr()`); y sus tests
        `test_i18n_coverage_v141.py` (toda clave de `tr()` con su traducción),
        `test_menu_reachability_v142.py`, `test_menus_spanish_v1290.py`,
        `test_qt_translations_v1292.py` y `test_help_topics_v1250.py`.
      - En Slip2D, la publicación: `.claude/commands/release.md` (la versión en siete sitios, con
        `test_version_consistency_v176.py` como lista que manda; los contadores de tests de los dos
        README; el changelog con lo encontrado; la suite entera; el resumen antes del commit).
        `validacion/README.md` con la tabla de casos: qué fija cada uno y su fuente.
      - Lo observado: el menú Ayuda de la referencia (carpeta A,
        `menus_modelo/00_arbol_menus_modelo.md`, «Help»): temas de ayuda, tutoriales, soporte,
        actualizaciones y «Acerca de»; la nota de allí: se adapta al de la suite, no se copia.
      - Los casos: `../Referencias/Ejemplos/Casos_por_problema/00_INDICE.md`, «Cómo se usará»,
        punto 4 (versión publicable de un caso: modelo propio, datos, comparación y fuente
        científica; nunca el PDF, el texto, las figuras ni el nombre del programa comercial).
- [ ] Leer y comprobar las fuentes de «Validación numérica» y de «Fuentes por conseguir»; las fichas
      de los casos no son fuente.
- [ ] Releer las fichas de los casos que la cierran y su «Seguimiento».
- [ ] Convertir las «Dudas abiertas» en decisiones propuestas (D1, D2…) con su porqué, para el OK de
      la propietaria.

## Depende de

- Spec 001 (el congelado y las ruedas, D6) y `006-interfaz-y-calculo` (la interfaz que se congela,
  el menú Ayuda, la traducción).
- Spec `004-modelo-y-proyecto`: el `modelo.ogr` de cada caso, que las páginas y los tutoriales
  abren.
- Cada spec de cálculo, para la parte de la ayuda y de las páginas que le toca: esta spec fija el
  andamiaje y las comprobaciones; el contenido crece con cada versión.

## Contexto y objetivo

Hoy el programa solo se usa desde el árbol de fuentes, con el `.venv`. Para que lo use un ingeniero
hacen falta tres cosas, que el plan agrupa como trabajo transversal: un **instalador** por versión
que funcione sin Python en las tres plataformas, a partir del congelado de la spec 001; la **ayuda
de usuario**, en español y en inglés, con **tutoriales**; y la **página pública de cada caso de
validación**, que es lo que permite auditar el programa (`mission.md`: un resultado que no se puede
comprobar no vale nada). Las ruedas ya se construyen y se prueban en la CI. Slip2D no tiene
instalador; su ayuda vive en el sitio del proyecto y se abre desde F1.

## Usuarios / actores

- **El ingeniero** que instala el programa sin saber Python, en Windows, macOS o Linux.
- **El docente y el estudiante**, que siguen los tutoriales.
- **Quien audita un resultado**: lee la página del caso, su fuente y su tolerancia, y lo repite.
- **La propietaria**, que publica cada versión con su instalador y sus páginas.

## Historias de usuario

- H1: Como ingeniero quiero instalar una versión concreta con un instalador y abrirla sin tener
  Python, para usarla en un equipo de trabajo.
- H2: Como ingeniero quiero pulsar F1 o ir al menú Ayuda y leer, en mi idioma, qué hace el diálogo
  que tengo abierto, de dónde sale su fórmula y qué valores por defecto cambian el resultado.
- H3: Como estudiante quiero seguir un tutorial paso a paso con un modelo que se abre y calcula.
- H4: Como auditor quiero ver, para cada caso de validación, su fuente científica, su tipo de
  referencia, su malla, su tolerancia y lo que calcula esta versión, y repetirlo desde el programa.

## Requisitos funcionales (EARS)

**Instalador y ruedas**

- RF-1: EL SISTEMA produce en la CI, para cada versión publicada, un instalador por plataforma con
  la interfaz, el motor compilado y los casos de validación, a partir del congelado de la spec 001;
  el nombre del instalador lleva la versión (duda 11).
- RF-2: CUANDO se instala en un equipo sin Python, EL SISTEMA arranca, abre un caso de validación,
  lo calcula y da el resultado dentro de su tolerancia e idéntico al de la suite en el árbol.
- RF-3: EL SISTEMA incluye en el instalador la licencia AGPL, el enlace al código fuente de esa
  versión y los avisos de licencia de cada dependencia congelada (duda 5).
- RF-4: EL SISTEMA no hace ninguna llamada de red al instalar, al arrancar ni al calcular; «Buscar
  actualizaciones», si se ofrece, no contacta con ningún servidor (regla de Slip2D).
- RF-5: EL SISTEMA sigue construyendo y probando las ruedas en la CI; dónde se publican, según la
  duda 6.

**Ayuda y tutoriales**

- RF-6: EL SISTEMA ofrece ayuda de usuario en español y en inglés, alcanzable desde el menú Ayuda
  (regla 3) y, según la duda 8, desde cada diálogo; abre la del idioma de la interfaz.
- RF-7: Cada página de ayuda de un cálculo cita la fuente científica de sus fórmulas (autor y año),
  lista los valores por defecto que cambian el resultado (regla 12) y enlaza los casos que lo
  validan; no copia texto de los manuales del programa de referencia ni nombra productos.
- RF-8: Cada tutorial va con su `modelo.ogr`, y un test lo abre y lo calcula en cada versión, para
  que el tutorial no se quede atrás del programa.
- RF-9: SI una acción de menú no tiene página de ayuda, o una página no existe en los dos idiomas,
  ENTONCES un test falla (como en Slip2D para `tr()` y para los menús).

**Páginas de los casos de validación**

- RF-10: EL SISTEMA genera, para cada carpeta de `validacion/casos/`, su página pública a partir de
  `caso.md`, `esperado.json` y el resultado de la versión: fuente científica, tipo de referencia
  (una `comparacion` se dice como tal, no como validación), malla y elemento con que se fijó la
  tolerancia, tolerancia, valor esperado, valor calculado y error.
- RF-11: La página de un caso no lleva el PDF, el texto, las figuras ni el nombre del programa
  comercial (`validacion/README.md`; índice de casos, «Cómo se usará», punto 4).
- RF-12: CUANDO un caso falla en una versión, su página lo dice; no se publica una página verde de
  un caso rojo.

**Publicación**

- RF-13: EL SISTEMA tiene una orden de publicación propia, como la de Slip2D: la versión en todos
  sus sitios con un test que los compara, el changelog con lo encontrado, la suite entera en verde
  y el resumen antes del commit (duda 13).

## Validación numérica

**No aplica**: esta spec no calcula nada ni cambia ningún cálculo. Lo que sí tiene que demostrar es
que el programa instalado es el mismo que el probado, y que la documentación no miente ni se queda
atrás. Esas comprobaciones sustituyen a los casos:

| Comprobación | Referencia | Qué se compararía |
|---|---|---|
| El instalador calcula | — (identidad) | En cada plataforma de la CI, el programa instalado sin Python calcula todos los casos de `validacion/casos/` dentro de su tolerancia e idénticos, bit a bit, a la suite en el árbol |
| La interfaz arranca instalada | — | El programa instalado abre su ventana sin pantalla, carga un `modelo.ogr` y se cierra sin error |
| Sin red | — | El programa instalado no abre ninguna conexión al arrancar ni al calcular un caso |
| Licencias | — | El instalador lleva la licencia, el enlace al fuente de la versión y el aviso de cada dependencia congelada |
| Ayuda completa | — | Toda acción de menú con su página, toda página en los dos idiomas, ningún enlace interno roto (sin red) |
| Tutoriales vivos | — | Cada tutorial abre y calcula su `modelo.ogr` en la versión |
| Páginas de los casos | — | Una página por caso, con fuente, tipo de referencia, malla, tolerancia y resultado de la versión |
| Sin marcas | — | Ni la ayuda ni los tutoriales ni las páginas nombran productos ni marcas comerciales (duda 14) |
| Regla 7 | — | Ninguna opción del instalador ni de la ayuda cambia un número; si alguna lo hiciera, su test |

## Fuentes por conseguir

- Ninguna fórmula. Lo que hay que conseguir son licencias: la de cada herramienta nueva de
  instalación o de generación de la ayuda (compatible con AGPL-3.0, con el OK de la propietaria) y
  las condiciones de la LGPL de PySide6 y Qt para distribuirlas congeladas.
- Las fuentes que citen la ayuda y las páginas son las de cada spec de cálculo, ya comprobadas.

## Requisitos no funcionales

- **Ninguna dependencia nueva sin preguntar**: generador de instaladores, de ayuda o de páginas, cada
  uno con su licencia comprobada (AGPL-3.0); PyInstaller ya está aprobado como herramienta (D6).
- Las tres plataformas de la CI; el tamaño del instalador y su tiempo de arranque, medidos.
- Sin telemetría; sin comprobación automática de versiones.
- Todo texto de la interfaz que añada esta spec (menú Ayuda, «Acerca de») pasa por `tr()` (regla 2).

## Casos límite

- Instalar dos versiones a la vez; actualizar sobre una anterior; desinstalar.
- Ruta de instalación con espacios o caracteres no ASCII; usuario sin permisos de administrador.
- Sistema sin navegador (Slip2D lo resuelve diciendo la dirección en la barra de estado).
- Un caso nuevo sin `modelo.ogr` (005 hoy); un caso en rojo en la versión que se publica.
- Ayuda de una función que cambió de comportamiento entre versiones.

## Fuera de alcance

- La validación misma (cada fase cierra con sus casos) y los pendientes de interfaz de S06.
- Informes en PDF del programa; un servicio alojado; la integración con Slip2D en un solo
  instalador de la suite (duda 12).
- Traducciones a otros idiomas que el español y el inglés.

## Criterios de finalización

- [ ] Dudas convertidas en decisiones y aprobadas por la propietaria
- [ ] El instalador de cada plataforma, construido en la CI, se instala sin Python y calcula todos
      los casos dentro de su tolerancia e idénticos a la suite en el árbol
- [ ] Licencias y aviso de cada dependencia dentro del instalador
- [ ] Toda acción de menú con su página de ayuda, en español y en inglés, con test
- [ ] Cada tutorial con su `modelo.ogr` calculado por un test
- [ ] Cada caso de `validacion/casos/` con su página generada y su resultado de la versión
- [ ] La orden de publicación de este repositorio, con su test de versiones
- [ ] Changelog con lo encontrado

## Dudas abiertas

- [NECESITA ACLARACIÓN] **1. Quién hace el instalador con interfaz**: la 006 ya lo pide como requisito
  no funcional y en sus criterios. (a) La 006 congela la interfaz y esta spec hace el instalador;
  (b) todo en la 006 y aquí solo ayuda y páginas; (c) todo aquí, y la 006 quita la línea.
- [NECESITA ACLARACIÓN] **2. Forma del instalador** por plataforma: la carpeta del congelado
  comprimida; un instalador propio de cada sistema; una imagen portátil. Cada herramienta, con su
  licencia y el OK de la propietaria.
- [NECESITA ACLARACIÓN] **3. Firma del instalador** en Windows y macOS: sin firma el sistema avisa o
  lo bloquea; firmar pide una cuenta de desarrollador de cada sistema, con su coste.
- [NECESITA ACLARACIÓN] **4. Plataformas**: la CI hace macOS ARM, Linux x86_64 y Windows x64. ¿macOS
  Intel, Linux ARM?
- [NECESITA ACLARACIÓN] **5. Licencias en el congelado**: la AGPL pide ofrecer el fuente
  correspondiente (¿enlace a la etiqueta o el fuente dentro?); la LGPL de PySide6 y Qt pide que se
  puedan sustituir sus bibliotecas (el congelado en carpeta lo permite; en un solo archivo, por
  comprobar); avisos de NumPy, SciPy, h5py y de los crates de Rust.
- [NECESITA ACLARACIÓN] **6. Publicar las ruedas**: el índice público de paquetes de Python no admite,
  por lo que se sabe, dependencias con dirección directa como `ogr-core @ git+…` (por comprobar).
  Opciones: publicar también `ogr-core` allí (petición a OGR-Core); publicarlas solo con cada
  versión del repositorio; no publicarlas.
- [NECESITA ACLARACIÓN] **7. Dónde vive la ayuda**: en el sitio del proyecto, como Slip2D (F1 abre
  el navegador); dentro del instalador, sin red; o las dos. Y en qué formato se escribe, y si su
  fuente va en este repositorio o en el del sitio.
- [NECESITA ACLARACIÓN] **8. Ayuda contextual**: una página por diálogo, abierta con F1 desde él, o
  un índice por menús.
- [NECESITA ACLARACIÓN] **9. Las páginas de los casos**: generadas por un script de este repositorio
  en cada versión o escritas a mano; ¿con la historia del error por versión?; ¿las comparaciones
  en la misma lista, marcadas, o aparte?
- [NECESITA ACLARACIÓN] **10. Tutoriales**: cuántos y cuáles; ¿sobre los casos de validación o sobre
  modelos propios? Los de la referencia no se pueden copiar.
- [NECESITA ACLARACIÓN] **11. Cada cuánto un instalador**: «por versión», dice el plan; hoy cada tarea
  sube la versión (0.0.x). ¿En cada versión o en cada cierre de fase?
- [NECESITA ACLARACIÓN] **12. La suite**: ¿un instalador por programa o uno de OpenGeoRock con Slip2D
  y FEM2D? Slip2D no tiene instalador y fija otra etiqueta del núcleo.
- [NECESITA ACLARACIÓN] **13. La orden de publicación**: escribirla en este repositorio a partir de
  la de Slip2D (es un archivo de herramientas del agente: necesita el OK de la propietaria).
- [NECESITA ACLARACIÓN] **14. Comprobar que no hay marcas** sin escribirlas en el repositorio: un
  test que las liste las nombraría en el código, que es lo que prohíbe `AGENTS.md`. ¿Lista fuera del
  repositorio, huellas de las palabras, o revisión a mano?
- [NECESITA ACLARACIÓN] **15. Idioma por defecto** del programa instalado: el del sistema, el
  español o el inglés.

S06 es de `D_sintesis/` del análisis de interfaz
(`../Referencias/Doc_Guia/Analisis_interfaz_funcionamiento/`); el árbol de menús, de su carpeta A.
