# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Structured radial mesh of six-node triangles on a quarter of an annulus,
a <= r <= b, 0 <= theta <= 90 degrees (spec 001, RF-7).

How it is built. Take the rectangle a <= r <= b, 0 <= theta <= pi/2 in polar
coordinates and a grid on it: n_radial divisions in r, graded, and n_theta
equal divisions in theta. Each grid cell is split by one diagonal into two
straight six-node triangles of the (r, theta) plane. Every node, corner or
mid-side, is then placed at the EXACT image (r cos theta, r sin theta) of its
(r, theta) point. So:

* the mid-side nodes of the edges of constant r lie on the circle of that
  radius: the hole r = a and the outer boundary r = b are followed by the
  quadratic (isoparametric) edges, as the hole needs (element_t6, Chapter 9
  of Zienkiewicz and Taylor 2000);
* the mid-side node of an edge of constant theta is the midpoint of that
  straight radial segment, at r = (r_i + r_i+1)/2, so radial edges are
  straight with their mid-side node in the middle;
* the mid-side node of a diagonal sits at the image of the centre of the
  cell, (r_i+1/2, theta_j+1/2).

The nodes are, in this way, the points of the grid with half the spacing,
(2 n_radial + 1) x (2 n_theta + 1) of them, and every one of them is used.

Three-node triangles (spec 002, T10): each six-node triangle is cut into
four by its mid-side nodes, (1, 4, 6), (4, 2, 5), (6, 5, 3) and (4, 5, 6) in
the node order of element_t6, all anticlockwise. The nodes are the same, so a
three-node and a six-node mesh of the same parameters can be compared node
by node; the sides on the circles are then chords between nodes on them.

Radial grading: the size of consecutive radial divisions grows by the factor
``growth``, dr_(i+1) = growth dr_i (a geometric progression; growth = 1 is a
uniform mesh). Small elements at the hole, where the stress gradient is.

Nothing here is a formula from a source except the isoparametric mapping:
the checks of the mesh are identities (its area against Archimedes'
quadrature of the parabola; positive Jacobians), in
tests/test_mesh_radial_v001.py.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class RadialMesh:
    """Nodes, elements and the node sets the boundary conditions need."""
    #: (x, y) of each node.
    nodes: list[tuple[float, float]]
    #: Six node numbers per element, in the order of element_t6: corners
    #: 1, 2, 3 counter-clockwise, then mid-sides 4 (1-2), 5 (2-3), 6 (3-1);
    #: or three, counter-clockwise, with nodes_per_element = 3.
    elements: list[tuple[int, ...]]
    #: Node numbers on r = a, on r = b, on theta = 0 (the x axis) and on
    #: theta = 90 degrees (the y axis), each in increasing theta or r.
    hole: list[int]
    outer: list[int]
    x_axis: list[int]
    y_axis: list[int]
    #: The corner radii r_0 = a < ... < r_n = b.
    radii: list[float]
    inner_radius: float
    outer_radius: float


def graded_radii(a: float, b: float, n_radial: int, growth: float
                 ) -> list[float]:
    """r_0 = a, ..., r_n = b with dr_(i+1) = growth dr_i."""
    if n_radial < 1 or not 0.0 < a < b or growth <= 0.0:
        raise ValueError("need n_radial >= 1, 0 < a < b and growth > 0")
    if growth == 1.0:
        sizes = [1.0] * n_radial
    else:
        sizes = [growth ** i for i in range(n_radial)]
    total = sum(sizes)
    radii = [a]
    for size in sizes:
        radii.append(radii[-1] + (b - a) * size / total)
    radii[-1] = b               # exactly, whatever the rounding of the sum
    return radii


def _point(r: float, k: int, n_half: int) -> tuple[float, float]:
    """(x, y) of radius r at the angle k/n_half of 90 degrees. The two axes
    are set exactly, so the restraints act on nodes that lie on them."""
    if k == 0:
        return (r, 0.0)
    if k == n_half:
        return (0.0, r)
    theta = 0.5 * math.pi * k / n_half
    return (r * math.cos(theta), r * math.sin(theta))


def split_into_three_node(elements: list[tuple[int, ...]]) -> list[tuple[int, int, int]]:
    """Each six-node triangle as four three-node ones on the same nodes."""
    out = []
    for n1, n2, n3, n4, n5, n6 in elements:
        out += [(n1, n4, n6), (n4, n2, n5), (n6, n5, n3), (n4, n5, n6)]
    return out


def quarter_annulus(a: float, b: float, n_radial: int, n_theta: int,
                    growth: float = 1.0, nodes_per_element: int = 6) -> RadialMesh:
    """The mesh described in the module docstring."""
    if n_theta < 1:
        raise ValueError("need n_theta >= 1")
    if nodes_per_element not in (3, 6):
        raise ValueError("three or six nodes per element")
    radii = graded_radii(a, b, n_radial, growth)
    # Radii of the half-spacing grid: corners at even i, mid-points at odd i.
    half_r = []
    for i in range(n_radial):
        half_r += [radii[i], 0.5 * (radii[i] + radii[i + 1])]
    half_r.append(radii[-1])
    n_half_t = 2 * n_theta

    def number(i: int, k: int) -> int:
        """Node number of the half-grid point (radius i, angle k)."""
        return i * (n_half_t + 1) + k

    nodes = [_point(r, k, n_half_t) for r in half_r for k in range(n_half_t + 1)]

    elements = []
    for i in range(0, 2 * n_radial, 2):
        for k in range(0, n_half_t, 2):
            # Cell corners in (r, theta): A = (i, k), B = (i+2, k),
            # C = (i+2, k+2), D = (i, k+2); diagonal A-C. In the (r, theta)
            # plane, A -> B -> C runs counter-clockwise (r to the right,
            # theta up), and the polar map keeps the orientation (its
            # Jacobian is r > 0), so both triangles have det J > 0.
            a_, b_, c_, d_ = (i, k), (i + 2, k), (i + 2, k + 2), (i, k + 2)
            for p1, p2, p3 in ((a_, b_, c_), (a_, c_, d_)):
                mids = [((p[0] + q[0]) // 2, (p[1] + q[1]) // 2)
                        for p, q in ((p1, p2), (p2, p3), (p3, p1))]
                elements.append(tuple(number(*p) for p in (p1, p2, p3, *mids)))

    if nodes_per_element == 3:
        elements = split_into_three_node(elements)
    last = 2 * n_radial
    return RadialMesh(
        nodes=nodes, elements=elements,
        hole=[number(0, k) for k in range(n_half_t + 1)],
        outer=[number(last, k) for k in range(n_half_t + 1)],
        x_axis=[number(i, 0) for i in range(last + 1)],
        y_axis=[number(i, n_half_t) for i in range(last + 1)],
        radii=radii, inner_radius=a, outer_radius=b)

