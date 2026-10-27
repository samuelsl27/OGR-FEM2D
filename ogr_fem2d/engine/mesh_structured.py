# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Structured mesh of triangles on a rectangle, graded (spec 002, T10).

For the tests and the cases of spec 002 (the strip load of STR-04), not the
mesher of spec 003: the grid lines are given, x_0 < ... < x_m and
y_0 < ... < y_n, each cell is cut by one diagonal into two triangles, and
with six nodes the mid-side nodes sit at the midpoints of the straight
sides. ``graded`` makes the lines of a geometric progression, so the
elements can be small where the stresses change fast (under the edge of a
strip load) and large far away.

Diagonals: "up" from the bottom-left to the top-right corner of every cell,
"down" the other one, "alternate" the two in a checkerboard (a mesh that
does not lean to one side).

Element nodes as element_t3 and element_t6 expect them: corners
anticlockwise, then the mid-side node of side k (from corner k to k + 1).

The checks are identities (exact area, every inner side shared by two
elements with the same mid-side node, positive Jacobians), in
tests/test_mesh_structured_v002.py.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from dataclasses import dataclass

DIAGONALS = ("up", "down", "alternate")
SIDES = ("left", "right", "bottom", "top")


def graded(start: float, end: float, n: int, growth: float = 1.0) -> list[float]:
    """start = x_0, ..., x_n = end, with x_(i+1) - x_i = growth (x_i - x_(i-1)):
    a geometric progression (growth = 1, uniform; growth < 1, smaller
    towards ``end``). ``end`` may be below ``start``."""
    if n < 1 or growth <= 0.0 or start == end:
        raise ValueError("need n >= 1, growth > 0 and start != end")
    sizes = [growth ** i for i in range(n)]
    total = sum(sizes)
    lines = [start]
    for size in sizes[:-1]:
        lines.append(lines[-1] + (end - start) * size / total)
    lines.append(end)
    return lines


@dataclass(frozen=True)
class StructuredMesh:
    """Nodes, elements and what the boundary conditions need."""
    nodes: list[tuple[float, float]]
    elements: list[tuple[int, ...]]
    xs: list[float]
    ys: list[float]
    #: node numbers on each side of the rectangle, in increasing y (left,
    #: right) or x (bottom, top)
    boundary: dict[str, list[int]]
    #: (element, local side) of the element sides on each side of the
    #: rectangle, in increasing y or x: where edge loads go
    boundary_sides: dict[str, list[tuple[int, int]]]


def rectangle(xs: list[float], ys: list[float], nodes_per_element: int = 6,
              diagonal: str = "up") -> StructuredMesh:
    """The mesh of the rectangle [xs[0], xs[-1]] x [ys[0], ys[-1]] on the grid
    lines ``xs`` and ``ys`` (each increasing)."""
    if nodes_per_element not in (3, 6):
        raise ValueError("three or six nodes per element")
    if diagonal not in DIAGONALS:
        raise ValueError(f"diagonal must be one of {DIAGONALS}")
    for lines in (xs, ys):
        if len(lines) < 2 or any(b <= a for a, b in zip(lines, lines[1:])):
            raise ValueError("grid lines must be at least two and increasing")
    six = nodes_per_element == 6
    # The grid of nodes: with six nodes, the lines and their midpoints.
    if six:
        gx = [v for a, b in zip(xs, xs[1:]) for v in (a, 0.5 * (a + b))] + [xs[-1]]
        gy = [v for a, b in zip(ys, ys[1:]) for v in (a, 0.5 * (a + b))] + [ys[-1]]
    else:
        gx, gy = list(xs), list(ys)
    step = 2 if six else 1
    columns = len(gx)
    number = lambda i, j: j * columns + i
    nodes = [(x, y) for y in gy for x in gx]

    elements = []
    for cj, j in enumerate(range(0, len(gy) - 1, step)):
        for ci, i in enumerate(range(0, len(gx) - 1, step)):
            a, b = (i, j), (i + step, j)                 # bottom-left, bottom-right
            c, d = (i + step, j + step), (i, j + step)   # top-right, top-left
            up = diagonal == "up" or (diagonal == "alternate" and (ci + cj) % 2 == 0)
            triangles = ((a, b, c), (a, c, d)) if up else ((a, b, d), (b, c, d))
            for corners in triangles:
                element = [number(*p) for p in corners]
                if six:
                    element += [number((p[0] + q[0]) // 2, (p[1] + q[1]) // 2)
                                for p, q in zip(corners, corners[1:] + corners[:1])]
                elements.append(tuple(element))

    last_i, last_j = len(gx) - 1, len(gy) - 1
    boundary = {"left": [number(0, j) for j in range(last_j + 1)],
                "right": [number(last_i, j) for j in range(last_j + 1)],
                "bottom": [number(i, 0) for i in range(last_i + 1)],
                "top": [number(i, last_j) for i in range(last_i + 1)]}
    on = {"left": lambda p: p[0] == xs[0], "right": lambda p: p[0] == xs[-1],
          "bottom": lambda p: p[1] == ys[0], "top": lambda p: p[1] == ys[-1]}
    boundary_sides = {}
    for name in SIDES:
        found = []
        for e, element in enumerate(elements):
            for k in range(3):
                p, q = nodes[element[k]], nodes[element[(k + 1) % 3]]
                if on[name](p) and on[name](q):
                    found.append((min(p[1], q[1]) if name in ("left", "right")
                                  else min(p[0], q[0]), e, k))
        boundary_sides[name] = [(e, k) for _, e, k in sorted(found)]
    return StructuredMesh(nodes, elements, list(xs), list(ys), boundary, boundary_sides)
