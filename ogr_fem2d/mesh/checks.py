# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The checks of a mesh before it is delivered (spec 003, RF-13 and RF-14).

**A valid element** (RF-13). The map from the parent triangle is one to one
when the determinant of its jacobian keeps its sign over the element
(Zienkiewicz and Taylor 2000, §9.2, pp. 205-206; the matrix J, §9.5, Eqs.
(9.10)-(9.11), pp. 208-209). In a three-node triangle det J is constant,
twice the area. In a six-node triangle it is a polynomial of degree 2, and
its minimum over the whole element is found exactly (``minimum_det``); it is
also checked, to name the place, at the six nodes and at the integration
points of the rule the engine uses (``quadrature.rule_for``).

The plan first said "the nodes and the integration points". That is not
enough (found in T6, spec 003 changelog): an element with det J > 0 at its
six nodes can fold inside, and in plane strain the integration points of the
six-node triangle are its mid-side nodes, so the engine would compute it
with positive determinants everywhere it looks.

On a straight side with its mid-side node at a fraction t of the side from a
corner, dx/dxi at that corner is L (4t - 1) and at the other one L (3 - 4t):
det J vanishes at t = 1/4 and 3/4, which is the "middle half" of the source
(fig. 9.6), and the check at the nodes is that rule.

A determinant below ``model.SLIVER`` times twice the square of the longest
side is taken as zero: it is the engine's own threshold for a degenerate
corner triangle (2A <= 2 SLIVER L^2).

**A conforming, connected mesh** (RF-14), on the corners:

* every side belongs to one or two elements, and no node lies inside a
  side of the boundary (a hanging node);
* the elements are connected through their sides (more than one piece is a
  warning: each piece then needs its own restraints);
* a node where elements meet in more than one fan (two regions joined by a
  node alone) is a warning;
* Euler's relation for a plane triangulation, V - E + T = C - H, gives the
  number of holes H of the meshed domain, C being its pieces (a classical
  theorem, not in the bibliography).

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from ..engine.model import SLIVER, Problem
from ..engine.reference import element_t3, element_t6, triangle
from ..engine.reference.quadrature import rule_for
from .geometry import _orient
from .quadratic import edge_key

Point = tuple[float, float]


class MeshError(ValueError):
    """The mesh cannot be delivered: every problem found."""

    def __init__(self, problems: list[Problem]):
        self.problems = problems
        super().__init__("the mesh is not valid:\n" + "\n".join(f"  {p}" for p in problems))


def jacobian_dets(xy: Sequence[Point], analysis: str) -> list[tuple[str, float]]:
    """det J of an element at the points where it is checked, each with its
    name: the nodes, then the integration points of the engine's rule."""
    n = len(xy)
    shape = element_t6 if n == 6 else element_t3
    nodes_l = shape.NODES_L
    out = []
    for k, ls in enumerate(nodes_l):
        out.append((f"node {k}", triangle.jacobian(shape, list(xy), *ls)[1]))
    for k, (ls, _w) in enumerate(rule_for(n, analysis).points):
        out.append((f"integration point {k}", triangle.jacobian(shape, list(xy), *ls)[1]))
    return out


