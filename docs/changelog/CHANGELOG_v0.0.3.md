# OGR FEM2D v0.0.3 (2026-11-18)

**Sube a `ogr-core` v0.2.0: un solo núcleo otra vez** (fase 3 de la unificación del núcleo;
ADR-0002, sección «Se levanta la modificación»). Ningún número del motor cambia: ni `validacion/`
ni `rust/` se tocan.

## Resultado

- `pyproject.toml` fija `ogr-core @ git+https://github.com/samuelsl27/OGR-Core@v0.2.0`.
- **Lo que se midió en local no es la etiqueta, sino el `main` de OGR-Core en `9b72044`**: el
  `.venv` tiene el núcleo instalado en editable desde `C:\Samuel\OGR_Suite\Core\OGR-Core`, que va
  dos commits por delante de `v0.2.0`. Esos dos commits solo añaden un test
  (`tests/test_runner_exit_v10.py`); `git diff v0.2.0 9b72044 -- ogr_core pyproject.toml` está
  vacío, así que `ogr_core/` es el de la etiqueta. **La CI instala el núcleo desde la etiqueta**
  (la rueda trae `ogr-core` como dependencia).
- `poc/benchmark.py` limita los hilos de NumPy **solo al ejecutarse** (`python poc/benchmark.py`
  o `-m poc.benchmark`), no al importarse: `ONE_THREAD` y `one_thread(environ)`. Ejecutado como
  guion hace lo mismo que antes.
- `tests/_runner.py`: la cabecera y el mensaje «WRONG SHARED TREE» ya no dan por hecho qué responde
  por `ogr_core` en otro Python; ninguna opción nueva del runner.
- Documentación: `AGENTS.md`, `README.md`, `tech-stack.md`, `roadmap.md` (una nota en la fila 0b,
  que se queda como historia) y la sección nueva de ADR-0002.
- Tests: 189 (185 de antes y 4 nuevos), en verde en local y sin ninguna fuga.

## Lo que se encontró

- **Una fuga desde la v0.0.1 que nadie miraba.** El runner de `ogr-core` 0.2.0 comprueba, archivo
  a archivo, lo que un test deja cambiado en el proceso (regla 5). Al subir, nombró
  `tests/test_benchmark_v001.py`: deja `OMP_NUM_THREADS`, `OPENBLAS_NUM_THREADS` y
  `MKL_NUM_THREADS` en el entorno. Los ponía `poc/benchmark.py` al importarse
  (`os.environ.setdefault`), a propósito, para que NumPy cargara con un hilo; el test lo importa,
  y desde ese archivo todos los procesos que arrancaran los tests siguientes los heredaban. Hoy el
  único test que arranca procesos es el de la cuota de CPU, del mismo archivo, y su hijo importaba
  el benchmark él mismo: la fuga no rompía nada todavía. Se midió el 2026-11-18 sobre una copia
  (185 de 185 tests pasan contra el núcleo 0.2.0, desde su árbol y desde la etiqueta, y la corrida
  sale en rojo por la fuga).
  - **Salidas que se pesaron**: que el test repusiera el entorno (la importación seguiría cambiando
    el proceso y cualquier test futuro tendría que acordarse); declararlo en `allowed` (legitima lo
    que la regla 5 prohíbe: una corrida filtrada y la entera se comportarían distinto); que el
    módulo lo haga solo al ejecutarse. **El propietario eligió la tercera.**
  - **Un riesgo que el detector no puede ver**: si `poc.benchmark` hubiera sido lo primero que
    cargaba NumPy en el proceso de la suite, el BLAS de ese proceso habría quedado con un hilo el
    resto de la corrida; eso no está en el entorno ni se arregla reponiéndolo. Con la salida
    elegida desaparece.
  - El test de la cuota de CPU da ahora a su proceso hijo el entorno del benchmark de forma
    explícita (`env=` con `one_thread`), en lugar de depender de que importarlo lo cambie.
  - Tests nuevos (`TestOneThread`): importar el benchmark en un intérprete limpio no deja las tres
    variables; ejecutarlo como guion las tiene puestas **en el momento en que se pide `numpy`** (un
    buscador primero en `sys.meta_path` lo apunta; `--help` para antes de medir); un valor que ya
    estaba se respeta. Dientes: cuatro mutantes (importar lo pone como antes, sin llamada, llamada
    tras importar NumPy, pisar el valor del usuario), y mueren los cuatro.
- **El registro del benchmark puede no decir con cuántos hilos midió.** Su JSON guarda en
  `machine.threads` lo que dice el entorno **al llamar a `main()`**, no con lo que cargó NumPy.
  Antes de esta versión, si NumPy ya estaba cargado al importar el benchmark (una sesión
  interactiva), el registro decía `"1"` y el BLAS tenía los hilos de siempre. Desde esta versión,
  quien llame a `main()` desde Python sin pasar por el guion verá `null` en el JSON, pero el `.txt`
  y lo que se imprime no lo dicen. Lo que sí lo caza es la cuota de CPU: un cálculo que usa más de
  un hilo sale por encima de 1.05 y la medida se declara no válida. **Queda abierto** (regla 12);
  ver «Queda abierto».
