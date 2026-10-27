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

The Mohr-Coulomb half: the same ring and meshes, perfectly plastic
Mohr-Coulomb with psi = 0 and 30 degrees, against the exact solution of that
ring, ``salencon_edge_finite`` (spec 001, D8): Salençon (1969) with the edge
zone sigma_z = sigma_theta for r < 1.2814 m, where his hypothesis fails, and
u(b) = 0. Error: u_r at the nodes of the hole, the largest relative error.
Invariants:

* it falls with each halving, by at least a factor 2 (observed when the test
  was written, 5 steps: 70.7 %, 11.0 %, 1.13 % with psi = 0 and 143.8 %,
  52.8 %, 9.45 % with psi = 30; with psi = 30 the two next meshes of the
  family gave 1.84 % and 0.34 %, tasks.md, T8);
* the plastic radius, the farthest plastic integration point, is within one
  element (the radial size of the element that contains R0) of R0;
* the regions of the return: plastic points with r < r_e on the edge (sigma_z
  equal to an in-plane principal stress), the others on the main plane with
  sigma_z strictly between the in-plane principal stresses, on the finest of
  the three meshes and outside one element on each side of r_e (the mesh
  resolves the transition within an element, as it resolves R0).
"""
from __future__ import annotations

import math

import _hole
from ogr_fem2d.engine.reference import mohr_coulomb as mc
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


def _plastic_case(psi_degrees, n_radial, n_theta, growth):
    material = mc.MohrCoulomb(_hole.closed.E, _hole.closed.NU,
                              _hole.closed.COH, _hole.closed.PHI,
                              math.radians(psi_degrees))
    return _hole.excavate(B, n_radial, n_theta, growth, material, 5, 1e-10,
                          25, max_cuts=4)


class TestMohrCoulombRing:
    def test_the_error_falls_and_the_plastic_radius_is_right(self):
        for psi in (0.0, 30.0):
            exact = _hole.closed.salencon_edge_finite(B, math.radians(psi))
            errors = []
            for n_radial, n_theta, growth in MESHES:
                mesh, result = _plastic_case(psi, n_radial, n_theta, growth)
                errors.append(max(
                    abs(_hole.radial_inward(mesh, result, n) / exact["u_a"] - 1.0)
                    for n in mesh.hole))
                farthest = max(math.hypot(*p.xy) for p, plastic
                               in zip(result.points, result.plastic) if plastic)
                size = next(r2 - r1 for r1, r2 in zip(mesh.radii, mesh.radii[1:])
                            if r1 <= exact["R0"] <= r2)
                assert abs(farthest - exact["R0"]) <= size, (psi, farthest, size)
            for coarse, fine in zip(errors, errors[1:]):
                assert fine < 0.5 * coarse, (psi, errors)

    def test_edge_inside_r_e_and_plane_outside(self):
        r_e = _hole.closed.edge_radius()
        for psi in (0.0, 30.0):
            mesh, result = _plastic_case(psi, *MESHES[-1])
            # the transition is resolved within one element, as R0 is
            size = next(r2 - r1 for r1, r2 in zip(mesh.radii, mesh.radii[1:])
                        if r1 <= r_e <= r2)
            on_edge = on_plane = 0
            for point, stress, plastic in zip(result.points, result.stresses,
                                              result.plastic):
                if not plastic:
                    continue
                # the in-plane PRINCIPAL stresses (tension positive): with a
                # discretisation, tau_r_theta is small but not zero, so the
                # polar components are not exactly principal
                r = math.hypot(*point.xy)
                hi, lo, _ = mc.principal_in_plane(stress[0], stress[1], stress[3])
                s_z = stress[2]
                gap = min(abs(s_z - hi), abs(s_z - lo))
                if r < r_e - size:
                    assert gap < 1e-8 * _hole.P0, (psi, r, hi, lo, s_z)
                    on_edge += 1
                elif r > r_e + size:
                    assert lo + 1e-6 < s_z < hi - 1e-6, (psi, r, hi, lo, s_z)
                    on_plane += 1
            assert on_edge > 0 and on_plane > 0, (psi, on_edge, on_plane)
