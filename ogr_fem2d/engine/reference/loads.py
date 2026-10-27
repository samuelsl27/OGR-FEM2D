# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Consistent nodal forces of the loads (spec 002, RF-6 and T7).

Sources, Zienkiewicz, O. C. and Taylor, R. L. (2000). *The Finite Element
Method*, 5th ed., vol. 1:

* body forces, Eq. (2.13b), p. 24: int N^T b dV; in axisymmetry over the
  whole ring, 2 pi int N^T b r dr dz (Eq. 5.19, p. 119; spec 002, D2). The
  self weight is b = (0, -gamma), gravity along -y (docs/motor/entrada.md);
* tractions on a side, Eq. (2.15), p. 25: int N^T t dA over the loaded
  boundary, here a side of an element, per unit thickness in plane strain
  and over the ring in axisymmetry (2 pi r ds);
* a point force: not printed in the source. It is the virtual work of
  §2.2.4, Eq. (2.10), p. 24, applied to a force P at x_p: its work is
  u(x_p)^T P = a^T N(x_p)^T P, so the nodal forces are N_a(x_p) P (our
  derivation; spec 002, plan, "Formulación"). In axisymmetry P is the force
  of the whole ring of radius x_p (D2);
* the integral along a side: Gauss-Legendre with ten points, Table 9.1,
  p. 220, exact for polynomials of degree 19. On a straight side the
  integrand is a polynomial of degree 4 at most (N of degree 2, the linear
  traction, r in axisymmetry), and on a curved side of a six-node triangle
  loaded normally of degree 6 (the normal times ds is (dy, -dx), a
  polynomial): exact in both. A traction given in global components on a
  curved side needs |dx/ds|, which is not a polynomial: there the rule is
  an approximation. Measured against an adaptive integral of the arc
  (spec 002, T7): with five points the error reached 1.7e-6 on a side
  spanning 90 degrees of a circle, with ten 2.2e-11, and on a side of 22.5
  degrees or less it is rounding. Ten points, then: they cost nothing
  beside the rest of the analysis.

Sides (docs/motor/entrada.md): side k goes from corner k to corner
(k + 1) % 3 and, in the six-node triangle, through its mid-side node k + 3.
Along it, s goes from 0 at the first corner to 1 at the second; the shape
functions of the triangle restricted to the side (Z&T p. 182 with L_k =
1 - s, L_(k+1) = s and the third area coordinate zero) are 1 - s and s
for three nodes, and (1 - s)(1 - 2 s), 4 s (1 - s), s (2 s - 1) for six
(first corner, mid-side node, second corner). The traction varies linearly
in s from its value at the first corner to that at the second: linearly
along the side when the side is straight.

Normal and tangential components: the corners of an element go
anticlockwise, so its interior is on the left of each side and the outward
normal is on the right. With (dx, dy) the derivative of the side's position
in s, the normal force per ds is t_n (dy, -dx) and the tangential one
t_t (dx, dy), both already multiplied by |dx/ds|. t_n > 0 pulls (tension
positive); a pressure is t_n < 0.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math

from . import triangle
from .quadrature import Rule

#: Table 9.1, n = 10: (abscissa on [-1, 1], weight), as printed (15
#: decimals), the five positive abscissae and their mirror images.
_HALF = ((0.973906528517172, 0.066671344308688),
         (0.865063366688985, 0.149451349150581),
         (0.679409568299024, 0.219086362515982),
         (0.433395394129247, 0.269266719309996),
         (0.148874338981631, 0.295524224714753))
GAUSS_LEGENDRE_10 = tuple((-a, w) for a, w in _HALF) + tuple((a, w) for a, w in reversed(_HALF))


def side_nodes(nodes_per_element: int, side: int) -> tuple[int, ...]:
    """Local indices of the nodes of a side, from its first corner to its
    second (through the mid-side node with six nodes)."""
    first, second = side, (side + 1) % 3
    if nodes_per_element == 3:
        return first, second
    return first, side + 3, second


def side_functions(n: int, s: float) -> tuple[list[float], list[float]]:
    """Shape functions along a side of n = 2 or 3 nodes and their s
    derivatives, nodes in the order of side_nodes()."""
    if n == 2:
        return [1.0 - s, s], [-1.0, 1.0]
    return ([(1.0 - s) * (1.0 - 2.0 * s), 4.0 * s * (1.0 - s), s * (2.0 * s - 1.0)],
            [4.0 * s - 3.0, 4.0 - 8.0 * s, 4.0 * s - 1.0])


