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

> **Estado (2026-11-23): la malla, fijada por el estudio de la T15; el caso, dentro de su
> tolerancia.** Las tolerancias se fijaron antes de medir (2026-11-22) y no han cambiado.

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

T6, malla graduada de la spec 003 (`mesher.mesh`, OGR-Core 0.2.6), B = √2, con:

- una **ventana** cuadrada |x|, |y| ≤ 3 m de tamaño **h = 0.1 m** alrededor del hueco;
- **64 nudos en el hueco** (4 ⌈πa/2h⌉: tramos no más largos que h);
- una **cota máxima de 5 m** (50 h).

20 136 elementos de 6 nudos (28 066 con la cota). `tests/_kirsch_mesh.py` la construye;
`spec/features/003-malla/comprobaciones/estudio_005.py` rehace el estudio.

**Cómo se llegó (2026-11-23, el changelog v0.0.8 da las tablas).** El estudio previsto, el de las
divisiones del hueco con la graduada sola, **no convergía**: con 36, 64, 128 y 256 nudos (16 y 32 no
caben con tramos de 10°, D15), el peor ur(a) del caso se quedaba en −0.52 % y el de la identidad con
σ2 = σ1/2 entre el 3 y el 6 %. Los elementos de la graduación de Ruppert crecen en proporción a la
distancia al hueco, y las divisiones del hueco solo afinan junto a él. La propietaria eligió una
ventana alrededor del hueco. Con la ventana sola, el error de ur en la identidad anisótropa se paraba
en el 0.77 % al afinar h: lo dan los elementos de decenas de metros junto al contorno, que no siguen
el término en cos 2θ (decae solo como 1/r). Una cota máxima lo baja (con h = 0.1: 0.70 %, 0.50 % y
0.24 % con 20, 10 y 5 m). El estudio final afina las dos a la vez, h y 50 h:

| h (m) | Elementos | Caso σθ | Caso ur | Id. 30/30 σθ | Id. 30/30 ur | Id. 30/15 σθ | Id. 30/15 ur |
|---|---|---|---|---|---|---|---|
| 0.2 | 7 395 (cota 10 m) | 0.487 % | −0.078 % | 0.501 % | −0.055 % | 1.045 % | 0.513 % |
| **0.1** | **28 066** | **−0.086 %** | **−0.050 %** | **0.084 %** | **−0.028 %** | **0.344 %** | **0.236 %** |
| 0.05 | 108 403 | −0.033 % | −0.027 % | 0.041 % | −0.005 % | −0.149 % | 0.060 % |

Todas las columnas bajan en cada paso. La de h = 0.1 es la primera que cumple el 0.5 % en todo, y es la
del caso.

**El contorno cuadrado.** En la misma malla, el caso (contorno fijo) y la identidad hidrostática
(contorno con el desplazamiento exacto) se diferencian en el peor ur en un 0.022 % (−0.050 frente a
−0.028), y en σθ en menos que el error de la malla (los dos peores, de signo opuesto, se acercan al
afinar: 0.17 puntos con h = 0.1 y 0.07 con 0.05). El efecto del cuadrado a 100 m queda por debajo
del 0.1 %.