def minimum_det(xy: Sequence[Point]) -> tuple[float, tuple[float, float]]:
    """The minimum of det J over the whole element and where it is, (xi,
    eta), for a six-node triangle (a three-node one has det J constant).

    det J is a polynomial of degree 2 in (xi, eta): the entries of J are
    derivatives of the quadratic map, linear, and det J is a product of two
    of them. The quadratic interpolation through the six nodes reproduces any
    polynomial of degree 2, so det J = p(xi, eta) = c0 + c1 xi + c2 eta
    + c3 xi^2 + c4 xi eta + c5 eta^2 with the coefficients that match it at
    the six nodes. The minimum of p over the closed triangle is at a corner,
    at the stationary point of p along a side if it falls inside the side,
    or at the stationary point inside (a 2 x 2 linear system): elementary
    calculus, no further source."""
    if len(xy) == 3:
        det = triangle.jacobian(element_t3, list(xy), 1.0, 0.0, 0.0)[1]
        return det, (0.0, 0.0)
    d = [triangle.jacobian(element_t6, list(xy), *ls)[1] for ls in element_t6.NODES_L]
    # nodes (xi, eta): (0,0) (1,0) (0,1) (1/2,0) (1/2,1/2) (0,1/2)
    c0 = d[0]
    c3 = 2.0 * d[1] + 2.0 * d[0] - 4.0 * d[3]
    c1 = -3.0 * d[0] - d[1] + 4.0 * d[3]
    c5 = 2.0 * d[2] + 2.0 * d[0] - 4.0 * d[5]
    c2 = -3.0 * d[0] - d[2] + 4.0 * d[5]
    c4 = 4.0 * (d[4] - c0 - 0.5 * c1 - 0.5 * c2 - 0.25 * c3 - 0.25 * c5)

    def p(x: float, y: float) -> float:
        return c0 + c1 * x + c2 * y + c3 * x * x + c4 * x * y + c5 * y * y

    candidates = [(0.0, 0.0), (1.0, 0.0), (0.0, 1.0)]
    for (ax, ay), (bx, by) in (((0.0, 0.0), (1.0, 0.0)), ((1.0, 0.0), (0.0, 1.0)),
                               ((0.0, 1.0), (0.0, 0.0))):
        pa, pm, pb = p(ax, ay), p(0.5 * (ax + bx), 0.5 * (ay + by)), p(bx, by)
        a2 = 2.0 * pa - 4.0 * pm + 2.0 * pb           # q(t) = pa + b1 t + a2 t^2
        b1 = -3.0 * pa + 4.0 * pm - pb
        if a2 != 0.0:
            t = -b1 / (2.0 * a2)
            if 0.0 < t < 1.0:
                candidates.append((ax + t * (bx - ax), ay + t * (by - ay)))
    det2 = 4.0 * c3 * c5 - c4 * c4                    # grad p = 0
    if det2 != 0.0:
        x = (-2.0 * c5 * c1 + c4 * c2) / det2
        y = (-2.0 * c3 * c2 + c4 * c1) / det2
        if x > 0.0 and y > 0.0 and x + y < 1.0:
            candidates.append((x, y))
    value, where = min((p(x, y), (x, y)) for x, y in candidates)
    return value, where


def element_problems(nodes: Sequence[Point], elements: Sequence[tuple[int, ...]],
                     analysis: str) -> list[Problem]:
    """RF-13: every element whose jacobian does not stay positive over the
    whole element (``minimum_det``), and, as the points the engine uses, at
    its nodes and integration points."""
    return [p for _e, p in indexed_element_problems(nodes, elements, analysis)]


def indexed_element_problems(nodes: Sequence[Point], elements: Sequence[tuple[int, ...]],
                             analysis: str) -> list[tuple[int, Problem]]:
    """``element_problems`` with the index of every element rejected."""
    out = []
    for e, element in enumerate(elements):
        xy = [nodes[i] for i in element]
        corners = xy[:3]
        longest = max((corners[k][0] - corners[(k + 1) % 3][0])
                      * (corners[k][0] - corners[(k + 1) % 3][0])
                      + (corners[k][1] - corners[(k + 1) % 3][1])
                      * (corners[k][1] - corners[(k + 1) % 3][1]) for k in range(3))
        floor = 2.0 * SLIVER * longest
        lowest, at = minimum_det(xy)
        checked = jacobian_dets(xy, analysis) + [(f"(xi, eta) = ({at[0]:.4g}, {at[1]:.4g}), "
                                                  "its minimum", lowest)]
        for where, det in checked:
            if det <= floor:
                out.append((e, Problem(
                    "jacobian", f"element {e}, {where}",
                    f"det J = {det:.6g}: the map from the parent triangle is not one to one "
                    "(Zienkiewicz and Taylor 2000, §9.2); a mid-side node outside the middle "
                    "half of its side, or an inverted or flat element")))
                break
    return out


