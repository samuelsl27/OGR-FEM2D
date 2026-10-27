# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.0.2 (spec 002, T8) — the initial stress fields (initial_stress.py).

Invariants protected:

* **the constant field is the tensor of its principal stresses**: its
  principal values are sigma_1 and sigma_3 and the angle of the major one
  is the one given, by Eqs. (2.31)-(2.33) of Jaeger, Cook and Zimmerman
  (2007), independent of the rotation used to build it; and the signs are
  the engine's (compression in, tension out);
* **the gravitational field is the weight of the column** (JCZ 2007,
  Eqs. 13.1 and 13.5): at any depth, sigma_v adds up the strata above and
  the horizontal stresses are K and Kz of the stratum the point is in;
* **the gravitational field is in equilibrium with the self weight**: a
  block of two horizontal strata, with rollers on its sides and bottom and
  the unit weights of the strata as its materials', does not move in a
  stage of gravity alone: exactly (the stage is rounding and is not
  solved) in plane strain with three- and six-node triangles, and in
  axisymmetry with six-node ones; with three-node triangles in axisymmetry
  the centroid does not integrate the terms of degree 2 exactly, and the
  displacement is not zero but falls with every halving of h (more than
  twice; observed 2.7 to 3.9, an order of 1.4 to 1.9 and not the 2 that
  task T1 expected). The reactions at the bottom carry the whole weight;
* **a constant field with the tractions it implies on the boundary** does
  not move either (a hydrostatic field and its pressure on the free sides);
* **the amendment of D3**: in axisymmetry K != Kz, and a constant field
  with sigma_r != sigma_theta or tau_rz != 0, are refused with the reason;
  the same are accepted in plane strain;
* **bad input**: sigma_1 < sigma_3, a point above the surface or below the
  strata, strata out of order or with negative values are refused.
