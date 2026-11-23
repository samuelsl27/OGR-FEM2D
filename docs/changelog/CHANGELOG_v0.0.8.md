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

## T7 — la prueba de la parcela con mallas generadas (2026-11-22)

`tests/test_mesh_patch_v008.py`: con el desplazamiento de un campo lineal impuesto en los nudos del
contorno (esquinas y nudos intermedios), el motor da ese campo en todos los nudos interiores a 10⁻¹⁰ y
la tensión de Hooke, constante, en todos los puntos de integración a 10⁻⁹ (Zienkiewicz y Taylor 2000,
§9.7, teorema 3, y §5.2.2 en axisimetría). En deformación plana, con T3 del generador del núcleo en el
cuadrado con el hueco y con esos T6 curvos sobre el círculo; en axisimetría, con el cuarto de corona
del generador, T3 y T6 curvos, con nudos sobre el eje.

- **Un error de mis datos de prueba**: el vértice «sobre el eje» salía de cos(π/2) = 6·10⁻¹⁷, no de 0.
  Se fijan los extremos exactos.
- **Lo que esta prueba no puede ver, por su propia fuente**: un nudo intermedio desplazado a lo largo
  de su lado (el teorema 3 vale para cualquier posición). Eso lo ven la T5 (posición) y la T6
  (jacobiano). Sí ve nudos intermedios sin compartir y en lados equivocados: 3 mutaciones de
  `quadratic.py` corridas contra estos tests, 3 cazadas.

## T9 — la salida del mallador y su paso al motor (2026-11-22)

Se hace antes que la T8 porque la malla radial entrega su resultado con esta salida.
`ogr_fem2d/mesh/mesher.py`: `Mesh` (nudos, elementos, región y material de cada elemento, contornos,
notas, avisos), `boundary_map` (para cada tramo de un contorno, los elementos y el lado que lo tienen,
con la convención de `EdgeLoad.side`, y su nudo intermedio; rechaza un tramo que no es lado, RF-3) y
`to_engine` (el `EngineModel`, validado por el motor). Documentado en `docs/malla/entrada.md`.

- **El mapa sirve para poner cargas**: una presión uniforme en el hueco, puesta en los lados de la roca
  que da el mapa y con la excavación desactivada, es un contorno cerrado: las reacciones suman cero a
  10⁻⁹ y la pared se mueve hacia fuera, con T3 y con T6.
- **Un punto débil de mis datos, visto antes de las mutaciones**: la región y el material coincidían
  (0 y 1), y confundir uno con otro en `to_engine` habría pasado. En el test la roca es ahora región 0
  y material 1.

**Los tests**: `tests/test_mesh_output_v008.py`, 5. **Dientes**: 6 mutaciones (un solo elemento por
tramo, el nudo intermedio del lado siguiente, el lado mal numerado, aceptar un tramo que no es lado,
no validar, material = región): 6 de 6 cazadas.

## T8 — la malla radial (2026-11-22)

`ogr_fem2d/mesh/radial.py`: el anillo completo a ≤ r ≤ b alrededor de un hueco circular (D8), con
la progresión de radios de `engine/mesh_radial.graded_radii`, n_theta ángulos iguales (al menos 3,
para que cada arco sea de menos de 180°), cada celda partida por la misma diagonal, los nudos sobre
los ejes exactos y, en T6, los lados de r constante sobre su circunferencia (`quadratic.promote`).
Entrega la salida común (`Mesh`) con los contornos «hole» y «outer».

- **Decisión de detalle dentro de D8**: el hueco no se malla. El dominio es el anillo y la excavación
  entra como en el caso 001, por la tensión inicial de los elementos que quedan (ec. 2.13b). Mallar el
  círculo con una rejilla polar pondría en su centro un abanico de triángulos degenerados, y la malla
  radial del programa de referencia es para verificar. Es solo de deformación plana: alrededor de un
  centro, el anillo pasa por x < 0.
- **El anillo contra su solución exacta**: excavar un hueco de 1 m con 30 MPa hidrostáticos (STR-01),
  hasta b = 100 m con el exterior fijo, frente a `lame_fixed_outer` (spec 001; Jaeger, Cook y
  Zimmerman 2007, ecs. 8.78–8.81). Con la densidad de la malla que fija el caso 001 (8 divisiones
  angulares por cuadrante, 32 radiales, crecimiento 1.69^¼): **0.020 % en ur(a) y 0.159 % en σθ(a)**,
  el peor punto (tolerancia 0.5 %); con 64 × 64, 0.002 % y 0.042 % (σθ baja unas cuatro veces).
