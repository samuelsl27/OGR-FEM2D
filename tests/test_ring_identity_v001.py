# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.0.1 (spec 001, T8) — the ring of the case sheets, with its outer boundary
FIXED at 21 m, against the exact solution of that same ring (D3 bis): what is
left is the discretisation alone, and it must fall with every refinement.

The exact solution is ``lame_fixed_outer`` of comprobaciones/
soluciones_cerradas.py: the general solution of Jaeger, Cook and Zimmerman
(2007), Eqs. (8.78)-(8.81), with u(b) = 0, derived and checked in task T1.

Three nested meshes (n_theta doubles, n_radial doubles and the growth is
square-rooted, so every radius of a coarse mesh is a radius of the next one):
each halves the element size. Errors measured where the engine computes:

* u_r at every node, against the exact u_r at its radius, over u_r(a):
  the whole displacement field, the outer boundary included;
* u_r at the nodes of the hole, the largest relative error;
* sigma_theta at the integration points ON the hole (the quadratic rule of
  Table 9.2 puts one at the middle of each hole edge, on the circle), the
  largest relative error.

Invariant: all three fall with each halving. The orders observed when the
test was written (spec 001, tasks.md, T8): about 2.9 for u_r, and between 1.5
and 1.9 for sigma_theta, where Zienkiewicz and Taylor (2000), §14.1, p. 367,
give O(h^p) = O(h^2) for the stresses of quadratic elements. The test asks
for a fall of at least a factor 2 per halving (order >= 1): a lost order of
the element, or a wrong boundary, would stop the fall or slow it below that.

The Mohr-Coulomb half of T8 (against ``salencon_finite``) waits for the
owner's decision on the equilibrium iterations (changelog, T7).
"""
from __future__ import annotations

import math

import _hole
from ogr_fem2d.engine.reference.elastic import Elastic

B = 21.0
ELASTIC = Elastic(_hole.closed.E, _hole.closed.NU)
MESHES = [(6, 2, 1.44), (12, 4, 1.2), (24, 8, 1.2 ** 0.5)]   # n_r, n_theta, growth


def _errors(n_radial, n_theta, growth):
    mesh, result = _hole.excavate(B, n_radial, n_theta, growth, ELASTIC,
                                  1, 1e-10, 5)
    u_a = _hole.closed.lame_fixed_outer(_hole.A, B)[2]
    s_a = _hole.closed.lame_fixed_outer(_hole.A, B)[1]
    field = 0.0
    for n, (x, y) in enumerate(mesh.nodes):
        exact = _hole.closed.lame_fixed_outer(math.hypot(x, y), B)[2]
        field = max(field, abs(_hole.radial_inward(mesh, result, n) - exact) / u_a)
    hole_u = max(abs(_hole.radial_inward(mesh, result, n) / u_a - 1.0)
                 for n in mesh.hole)
    on_hole = []
    for point, stress in zip(result.points, result.stresses):
        r, _s_r, s_t, _s_z = _hole.polar_compressive(point, stress)
        if abs(r - _hole.A) < 1e-12:
            on_hole.append(abs(s_t / s_a - 1.0))
    # one integration point per hole edge, on the circle
    assert len(on_hole) == n_theta, (n_theta, len(on_hole))
    return field, hole_u, max(on_hole)


class TestElasticRing:
    def test_the_meshes_are_nested(self):
        from ogr_fem2d.engine.mesh_radial import graded_radii
        for (n1, _, g1), (n2, _, g2) in zip(MESHES, MESHES[1:]):
            coarse = graded_radii(_hole.A, B, n1, g1)
            fine = graded_radii(_hole.A, B, n2, g2)
            assert all(abs(c - f) < 1e-12 * B for c, f in zip(coarse, fine[::2]))

    def test_every_error_falls_with_each_halving(self):
        errors = [_errors(*m) for m in MESHES]
        names = ("u_r of the field", "u_r on the hole", "sigma_theta on the hole")
        for k, name in enumerate(names):
            series = [e[k] for e in errors]
            for coarse, fine in zip(series, series[1:]):
                assert fine < 0.5 * coarse, (name, series)
        # and the finest mesh is already close: within 0.5 % of u_r(a)
        assert errors[-1][1] < 5e-3, errors[-1]
