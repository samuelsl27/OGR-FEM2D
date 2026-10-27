# OGR FEM2D v0.0.2 (en curso)

**Fase 1, primera parte: el motor elástico general** (spec 002).

## Lo que se encontró

- **Tarea T0** (2026-10-27): el propietario aprueba D1–D7 tal como se propusieron.
- **Tarea T1, las fuentes** (`spec/features/002-motor-elastico/plan.md`, «Formulación»):
  - la solución de Michell para la carga en faja (Timoshenko y Goodier 1951, §34) coincide a
    2·10⁻¹⁶ MPa con la superposición numérica de la fuerza puntual de Flamant (§33): las dos
    fuentes se comprueban una contra otra;
  - en la cavidad esférica, el contorno fijo a 21 m solo aparta la solución exacta del modelo un
    0.022 % en ur(a) (el efecto va con 1/b³), así que STR-09 no necesita dos geometrías;
  - en STR-04 no hay desplazamiento de referencia: el de Flamant lleva log r y una constante que
    depende del punto que se toma como fijo (§33, ecs. g–72); solo se comparan tensiones;
  - la regla cuadrática del T6 pone puntos de integración sobre el eje en axisimetría (D1);
  - la (5.13) y el §5.2.6 de Zienkiewicz y Taylor (2000) trabajan con el anillo entero: confirman D2;
  - la carga puntual dentro de un elemento no está impresa en la fuente; se deriva del trabajo
    virtual de la (2.10): fᵢ = Nᵢ(x_p)·P;
  - la ley K = a + b·zᶜ de la tensión gravitatoria del análisis inicial no tiene fuente (D3);
  - **anomalía en D3 (error propio de la spec)**: en axisimetría el equilibrio radial lleva
    (σr − σθ)/r (Timoshenko y Goodier 1951, §116, ec. 177, pág. 343). Un campo gravitatorio con
    K ≠ Kz, o uno constante con σr ≠ σθ o con τrz ≠ 0, **no está en equilibrio**, y el motor lo
    convertiría en una carga que nadie ha puesto. D3 proponía K y Kz por separado sin decir esto.
    **Enmienda de D3** (decidida por el propietario el 2026-10-27): en axisimetría el preproceso
    exige K = Kz en el campo gravitatorio y, en el constante, σr = σθ y τrz = 0; si no, un error
    que lo explica. En deformación plana, K y Kz siguen separados.
  - con T3 en axisimetría, la regla del centroide no integra exactos los términos de grado 2 de la
    tensión inicial y del peso propio: la identidad gravitatoria será exacta en deformación plana y
    en axisimetría con T6, y con T3 axisimétrico se espera un error que baja con h² (se comprobará
    en la T8).
- **Tarea T2, la entrada del motor** (`ogr_fem2d/engine/model.py`, `docs/motor/entrada.md`): el
  esquema discreto y 27 reglas de validación, que informan todas a la vez con su sitio. Al probar
  los dientes, tres mutaciones sobrevivían (un elemento de área nula, que la tabla solo probaba
  invertido; un nudo con x < 0 en deformación plana; ψ > φ): se añadió el test que las caza.
- **Tarea T3, las reglas de integración** (`ogr_fem2d/engine/reference/quadrature.py`): la tabla 9.2
  de Zienkiewicz y Taylor (2000) **trunca** sus valores a diez decimales, no los redondea (α₂ =
  0.79742698535… sale como 0.7974269853), y sus pesos suman 0.9999999996. La regla quíntica se
  escribe en forma cerrada, que la fuente no imprime, y se comprueba contra cada dígito de la tabla
  y contra la integral exacta de los monomios hasta grado 5 (ec. 8.38) a 1e-15. La regla cuadrática
  del T6 sale ahora de este módulo, con los mismos puntos y en el mismo orden que en la spec 001.
- **Tarea T4, el T3 y el T6 generalizado** (`reference/triangle.py`, `element_t3.py`): el triángulo
  isoparamétrico es uno solo, con las funciones de forma y la regla como parámetros. Los casos 001
  y 002 dan los mismos números **bit a bit** que antes, en la referencia y en Rust. Al probar los
  dientes, la rigidez por punto con el ancho fijo del T6 no la cazaba ningún test, porque en
  elasticidad no se ensambla: se añadió la comprobación de que las dos rutas dan la misma matriz.
- **Tarea T5, la axisimetría** (Zienkiewicz y Taylor 2000, §5.2): el T3 con el centroide, que es
  la ec. (5.14) de la fuente, tiene en el elemento aislado **un segundo modo de energía nula**,
  espurio, porque B es de 4 × 6 en un solo punto. El test esperaba uno solo, como en el T6 con
  siete puntos. Comprobado que la malla ensamblada no tiene ningún mecanismo, con y sin el eje,
  y que la parcela y el cilindro traccionado salen exactos con los dos elementos. Los casos 001 y
  002 siguen dando los mismos números bit a bit.
- **Tarea T6, restricciones, impuestos y reacciones** (`ogr_fem2d/engine/analysis.py`). Dos hallazgos
  en el criterio de las fases, los dos por el redondeo:
  - **una fase con la misma carga total que la anterior no daba carga cero**, sino un resto de
    redondeo de 1e-16 de las fuerzas; dividido por él, el residuo relativo era ruido y Newton no
    convergía. Ahora una fase cuyo desequilibrio es menor que 1e-12 veces la mayor fuerza en juego
    no tiene carga y no se resuelve (`solver.NO_LOAD`); el resultado lo dice (`solved`);
  - **una carga pequeña frente a las fuerzas presentes no podía converger**: el residuo no baja
    del redondeo de esas fuerzas, y relativo a una carga de 1e-9 de ellas ese suelo es 1e-7,
    por encima de cualquier tolerancia estricta. Es el caso de una sobrecarga pequeña sobre un
    terreno con grandes tensiones gravitatorias. Ahora una iteración con el residuo por debajo de
    1e-12 veces la mayor fuerza en juego también converge. Donde la tolerancia se alcanza, ese
    suelo queda muy por debajo y no cambia nada: los casos 001 y 002 dan los mismos números bit
    a bit. La tolerancia por defecto del programa sigue siendo cosa de la fase 2 (spec 007).
