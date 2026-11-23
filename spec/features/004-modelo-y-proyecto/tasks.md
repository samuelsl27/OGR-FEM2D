# Tareas — Spec 004, modelo FEM y proyecto `.ogrfem2d`

Pequeñas y verificables, ordenadas por dependencia. Al terminar cada una:
- este archivo y el changelog, al día;
- la suite entera en verde (`.venv/Scripts/python tests/_runner.py`);
- el commit directo en `main`, sin push hasta que la propietaria lo pida.

Cada test lleva su cabecera y tiene dientes: mutaciones sistemáticas
(`{etiqueta: (archivo, texto, sustituto)}`), anotadas aquí.

## Antes de programar

- [x] T0. **Spec, plan y tareas aprobados**, con D1–D16. Va en un commit propio.
  - El ADR-0004 (`docs/decisiones/ADR-0004-formato-ogrfem2d.md`): formato propio, apertura del `.ogr`
    de Slip2D, malla dentro del archivo, y su coste en tamaño.
  - `AGENTS.md` («Stack», la línea del formato), ADR-0003, `tech-stack.md` y `plan_de_desarrollo.md`,
    corregidos donde nombran el `.ogr` de este programa.

  *Hecho cuando:* la propietaria ha dado el OK, y las decisiones están anotadas como aprobadas en
  `spec.md` y `plan.md`. (Hecho el 2026-11-23: OK de la propietaria a D1–D16; ADR-0004 escrito;
  corregidos `AGENTS.md`, que además dice en su presentación que cada programa tiene su formato,
  ADR-0003, `tech-stack.md`, `plan_de_desarrollo.md` y `validacion/README.md`.)

## El modelo y sus piezas

- [x] T1. **v0.0.9**, `model/model.py` y `docs/modelo/formato.md` — RF-1, 3, 5 y 6.
  - Las dataclasses congeladas del modelo y `validate()`, con `Problem` (regla, sitio, por qué), que
    reúne todos los problemas a la vez, como el motor.
  - El sistema de unidades, de la lista del núcleo; uno desconocido, error (D5).
  - x < 0 en axisimetría, arcos incluidos.
  - La versión pasa a 0.0.9 en `pyproject.toml` y en `ogr_fem2d.__version__`, y empieza
    `CHANGELOG_v0.0.9.md`.

  *Hecho cuando:* cada regla tiene su test con un modelo que la incumple, y el error dice el sitio.
  (Hecho el 2026-11-23: 17 reglas, `tests/test_model_input_v009.py`, 17 tests; 27 mutaciones, 27
  cazadas tras añadir tres tests. Hallazgo de D10: la asignación lleva un material por región y una
  bandera de excavada por fase, changelog.)
- [x] T2. `model/regions.py`: de los contornos a las regiones (D15) — RF-1.
  - Puntos y segmentos sin repetir, con las reglas de cruce de `mesh/geometry`.
  - Las caras del grafo plano, con los arcos por su tangente, y los huecos por anidamiento.
  - El orden canónico del plan.
  - Los errores: un corte fuera de los vértices, un extremo suelto, ningún externo o dos, el mismo
    segmento con arcos distintos, y una región sin asignar o con dos asignaciones.

  *Hecho cuando:* Σ áreas = área del externo y Euler cuadra en los modelos de prueba (estratos, túnel
  con arcos, fase abierta, hueco suelto, dos arcos tangentes), y cada error nombra su contorno.
  (Hecho el 2026-11-23: 15 tests, seis modelos; 18 mutaciones, 18 cazadas. **Hallazgo corregido**:
  el cero negativo de una tangente ordenaba mal los lados en un vértice, changelog.)
- [x] T3. `model/stages.py`: fases con id estable (D10) — RF-3 y RF-4.
  - Insertar, que copia la fase anterior, o la primera si se inserta delante de ella; borrar;
    renombrar.
  - Asignar con propagación o con «solo esta fase».
  - La tabla región × fase, explícita.

  *Hecho cuando:* cada operación tiene su test, y reactivar una excavada o cambiar el material entre
  fases se rechaza con su motivo.
  (Hecho el 2026-11-23: 15 tests; 12 mutaciones, 12 cazadas, y una comprobación redundante quitada.)
