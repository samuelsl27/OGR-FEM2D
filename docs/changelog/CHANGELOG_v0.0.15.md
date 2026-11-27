# OGR FEM2D v0.0.15

**Fase 1, octava parte: el cálculo y la interpretación en la interfaz** (spec 006, parte D). Sobre
las operaciones de la parte B y el modelador de la parte C, en la rama corta `dev/modelador`. Este
archivo cuenta lo que fue entrando, tarea a tarea.

## T30 — la ventana de cálculo (2026-11-27)

`ogr_fem2d/gui/compute_window.py`; Análisis > Calcular (F9) y Ventana > Cálculo (RF-9 a RF-12, RF-18;
D9; la guía, §4, §5 y §14).

- **La ventana va al lado del modelo, no delante**: el cálculo corre en el proceso hijo de
  `analysis_run`, así que la ventana del modelo sigue viva mientras tanto. La de cálculo lo sigue
  preguntando a `job_get` cada 100 ms. Medido con el modelo de tres fases de los tests: la ventana no
  se para nunca más de 0,25 s (lo vigila un test).
- **La cola** es la lista de trabajos del espacio de trabajo (`job_list`), con su modelo, su tipo
  (cálculo o mallado), su estado y su tiempo; el elegido es el que se sigue. **El núcleo corre un
  trabajo cada vez**: un segundo cálculo con otro en marcha se rechaza con su motivo (`Busy`), no se
  encola. Una cola que espera y arranca sola tomaría el modelo al arrancar, no al pedirlo, y eso es
  otra decisión; queda anotado por si se quiere.
- **El progreso**: la fase (de cuántas, con su nombre) y, de una fase resuelta, sus escalones y su
  última iteración (D9: en elasticidad, un escalón de una iteración).
- **Cancelar sigue D9**: entre dos fases dentro del plazo (las fases resueltas quedan escritas y los
  resultados dicen `cancelled`), o matando el árbol del proceso. El plazo (5 s) se espera fuera del
  hilo de la ventana, para que no se congele: Cancelar vuelve enseguida (un test lo mide, < 0,5 s).
- **El registro** dice cada fase al empezar y al terminar, y se guarda para cada trabajo de la sesión
  (RF-11). **Hallazgo**: el progreso se lee, no se escucha, y una fase que empieza y termina entre dos
  lecturas no se ve. El registro la escribe igual, con lo que se sabe de ella (resuelta); las que sí
  se ven llevan sus escalones e iteración. Un test comprueba que cada fase sale una vez, ni más ni
  menos.
- **El resumen al terminar** (guía §5), también en la barra de estado: lo resuelto y dónde está
  escrito; de una fase que no se pudo resolver, **cuál, por su número y su nombre, y lo que dijo el
  motor** (RF-11); de una cancelación, lo que quedó. El botón «ir a los resultados» llega con la
  interpretación (T31).
- **Un rechazo antes de empezar nombra el objeto**: «No calculado: material 'rock': Un material no
  tiene E o ν, que el cálculo necesita: Propiedades > Definir materiales.» Las reglas `mesh_stale` y
  `material_incomplete` de `to_engine` tienen ahora su frase en `gui/problems.py`.
- **Calcular solo se ofrece con la malla del modelo**, y si no, dice por qué (sin malla, o malla de
  otra geometría). **Un modelo sin guardar se guarda antes, si la persona lo dice**: los resultados se
  escriben junto al archivo, con su huella (diálogo «Guardar y calcular»).
- **Cerrar con un cálculo en marcha pregunta una vez** y, con un sí, lo para de verdad (sin plazo:
  el programa se va). Las dos preguntas (el cálculo y los cambios sin guardar) se hacen antes de
  hacer nada, para que un Cancelar deje todo como estaba.
- La versión pasa a 0.0.15.

- **Una ventana sobre una sesión que no es suya** (la de un agente, D8) no la apaga al cerrar: por eso
  para el cálculo ella misma. Lo encontró el barrido de mutaciones: con la sesión propia, el apagado
  del espacio de trabajo ya lo mataba, y quitar la parada no rompía ningún test.

Tests: `test_gui_compute_v0015.py`, 9 tests. Regla 7, 17 mutaciones (el hueco del registro, el
detalle de una fase, el plazo de Cancelar y su hilo, el botón, el resumen con su fase y las palabras
del motor, la pregunta y la parada al cerrar, la puerta de Calcular, guardar antes, el rechazo con su
objeto, el resumen en la barra de estado, la frase de la regla): todas cazadas, una después de añadir
el test de la sesión compartida.
