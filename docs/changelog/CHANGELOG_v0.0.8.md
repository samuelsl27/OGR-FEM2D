# OGR FEM2D v0.0.8 (en curso)

**Fase 1, segunda parte: la malla** (spec 003). Este archivo cuenta lo que va entrando, tarea a
tarea; se cierra con la T17.

## La spec, el plan y las tareas (2026-11-22)

Aprobados con D1–D13 tal como se propusieron (`spec/features/003-malla/`). Lo que se encontró al
escribirlos:

- **El generador del núcleo no cumple su propio suelo de calidad.** `ogr_core.fem.generate_mesh`
  (igual en v0.2.2, v0.2.3 y `main`), en un cuadrado de 20 m con un hueco circular de 40 lados, da un
  ángulo mínimo de 4.9° con h = 1 m y de 6.8° con h = 2 m, frente al suelo de 25° que se pone. La
  causa: solo subdivide los contornos y no gradúa. Área, conformidad y respeto de los contornos, bien.
  Va como nota en la petición a OGR-Core (D2).
- **No había fuente de mallado ni de calidad en la bibliografía.** Se consiguieron, en copias libres
  de los autores, Shewchuk (2002a, refinamiento de Delaunay), Shewchuk (2002b, medidas de calidad) y
  Ruppert (1995); Babuška y Aziz (1976) y Zlámal (1968), no. Zienkiewicz y Taylor (2000) da el
  criterio del elemento curvo (§9.2) y el teorema 3 de la parcela isoparamétrica (§9.7). Índice en
  `Referencias/Bibliografia/00_LEEME.md`.
- **El texto que sacan de estos PDF las herramientas pierde los símbolos matemáticos**: las fórmulas
  se leyeron sobre la página renderizada.
- **Error propio en la spec, reportado y enmendado (RF-5)**: el borrador decía que la graduación de la
  malla graduada tenía fuente con la cota por defecto B = √2. El teorema 8 de Shewchuk (2002a, pág. 23)
  exige B > √2 estrictamente; con √2 quedan el ángulo de 20.7° y la terminación, y la graduación se
  mide.
- **D13**: un arco entra al refinado como cadena de cuerdas, y un vértice que el refinado añada sobre
  una cuerda no caería sobre el arco. Se llevará al arco y se comprobará el jacobiano.

## T3 — la entrada del mallador (2026-11-22)

`ogr_fem2d/mesh/geometry.py` (paquete nuevo `ogr_fem2d/mesh`, fuera del motor) y
`docs/malla/entrada.md`: puntos compartidos por índice, regiones con contorno antihorario y huecos
horarios, atributos por segmento (arco por su centro, divisiones forzadas, excavación) y los ajustes
(graduada o uniforme, T3 o T6, cota B, tamaños y ventanas). 25 reglas de validación, todas a la vez,
cada una con su sitio. Lo que se deriva de una entrada válida: los segmentos en orden estable, los
que reciben los nudos de la malla graduada y el área exacta de cada región.

Lo que se encontró:

- **El validador cazó dos geometrías mías mal hechas al escribir los tests**: un talud de dos capas
  con el vértice (25, 10) en mitad del contacto sin compartirlo (una unión en T), y un «gajo» con el
  arco casi en semicírculo cuyos lados rectos, tangentes en los extremos, volvían a cortar el arco. Las
  dos eran errores de los datos de prueba y el validador tenía razón; se corrigieron los datos.
- **Un ajuste que no hace nada se rechaza (regla 7)**: un tamaño uniforme en una malla graduada, los
  nudos de la graduada en una uniforme, o `boundary_nodes` cuando todos los segmentos que los
  recibirían tienen sus divisiones forzadas.
- **Los arcos cuentan en «dentro» y en el área**: el número de vueltas de las cuerdas se corrige con
  ±1 por cada segmento circular que contiene el punto, y el área con ±R²/2 (θ − sen θ). Un punto entre
  un arco que entra en la región y su cuerda queda fuera.

