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

## T5 — de T3 a T6 (2026-11-22)

`ogr_fem2d/mesh/quadratic.py`: un nudo intermedio por lado, compartido por sus dos elementos; en el
centro de un lado recto y en el punto medio del arco en un lado que es un trozo de arco (D4), con el
orden de nudos de `element_t6` (Zienkiewicz y Taylor 2000, pág. 182, fig. 8.15b). Probado sobre
mallas T3 que ya existían: el rectángulo estructurado de la spec 002, el cuarto de corona de la spec
001 partido en T3 y el generador del núcleo en el cuadrado con hueco.

- **El área, por Arquímedes**: la malla T6, integrada con el propio elemento del motor
  (`element_t6.area`, exacta porque det J es de grado 2), es la malla recta más 2/3·cuerda·flecha
  por cada lado de contorno sobre un arco (sumado en el arco exterior, que se abomba hacia fuera, y
  restado en el del hueco, que se abomba hacia dentro), a 10⁻¹³. Y queda más cerca del cuarto de
  corona verdadero que la malla recta, más de diez veces.
- **Una cita sin comprobar en mi primer borrador del módulo** («§8.8.2») se cambió por la que usa
  `element_t6.py`, comprobada en la spec 001 (pág. 182, fig. 8.15b).

**Los tests**: `tests/test_mesh_quadratic_v008.py`, 6. **Dientes**: 8 mutaciones (radio, punto medio
de la cuerda en vez del arco, arco mayor, punto fuera del centro en un lado recto, nudos sin
compartir, orden de los intermedios y de las esquinas, lado con sentido): 8 de 8 cazadas.

## T6 — las comprobaciones de la malla (2026-11-22)

`ogr_fem2d/mesh/checks.py`: el jacobiano de cada elemento (RF-13) y la topología (RF-14): lados de
tres elementos y nudos colgantes, que impiden entregar la malla; piezas sin lados comunes y nudos que
unen abanicos de elementos (dos regiones unidas por un nudo), que son avisos; y la relación de Euler
V − E + T = C − H, que da los huecos del dominio.

- **La «mitad central» de Zienkiewicz y Taylor (2000, §9.2, fig. 9.6) es exactamente det J > 0 en las
  esquinas**: con el nudo intermedio de un lado recto a la fracción t, det J vale 2(4t − 1) y 2(3 − 4t)
  en las dos esquinas del triángulo de prueba (calculado a mano desde las funciones de forma de la
  pág. 182). El test acepta t = 0.26 y 0.74 y rechaza 0.25, 0.2, 0.75 y 0.8.
- **Anomalía, error propio del plan, corregido en esta tarea**: el plan decía que el jacobiano se
  comprobaba «en los seis nudos y en los puntos de integración» y que una garantía en todo el elemento
  no se afirmaba. **No basta**: una búsqueda al azar encontró en 148 intentos un T6 con det J > 0 en
  sus seis nudos (mínimo 0.167) y −0.055 en un punto interior de la regla de 7 puntos. En axisimetría
  se habría rechazado; en deformación plana no, porque allí los puntos de integración del T6 son sus
  nudos intermedios, y el motor lo habría calculado con determinantes positivos en todos los puntos
  que mira, con el elemento plegado. RF-13 de la spec pide el signo en todo el elemento. El arreglo
  no necesita fuente nueva: det J es un polinomio de grado 2, la interpolación cuadrática por los
  seis nudos lo reproduce exacto, y su mínimo sobre el triángulo está en un vértice, en el extremo de
  la parábola de un lado o en el punto estacionario interior (un sistema lineal de 2 × 2). Se hizo
  sin preguntar porque la propietaria pidió seguir hasta el final y el cambio solo endurece la
  comprobación hacia lo que pide la spec; queda enmendada la fila del plan. **Para revisar.**
- El mínimo exacto se comprueba contra un barrido de det J con el jacobiano del motor en 45 451
  puntos del triángulo, en el elemento plegado, en uno con el mínimo en el interior (encontrado al
  azar), en dos rectos y en cinco del cuarto de corona curvo.

**Los tests**: `tests/test_mesh_checks_v008.py`, 13. **Dientes**: 17 mutaciones. Sobrevivían tres:

- la lista de lados de contorno no la miraba ningún test: se añadió la comparación con el perímetro
  del rectángulo, sacado de la geometría;
- quitar el punto estacionario interior o equivocar su fórmula: ningún caso tenía el mínimo dentro;
  se añadió uno.

Al final, 17 de 17.

## Pruebas

| Corrida | Resultado |
|---|---|
| T3, suite entera contra la etiqueta instalada (`shared: ogr_core 0.2.3 … (installed, no git tree)`) | **224 de 224** (205 de antes y 19 nuevos), código 0, ninguna fuga |
| T4, la misma | **239 de 239** (15 nuevos), código 0, ninguna fuga |
| T5, la misma | **245 de 245** (6 nuevos), código 0, ninguna fuga |
| T6, la misma | **258 de 258** (13 nuevos), código 0, ninguna fuga |
