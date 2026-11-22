# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The radial mesh: a structured mesh of a full annulus a <= r <= b around one
circular hole (spec 003, RF-8, D8). It is for verification: reproducible and
symmetric, as the radial mesh of the reference program is meant to be. It is
not built from a geometry and does not go through the refinement; the outer
circle is its own.

How it is built. The polar grid r_0 = a < ... < r_n = b (the progression of
``engine/mesh_radial.graded_radii``: dr_(i+1) = growth dr_i, a geometric
progression, growth = 1 uniform) by n_theta equal angles. Each cell is cut by
the same diagonal into two triangles, anticlockwise in the (r, theta) plane
and therefore in the plane (the polar map has det = r > 0). Corners at their
exact polar images (the points on the axes x and y exactly there, as in
``mesh_radial``). With six-node triangles, the sides of constant r are arcs
about the centre and get their mid-side node on the circle; the others, in
the middle (``quadratic.promote``, D4).

The hole is not meshed: the annulus is the domain, and an excavation enters
as in case 001, by the initial stress of the elements left (Zienkiewicz and
Taylor 2000, Eq. 2.13b). Meshing the disc in a polar grid would put a fan of
degenerate triangles at its centre. The radial mesh is plane strain: about a
centre, the annulus reaches x < 0.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from ..engine.mesh_radial import graded_radii
from ..engine.model import Problem
from . import checks, quadratic
from .geometry import MeshInputError, _finite
from .mesher import Mesh, boundary_map

#: The rules of radial_settings_problems.
RULES = ("radius", "divisions", "growth", "element_kind")


@dataclass(frozen=True)
class RadialSettings:
    """The radial mesh (D8): hole radius ``a``, outer radius ``b``, the
    divisions of the hole ``n_theta`` (at least 3, so every arc is below 180
    degrees), the radial divisions ``n_radial``, the growth of consecutive
    radial divisions, the element and the material of all its elements."""
    a: float
    b: float
    n_theta: int
    n_radial: int
    growth: float = 1.0
    nodes_per_element: int = 6
    centre: tuple[float, float] = (0.0, 0.0)
    material: int = 0


def problems(s: RadialSettings) -> list[Problem]:
    out = []
    if not (_finite(s.a, s.b, *s.centre) and 0.0 < s.a < s.b):
        out.append(Problem("radius", "settings", f"needs 0 < a < b; a = {s.a!r}, b = {s.b!r}"))
    for name, value, least in (("n_theta", s.n_theta, 3), ("n_radial", s.n_radial, 1)):
        if not (isinstance(value, int) and not isinstance(value, bool) and value >= least):
            out.append(Problem("divisions", "settings",
                               f"{name} = {value!r} is not an integer >= {least}"))
    if not (_finite(s.growth) and s.growth > 0.0):
        out.append(Problem("growth", "settings", f"growth {s.growth!r} is not > 0"))
    if s.nodes_per_element not in (3, 6):
        out.append(Problem("element_kind", "settings",
                           f"nodes_per_element {s.nodes_per_element!r} is not 3 or 6"))
    return out


def _point(centre, r: float, j: int, n: int) -> tuple[float, float]:
    """The corner at radius r and angle 2 pi j / n; on the four half-axes,
    exactly there."""
    quarter = 4 * j
    if quarter % n == 0:
        dx, dy = ((r, 0.0), (0.0, r), (-r, 0.0), (0.0, -r))[(quarter // n) % 4]
    else:
        t = 2.0 * math.pi * j / n
        dx, dy = r * math.cos(t), r * math.sin(t)
    return (centre[0] + dx, centre[1] + dy)


def radial_mesh(s: RadialSettings) -> Mesh:
    """The radial mesh of ``s``, with its boundaries "hole" and "outer"."""
    found = problems(s)
    if found:
        raise MeshInputError(found)
    radii = graded_radii(s.a, s.b, s.n_radial, s.growth)
    n = s.n_theta
    nodes = [_point(s.centre, r, j, n) for r in radii for j in range(n)]

    def node(i: int, j: int) -> int:
        return i * n + (j % n)

    triangles = []
    for i in range(s.n_radial):
        for j in range(n):
            p00, p10, p11, p01 = node(i, j), node(i + 1, j), node(i + 1, j + 1), node(i, j + 1)
            triangles += [(p00, p10, p11), (p00, p11, p01)]
    elements = triangles
    if s.nodes_per_element == 6:
        arcs = {quadratic.edge_key(node(i, j), node(i, j + 1)): s.centre
                for i in range(s.n_radial + 1) for j in range(n)}
        quad = quadratic.promote(nodes, triangles, arcs)
        nodes, elements = list(quad.nodes), list(quad.elements)
    hole = [node(0, j) for j in range(n)] + [node(0, 0)]
    outer = [node(s.n_radial, j) for j in range(n)] + [node(s.n_radial, 0)]
    report = checks.check(nodes, elements, "plane_strain")
    notes = {"kind": "radial", "a": s.a, "b": s.b, "n_theta": n, "n_radial": s.n_radial,
             "growth": s.growth, "radii": tuple(radii), "nodes_per_element": s.nodes_per_element}
    return Mesh("plane_strain", tuple(nodes), tuple(tuple(e) for e in elements),
                (0,) * len(elements), (s.material,) * len(elements),
                boundary_map(elements, [("hole", hole), ("outer", outer)]),
                notes, report.warnings)