**Los tests**: `tests/test_mesh_input_v008.py`, 19. **Dientes**: 36 mutaciones, de una en una y
restaurando el archivo: cada una de las 25 reglas apagada y once más (signo del arco en el número de
vueltas y en el área, lado del arco menor, sentido de los segmentos compartidos, saltarse los lados
propios en el solape, unión en T, B > en vez de ≥, preferencia de la excavación en la graduada, el
arco que llega al eje, el hueco fuera del contorno, excluir los extremos del arco). Al principio
sobrevivían dos:

- excluir los extremos del arco por distancia era **redundante**: la prueba del lado de la cuerda ya
  los excluye. Se quitó esa comprobación en vez de inventarle un test;
- quitar la comprobación del **sentido** de un segmento compartido no la cazaba nada, porque el caso
  de la tabla usaba tres anillos; con una región duplicada (dos anillos, mismo sentido) habría pasado
  sin aviso, ya que el test de solape salta los lados compartidos. Test nuevo:
  `test_a_region_given_twice`.

Con eso, 35 de 35 cazadas.

- **Error propio de herramienta, después del commit `da29d0d`**: el guion de las mutaciones restauraba
  el archivo con `Path.write_text`, que en Windows escribe CRLF, y `geometry.py` quedó en CRLF en la
  copia de trabajo (el commit va en LF, por `.gitattributes`). Se rehízo la copia desde git y el
  guion pasa a leer y escribir bytes. Es lo mismo que la v0.0.4 vio con otros guiones.

## T4 — el paso 1, la discretización de los contornos (2026-11-22)

`ogr_fem2d/mesh/discretize.py`: los nudos de cada segmento. Divisiones forzadas, las que son; en la
graduada, `boundary_nodes` repartidas por longitud con al menos una por segmento y suma exacta (el
método del mayor resto, empates al primero), y los demás segmentos con sus extremos; en la uniforme,
⌈L/h⌉, con h dada o la de N triángulos equiláteros. Los arcos, a ángulos iguales del arco menor y
sobre la circunferencia; los nudos nuevos, después de los de la entrada, en orden estable.

Lo que se encontró:

- **Una expectativa mía equivocada en un test**: pedía que el reparto quedara a menos de una división
  del ideal en todos los segmentos. Con pocas divisiones y segmentos diminutos el mínimo de una por
  segmento lo impide (8 divisiones dejan 3 a los dos segmentos largos, cuyo ideal suma 6). El test
  pide ahora suma exacta, al menos una, más divisiones al más largo, y la cota de una solo donde el
  mínimo no pesa. **Y esa rama no se ejecutaba nunca** con las longitudes del test (un segmento de
  0.01 la deja fuera hasta un total de 1651): se añadió otra lista de longitudes y un recuento que
  falla si la comprobación no corre.
- **Un test circular**: la cota «ningún trozo pasa de h» se comprobaba con la propia
  `segment_length`. Ahora las longitudes salen de la geometría (π/2 para el cuarto de circunferencia
  de radio 1), y un test comprueba que el arco se mide por el arco y no por la cuerda (con h = 1.5,
  π/2 da dos divisiones y la cuerda √2, una).

**Los tests**: `tests/test_mesh_discretize_v008.py`, 15. **Dientes**: 18 mutaciones. Al principio
sobrevivían cuatro:

- tomar el techo o redondear L/h no se distinguían en el túnel: se añadió el talud con h = 3
  (40/3 = 13.3: 14 divisiones, no 13);
- olvidar las divisiones forzadas en la uniforme: no había test;
- medir el arco por la cuerda: el test era circular (arriba);
- redondear en vez de truncar en el reparto: se comparó por fuerza bruta (120 000 repartos) y solo
  difiere en los desempates, que la variante da al último; se añadió el caso [5, 5, 1, 4] con 5 y 8
  divisiones.

Al final, 18 de 18 cazadas.

## Pruebas

| Corrida | Resultado |
|---|---|
| T3, suite entera contra la etiqueta instalada (`shared: ogr_core 0.2.3 … (installed, no git tree)`) | **224 de 224** (205 de antes y 19 nuevos), código 0, ninguna fuga |
| T4, la misma | **239 de 239** (15 nuevos), código 0, ninguna fuga |