def edge_forces(xy: list[tuple[float, float]], start: tuple[float, float],
                end: tuple[float, float], normal: bool = False,
                axisymmetric: bool = False) -> list[tuple[float, float]]:
    """Nodal forces (fx, fy) of a traction on one side, int N^T t ds
    (Eq. 2.15), for the side's nodes ``xy`` in the order of side_nodes().
    ``start`` and ``end`` are the traction at the two corners, in (x, y) or,
    with ``normal``, as (normal, tangential)."""
    n = len(xy)
    f = [[0.0, 0.0] for _ in range(n)]
    for xi, w in GAUSS_LEGENDRE_10:
        s, ws = 0.5 * (1.0 + xi), 0.5 * w            # [-1, 1] -> [0, 1]
        shape, dshape = side_functions(n, s)
        x = sum(shape[a] * xy[a][0] for a in range(n))
        dx = sum(dshape[a] * xy[a][0] for a in range(n))
        dy = sum(dshape[a] * xy[a][1] for a in range(n))
        t1 = (1.0 - s) * start[0] + s * end[0]
        t2 = (1.0 - s) * start[1] + s * end[1]
        if normal:
            fx, fy = t1 * dy + t2 * dx, -t1 * dx + t2 * dy
        else:
            length = math.hypot(dx, dy)
            fx, fy = t1 * length, t2 * length
        factor = ws * (2.0 * math.pi * x if axisymmetric else 1.0)
        for a in range(n):
            f[a][0] += factor * shape[a] * fx
            f[a][1] += factor * shape[a] * fy
    return [(a, b) for a, b in f]


def body_forces(shape, xy: list[tuple[float, float]], b: tuple[float, float],
                rule: Rule, axisymmetric: bool = False) -> list[tuple[float, float]]:
    """Nodal forces of a constant body force b per unit volume,
    int N^T b dV (Eq. 2.13b; Eq. 5.19 over the ring), by the element's own
    rule: the same as its stiffness and its initial-stress term."""
    f = [[0.0, 0.0] for _ in shape.NODES_L]
    for (l1, l2, l3), w in rule.points:
        det = triangle.jacobian(shape, xy, l1, l2, l3)[1]
        factor = triangle.weight(shape, xy, l1, l2, l3, w, det, axisymmetric)
        for a, n in enumerate(shape.shape_functions(l1, l2, l3)):
            f[a][0] += factor * n * b[0]
            f[a][1] += factor * n * b[1]
    return [(a, c) for a, c in f]


#: How far outside its element a point load may be found, in area
#: coordinates: rounding, not a tolerance on the user's position.
INSIDE = 1e-9


def local_coordinates(shape, xy: list[tuple[float, float]], x: float, y: float
                      ) -> tuple[float, float, float]:
    """(L1, L2, L3) of the point (x, y) in the element: the isoparametric map
    inverted by Newton's method from the centroid (exact in one step for a
    straight-sided element, whose map is linear). ValueError if the point is
    not in the element."""
    xi = eta = 1.0 / 3.0
    for _ in range(50):
        l = (1.0 - xi - eta, xi, eta)
        n = shape.shape_functions(*l)
        rx = x - sum(n[a] * xy[a][0] for a in range(len(n)))
        ry = y - sum(n[a] * xy[a][1] for a in range(len(n)))
        (j11, j12), (j21, j22) = triangle.jacobian(shape, xy, *l)[0]
        det = j11 * j22 - j12 * j21
        # [rx, ry] = [[dx/dxi, dx/deta], [dy/dxi, dy/deta]] [dxi, deta]
        dxi = (j22 * rx - j21 * ry) / det
        deta = (-j12 * rx + j11 * ry) / det
        xi, eta = xi + dxi, eta + deta
        if abs(dxi) + abs(deta) < 1e-15:
            break
    l = (1.0 - xi - eta, xi, eta)
    if min(l) < -INSIDE:
        raise ValueError(f"the point ({x:.6g}, {y:.6g}) is not in the element "
                         f"(area coordinates {l[0]:.3g}, {l[1]:.3g}, {l[2]:.3g})")
    return l


def point_forces(shape, xy: list[tuple[float, float]], x: float, y: float,
                 fx: float, fy: float) -> list[tuple[float, float]]:
    """Nodal forces N_a(x, y) (fx, fy) of a force at (x, y) of the element
    (the virtual work of Eq. 2.10)."""
    return [(n * fx, n * fy) for n in shape.shape_functions(*local_coordinates(shape, xy, x, y))]