- **Con pocos ángulos, los T6 se pliegan**: con 4 divisiones del hueco (arcos de 90°), la flecha del
  arco, R(1 − cos 45°), es mayor que el ancho de su anillo de elementos; el lado curvo cruza el
  triángulo y det J cambia de signo. La comprobación de la T6 lo rechaza con su motivo (con T3, que
  usa cuerdas, no pasa nada). Lo encontró un test mío con 6 × 2, que se cambió a 12 × 2; el rechazo
  queda fijado en su propio test.

**Los tests**: `tests/test_mesh_radial_v008.py`, 8. **Dientes**: 10 mutaciones (crecimiento olvidado,
diagonal invertida, arcos sin marcar, ejes no exactos, el contorno exterior en el anillo anterior,
n_theta mínimo 2, cada regla apagada, material olvidado). Sobrevivían dos: el material, que ningún
test ponía distinto de 0 (test añadido), y «arcos sin marcar», que era una mutación mía que no
cambiaba nada (`{} or {…}` vale el segundo); rehecha, cazada. Al final, 10 de 10.

## T10 — Kirsch con campo no hidrostático (2026-11-22)

`spec/features/003-malla/comprobaciones/soluciones_cerradas.py`: las tensiones de Kirsch
(Jaeger, Cook y Zimmerman 2007, ecs. 8.113–8.115, pág. 219) y el desplazamiento que causa la
excavación: el de las ecs. (8.121)–(8.125), págs. 220–221, menos el del medio sin hueco (A = B = C =
0 en la 8.122, derivación propia), con σ2 girando 90°; y su paso al convenio del motor. Es el lado
externo de la identidad del caso 005. `tests/_kirsch.py` lo carga por su ruta con un nombre propio,
como `_sphere.py`.

- **Las dos partes de la fuente se comprueban una contra otra**: las deformaciones del desplazamiento
  (diferencias centradas, deformaciones en polares), por la ley de Hooke en deformación plana, dan el
  cambio de tensión de las (8.113)–(8.115) a 10⁻⁶ de la escala, con campos uniaxial, biaxial,
  invertido y con una tracción. Eso fija los signos de u_r y de u_θ (la fuente cuenta los
  desplazamientos positivos hacia −r y −θ) y la resta del campo sin hueco. Con σ1 = σ2 da la (8.90)
  de la spec 001 a 10⁻¹⁴.
- Girar σ2 con θ − π/2 en vez de θ + π/2 sería una mutación equivalente (las funciones de 2θ no lo
  distinguen); por eso la mutación del giro usa 45°.

**Los tests**: `tests/test_kirsch_closed_v008.py`, 5. **Dientes**: 8 mutaciones (signo de u_θ, κ + 1
por κ − 1, sin restar el campo sin hueco, σ2 girado 45°, 8G por 4G, un coeficiente de la 8.113, el
convenio del motor de dos maneras): 8 de 8 cazadas.

## T11, T12 y T15, la parte que no espera al núcleo (2026-11-22)

Lo que queda de la spec usa el mallador de calidad pedido a OGR-Core (D2), que no existe todavía. Se
hizo lo que es de FEM2D y no depende de la API que decida su sesión:

- `ogr_fem2d/mesh/sizing.py` (T11): la cota de tamaño según la posición (Shewchuk 2002a, pág. 11), la
  menor de las que cubren el punto: la global (h de la uniforme, la cota máxima de la graduada o
  ninguna) y la de cada ventana o polígono que lo contiene, borde incluido. Probada como función;
  comprobarla sobre la malla espera al núcleo.
