# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The circular-hole model of spec 001, built for the engine, and the polar
quantities the tests compare (not a test file: the runner only collects
test_*.py).

The model (spec 001, plan, «Simetría» and «Excavación»): the quarter annulus
a <= r <= b of mesh_radial, rollers on the two axes (v = 0 on the x axis,
u = 0 on the y axis), the outer boundary fixed in both directions, every
point starting at the field stress of the cases, hydrostatic p0 = 30 MPa of
compression in the three directions, and the stage's total external load
zero: the hole is left free.

Signs: the engine is tension-positive with u outward (D1); the closed forms
of comprobaciones/soluciones_cerradas.py are compression-positive with u
inward. The conversion is here, in one place.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

from ogr_fem2d.engine.mesh_radial import quarter_annulus
from ogr_fem2d.engine.reference import solver

_CHECKS = (Path(__file__).resolve().parents[1] / "spec" / "features"
           / "001-prueba-de-concepto" / "comprobaciones")
if str(_CHECKS) not in sys.path:
    sys.path.insert(0, str(_CHECKS))
import soluciones_cerradas as closed  # noqa: E402

A = closed.A
P0 = closed.P0
FIELD = (-P0, -P0, -P0, 0.0)          # tension-positive, sigma_zz included


def model(b, n_radial, n_theta, growth, material):
    mesh = quarter_annulus(A, b, n_radial, n_theta, growth)
    restrained = set()
    for n in mesh.x_axis:
        restrained.add(2 * n + 1)
    for n in mesh.y_axis:
        restrained.add(2 * n)
    for n in mesh.outer:
        restrained |= {2 * n, 2 * n + 1}
    return mesh, solver.Model(mesh.nodes, mesh.elements,
                              [material] * len(mesh.elements),
                              frozenset(restrained))


def excavate(b, n_radial, n_theta, growth, material, steps, tolerance,
             max_iterations):
    mesh, m = model(b, n_radial, n_theta, growth, material)
    n_points = 3 * len(mesh.elements)
    result = solver.solve_stage(m, [FIELD] * n_points,
                                [0.0] * (2 * len(mesh.nodes)), steps,
                                tolerance, max_iterations)
    return mesh, result


def radial_inward(mesh, result, node):
    """u_r positive inward at a node: the convention of the closed forms."""
    x, y = mesh.nodes[node]
    r = math.hypot(x, y)
    return -(result.displacement[2 * node] * x
             + result.displacement[2 * node + 1] * y) / r


def polar_compressive(point, stress):
    """(r, sigma_r, sigma_theta, sigma_z) at an integration point,
    compression positive."""
    x, y = point.xy
    r = math.hypot(x, y)
    c, s = x / r, y / r
    s_xx, s_yy, s_zz, t_xy = stress
    sigma_r = s_xx * c * c + s_yy * s * s + 2.0 * t_xy * s * c
    sigma_t = s_xx * s * s + s_yy * c * c - 2.0 * t_xy * s * c
    return r, -sigma_r, -sigma_t, -s_zz
