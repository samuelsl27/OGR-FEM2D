# 008 — Zapata en faja sobre un material puramente cohesivo (Prandtl)

| Campo | Valor |
|---|---|
| Ficha de trabajo | `VER-STR-05` (en `../Referencias/Ejemplos/Casos_por_problema/`) |
| Fuente científica | Prandtl (1921), *ZAMM* 1(1), 15–20, y Hill (1950), *The Mathematical Theory of Plasticity*, Oxford, a través de de Souza Neto, Perić y Owen (2008), *Computational Methods for Plasticity*, Wiley, §7.5.4, ec. (7.178), págs. 252–255, y §8.4.3, págs. 346–349 |
| Tipo de referencia | analítica |
| Tipo de análisis | deformación plana; Mohr-Coulomb con φ = ψ = 0 (Tresca); fases de carga en totales |

La ficha cita la carga de Prandtl a través de Terzaghi y Peck (1967), que no está en la
bibliografía; los originales de Prandtl y de Hill tampoco (spec 007, «Fuentes por conseguir»). Se
cita por de Souza Neto et al. (2008), que la dan y la usan para validar su zapata de Tresca.

## Geometría

Zapata en faja de semianchura b = 3 m (anchura B = 6 m) en la superficie de un medio sin peso. Por la
simetría respecto a x = 0 se modela la mitad, 0 ≤ x ≤ W y −D ≤ y ≤ 0, con y hacia arriba y la
superficie en y = 0. **La ficha no da el dominio**: lo fija un estudio, empezando por la proporción de
de Souza Neto et al. (§7.5.4: medio dominio de 5 por 5 veces la anchura de la zapata).

## Materiales y parámetros

Los de la ficha: E = 250 MPa, ν = 0.2, c = 0.1 MPa, φ = 0. La dilatancia, ψ = 0 (Tresca, el material
de la solución). Sin peso ni tensión inicial: la carga de Prandtl es la del medio sin peso.

## Dos variantes (spec 007, D6)

- **(a) Zapata rígida y lisa con el asiento impuesto**, la de de Souza Neto et al. (§8.4.3): los
  nudos de la superficie con 0 ≤ x ≤ b bajan lo mismo (v impuesto) y se mueven libres en x (lisa).
  Una fase por asiento, en totales. La presión media de cada fase es la suma de las reacciones
  verticales de esos nudos dividida por b. La curva presión–asiento hace meseta en la carga límite.
- **(b) Zapata flexible con carga uniforme por fases**, la de la ficha: una presión uniforme q sobre
  0 ≤ x ≤ b, en fases de q creciente. Las de debajo de la carga límite convergen; la de encima no.

## Condiciones de contorno

x = 0: u = 0 (simetría). x = W: u = 0 (rodillos). y = −D: u = v = 0. La ficha no documenta los apoyos
(«según la figura 5.1»); estos son los elegidos, y su efecto entra en el estudio de dominio.

## Valor esperado y de dónde sale

**P_lim = (2 + π) c = 0.514159 MPa** (de Souza Neto et al. 2008, ec. 7.178, que la atribuyen a
Prandtl y a Hill; para la zapata lisa, el mecanismo de Hill). Lo que dan sus mallas (5.19 c con 135
Q8, §8.4.3) **no** es el valor esperado: es su discretización.

La variante (b) usa la misma carga límite: el campo de tensiones de Prandtl es uniforme bajo la faja
y su cuña central baja como un sólido, así que una presión uniforme tendría la misma. **Esto está por
comprobar en Hill (1950) o en Prandtl (1921)** (spec 007, D6): mientras tanto la variante (b) se
juzga con una banda de ±5 %, no con la meseta.

Los asientos y las cargas de la reproducción P13 del análisis **no son valor esperado**
(`validacion/README.md`).

## Tolerancia y estudios

En `esperado.json`, escritos antes de la primera medida, con el protocolo de cada estudio: el de
dominio, el de malla (spec 007, D7) y el de los valores por defecto del programa (D1 y D3).