- `ogr_fem2d/mesh/pslg.py` (T12; un archivo que el plan no tenía, separado de `mesher.py`): el PSLG
  que recibirá el núcleo (los nudos del paso 1, las piezas entre nudos consecutivos etiquetadas con su
  segmento, una semilla estrictamente dentro de cada región con su material, un punto en cada vacío)
  y la proyección de D13.
  - **Las semillas, sin dependencias nuevas**: Shapely está en el `.venv` solo como dependencia de
    `ogr-core`, y usarla aquí sería añadir una. A lo largo de líneas horizontales a media altura entre
    vértices, el tramo interior más ancho (cortes par-impar), su punto medio, comprobado después con el
    número de vueltas exacto. Probado en la roca, la excavación, dos capas, un cuadrado mordido por un
    arco y una lámina mil veces más larga que gruesa.
  - **Hallazgo (D14, abierta en la spec)**: llevar al arco los vértices que el mallador deja sobre una
    cuerda puede **invertir elementos**. Medido con el generador actual del núcleo (que también pone
    nudos sobre las cuerdas) en un cuadrado con un hueco de 8 a 32 cuerdas y h de 0.05 a 0.2: hay
    elementos invertidos, T3 y T6, cuando la flecha de la cuerda pasa de unas 0.7 veces h (8 cuerdas
    con h = 0.1: 16 elementos; con h = 0.05: 152), y ninguno hasta 0.38. RF-13 rechaza esa malla con
    su motivo, así que no hay malla mala silenciosa; qué hacer para que no pase lo decide la
    propietaria (D14). El plan lo tenía en «Riesgos» («si pasa, es un hallazgo y se para»).
  - Dos errores de mis datos de prueba por el camino: los vértices del octógono redondeados a 15
    decimales se apartaban del círculo 5·10⁻¹⁶ (se construyen con los ceros de los ejes exactos y sin
    redondear lo demás).
- `validacion/casos/005-kirsch-malla-general/` (T15): `caso.md` y `esperado.json` con las tolerancias
  de D12 **escritas antes de medir** y la malla a `null`, como el caso 001. El caso queda en `PENDING`
  de `test_validation_cases_v001.py`, con su motivo, como pide ese test para que ningún caso falte
  sin decirlo.

**Los tests**: `tests/test_mesh_pslg_v008.py`, 8 (PSLG, semillas, vacíos, D13 y la cota). **Dientes**:
13 mutaciones (8 de `pslg.py`, 5 de `sizing.py`). Sobrevivían dos: el sentido de la cadena de un
anillo, que las semillas no notaban porque la regla par-impar no depende del orden (test nuevo: la
cadena cerrada son piezas del PSLG y tiene el signo de área del anillo), y el borde de una ventana,
que el punto de prueba no veía por estar en el lado que la regla de cruces ya cuenta (puntos en los
cuatro lados). Al final, 13 de 13.

## Lo que corrigió el plan de la sesión de OGR-Core (2026-11-22)

La sesión del núcleo leyó las fuentes enteras para su plan del mallador y corrigió dos cosas de los
documentos de esta spec; se aplican aquí:

- **Las constantes de normalización de las medidas de calidad tienen fuente**: la tabla 6 (pág. 53)
  de Shewchuk (2002b) imprime 4(12 + 7√3)^(1/3)/3 y 4√3. El plan las daba como aritmética propia.
  Comprobado que coinciden con las que se habían calculado (elevando al cubo).
- **El B del ejemplo del teorema 8 es 1/(2 sen 15°) = 1.93185…**, no 1.93 (con 1.93 justo, D_S da
  9.03 y no 9.01). Cambiado en la spec, el plan y la T13.

Sus otras precisiones (el lema 1 no dice por sí solo que la malla final sea de Delaunay; las capas
concéntricas valen para todo subsegmento con un extremo compartido y hacen que la malla dependa de la
unidad de longitud; el teorema 8 pide también α_min > 60°) son de su implementación y no cambian lo
que esta spec afirma. Las puntualizaciones de FEM2D a ese plan, en
`Promts_desarrollo/2026_11_22_respuesta_al_plan_de_ogr_core.md`.

## D14 decidida y T4b: los arcos, en tramos de 60° como mucho (2026-11-22)

**Lo que se buscó.** A petición de la propietaria se buscó en la literatura cómo se trata un contorno
curvo en el refinado de Delaunay. Tres familias:

- **Refinar sobre la curva**: Pav y Walkington («Delaunay refinement by corner lopping», Meshing
  Roundtable, hacia 2005; leído §1–3), siguiendo a Boivin y Ollivier-Gooch (2002; de pago, no
  conseguido). La curva se parte por un punto de la curva (en un arco, su punto medio), la invasión se
  mide con el círculo de la cuerda y cada curva se trocea antes en piezas cuya tangente gira como mucho
  π/3; la terminación la prueban con «corner lopping», no con capas concéntricas.
