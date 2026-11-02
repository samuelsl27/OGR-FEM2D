# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The strip load of spec 002 (case 004, ficha VER-STR-04), built for the
engine, and Michell's stresses the tests compare (not a test file).

The model (validacion/casos/004-carga-en-faja-elastica/caso.md): half of the
half-space by symmetry, 0 <= x <= W, -D <= y <= 0, y up, the surface at
y = 0 and the depth z = -y; a pressure q on 0 <= x <= b. Two boundaries:

* ``supported``: u = 0 on x = 0 (symmetry) and on x = W, u = v = 0 on
  y = -D: the case, whose answer moves with W and D;
* ``exact``: u = 0 on x = 0, and on x = W and y = -D the tractions of
  Michell's own solution, sigma . n, as consistent nodal forces, with one v
  held to stop the vertical translation: the truncated half-space carries
  exactly the stresses of the infinite one, so the error is only the
  discretization (the identity of spec 002, «Validación»).

Michell's stresses in components: T&G §34 gives the principal values and
that sigma_1 bisects the angle between the radii to the edges (angle beta
from the vertical, strip_principal). With d = (sin beta, cos beta) in
(x, z), z downward, sigma = sigma_1 d d^T + sigma_3 e e^T, e perpendicular
to d (the tensor of JCZ 2007, Eq. 2.30, from its principal axes). In the
engine's (x, y), y = -z, so sigma_yy = sigma_zz and tau_xy = -tau_xz, and
the engine is tension-positive (D1).