- [x] T4. `model/conventions.py` y `model/field.py`: el único cambio de signo (D6), la tensión de
  campo constante y gravitatoria con estratos (D14), y los cuatro modos de carga inicial (D11) —
  RF-7 y RF-8.

  *Hecho cuando:*
  - una compresión de campo llega al motor negativa;
  - con superficie horizontal y «tensión de campo y peso propio», el desplazamiento es nulo;
  - los cuatro modos dan cuatro resultados distintos (regla 7);
  - en axisimetría, K ≠ Kz y σr ≠ σθ dan el error de la spec 002.

  (Hecho el 2026-11-23: 10 tests; 8 mutaciones, 8 cazadas. **Hallazgo corregido, para revisar**: un
  punto sobre el fondo de un estrato tomaba el K del de arriba; ahora, el del estrato de su elemento,
  changelog.)
- [ ] T5. `model/conditions.py`: de las condiciones a nudos (D16) — RF-9.
  - El defecto del externo, explícito.
  - La precedencia vértice, segmento, defecto, y la unión en los nudos compartidos.
  - Las liberaciones.
  - Los impuestos con su factor por fase, en totales.
  - La activación por fase.

  *Hecho cuando:* liberar un segmento no suelta la esquina del vecino, el vértice manda, y dos
  impuestos en conflicto dan un error que los nombra a los dos.
- [ ] T6. `model/loads.py`: de las cargas a `EdgeLoad` y `NodalLoad` — RF-10.
  - Cargas repartidas lineales sobre un tramo de varios segmentos, con cada orientación de
    `LoadOrientation`.
  - Cargas puntuales en un vértice.
  - El factor por fase (0 = ausente).
  - En axisimetría, el anillo entero.

  *Hecho cuando:*
  - la resultante y el momento de una carga lineal sobre varios segmentos son exactos;
  - cada orientación mueve el número;
  - una carga sobre un contacto entre dos regiones activas se rechaza, nombrando la carga, el
    contorno y la fase.

## La traducción, el archivo, la huella y el deshacer

- [ ] T7. `model/translate.py`, `to_mesh_input` y `mesh` — RF-11 y RF-12.
  - En el `MeshInput`, la región como etiqueta de material (D3).
  - La procedencia de cada punto, segmento y región.
  - Los errores del mallador, reescritos con el contorno o la región.
  - La malla, con la huella de su entrada.

  *Hecho cuando:* dos traducciones del mismo modelo dan lo mismo bit a bit, y cada error del mallador
  llega con el nombre del objeto del modelo.
- [ ] T8. `translate.to_engine` — RF-11 y RF-12.
  - El material de cada elemento por fase, según la tabla.
  - Las tensiones iniciales, las condiciones y las cargas.
  - La malla de otro modelo, rechazada.
  - Los errores del motor, con la región, el material o la fase.

  *Hecho cuando:*
  - mover un vértice o cambiar un ajuste de malla deja la malla como de otro modelo, y se rechaza;
  - cambiar un material no la invalida;
  - el mismo modelo da la misma entrada del motor bit a bit.
- [ ] T9. `model/ogr_file.py`: el `.ogrfem2d` — RF-13.
  - Las secciones del plan, con la malla un nudo y un elemento por línea.
  - `format`, `format_version` y `written_by`.
  - La comprobación de la forma, sección a sección.

  *Hecho cuando:*
  - la ida y vuelta da el mismo modelo y los mismos bytes;
  - una versión posterior, una clave desconocida y un tipo erróneo dan su error, que los nombra;
  - `docs/modelo/formato.md` está completo.
- [ ] T10. `model/fingerprint.py`: la huella del modelo y la del documento (D12) — RF-16.

  *Hecho cuando:* la tabla de mutaciones pasa: cada dato que mueve el resultado, malla incluida,
  cambia la huella del modelo; el nombre, el color, el resumen y el sistema de unidades, no; la del
  documento cambia con todo.
- [ ] T11. `model/history.py`: el documento y la orden «antes / después» sobre el `CommandStack` del
  núcleo — RF-15.

  *Hecho cuando:* una secuencia de ediciones, deshecha entera y rehecha, da modelos idénticos (`==` y
  la misma huella), y deshacer sin nada que deshacer no hace nada.

## Abrir otros formatos

