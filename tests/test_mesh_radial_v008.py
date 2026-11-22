# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.0.8 (spec 003, T8) — the radial mesh of a full annulus (RF-8, D8;
ogr_fem2d/mesh/radial.py).

Invariants protected:

* **the grid**: radii from a to b with dr_(i+1) = growth dr_i, n_theta equal
  angles, every corner at its polar image, those on the axes exactly there;
* **the mesh is sound**: one hole by Euler, one piece, no warning, every
  element one to one (checks.py); six-node sides of constant r on their
  circle; the boundaries "hole" and "outer" are the circles r = a and r = b;
* **it computes the annulus**: the excavation of a hole of 1 m in a
  hydrostatic field of 30 MPa (the data of STR-01), on the annulus to
  b = 100 m with the outer circle fixed, gives sigma_theta(a) and u_r(a)
  within 0.5 % of the exact solution of that ring (lame_fixed_outer, spec
  001, from Jaeger, Cook and Zimmerman 2007, Eqs. 8.78-8.81), at every
  integration point and every node on the hole, with the mesh density of
  the mesh that fixes case 001 (8 angular divisions a quarter, 32 radial,
  growth 1.69^(1/4));
* **bad settings are refused, all at once**.
"""
from __future__ import annotations

import math

from _hole import closed

from ogr_fem2d.engine import analysis
from ogr_fem2d.engine import model as em
from ogr_fem2d.engine.reference.elastic import Elastic
from ogr_fem2d.mesh import checks
from ogr_fem2d.mesh import geometry as g
from ogr_fem2d.mesh import radial

S = radial.RadialSettings(a=1.0, b=5.0, n_theta=12, n_radial=4, growth=1.3)


class TestTheGrid:
    def test_radii_angles_and_the_axes(self):
        mesh = radial.radial_mesh(radial.RadialSettings(1.0, 5.0, 12, 4, 1.3, 3))
        radii = mesh.notes["radii"]
        assert radii[0] == 1.0 and radii[-1] == 5.0
        dr = [radii[i + 1] - radii[i] for i in range(4)]
        for i in range(3):
            assert math.isclose(dr[i + 1], 1.3 * dr[i], rel_tol=1e-13)
        for i, r in enumerate(radii):
            for j in range(12):
                x, y = mesh.nodes[i * 12 + j]
                t = 2 * math.pi * j / 12
                assert math.isclose(x, r * math.cos(t), abs_tol=1e-15 * r)
                assert math.isclose(y, r * math.sin(t), abs_tol=1e-15 * r)
        assert (0.0, 1.0) in mesh.nodes and (-5.0, 0.0) in mesh.nodes and (0.0, -5.0) in mesh.nodes


class TestSound:
    def test_one_hole_one_piece_no_warning(self):
        for npe in (3, 6):
            mesh = radial.radial_mesh(radial.RadialSettings(1.0, 5.0, 12, 4, 1.3, npe))
            topo = checks.topology(mesh.nodes, mesh.elements)
            assert (topo.holes, topo.components, mesh.warnings) == (1, 1, ())
            assert checks.element_problems(mesh.nodes, mesh.elements, "plane_strain") == []

    def test_every_element_takes_the_material(self):
        mesh = radial.radial_mesh(radial.RadialSettings(1.0, 5.0, 12, 2, material=2))
        assert set(mesh.element_material) == {2} and set(mesh.element_region) == {0}

    def test_too_few_angles_fold_the_six_node_triangles(self):
        # with 4 angles of 90 degrees, the sagitta of an arc, R (1 - cos 45),
        # is wider than its ring of elements: the curved side crosses the
        # triangle and det J changes sign (Zienkiewicz and Taylor 2000, §9.2);
        # with chords (three nodes) nothing folds
        try:
            radial.radial_mesh(radial.RadialSettings(1.0, 5.0, 4, 2))
        except checks.MeshError as e:
            assert {p.rule for p in e.problems} == {"jacobian"}, e.problems
        else:
            raise AssertionError("not refused")
        radial.radial_mesh(radial.RadialSettings(1.0, 5.0, 4, 2, nodes_per_element=3))

    def test_curved_sides_and_the_two_circles(self):
        mesh = radial.radial_mesh(S)
        for name, r in (("hole", 1.0), ("outer", 5.0)):
            b = mesh.boundary(name)
            assert len(b.nodes) == 13 and b.nodes[0] == b.nodes[-1]
            for n in b.nodes + b.mids:
                assert abs(math.hypot(*mesh.nodes[n]) - r) <= 4e-16 * r, (name, n)
            assert all(len(found) == 1 for found in b.sides)


class TestTheAnnulus:
    def test_the_excavation_against_the_exact_ring(self):
        b = 100.0
        mesh = radial.radial_mesh(radial.RadialSettings(1.0, b, 32, 32, 1.69 ** 0.25))
        outer = set(mesh.boundary("outer").nodes + mesh.boundary("outer").mids)
        stage = em.Stage(active=(True,) * len(mesh.elements),
                         restraints=tuple(em.Restraint(n, True, True) for n in sorted(outer)),
                         tolerance=1e-12)
        model = em.EngineModel("plane_strain", mesh.nodes, mesh.elements,
                               (em.Material(Elastic(closed.E, closed.NU)),),
                               mesh.element_material, (stage,))
        field = (-closed.P0, -closed.P0, -closed.P0, 0.0)          # tension positive
        model = em.EngineModel(model.analysis, model.nodes, model.elements, model.materials,
                               model.element_material, model.stages, (field,) * model.n_points)
        out = analysis.run(model)[0]
        _s_r, s_t, u_in = closed.lame_fixed_outer(1.0, b)

        hole = mesh.boundary("hole")
        for n in hole.nodes + hole.mids:
            x, y = mesh.nodes[n]
            ur_in = -(out.displacement[2 * n] * x + out.displacement[2 * n + 1] * y)
            assert abs(ur_in - u_in) <= 0.005 * u_in, (n, ur_in, u_in)
        # T6, plane strain: the integration points are the mid-side points, so
        # those of the hole's sides are on r = a
        from ogr_fem2d.engine.initial_stress import integration_point_coordinates
        points = integration_point_coordinates(model)
        on_hole = [k for k, p in enumerate(points) if abs(math.hypot(*p) - 1.0) < 1e-12]
        assert len(on_hole) == 32
        for k in on_hole:
            sxx, syy, _szz, txy = out.stresses[k]
            x, y = points[k]
            c, s = x, y                                    # r = 1
            hoop = sxx * s * s + syy * c * c - 2.0 * txy * s * c
            assert abs(-hoop - s_t) <= 0.005 * s_t, (k, -hoop, s_t)


class TestSettings:
    def test_refused_all_at_once(self):
        bad = radial.RadialSettings(a=2.0, b=1.0, n_theta=2, n_radial=0, growth=0.0,
                                    nodes_per_element=4)
        try:
            radial.radial_mesh(bad)
        except g.MeshInputError as e:
            assert sorted({p.rule for p in e.problems}) == sorted(radial.RULES)
        else:
            raise AssertionError("not refused")

    def test_two_divisions_of_the_hole_are_half_circles(self):
        assert [p.rule for p in radial.problems(radial.RadialSettings(1.0, 5.0, 2, 4))] == \
            ["divisions"]
        assert radial.problems(radial.RadialSettings(1.0, 5.0, 3, 4)) == []