- **Curvar después y arreglar el interior** (las mallas de orden alto: Sherwin y Peiró 2002, Persson y
  Peraire, Toulorge et al. 2013): iterativo, sin garantía general. Leído solo a través de quien los cita.
- **Mallado curvo con calidad garantizada** (Mandad y Campen 2021): solo el resumen; desproporcionado
  para T6 en 2D.

**La decisión (D14), de la propietaria**: refinar sobre la curva, pedido al núcleo
(`Promts_desarrollo/2026_11_22_peticion_ogr_core_contornos_curvos.md`), con la red de seguridad de
volver a mallar con más divisiones si RF-13 rechaza la malla. D13 queda sustituida. Las dos copias de
Pav y Walkington y de Miller, Pav y Walkington (2005), en la bibliografía.

**T4b**: `geometry.minimum_divisions`, ⌈θ/60°⌉ para un arco (Pav y Walkington, def. 4, pág. 4), en
todos los modos de `discretize` (la graduada los reparte con `share_out` respetando mínimos); unas
divisiones forzadas por debajo se rechazan (`divisions`) y `boundary_nodes` tiene que llegar a la suma
de los mínimos (`graded_nodes`). Un arco de 60° justos es un tramo aunque sus coordenadas vengan
redondeadas (con (0.5, 0.8660254037845), θ sale 1.00000000000003 × π/3: sin el margen se partiría en
dos). Enmienda de D3 y de RF-2 en la spec.

- Siete tests de antes se cayeron, todos por la regla nueva y como se esperaba: datos con menos nudos
  que la suma de mínimos (el cuadrado mordido por un arco de 127°, el gajo de 179°, el arco del eje),
  `boundary_nodes = 4` en el túnel (ahora hacen falta 8), y «la menor cantidad de divisiones», que
  ahora tiene el suelo de 60°. Se ajustaron los datos y la expectativa, no el código.
- Las mutaciones de la T4 se volvieron a pasar: cinco «sobrevivían» porque su texto ya no existía en
  el código cambiado; rehechas sobre el código nuevo, 18 de 18. Las de la T3, 35 de 35.

**Los tests**: `tests/test_mesh_arc_pieces_v008.py`, 6 (el giro de cada tramo medido desde el centro,
no con la función del código). **Dientes**: 8 mutaciones (giro máximo de 90°, sin margen de redondeo,
forzadas por debajo aceptadas, suma de mínimos olvidada, reparto sin mínimos, segmentos que no reciben
nudos con una sola división, uniforme sin mínimo, devolver divisiones por debajo del mínimo): 8 de 8.

## El mallador del núcleo, probado desde FEM2D (2026-11-23)

La sesión de OGR-Core contestó a la petición D2 (`Promts_desarrollo/2026_11_23_respuesta_ogr_core_
mallador_de_calidad.md`): `ogr_core.fem.refine.quality_triangulation`, en su `main` (`f2f7b99`,
`0.2.5.dev0`), sin etiquetar todavía. Acepta el `PSLG` de FEM2D tal cual.

**Lo que se vio al probarlo** (con `PYTHONPATH` al árbol del núcleo, sin cambiarle de rama):

- **D14 no está en el núcleo**: `refine.py` no sabe de arcos, la respuesta no menciona la segunda
  petición y, con malla uniforme de h ≤ 0.5 m, el refinado añade vértices sobre las cuerdas del hueco
  (3 con h = 0.5; 9 con h = 0.25). La propietaria lleva la petición y la T12 espera; un test lo deja
  escrito y fallará cuando el núcleo lo resuelva.
- **Las ventanas pequeñas no se veían**: el núcleo mira la cota en los tres vértices y el centroide de
  cada triángulo, y una ventana de 0.4 m con tamaño 0.05 dejaba la malla igual (234 triángulos,
  ninguno dentro). **Decisión de la propietaria (2026-11-23)**: las esquinas de cada ventana que caen
  dentro del dominio entran en el PSLG como nudos sueltos (`pslg.window_corners`). Con ellas la
  ventana se llena de triángulos de 0.05 como mucho.