- [ ] T12. `model/import_slip2d.py`: un `.ogr` de Slip2D a modelo, por `Project.load` del núcleo
  fijado (D16) — RF-14.
  - Lo que se trae: el externo y los de material, las asignaciones, los materiales (nombre, color y
    γ, sin E ni ν), y las cargas repartidas y puntuales, con vértices insertados.
  - Las restricciones: laterales y fondo fijos, superficie libre.
  - El informe: lo que no se trae, los vértices insertados y lo que se ha puesto por defecto.

  *Hecho cuando:* sobre un `Project` creado en el test con la API del núcleo, las regiones y las
  áreas son las de `build_regions` a redondeo, el informe es completo y el modelo no se traduce al
  motor hasta tener E y ν.
- [ ] T13. `model/import_dxf.py`: un DXF a contornos, con el lector del núcleo y el mapa de capas a
  los cuatro tipos (D13) — RF-14.

  *Hecho cuando:* un DXF escrito en el test con las cuatro capas y un arco da los contornos y el aviso
  del arco aplanado.
- [ ] T13b. **La petición al núcleo**: que el lector DXF conserve los arcos (ARC, CIRCLE y bulge) como
  arcos.

  *Hecho cuando:* el escrito está en `Promts_desarrollo/` y la propietaria sabe que no bloquea nada.

## Identidades y casos

- [ ] T14. Las identidades de principio a fin.
  - Unidades: tensiones ×1000 dan desplazamientos iguales y tensiones proporcionales.
  - Signos: una presión normal positiva sobre un contorno exterior y sobre uno de excavación, hacia el
    terreno.

  *Hecho cuando:* las dos están en verde y tienen dientes.
- [ ] T15. **Caso 005 con `modelo.ogrfem2d`** (D4).
  - El modelo del caso, con su malla guardada.
  - Un test que comprueba cuatro cosas:
    - el `MeshInput` es el de `tests/_kirsch_mesh.py`;
    - la malla guardada es la de `mesher.mesh`, bit a bit;
    - la entrada del motor es la hecha a mano en kPa, salvo los ajustes del solver, que en elástico no
      actúan;
    - el caso cumple su 0.5 %.

  *Hecho cuando:* las cuatro se cumplen, el tamaño del archivo está anotado en el changelog, y la
  ficha STR-01 tiene su «Seguimiento».
- [ ] T16. **Caso 006, STR-04 con malla general** (D4).
  - `caso.md` y `esperado.json` **con la tolerancia antes de medir** y la malla a `null`. La
    tolerancia es la del caso 004 (0.01 q, absoluta, desde z = 0.25 m), en el mismo dominio de 200 ×
    200 m del medio modelo.
  - El modelo: la faja como tramo de contorno con su carga, el eje y el lateral con restricción en X,
    y el fondo fijo.
  - El estudio de convergencia, y la malla que fija la tolerancia.

  *Hecho cuando:* el caso cumple con la malla del estudio, y la ficha STR-04 tiene su «Seguimiento».
- [ ] T17. **Caso 007, STR-09 en axisimetría con malla general** (D4).
  - `caso.md` y `esperado.json` **con la tolerancia antes de medir**, la del caso 003 (0.5 %).
  - La cavidad de radio a en el eje, en dos arcos de 90°, y el contorno esférico fijo a 21 m.
  - El campo hidrostático de 10 MPa.
  - El estudio de convergencia, y la malla que fija la tolerancia.

  *Hecho cuando:* el caso cumple en σt y u_R(a) con la malla del estudio, y la ficha STR-09 tiene su
  «Seguimiento».

## El cierre

- [ ] T18. El barrido de las reglas 7 y 12: una tabla de cada ajuste nuevo del modelo con el test que
  demuestra que mueve el número, y los valores por defecto que cambian el resultado, listables desde
  el modelo.

  *Hecho cuando:* la tabla está en el changelog y no le falta ningún ajuste.
- [ ] T19. El cierre.
  - Cada fórmula de «Formulación», citada en el código.
  - Los casos 001 a 004, bit a bit.
  - `CHANGELOG_v0.0.9.md`, completo.
  - Avisar a la propietaria de dos cosas: la nota para Slip2D (abrir un `.ogrfem2d` es cosa de su
    sesión) y lo que la 005, la 006 y la 012 tienen que reevaluar de esta spec.

  *Hecho cuando:* todos los criterios de finalización de `spec.md` están marcados.
