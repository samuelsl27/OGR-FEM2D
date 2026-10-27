# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.0.2 (spec 002, T7) — consistent nodal forces of point, edge and body
loads (reference/loads.py), and the loads through the analysis.

Against closed forms, or identities that need no source:

* **the line rule** is Gauss-Legendre with ten points, Table 9.1 of
  Zienkiewicz and Taylor (2000), p. 220: every printed value is the exact
  one ROUNDED to its fifteen decimals (the roots of the Legendre polynomial
  P_10 and the weights 2 / ((1 - x^2) P_10'(x)^2), §9.8.2, computed here
  with forty digits; NumPy's own values are off by 2e-16, too much for a
  check digit by digit); the rule integrates every monomial up to degree 19
  and misses degree 20;
* **a linear traction on a straight side**: its nodal forces add up to the
  area of the trapezoid, L (t1 + t2) / 2, and their moment about the first
  corner is that of the trapezoid, L^2 (t1 + 2 t2) / 6; with three nodes
  they are L (2 t1 + t2) / 6 and L (t1 + 2 t2) / 6, with six a uniform
  traction gives L t (1/6, 2/3, 1/6): the integrals of the side's shape
  functions;
* **a normal traction on a curved side**: whatever the curve, int n ds is
  the chord turned a right angle, so a uniform normal t_n gives
  t_n (dy, -dx) of the chord, and a tangential one t_t (dx, dy): exact
  because n ds is a polynomial; a traction in global components gives t
  times the arc length, which the rule approximates (checked against an
  adaptive integral of the arc to 1e-9);
* **the ring** (D2): a uniform axial traction q on a side from r1 to r2
  carries q pi (r2^2 - r1^2), and a pressure p on a side at radius R of
  height h carries p 2 pi R h;
* **self weight**: the forces add up to gamma times the area (plane strain)
  or the volume of the ring, with both elements; on a straight six-node
  triangle the corners get nothing and the mid-side nodes A/3 each
  (Eq. 8.38: int (2 L - 1) L dA = 0, int 4 L1 L2 dA = A/3);
* **a point force**: on a node it all goes to that node; anywhere, the
  forces add up to it and keep its moment (sum_a N_a x_a = x in an
  isoparametric element), curved six-node triangles included, and the
  inverted map gives back the area coordinates the point was made from;
  outside its element it is refused, by the analysis with its stage and
  element;
* **through the analysis**: a laterally confined column under its own
  weight, plane strain and axisymmetry, with six-node triangles (which hold
  its quadratic displacement exactly) is in the exact state, sigma_y =
  -gamma (h - y), sigma_x = sigma_z = nu / (1 - nu) sigma_y, v = -gamma
  (h y - y^2/2) / M with M = E (1 - nu) / ((1 + nu)(1 - 2 nu)); and with
  every kind of load at once, the reactions balance the closed-form
  resultants of the loads.
"""
from __future__ import annotations

import math
import random
from decimal import Decimal, getcontext

import numpy as np
from scipy.integrate import quad

import _blocks
from ogr_fem2d.engine import analysis
from ogr_fem2d.engine import model as m
from ogr_fem2d.engine.reference import element_t3 as t3
from ogr_fem2d.engine.reference import element_t6 as t6
from ogr_fem2d.engine.reference import loads
from ogr_fem2d.engine.reference import quadrature as q
from ogr_fem2d.engine.reference.elastic import Elastic

E, NU, GAMMA = 20000.0, 0.2, 0.027


def total(forces):
    return sum(f[0] for f in forces), sum(f[1] for f in forces)


class TestLineRule:

    def test_table_9_1(self):
        getcontext().prec = 40
        got = loads.GAUSS_LEGENDRE_10

        def legendre(x):                       # P_10(x) and its derivative
            p0, p1 = Decimal(1), x
            for k in range(2, 11):
                p0, p1 = p1, ((2 * k - 1) * x * p1 - (k - 1) * p0) / k
            return p1, 10 * (x * p1 - p0) / (x * x - 1)

        for (a, w), start in zip(got, np.polynomial.legendre.leggauss(10)[0]):
            x = Decimal(repr(float(start)))
            for _ in range(8):                 # Newton on the root
                p, dp = legendre(x)
                x -= p / dp
            weight = 2 / ((1 - x * x) * legendre(x)[1] ** 2)
            assert Decimal(repr(a)) == round(x, 15), (a, x)
            assert Decimal(repr(w)) == round(weight, 15), (w, weight)
        for k in range(20):
            exact = 0.0 if k % 2 else 2.0 / (k + 1)
            assert abs(sum(w * a ** k for a, w in got) - exact) < 1e-14, k
        assert abs(sum(w * a ** 20 for a, w in got) - 2.0 / 21) > 1e-8


class TestSides:

    def test_a_linear_traction_on_a_straight_side(self):
        a, b = (0.3, 0.1), (2.0, 1.4)
        length = math.dist(a, b)
        mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
        for nodes in ([a, b], [a, mid, b]):
            positions = [0.0, 1.0] if len(nodes) == 2 else [0.0, 0.5, 1.0]
            for t1, t2 in ((1.5, 1.5), (0.0, 2.0), (-1.0, 3.0)):
                f = loads.edge_forces(nodes, (0.0, t1), (0.0, t2))
                assert abs(total(f)[1] - length * (t1 + t2) / 2) < 1e-14
                moment = sum(s * length * fy for s, (_, fy) in zip(positions, f))
                assert abs(moment - length ** 2 * (t1 + 2 * t2) / 6) < 1e-13
            f = loads.edge_forces([a, b], (0.0, 1.0), (0.0, 4.0))
            assert abs(f[0][1] - length * (2 + 4) / 6) < 1e-14
            assert abs(f[1][1] - length * (1 + 8) / 6) < 1e-14
        f = loads.edge_forces([a, mid, b], (2.0, 0.0), (2.0, 0.0))
        for got, share in zip(f, (1 / 6, 2 / 3, 1 / 6)):
            assert abs(got[0] - 2.0 * length * share) < 1e-14

    def test_a_normal_traction_on_a_curved_side(self):
        a, mid, b = (1.0, 0.0), (0.75, 0.72), (0.0, 1.0)   # bulging outwards
        dx, dy = b[0] - a[0], b[1] - a[1]
        tn, tt = -3.0, 0.7
        f = total(loads.edge_forces([a, mid, b], (tn, tt), (tn, tt), normal=True))
        want = (tn * dy + tt * dx, -tn * dx + tt * dy)
        assert max(abs(f[0] - want[0]), abs(f[1] - want[1])) < 1e-14, (f, want)

    def test_a_global_traction_on_a_curved_side(self):
        a, mid, b = (1.0, 0.0), (0.75, 0.72), (0.0, 1.0)

        def speed(s):
            _, ds = loads.side_functions(3, s)
            return math.hypot(sum(d * p[0] for d, p in zip(ds, (a, mid, b))),
                              sum(d * p[1] for d, p in zip(ds, (a, mid, b))))
        arc = quad(speed, 0.0, 1.0, epsabs=1e-13, epsrel=1e-13, limit=200)[0]
        f = total(loads.edge_forces([a, mid, b], (0.0, -2.0), (0.0, -2.0)))
        assert abs(f[1] + 2.0 * arc) < 1e-9 * arc and abs(f[0]) < 1e-15

    def test_the_ring(self):
        r1, r2, qz = 0.5, 2.0, 1.7
        for nodes in ([(r1, 3.0), (r2, 3.0)], [(r1, 3.0), ((r1 + r2) / 2, 3.0), (r2, 3.0)]):
            f = total(loads.edge_forces(nodes, (0.0, qz), (0.0, qz), axisymmetric=True))
            assert abs(f[1] - qz * math.pi * (r2 ** 2 - r1 ** 2)) < 1e-13
        # outer face of a cylinder of radius R, from z = 0 up to h: side going
        # up, interior on its left (r < R), outward normal +r; pressure p
        big_r, h, p = 2.0, 1.5, 4.0
        f = total(loads.edge_forces([(big_r, 0.0), (big_r, h)], (-p, 0.0), (-p, 0.0),
                                    normal=True, axisymmetric=True))
        assert abs(f[0] + p * 2 * math.pi * big_r * h) < 1e-12 and abs(f[1]) < 1e-15


TRI = [(0.7, -0.2), (2.1, 0.4), (1.2, 1.7)]


def straight_t6(c):
    return c + [((c[0][0] + c[1][0]) / 2, (c[0][1] + c[1][1]) / 2),
                ((c[1][0] + c[2][0]) / 2, (c[1][1] + c[2][1]) / 2),
                ((c[2][0] + c[0][0]) / 2, (c[2][1] + c[0][1]) / 2)]


def area(c):
    return 0.5 * ((c[1][0] - c[0][0]) * (c[2][1] - c[0][1]) - (c[2][0] - c[0][0]) * (c[1][1] - c[0][1]))


class TestBody:

    def test_the_weight_adds_up(self):
        a = area(TRI)
        r_c = sum(x for x, _ in TRI) / 3
        for shape, xy in ((t3, TRI), (t6, straight_t6(TRI))):
            for axi, size in ((False, a), (True, 2 * math.pi * r_c * a)):
                rule = q.rule_for(len(xy), q.AXISYMMETRIC if axi else q.PLANE_STRAIN)
                f = total(loads.body_forces(shape, xy, (0.0, -GAMMA), rule, axi))
                assert abs(f[1] + GAMMA * size) < 1e-15 and f[0] == 0.0, (shape, axi)

    def test_the_six_node_shares(self):
        f = loads.body_forces(t6, straight_t6(TRI), (0.0, -GAMMA), q.QUADRATIC)
        a = area(TRI)
        for k, (_, fy) in enumerate(f):
            assert abs(fy - (0.0 if k < 3 else -GAMMA * a / 3)) < 1e-16, (k, fy)


class TestPoint:

    def test_on_a_node_and_anywhere(self):
        curved = straight_t6(TRI)
        curved[4] = (curved[4][0] + 0.12, curved[4][1] + 0.08)       # a bent side
        for shape, xy in ((t3, TRI), (t6, curved)):
            for k in range(len(xy)):
                f = loads.point_forces(shape, xy, *xy[k], 1.0, -2.0)
                for j, (fx, fy) in enumerate(f):
                    want = (1.0, -2.0) if j == k else (0.0, 0.0)
                    assert abs(fx - want[0]) < 1e-12 and abs(fy - want[1]) < 1e-12
            rng = random.Random(4)
            for _ in range(10):
                l2, l3 = rng.random(), rng.random()
                if l2 + l3 > 1:
                    l2, l3 = 1 - l2, 1 - l3
                l = (1 - l2 - l3, l2, l3)
                n = shape.shape_functions(*l)
                x = sum(n[a] * xy[a][0] for a in range(len(n)))
                y = sum(n[a] * xy[a][1] for a in range(len(n)))
                back = loads.local_coordinates(shape, xy, x, y)
                assert max(abs(u - v) for u, v in zip(back, l)) < 1e-13
                f = loads.point_forces(shape, xy, x, y, 0.4, -1.3)
                fx, fy = total(f)
                assert abs(fx - 0.4) < 1e-14 and abs(fy + 1.3) < 1e-14
                moment = sum(p[0] * g[1] - p[1] * g[0] for p, g in zip(xy, f))
                assert abs(moment - (x * -1.3 - y * 0.4)) < 1e-13

    def test_outside_is_refused(self):
        try:
            loads.point_forces(t3, TRI, 5.0, 5.0, 0.0, -1.0)
        except ValueError as err:
            assert "not in the element" in str(err)
        else:
            raise AssertionError("a point outside was loaded")


ROCK = m.Material(Elastic(E, NU), unit_weight=GAMMA)


def column(six, analysis_kind, w=1.0, h=3.0):
    """A column held at the bottom (v) and on both sides (u)."""
    b = _blocks.block(six, nx=2, ny=4, w=w, h=h)
    right = [n for n, (x, _) in enumerate(b.nodes) if x == w]
    restraints = ([m.Restraint(n, True, n in b.bottom()) for n in b.left() + right]
                  + [m.Restraint(n, False, True) for n in b.bottom() if n not in b.left() + right])
    st = m.Stage(active=(True,) * len(b.elements), restraints=tuple(restraints), tolerance=1e-12)
    return b, m.EngineModel(analysis_kind, tuple(b.nodes), tuple(b.elements), (ROCK,),
                            (0,) * len(b.elements), (st,))


class TestThroughTheAnalysis:

    def test_a_confined_column_under_its_own_weight(self):
        h = 3.0
        k0 = NU / (1 - NU)
        modulus = E * (1 - NU) / ((1 + NU) * (1 - 2 * NU))
        for kind in (m.PLANE_STRAIN, m.AXISYMMETRIC):
            b, model = column(True, kind, h=h)
            out = analysis.run(model)[0]
            points = analysis.solver.integration_points(analysis.solver.Model(
                list(b.nodes), list(b.elements), [ROCK.law] * len(b.elements), frozenset(), kind))
            for p, s in zip(points, out.stresses):
                sy = -GAMMA * (h - p.xy[1])
                assert abs(s[1] - sy) < 1e-13 and abs(s[0] - k0 * sy) < 1e-13, (kind, p.xy, s)
                assert abs(s[2] - k0 * sy) < 1e-13 and abs(s[3]) < 1e-13
            for n, (x, y) in enumerate(b.nodes):
                v = -GAMMA * (h * y - y * y / 2) / modulus
                assert abs(out.displacement[2 * n + 1] - v) < 1e-17, (kind, n)
                assert abs(out.displacement[2 * n]) < 1e-17

    def test_every_load_at_once_is_balanced(self):
        w, h = 2.0, 1.5
        for six in (False, True):
            b = _blocks.block(six, nx=3, ny=2, w=w, h=h)
            top_element = len(b.elements) - 1                       # its side 1 is on the top
            top = [b.nodes[k] for k in (b.elements[top_element][1], b.elements[top_element][2])]
            stage = m.Stage(
                active=(True,) * len(b.elements),
                restraints=tuple(m.Restraint(n, n == b.bottom()[0], True) for n in b.bottom()),
                nodal_loads=(m.NodalLoad(b.at(1, 1), 0.3, -0.2),),
                point_loads=(m.PointLoad(2, 1.1, 0.3, -0.5, -1.0),),
                edge_loads=(m.EdgeLoad(top_element, 1, (-2.0, 0.4), (-1.0, 0.4), normal=True),),
                tolerance=1e-12)
            model = m.EngineModel(m.PLANE_STRAIN, tuple(b.nodes), tuple(b.elements), (ROCK,),
                                  (0,) * len(b.elements), (stage,))
            out = analysis.run(model)[0]
            # the side runs from top[0] to top[1]: (dx, dy) = top[1] - top[0]
            dx, dy = top[1][0] - top[0][0], top[1][1] - top[0][1]
            tn, tt = (-2.0 + -1.0) / 2, 0.4                        # mean traction
            applied = (0.3 - 0.5 + tn * dy + tt * dx,
                       -0.2 - 1.0 - GAMMA * w * h - tn * dx + tt * dy)
            rx = sum(r[0] for r in out.reactions.values())
            ry = sum(r[1] for r in out.reactions.values())
            assert abs(rx + applied[0]) < 1e-12 and abs(ry + applied[1]) < 1e-12, (six, rx, ry, applied)

    def test_no_radial_point_force_on_the_axis(self):
        b, model = column(False, m.AXISYMMETRIC)
        st = model.stages[0]
        on_axis = m.PointLoad(0, 0.0, 0.0, 1.0, 0.0)
        for load, refused in ((on_axis, True), (m.PointLoad(0, 0.0, 0.0, 0.0, -1.0), False)):
            stage = m.Stage(active=st.active, restraints=st.restraints, point_loads=(load,))
            try:
                analysis.run(m.EngineModel(model.analysis, model.nodes, model.elements,
                                           model.materials, model.element_material, (stage,)))
            except analysis.LoadError as err:
                assert refused and "D1 bis" in str(err), err
            else:
                assert not refused, "a radial force on the axis was applied"

    def test_a_point_load_outside_names_its_stage(self):
        b, model = column(False, m.PLANE_STRAIN)
        bad = m.Stage(active=model.stages[0].active, restraints=model.stages[0].restraints,
                      point_loads=(m.PointLoad(0, 9.0, 9.0, 0.0, -1.0),))
        try:
            analysis.run(m.EngineModel(model.analysis, model.nodes, model.elements,
                                       model.materials, model.element_material,
                                       (model.stages[0], bad)))
        except analysis.LoadError as err:
            assert err.stage == 1 and err.element == 0, err
        else:
            raise AssertionError("a point load outside its element was applied")