- **Determinismo entre plataformas (aviso del núcleo, anomalía en este repositorio)**: los nudos de
  los arcos salían de `math.cos`, `math.sin` y `math.atan2`, y los de la malla radial de `cos`, `sin` y
  `**`, que vienen de la biblioteca de cada sistema y pueden redondear distinto la última cifra: el
  mismo modelo podía dar otra malla en Linux que en Windows (RF-11). No se ha visto aquí fallar (no hay
  Linux en esta máquina); lo midió el núcleo con su propio test. **Decisión de la propietaria
  (2026-11-23)**: trigonometría propia, `ogr_fem2d/mesh/_trig.py`, con + − × ÷ y raíz cuadrada (las
  series de Taylor y las identidades de siempre; seno y coseno por cuadrantes, a 3.3·10⁻¹⁶ de `math`),
  usada en `discretize`, `geometry`, `quadratic` y `radial`; las distancias, con raíz cuadrada en vez
  de `hypot` y `dist`; la progresión de la malla radial, con productos en vez de `**` (sin tocar
  `engine/mesh_radial.py`, del que dependen los casos 001 y 002 bit a bit). Una huella SHA-256 de cuatro
  discretizaciones y una malla radial, grabada en Windows, la comprobará la CI en Linux y macOS.
  - Al cambiar `hypot` por la raíz, un test de la T5 pasó de 4.3·10⁻¹⁶ a fallar por su tolerancia de
    4·10⁻¹⁶, que había puesto a ojo: el cálculo c + r·d/|d| encadena unos cuatro redondeos y medirlo
    otro, así que la cota es de seis unidades de redondeo, 6·2⁻⁵³. Se cambió la tolerancia por esa
    cota, con su cuenta en el test.

**Los tests**: `tests/test_mesh_determinism_v008.py`, 4 (la trigonometría contra `math`, ningún
módulo que decide la malla llama a la biblioteca del sistema ni usa `**`, leído en los tokens y no en
los comentarios, y la huella); `tests/test_mesh_refine_v008.py`, 10, **pendientes hasta que la
fijación llegue a la 0.2.5** (T14): con el núcleo fijado vuelven sin hacer nada, y uno falla si el
núcleo es 0.2.5 o posterior sin `refine`. Con `--dev-core` comprueban la cota de tamaño (uniforme,
cota máxima, ventanas), el teorema 4 (cociente ≤ √2), Delaunay en un dominio convexo, la graduación
del teorema 8 con B = 1/(2 sen 15°) y lfs por fuerza bruta (una comprobación en estas mallas: el núcleo
avisa de que sus capas quedan fuera de la prueba), la cuña de 5° del teorema 12, el mapa de piezas y
D14 pendiente. Más dos en `test_mesh_pslg_v008.py` para las esquinas. **Dientes**: 6 mutaciones del
determinismo y 4 de las ventanas y la cota contra el núcleo nuevo, todas cazadas.

## T14 — la fijación sube a `ogr-core` v0.2.5 (2026-11-23)

Decisión de la propietaria: subirla en cuanto la 0.2.5 estuviera etiquetada (`v0.2.5` → `8a1a52b`),
sin esperar a los arcos de la 0.2.6. La 0.2.5 trae el mallador de calidad (`ogr_core.fem.refine`), las
medidas de Shewchuk (2002b) en `ogr_core.fem.mesh` y sus mensajes; su §2 no pide nada a los programas y
avisa de que la 0.2.6 leerá `PSLG.arcs` (el mismo PSLG con arcos dará otra malla). `generate_mesh` no
cambia.

- `pyproject.toml`, las dos recetas del `README.md`, `AGENTS.md`, `tech-stack.md` y una nota fechada en
  `roadmap.md`; el `.venv` reinstalado desde la etiqueta (`--no-deps --force-reinstall`).
- `tests/test_project_setup_v001.py`: `_PIN` y sus listas de versiones se mueven con la fijación.
- `tests/test_mesh_refine_v008.py` corre ya en toda corrida: se quitó la guarda que lo dejaba pendiente
  con la 0.2.3 (y el test que impedía que esa guarda sobreviviera a la subida).
- **La fila de este programa en `docs/consumidores.md` de OGR-Core** dice `v0.2.3`: se corrige allí.
- Para verlo, esta sesión hizo `git fetch --tags` en el repositorio de OGR-Core: actualiza sus
  referencias remotas, no su rama ni sus archivos.

**Dientes**: `_PIN` de vuelta a 0.2.3 y la lista de la corrida normal cambiada, cazados; y el test del
teorema 4 con una malla hecha con B = 3 en vez de √2, cazado (la comprobación no pasa en vacío).

## D15 — los arcos, en tramos de 10° (2026-11-23)

