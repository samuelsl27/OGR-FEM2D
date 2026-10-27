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
    Pendiente de la decisión del propietario.
  - con T3 en axisimetría, la regla del centroide no integra exactos los términos de grado 2 de la
    tensión inicial y del peso propio: la identidad gravitatoria será exacta en deformación plana y
    en axisimetría con T6, y con T3 axisimétrico se espera un error que baja con h² (se comprobará
    en la T8).
