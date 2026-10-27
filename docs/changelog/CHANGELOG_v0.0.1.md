# OGR FEM2D v0.0.1 (en curso)

**Fase 0: la prueba de concepto del motor** (spec 001). Esta entrada se completa al cerrar la
versión, registrando **qué se encontró**.

## 0. Lo que se encontró (hasta ahora)

- **Tarea T1, las fuentes** (`spec/features/001-prueba-de-concepto/plan.md`, «Formulación»):
  - el desplazamiento del hueco en Mohr-Coulomb con dilatancia no nula no está impreso en Salençon
    (1969); la fórmula de la ficha coincide a 1e-12 con la integración de su modelo en pequeñas
    deformaciones, y ese es su respaldo;
  - con el contorno a 21 m (la geometría de las fichas), la solución exacta del modelo ya se aparta
    de las fórmulas de medio infinito en ur(a) un 0.60 % (Kirsch) y hasta un 1.83 % (Salençon); la
    spec decía «en torno a un 0.2 %» sin haberlo calculado. De ahí D3 bis: casos a 100 m y la
    identidad del anillo de 21 m.
- **Tarea T3, el entorno**: el núcleo se fija a `ogr-core` v0.1.0 y el runner se niega a medir
  contra cualquier otra versión, en particular contra el `ogr_core` de OGR Slip2D, que tiene el
  mismo nombre de paquete.