- **`AGENTS.md` afirmaba algo que ya no era cierto**: que en el Python del sistema `ogr_core` es la
  copia de Slip2D. El 2026-11-18, desde una carpeta neutra, ese Python **no resuelve `ogr_core` a
  nada**: Slip2D está instalado en editable sobre su carpeta, y esa carpeta tiene desprotegida la
  rama `dev/adoptar-ogr-core`, que ya no lleva `ogr_core/`. En la fase 0 sí era la copia de Slip2D;
  dejó de serlo al cambiar la rama. La cabecera y el mensaje del runner ya no nombran una causa
  concreta, y un test nuevo comprueba que un Python sin núcleo se rechaza con el motivo y código 2,
  no con una traza (`test_a_python_without_the_core_is_refused`; mutante: dejar salir la
  excepción, y muere).
- **Un resto viejo en el Python del sistema**, sin relación con esto: `~gr_slip2d-0.1.204.dist-info`
  (25 de septiembre), una desinstalación a medias de Slip2D v0.1.204 que pip ignora. La instalación
  editable actual (0.1.471) está intacta. Se borrará a mano cuando se desinstale Slip2D de ese
  Python; no se ha tocado.
- **El `main` de OGR Slip2D no ha adoptado el núcleo** (local y remoto en `d48e2b3`, v0.1.471). La
  adopción (v0.1.472–0.1.473) está en `dev/adoptar-ogr-core`, verificada y solo en local. La
  documentación de este repositorio lo dice con esa salvedad.
- **La CI no probaba nada desde el 2 de noviembre.** GitHub retiró ese día las máquinas `macos-14`
  (aviso del 2026-10-01 en su changelog), y el job `build (macos-14)` moría en un segundo con «The
  configuration 'macos-14-arm64-us-default' is not supported». Como `test` y `freeze` esperan a
  todo `build`, se saltaban en los tres sistemas: el push de `e3d34ba` y el primero de esta versión
  (`ecc87b7`) salieron en rojo sin correr la suite. El workflow pasa a `macos-15` (Apple silicon,
  una versión fija como antes; `macos-latest` cambiaría de sistema sin avisar). Queda a la vista que
  un solo sistema caído deja a los otros dos sin probar; cambiarlo es otra decisión.
- **`rust/Cargo.toml` sigue en 0.0.2.** En la v0.0.2 se subió junto con la versión del programa,
  pero ningún test ata las dos, el motor no cambia y esta fase pide `rust/` intacto (cambiarlo
  obligaría además a recompilar el módulo, que un test compara con la fecha de sus fuentes).

## Pruebas

En la máquina de desarrollo (Windows, Python del `.venv`), el 2026-11-18:

| Qué | Resultado |
|---|---|
| Suite entera, sin argumentos | `shared: ogr_core 0.2.0  C:\Samuel\OGR_Suite\Core\OGR-Core\ogr_core  @ 9b72044`; **189 de 189**, código 0, **ninguna fuga** |
| Comparada test a test con la de `e3d34ba` y el núcleo 0.1.0 (`comparar_suites.py`) | 185 con el mismo resultado, **0 cambian**, 0 desaparecen; 4 nuevos, los cuatro pasan |
| `git diff e3d34ba -- validacion/ rust/` | vacío |
| Mutantes de `poc/benchmark.py` y de `tests/_runner.py` (uno a uno, restaurando el archivo) | 5 de 5 mueren |
| El código de antes (importar pone las variables) contra el runner 0.2.0 | el test nuevo falla, y el detector nombra las tres variables (`✗ [LEAK]`) |

**La CI** (run 44387274486, sobre `230d40f`): Windows, macOS 15 (Apple silicon) y Linux, con Python
3.11, 3.12 y 3.13, con la rueda y el núcleo instalados desde la etiqueta
(`shared: ogr_core 0.2.0 …/site-packages/ogr_core (installed, no git tree)`): **189 de 189 en las
nueve combinaciones, ninguna fuga**; el ejecutable congelado, en verde en los tres sistemas. Fuera de
Windows, el detector de fugas no nombra nada.

El núcleo 0.1.0 instalado se quitó del `.venv` y el de OGR-Core se instaló en editable con
`pip install --no-deps -e`, para que pip no reinstale el núcleo desde GitHub encima.

## Queda abierto

- **El benchmark llamado desde Python** (regla 12): que el registro guarde los hilos con los que
  cargó NumPy (leídos antes de importarlo) y que el informe y el veredicto lo digan cuando no son
  uno. Es un cambio de la herramienta de la spec 001; va aparte, con el OK del propietario.
- Que un sistema caído en `build` no deje a los otros dos sin probar (ver «Lo que se encontró»).
- Cuando Slip2D fusione su adopción: actualizar la frase de ADR-0002, `AGENTS.md`, `README.md` y
  `tech-stack.md` que dicen que aún no lo ha hecho.