La sesión de OGR-Core contestó a la petición de D14 (`Promts_desarrollo/2026_11_23_respuesta_ogr_
core_contornos_curvos.md`): variante (ii), partir los tramos de arco sobre el arco, en su **0.2.6**,
con la API que FEM2D ya tiene (`PSLG.arcs`). Y trajo un hallazgo de la fuente que cambia lo que la spec
promete: Pav y Walkington solo prueban que el refinado **termina con arcos** si el ángulo pedido es menor
que una cota que depende de lo que gira cada tramo (corolario 3, pág. 13; η y μ, pág. 6; ζ, pág. 8). Se
recalculó aquí con esas fórmulas y coincide con su tabla: tramos de 60° → B > 7.21; 15° → 1.97; 10° →
1.76; 5° → 1.58. Con B = √2 no hay prueba con ningún troceo; en la práctica, si no terminara, el tope de
elementos corta con un error, y si termina, cada triángulo cumple la cota.

**Decisión de la propietaria (D15)**: tramos de 10° y B = √2 por defecto; la malla dirá con ella, cuando
haya arcos, que la terminación solo está probada con B ≥ 1.77 (regla 12; se hace en la T12 con la nota
del núcleo). Enmiendas de RF-2, RF-4, RF-9 y D3 en la spec; fila nueva en «Formulación».

- `geometry.MAX_ARC_TURN` pasa de π/3 a π/18; un cuarto de círculo pide ahora 9 divisiones y un túnel
  circular en cuatro arcos, 36 nudos en la malla graduada.
- Los tests se ajustaron a los mínimos nuevos (datos con más nudos; el arco medido por el arco, ahora
  con h = 0.17, donde el arco da 10 divisiones y la cuerda 9). La huella de determinismo cambia (la
  discretización es otra) y se regrabó, con la vieja anotada en el test.
- **El test de «D14 pendiente» dejó de ver vértices en las cuerdas** con h = 0.25: con tramos de 10° las
  cuerdas (0.17 m) son más cortas que h. El problema sigue donde el arco va más grueso que la malla: el
  test fuerza ahora 9 divisiones por cuarto con h = 0.05.
- Las mutaciones de la T4 y la T5 se volvieron a pasar: dos «sobrevivían» porque su texto (con
  `math.dist`) ya no existe desde el cambio a `_trig`; rehechas, 18 de 18 y 8 de 8. Las de la T4b, con
  el giro máximo mutado a 15°, 8 de 8.

## Pruebas

## Pruebas

| Corrida | Resultado |
|---|---|
| T3, suite entera contra la etiqueta instalada (`shared: ogr_core 0.2.3 … (installed, no git tree)`) | **224 de 224** (205 de antes y 19 nuevos), código 0, ninguna fuga |
| T4, la misma | **239 de 239** (15 nuevos), código 0, ninguna fuga |
| T5, la misma | **245 de 245** (6 nuevos), código 0, ninguna fuga |
| T6, la misma | **258 de 258** (13 nuevos), código 0, ninguna fuga |
| T7, la misma | **261 de 261** (3 nuevos), código 0, ninguna fuga |
| T9, la misma | **266 de 266** (5 nuevos), código 0, ninguna fuga |
| T8, la misma | **274 de 274** (8 nuevos), código 0, ninguna fuga |
| T10, la misma | **279 de 279** (5 nuevos), código 0, ninguna fuga |
| T11, T12 y T15 (parte sin el núcleo), la misma | **287 de 287** (8 nuevos), código 0, ninguna fuga |
| T4b (D14), la misma | **293 de 293** (6 nuevos), código 0, ninguna fuga |
| Determinismo, ventanas y el mallador del núcleo, la misma | **309 de 309** (16 nuevos; los 10 de `test_mesh_refine_v008.py` vuelven sin hacer nada con el núcleo fijado), código 0, ninguna fuga. Con `PYTHONPATH` al árbol del núcleo (`0.2.5.dev0 @ f2f7b99`) y `--dev-core`, solo `test_mesh_refine_v008.py`: 10 de 10 |
| T14, contra la `v0.2.5` instalada (`shared: ogr_core 0.2.5 … (installed, no git tree)`) | **308 de 308** (uno menos: el test de la guarda pendiente ya no tiene sentido), código 0, ninguna fuga; los 9 de `test_mesh_refine_v008.py` corren |
| D15, la misma | **308 de 308**, código 0, ninguna fuga |