The mesh: mesh_structured.rectangle on graded lines, with cells of h0 on
the strip and geometric growth g away from it, in x beyond the strip and
in depth.
"""
from __future__ import annotations

import importlib.util
import math
import sys
from pathlib import Path

from ogr_fem2d.engine import analysis
from ogr_fem2d.engine import model as m
from ogr_fem2d.engine.mesh_structured import graded, rectangle
from ogr_fem2d.engine.reference import loads
from ogr_fem2d.engine.reference.elastic import Elastic

_CHECKS = (Path(__file__).resolve().parents[1] / "spec" / "features"
           / "002-motor-elastico" / "comprobaciones" / "soluciones_cerradas.py")
_spec = importlib.util.spec_from_file_location("soluciones_cerradas_002", _CHECKS)
if _spec.name in sys.modules:
    closed = sys.modules[_spec.name]
else:
    closed = importlib.util.module_from_spec(_spec)
    sys.modules[_spec.name] = closed
    _spec.loader.exec_module(closed)

Q, B, E, NU = closed.Q, closed.B_HALF, 20000.0, 0.2


def michell_components(x: float, z: float) -> tuple[float, float, float]:
    """(sigma_xx, sigma_zz, tau_xz), compression positive, x horizontal and
    z downward, from the principal stresses and their direction."""
    s1, s3, beta = closed.strip_principal(x, z)
    s, c = math.sin(beta), math.cos(beta)
    return (s1 * s * s + s3 * c * c, s1 * c * c + s3 * s * s, (s1 - s3) * s * c)


def engine_stress(x: float, y: float) -> tuple[float, float, float]:
    """Michell's (sigma_xx, sigma_yy, tau_xy) in the engine's frame and
    sign (y up, tension positive)."""
    sxx, szz, txz = michell_components(x, -y)
    return -sxx, -szz, txz


def lines(start: float, end: float, h0: float, growth: float) -> list[float]:
    """Graded lines from ``start`` to ``end``, the first cell about h0."""
    length = abs(end - start)
    if growth == 1.0:
        n = max(1, round(length / h0))
    else:
        n = max(1, math.ceil(math.log(1 + length * (growth - 1) / h0) / math.log(growth)))
    return graded(start, end, n, growth)


def mesh_for(w: float, d: float, h0: float, growth: float, nodes_per_element: int = 6):
    xs = lines(0.0, B, h0, 1.0) + lines(B, w, h0, growth)[1:]
    zs = lines(0.0, 5.0, h0, growth)
    last = zs[-1] - zs[-2]
    if d > 5.0:
        zs += lines(5.0, d, last * growth, growth)[1:]
    ys = sorted(-z for z in zs)
    return rectangle(xs, ys, nodes_per_element, "alternate")


def _side_forces(mesh, element, side, traction):
    """Consistent nodal forces of an arbitrary traction t(x, y) on one side,
    int N t ds with Gauss-Legendre (Table 9.1, ten points): what an edge
    load does, with the exact traction at each point instead of a linear
    one."""
    nodes = [mesh.elements[element][k] for k in loads.side_nodes(len(mesh.elements[element]), side)]
    xy = [mesh.nodes[n] for n in nodes]
    f = {n: [0.0, 0.0] for n in nodes}
    for xi, w in loads.GAUSS_LEGENDRE_10:
        s = 0.5 * (1.0 + xi)
        shape, dshape = loads.side_functions(len(nodes), s)
        x = sum(a * p[0] for a, p in zip(shape, xy))
        y = sum(a * p[1] for a, p in zip(shape, xy))
        length = math.hypot(sum(a * p[0] for a, p in zip(dshape, xy)),
                            sum(a * p[1] for a, p in zip(dshape, xy)))
        tx, ty = traction(x, y)
        for n, a in zip(nodes, shape):
            f[n][0] += 0.5 * w * length * a * tx
            f[n][1] += 0.5 * w * length * a * ty
    return f


def model(w: float, d: float, h0: float, growth: float, nodes_per_element: int = 6,
          boundary: str = "supported"):
    mesh = mesh_for(w, d, h0, growth, nodes_per_element)
    bnd = mesh.boundary
    strip = tuple(m.EdgeLoad(e, side, (-Q, 0.0), (-Q, 0.0), normal=True)
                  for e, side in mesh.boundary_sides["top"]
                  if max(mesh.nodes[mesh.elements[e][k]][0] for k in (side, (side + 1) % 3)) <= B)
    held: dict[int, list[bool]] = {}

    def hold(nodes, x, y):
        for n in nodes:
            flags = held.setdefault(n, [False, False])
            flags[0], flags[1] = flags[0] or x, flags[1] or y

    hold(bnd["left"], True, False)                       # symmetry
    nodal = []
    if boundary == "supported":
        hold(bnd["right"], True, False)
        hold(bnd["bottom"], True, True)
    elif boundary == "exact":
        hold(bnd["bottom"][:1], False, True)             # stops the vertical translation
        forces: dict[int, list[float]] = {}
        right = lambda x, y: (engine_stress(x, y)[0], engine_stress(x, y)[2])     # n = (1, 0)
        bottom = lambda x, y: (-engine_stress(x, y)[2], -engine_stress(x, y)[1])  # n = (0, -1)
        for name, traction in (("right", right), ("bottom", bottom)):
            for e, side in mesh.boundary_sides[name]:
                for n, (fx, fy) in _side_forces(mesh, e, side, traction).items():
                    acc = forces.setdefault(n, [0.0, 0.0])
                    acc[0] += fx
                    acc[1] += fy
        nodal = [m.NodalLoad(n, fx, fy) for n, (fx, fy) in sorted(forces.items())]
    else:
        raise ValueError(boundary)
    restraints = tuple(m.Restraint(n, x, y) for n, (x, y) in sorted(held.items()))
    stage = m.Stage(active=(True,) * len(mesh.elements), restraints=restraints,
                    nodal_loads=tuple(nodal), edge_loads=strip, tolerance=1e-10, max_iterations=5)
    return mesh, m.EngineModel(m.PLANE_STRAIN, tuple(mesh.nodes), tuple(mesh.elements),
                               (m.Material(Elastic(E, NU)),), (0,) * len(mesh.elements), (stage,))


def principal_compressive(stress) -> tuple[float, float]:
    """(sigma_1, sigma_3) in the plane, compression positive."""
    sxx, syy, _, txy = (-v for v in stress)
    centre, radius = 0.5 * (sxx + syy), math.hypot(0.5 * (sxx - syy), txy)
    return centre + radius, centre - radius


def worst_errors(mesh, engine_model, outcome, z_min=0.25, z_max=5.0):
    """The largest |sigma_1 - Michell| and |sigma_3 - Michell|, over q, at
    the integration points of the first column of elements with z_min <= z
    <= z_max, each against Michell at its own (x, z)."""
    from ogr_fem2d.engine import initial_stress as ini
    points = ini.integration_point_coordinates(engine_model)
    per = len(points) // len(engine_model.elements)
    first = mesh.xs[1] * (1 + 1e-12)
    e1 = e3 = 0.0
    count = 0
    for e, element in enumerate(engine_model.elements):
        if max(mesh.nodes[n][0] for n in element) > first:
            continue
        for g in range(e * per, (e + 1) * per):
            x, y = points[g]
            if not z_min <= -y <= z_max:
                continue
            s1, s3 = principal_compressive(outcome.stresses[g])
            m1, m3, _ = closed.strip_principal(x, -y)
            e1, e3 = max(e1, abs(s1 - m1) / Q), max(e3, abs(s3 - m3) / Q)
            count += 1
    assert count, "no point in the compared column"
    return e1, e3


def solve(w, d, h0, growth, nodes_per_element=6, boundary="supported", variant=None):
    mesh, engine_model = model(w, d, h0, growth, nodes_per_element, boundary)
    kwargs = {} if variant is None else {"variant": variant}
    return mesh, engine_model, analysis.run(engine_model, **kwargs)[0]