@dataclass(frozen=True)
class Topology:
    """What the corners of a mesh say about its shape."""
    vertices: int
    edges: int
    triangles: int
    over_shared: tuple[tuple[int, int], ...]       # sides of three elements or more
    hanging: tuple[tuple[int, tuple[int, int]], ...]  # (node, boundary side it lies in)
    components: int
    pinches: tuple[int, ...]                       # nodes joining fans of elements
    boundary: tuple[tuple[int, int], ...]          # sides of one element

    @property
    def holes(self) -> int:
        """H = C - (V - E + T), meaningful for a conforming mesh without
        pinches."""
        return self.components - (self.vertices - self.edges + self.triangles)


def topology(nodes: Sequence[Point], elements: Sequence[tuple[int, ...]]) -> Topology:
    corners = [tuple(e[:3]) for e in elements]
    uses: dict[tuple[int, int], list[int]] = {}
    for k, (a, b, c) in enumerate(corners):
        for i, j in ((a, b), (b, c), (c, a)):
            uses.setdefault(edge_key(i, j), []).append(k)
    over = tuple(key for key, els in uses.items() if len(els) > 2)
    boundary = tuple(key for key, els in uses.items() if len(els) == 1)

    on_boundary = sorted({i for key in boundary for i in key})
    hanging = []
    for key in boundary:
        a, b = nodes[key[0]], nodes[key[1]]
        for w in on_boundary:
            if w in key:
                continue
            p = nodes[w]
            if (_orient(a, b, p) == 0 and min(a[0], b[0]) <= p[0] <= max(a[0], b[0])
                    and min(a[1], b[1]) <= p[1] <= max(a[1], b[1])):
                hanging.append((w, key))

    # pieces: elements connected through their sides (union-find)
    parent = list(range(len(corners)))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for els in uses.values():
        for k in els[1:]:
            ra, rb = find(els[0]), find(k)
            if ra != rb:
                parent[max(ra, rb)] = min(ra, rb)
    components = len({find(k) for k in range(len(corners))})

    # pinches: around a node, its elements connected through the sides that
    # contain the node; more than one group is a node joining fans
    around: dict[int, list[int]] = {}
    for k, tri in enumerate(corners):
        for i in tri:
            around.setdefault(i, []).append(k)
    pinches = []
    for i in sorted(around):
        els = around[i]
        group = {els[0]}
        grown = True
        while grown:
            grown = False
            for k in els:
                if k in group:
                    continue
                if any(i in key and k in uses[key] and any(o in group for o in uses[key])
                       for key in (edge_key(i, j) for j in corners[k] if j != i)):
                    group.add(k)
                    grown = True
        if len(group) < len(els):
            pinches.append(i)
    vertices = len({i for tri in corners for i in tri})
    return Topology(vertices, len(uses), len(corners), over, tuple(hanging),
                    components, tuple(pinches), boundary)


@dataclass(frozen=True)
class Report:
    """The checks of a mesh: its topology and the warnings to show with it
    (rule 12)."""
    topology: Topology
    warnings: tuple[str, ...]


def check(nodes: Sequence[Point], elements: Sequence[tuple[int, ...]], analysis: str,
          found: Sequence[tuple[int, Problem]] | None = None) -> Report:
    """RF-13 and RF-14: raises MeshError with every element that is not one
    to one, every side of three elements and every hanging node; returns the
    topology and the warnings (pieces, pinches). ``found``: the result of
    ``indexed_element_problems`` for these elements, if the caller has it."""
    if found is None:
        found = indexed_element_problems(nodes, elements, analysis)
    problems = [p for _e, p in found]
    topo = topology(nodes, elements)
    for key in topo.over_shared:
        problems.append(Problem("over_shared", f"side {key[0]}-{key[1]}",
                                "belongs to three elements or more: the mesh is not conforming"))
    for w, key in topo.hanging:
        problems.append(Problem("hanging_node", f"node {w}",
                                f"lies inside side {key[0]}-{key[1]} without being one of its "
                                "ends: the mesh is not conforming"))
    if problems:
        raise MeshError(problems)
    warnings = []
    if topo.components > 1:
        warnings.append(f"the mesh is in {topo.components} pieces joined by no side: each "
                        "needs its own restraints")
    for i in topo.pinches:
        warnings.append(f"node {i} joins parts of the mesh that share no side there")
    return Report(topo, tuple(warnings))
