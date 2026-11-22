# 005 — Hueco circular con malla general (Kirsch)

| Campo | Valor |
|---|---|
| Ficha de trabajo | `VER-STR-01` (en `../Referencias/Ejemplos/Casos_por_problema/`) |
| Fuente científica | Kirsch (1898), en Jaeger, Cook y Zimmerman (2007), *Fundamentals of Rock Mechanics*, 4.ª ed., §8.4, ecs. (8.90)–(8.92), págs. 216–218 (hidrostático); §8.5, ecs. (8.113)–(8.125), págs. 219–221 (identidad no hidrostática) |
| Tipo de referencia | analítica (el caso) e identidad (con el desplazamiento exacto en el contorno) |
| Tipo de análisis | deformación plana; elástico lineal; una fase de excavación |

El STR-01 del caso 001, pero con la **malla general** de la spec 003 (D5 de la spec 002, D12 de la
spec 003): contorno exterior **cuadrado**, el modelo completo sin simetría, T6 con los nudos del hueco
sobre la circunferencia y malla graduada. El caso 001 no cambia (regla 9).

> **Estado (2026-11-22): tolerancias fijadas antes de medir; la malla, por fijar.** El mallador
> general depende del refinado de calidad que se ha pedido a OGR-Core (spec 003, D2); el estudio de
> convergencia y la malla se hacen cuando esté (tarea T15).

## Geometría

Hueco de radio a = 1 m centrado en el origen. Contorno exterior cuadrado de semilado L = 100 m. La
excavación es una región (el círculo, cuatro arcos de 90°) que se desactiva en la fase.

## Materiales y parámetros

E = 10 000 MPa, ν = 0.2 (los de la ficha).

## Condiciones de contorno, tensión inicial y fases

- **El caso**: contorno exterior fijo en las dos direcciones; tensión inicial hidrostática de 30 MPa
  de compresión en las tres direcciones (σzz incluida); una fase, la excavación (la región del hueco
  desactivada), sin presión interior.
- **La identidad**, con la **misma malla**: en el contorno exterior se impone el desplazamiento que la
  excavación causa en el medio infinito (`spec/features/003-malla/comprobaciones/`, la (8.124)–(8.125)
  menos el campo sin hueco), con el campo hidrostático y con σ1 = 30, σ2 = 15 MPa (σ1 según x; en
  elasticidad σzz no interviene en el plano). Así el modelo tiene por solución exacta la de
  Kirsch y lo que se mide es solo la discretización; la diferencia entre el caso y la identidad
  hidrostática, en la misma malla, es el efecto del contorno cuadrado a 100 m.

## Valor esperado y de dónde sale

Con compresión positiva y ur positivo hacia el centro:

- caso e identidad hidrostática: σθ(a) = 2 p0 = **60 MPa** y ur(a) = p0 a / (2G) = **0.0036 m**
  (los del caso 001);
- identidad con σ1 = 30, σ2 = 15: σθ(a, θ) = (σ1 + σ2) − 2(σ1 − σ2) cos 2θ = 45 − 30 cos 2θ (8.116),
  entre 15 y 75 MPa, y ur(a, θ) el de `kirsch_induced_displacement`, punto a punto.

Se compara el **peor** punto: σθ en todos los puntos de integración sobre r = a (la regla cuadrática
del T6 pone uno en el centro de cada lado, sobre la circunferencia) y ur en todos los nudos sobre
r = a, esquinas e intermedios. **Tolerancia: 0.5 %** en los dos, en el caso y en la identidad (D12, la
de la spec 001, D3), relativa al valor del punto.

**Lo que no se sabe todavía**: el efecto del contorno cuadrado a 100 m. Con el circular a 100 m era
del 0.027 % en ur(a) (caso 001); el cuadrado no tiene solución cerrada y se medirá con la identidad.
Si con él no se cumple el 0.5 %, es un hallazgo y se agranda el dominio, no se afloja la tolerancia
(como en el caso 004).

## Malla y elemento con que se fija la tolerancia

T6, malla graduada de la spec 003 con `boundary_nodes` en los arcos del hueco y B = √2. **Por fijar**
con el estudio de 16, 32, 64 y 128 divisiones del hueco (D12). Las mallas de Delaunay no están
anidadas: si el error no baja en cada paso, es un hallazgo.