"""
from __future__ import annotations

import math

import _blocks
from ogr_fem2d.engine import analysis
from ogr_fem2d.engine import initial_stress as ini
from ogr_fem2d.engine import model as m
from ogr_fem2d.engine.reference.elastic import Elastic

E, NU = 20000.0, 0.2


def refused(call, *args):
    try:
        call(*args)
    except ini.InitialStressError as err:
        return str(err)
    raise AssertionError(f"{call.__name__}{args} was accepted")


class TestConstant:

    def test_principal_values_and_angle(self):
        for s1, s3, sz, angle in ((10.0, 4.0, 6.0, 0.0), (10.0, 4.0, 6.0, 30.0),
                                  (8.0, -1.0, 2.0, 117.0), (5.0, 5.0, 5.0, 40.0)):
            sxx, syy, szz, txy = (-x for x in ini.constant(s1, s3, sz, angle, m.PLANE_STRAIN))
            centre, radius = (sxx + syy) / 2, math.hypot((sxx - syy) / 2, txy)
            assert abs(centre + radius - s1) < 1e-13 and abs(centre - radius - s3) < 1e-13
            assert szz == sz
            if s1 > s3:
                # Eq. (2.31): the normal stress on the plane normal to the
                # given angle is sigma_1, and Eq. (2.32): no shear on it
                t = math.radians(angle)
                sigma = centre + (sxx - syy) / 2 * math.cos(2 * t) + txy * math.sin(2 * t)
                tau = (syy - sxx) / 2 * math.sin(2 * t) + txy * math.cos(2 * t)
                assert abs(sigma - s1) < 1e-13 and abs(tau) < 1e-13, (angle, sigma, tau)

    def test_signs_and_axes(self):
        assert ini.constant(10.0, 4.0, 6.0, 0.0, m.PLANE_STRAIN) == (-10.0, -4.0, -6.0, -0.0)
        s = ini.constant(10.0, 4.0, 6.0, 90.0, m.PLANE_STRAIN)
        assert abs(s[0] + 4.0) < 1e-14 and abs(s[1] + 10.0) < 1e-14


STRATA = [ini.Stratum(1.0, 0.020, 0.6, 0.5), ini.Stratum(-1.0, 0.026, 0.8, 0.9)]
SURFACE = 2.0                                     # top of the block, interface y = 1


class TestGravitational:

    def test_the_weight_of_the_column(self):
        for y, (gamma_above, k, kz) in ((1.4, (0.0, 0.6, 0.5)), (0.3, (0.020 * 1.0, 0.8, 0.9))):
            sxx, syy, szz, txy = ini.gravitational(y, SURFACE, STRATA, m.PLANE_STRAIN)
            layer = STRATA[0] if y >= 1.0 else STRATA[1]
            top = SURFACE if y >= 1.0 else 1.0
            sigma_v = gamma_above + layer.unit_weight * (top - y)
            assert abs(syy + sigma_v) < 1e-16 and abs(sxx + k * sigma_v) < 1e-16
            assert abs(szz + kz * sigma_v) < 1e-16 and txy == 0.0

    def test_bad_input(self):
        assert "above the surface" in refused(ini.gravitational, 2.5, SURFACE, STRATA, m.PLANE_STRAIN)
        assert "below the last" in refused(ini.gravitational, -1.5, SURFACE, STRATA, m.PLANE_STRAIN)
        assert "not below" in refused(ini._check_strata, SURFACE, STRATA[::-1], m.PLANE_STRAIN)
        assert ">= 0" in refused(ini._check_strata, SURFACE,
                                 [ini.Stratum(0.0, -1.0, 0.5, 0.5)], m.PLANE_STRAIN)
        assert "major" in refused(ini.constant, 1.0, 2.0, 1.0, 0.0, m.PLANE_STRAIN)


def layered(six, kind, ny=4, nx=2):
    """The block 0 <= y <= 2 of _blocks, two strata split at y = 1, rollers
    on the sides and bottom (u = 0 on the axis side in axisymmetry), one
    stage of gravity alone from the gravitational field."""
    b = _blocks.block(six, nx=nx, ny=ny, w=1.0, h=2.0)
    soils = (m.Material(Elastic(E, NU), unit_weight=STRATA[0].unit_weight),
             m.Material(Elastic(E, NU), unit_weight=STRATA[1].unit_weight))
    which = tuple(0 if sum(b.nodes[n][1] for n in e[:3]) / 3 > 1.0 else 1 for e in b.elements)
    right = [n for n, (x, _) in enumerate(b.nodes) if x == 1.0]
    restraints = ([m.Restraint(n, True, n in b.bottom()) for n in b.left() + right]
                  + [m.Restraint(n, False, True) for n in b.bottom() if n not in b.left() + right])
    stage = m.Stage(active=(True,) * len(b.elements), restraints=tuple(restraints),
                    tolerance=1e-10)
    model = m.EngineModel(kind, tuple(b.nodes), tuple(b.elements), soils, which, (stage,))
    strata = STRATA if kind == m.PLANE_STRAIN else [ini.Stratum(s.bottom, s.unit_weight, s.k, s.k)
                                                    for s in STRATA]
    field = ini.gravitational_field(model, SURFACE, strata)
    return b, m.EngineModel(kind, model.nodes, model.elements, soils, which, (stage,), field)


class TestInEquilibrium:

    def test_gravity_alone_moves_nothing(self):
        for six, kind in ((False, m.PLANE_STRAIN), (True, m.PLANE_STRAIN), (True, m.AXISYMMETRIC)):
            b, model = layered(six, kind)
            out = analysis.run(model)[0]
            assert max(abs(u) for u in out.displacement) < 1e-15, (six, kind)
            weight = 0.020 * 1.0 + 0.026 * 1.0                     # per unit width
            if kind == m.AXISYMMETRIC:
                weight *= math.pi * 1.0 ** 2                       # the cylinder r <= 1
            bottom = sum(out.reactions[n][1] for n in b.bottom())
            assert abs(bottom - weight) < 1e-12, (six, kind, bottom, weight)

    def test_three_node_axisymmetry_falls_with_h(self):
        sizes = []
        for n in (2, 4, 8):
            _, model = layered(False, m.AXISYMMETRIC, ny=2 * n, nx=n)
            sizes.append(max(abs(u) for u in analysis.run(model)[0].displacement))
        assert sizes[0] > 1e-12, sizes
        for coarse, fine in zip(sizes, sizes[1:]):
            assert coarse / fine > 2.0, sizes

    def test_a_constant_field_with_its_boundary_tractions(self):
        p = 3.0
        for six in (False, True):
            b = _blocks.block(six, nx=2, ny=2, w=1.0, h=1.0)
            # sides 1 (right) and 2 ... found by position: the free right and top
            edges = []
            for e, element in enumerate(b.elements):
                for side in range(3):
                    a, c = b.nodes[element[side]], b.nodes[element[(side + 1) % 3]]
                    if (a[0] == c[0] == 1.0) or (a[1] == c[1] == 1.0):
                        edges.append(m.EdgeLoad(e, side, (-p, 0.0), (-p, 0.0), normal=True))
            stage = m.Stage(active=(True,) * len(b.elements),
                            restraints=tuple(m.Restraint(n, True, False) for n in b.left())
                            + tuple(m.Restraint(n, n in b.left(), True) for n in b.bottom()),
                            edge_loads=tuple(edges), tolerance=1e-10)
            model = m.EngineModel(m.PLANE_STRAIN, tuple(b.nodes), tuple(b.elements),
                                  (m.Material(Elastic(E, NU)),), (0,) * len(b.elements), (stage,))
            field = ini.constant_field(model, p, p, p, 0.0)
            out = analysis.run(m.EngineModel(model.analysis, model.nodes, model.elements,
                                             model.materials, model.element_material,
                                             model.stages, field))[0]
            assert not out.solved and max(abs(u) for u in out.displacement) == 0.0, six


class TestAmendmentOfD3:

    def test_axisymmetry_needs_a_radially_balanced_field(self):
        b, model = layered(True, m.AXISYMMETRIC)
        assert "K = Kz" in refused(ini.gravitational_field, model, SURFACE, STRATA)
        for args in ((10.0, 4.0, 4.0, 0.0),          # sigma_r = 10 != sigma_theta = 4
                     (10.0, 4.0, 7.0, 45.0)):        # sigma_r = sigma_theta = 7, tau_rz = 3
            assert "D3" in refused(ini.constant, *args, m.AXISYMMETRIC)
            ini.constant(*args, m.PLANE_STRAIN)      # fine in plane strain
        ini.constant(10.0, 4.0, 10.0, 0.0, m.AXISYMMETRIC)     # sigma_r = sigma_theta = 10
        ini.constant(10.0, 4.0, 4.0, 90.0, m.AXISYMMETRIC)     # sigma_r = sigma_theta = 4
