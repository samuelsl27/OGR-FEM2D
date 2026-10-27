# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.0.2 (spec 002, T3) — the integration rules of the triangles
(reference/quadrature.py; Zienkiewicz and Taylor 2000, Table 9.2, p. 222).

Invariants protected:

* **each rule is exact to its degree, and only to it**: against the exact
  integral of every monomial in area coordinates, Eq. (8.38), p. 183,

      int L1^a L2^b L3^c dA = 2 A a! b! c! / (a + b + c + 2)!,

  the linear rule is exact (to rounding) up to degree 1, the quadratic up
  to 2 and the quintic up to 5, and each misses some monomial of the next
  degree. So a weight or a coordinate copied wrong, or points out of their
  permutation, are caught: the moment conditions are what defines the rule;
* **the quintic is the one printed**: Table 9.2 truncates its values to ten
  decimals, and the closed form, truncated the same way, gives every printed
  digit (quadrature.py says why it is written in closed form);
* **no quintic point is on a side** (D1): every area coordinate of every
  point is positive, so with a side on the axis no point has r = 0; the
  quadratic rule, by contrast, has a zero coordinate in every point;
* **the quadratic rule is spec 001's**: the same points in the same order,
  and element_t6 uses it, so the validated cases do not move;
* **D1**: which rule goes with each element and analysis.
"""
from __future__ import annotations

import itertools
import math

from ogr_fem2d.engine.reference import element_t6 as t6
from ogr_fem2d.engine.reference import quadrature as q

RULES = (q.LINEAR, q.QUADRATIC, q.QUINTIC)


def exact(a: int, b: int, c: int) -> float:
    """int L1^a L2^b L3^c dA / A, Eq. (8.38)."""
    return 2.0 * math.factorial(a) * math.factorial(b) * math.factorial(c) \
        / math.factorial(a + b + c + 2)


def rule_value(rule: q.Rule, a: int, b: int, c: int) -> float:
    return sum(w * l1 ** a * l2 ** b * l3 ** c for (l1, l2, l3), w in rule.points)


def monomials(degree: int):
    """Every (a, b, c) with a + b + c == degree."""
    return [(a, b, degree - a - b) for a in range(degree + 1) for b in range(degree + 1 - a)]


class TestExactness:

    def test_each_rule_is_exact_up_to_its_degree(self):
        for rule in RULES:
            for degree in range(rule.degree + 1):
                for a, b, c in monomials(degree):
                    error = abs(rule_value(rule, a, b, c) - exact(a, b, c))
                    assert error < 1e-15, (rule.name, (a, b, c), error)

    def test_and_misses_the_next_degree(self):
        for rule in RULES:
            worst = max(abs(rule_value(rule, *m) - exact(*m))
                        for m in monomials(rule.degree + 1))
            assert worst > 1e-4 * exact(rule.degree + 1, 0, 0), (rule.name, worst)

    def test_points_are_in_area_coordinates(self):
        for rule in RULES:
            for (l1, l2, l3), w in rule.points:
                assert abs(l1 + l2 + l3 - 1.0) < 1e-15, rule.name
                assert min(l1, l2, l3) >= 0.0 and w > 0.0, rule.name


class TestTable:

    def test_the_quintic_is_the_printed_one(self):
        a1, b1, a2, b2, w0, w1, w2 = q.PRINTED_QUINTIC
        printed = ((((1 / 3,) * 3), w0),
                   ((a1, b1, b1), w1), ((b1, a1, b1), w1), ((b1, b1, a1), w1),
                   ((a2, b2, b2), w2), ((b2, a2, b2), w2), ((b2, b2, a2), w2))
        assert len(q.QUINTIC) == 7
        for (l, w), (lp, wp) in zip(q.QUINTIC.points, printed):
            for x, xp in zip(l + (w,), lp + (wp,)):
                # the table TRUNCATES to ten decimals (alpha2 = 0.79742698535...
                # is printed 0.7974269853): every printed digit is the closed
                # form's, and what is left is below one unit of the tenth
                assert -1e-15 <= x - xp < 1e-10, (l, w, lp, wp)

    def test_no_quintic_point_is_on_a_side(self):
        assert min(min(l) for l, _ in q.QUINTIC.points) > 0.05
        # the quadratic rule is all on the sides: the reason for D1
        assert all(min(l) == 0.0 for l, _ in q.QUADRATIC.points)

    def test_the_quadratic_rule_is_that_of_spec_001(self):
        assert q.QUADRATIC.points == (((0.5, 0.5, 0.0), 1 / 3), ((0.0, 0.5, 0.5), 1 / 3),
                                      ((0.5, 0.0, 0.5), 1 / 3))
        assert t6.GAUSS_POINTS is q.QUADRATIC.points
        assert q.LINEAR.points == (((1 / 3, 1 / 3, 1 / 3), 1.0),)

    def test_d1_rule_by_element_and_analysis(self):
        assert q.rule_for(3, q.PLANE_STRAIN) is q.LINEAR
        assert q.rule_for(3, q.AXISYMMETRIC) is q.LINEAR
        assert q.rule_for(6, q.PLANE_STRAIN) is q.QUADRATIC
        assert q.rule_for(6, q.AXISYMMETRIC) is q.QUINTIC
        for args in ((4, q.PLANE_STRAIN), (6, "plane_stress")):
            try:
                q.rule_for(*args)
            except ValueError:
                continue
            raise AssertionError(f"rule_for{args} accepted")
