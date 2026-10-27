# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.0.1 (spec 001, T4) — the six-node triangle of the reference implementation
does what its source says, before it is used as the oracle of anything.

All against Zienkiewicz and Taylor (2000), *The Finite Element Method*, 5th
ed., vol. 1, or against identities that need no source:

* **shape functions** (p. 182): partition of unity, one at their own node and
  zero at the others, derivatives that add up to zero;
* **quadrature** (Table 9.2, quadratic rule): exact for every monomial of the
  area coordinates up to degree 2, against the exact integral of Eq. (8.38),
  int L1^a L2^b L3^c dA = a! b! c! 2A / (a+b+c+2)!; and NOT exact at degree 3,
  so the test also says which rule this is;
* **elasticity** (Eqs. 4.15-4.16): sigma_z = nu (sigma_x + sigma_y), and the
  uniaxial-strain modulus equals lambda + 2G;
* **stiffness**: symmetric, three zero eigenvalues (two translations and a
  rotation) and the rest positive;
* **rigid body**: translations and an infinitesimal rotation strain nothing;
* **patch test** (§10.3, tests A and B): on a patch of distorted elements, a
  linear displacement field is reproduced exactly — test A, the exact nodal
  values leave no residual at the interior nodes; test B, prescribing only the
  boundary, the solution at the interior nodes is the field;
* **stress and boundary**: the internal forces of a uniform stress on a free
  element are in equilibrium and equal the consistent nodal forces of the
  traction sigma.n on its edges (1/6, 2/3, 1/6 of each edge's resultant).
"""
from __future__ import annotations

import math
import random

import numpy as np

from ogr_fem2d.engine.reference import element_t6 as t6
from ogr_fem2d.engine.reference.elastic import (plane_strain_matrix,
                                                stress_increment)

E, NU = 10000.0, 0.2


def _straight(corners):
    """A straight-sided T6 from three corners: mid-sides at the midpoints."""
    (x1, y1), (x2, y2), (x3, y3) = corners
    return [(x1, y1), (x2, y2), (x3, y3),
            ((x1 + x2) / 2, (y1 + y2) / 2), ((x2 + x3) / 2, (y2 + y3) / 2),
            ((x3 + x1) / 2, (y3 + y1) / 2)]


_TRI = _straight([(0.3, -0.2), (2.1, 0.4), (0.8, 1.7)])


def _area(corners):
    (x1, y1), (x2, y2), (x3, y3) = corners
    return 0.5 * ((x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1))


class TestShapeFunctions:
    def test_partition_of_unity_and_derivatives(self):
        rng = random.Random(1)
        for _ in range(50):
            a, b = rng.random(), rng.random()
            if a + b > 1:
                a, b = 1 - a, 1 - b
            l = (1 - a - b, a, b)
            assert abs(sum(t6.shape_functions(*l)) - 1.0) < 1e-14
            d = t6.shape_derivatives_local(*l)
            assert abs(sum(x for x, _ in d)) < 1e-13
            assert abs(sum(y for _, y in d)) < 1e-13

    def test_kronecker_delta_at_the_nodes(self):
        for i, l in enumerate(t6.NODES_L):
            n = t6.shape_functions(*l)
            for j in range(6):
                assert abs(n[j] - (1.0 if i == j else 0.0)) < 1e-15, (i, j)


class TestQuadrature:
    def _integral(self, a, b, c):
        total = 0.0
        for (l1, l2, l3), w in t6.GAUSS_POINTS:
            total += w * t6.jacobian(_TRI, l1, l2, l3)[1] / 2.0 \
                * l1 ** a * l2 ** b * l3 ** c
        return total

    def _exact(self, a, b, c):          # Zienkiewicz y Taylor (2000), Eq. (8.38)
        area = _area(_TRI[:3])
        return (math.factorial(a) * math.factorial(b) * math.factorial(c)
                * 2.0 * area / math.factorial(a + b + c + 2))

    def test_exact_up_to_degree_two(self):
        for a in range(3):
            for b in range(3 - a):
                for c in range(3 - a - b):
                    got, want = self._integral(a, b, c), self._exact(a, b, c)
                    assert abs(got - want) < 1e-14 * max(1.0, abs(want)), (a, b, c)

    def test_not_exact_at_degree_three(self):
        got, want = self._integral(3, 0, 0), self._exact(3, 0, 0)
        assert abs(got - want) > 1e-3 * want, (got, want)

    def test_the_area_of_a_straight_element(self):
        assert abs(t6.area(_TRI) - _area(_TRI[:3])) < 1e-14


class TestElasticity:
    def test_sigma_z_and_the_constrained_modulus(self):
        lam = E * NU / ((1 + NU) * (1 - 2 * NU))
        g = E / (2 * (1 + NU))
        s = stress_increment(E, NU, (1e-3, 0.0, 0.0))
        assert abs(s[0] - (lam + 2 * g) * 1e-3) < 1e-12
        assert abs(s[1] - lam * 1e-3) < 1e-12
        assert abs(s[2] - NU * (s[0] + s[1])) < 1e-12
        assert abs(stress_increment(E, NU, (0, 0, 1e-3))[3] - g * 1e-3) < 1e-12

    def test_the_matrix_is_symmetric(self):
        d = plane_strain_matrix(E, NU)
        assert all(abs(d[i][j] - d[j][i]) < 1e-12 for i in range(3) for j in range(3))


def _rigid_modes(xy):
    tx = [1.0 if i % 2 == 0 else 0.0 for i in range(12)]
    ty = [0.0 if i % 2 == 0 else 1.0 for i in range(12)]
    rot = []
    for x, y in xy:
        rot += [-y, x]
    return tx, ty, rot


class TestStiffness:
    def test_symmetric_with_three_rigid_modes(self):
        k = np.array(t6.stiffness(_TRI, plane_strain_matrix(E, NU)))
        assert np.allclose(k, k.T, rtol=0, atol=1e-9 * abs(k).max())
        eig = np.sort(np.linalg.eigvalsh(k))
        tol = 1e-10 * eig[-1]
        assert np.all(np.abs(eig[:3]) < tol), eig[:4]
        assert np.all(eig[3:] > tol), eig[:4]

    def test_rigid_body_motion_strains_nothing(self):
        k = np.array(t6.stiffness(_TRI, plane_strain_matrix(E, NU)))
        for mode in _rigid_modes(_TRI):
            for eps in t6.strains(_TRI, mode):
                assert max(abs(e) for e in eps) < 1e-12, eps
            assert np.abs(k @ np.array(mode)).max() < 1e-8 * abs(k).max()


def _patch():
    """Five corner-to-corner T6 around a distorted interior node, with curved
    (moved) mid-side nodes inside: Zienkiewicz y Taylor (2000), §10.3."""
    corners = {0: (0.0, 0.0), 1: (2.0, 0.0), 2: (2.3, 1.8), 3: (0.1, 2.0),
               4: (-0.4, 1.0), 5: (0.9, 0.8)}              # 5 is interior
    tris = [(0, 1, 5), (1, 2, 5), (2, 3, 5), (3, 4, 5), (4, 0, 5)]
    nodes = dict(corners)
    mids = {}
    rng = random.Random(7)

    def mid(i, j):
        key = tuple(sorted((i, j)))
        if key not in mids:
            (xa, ya), (xb, yb) = corners[i], corners[j]
            inside = 5 in key
            # interior edges get their mid-side node moved: curved elements
            dx, dy = ((rng.uniform(-0.05, 0.05), rng.uniform(-0.05, 0.05))
                      if inside else (0.0, 0.0))
            mids[key] = len(nodes)
            nodes[len(nodes)] = ((xa + xb) / 2 + dx, (ya + yb) / 2 + dy)
        return mids[key]

    elements = [(a, b, c, mid(a, b), mid(b, c), mid(c, a)) for a, b, c in tris]
    interior = {5} | {n for key, n in mids.items() if 5 in key}
    return nodes, elements, interior


def _assemble(nodes, elements, d):
    n = 2 * len(nodes)
    k = np.zeros((n, n))
    for el in elements:
        xy = [nodes[i] for i in el]
        ke = np.array(t6.stiffness(xy, d))
        dofs = [2 * i + c for i in el for c in (0, 1)]
        k[np.ix_(dofs, dofs)] += ke
    return k


def _linear_field(x, y):
    return 0.01 + 0.002 * x - 0.0015 * y, -0.02 + 0.0007 * x + 0.003 * y


class TestPatch:
    def test_a_exact_values_leave_no_interior_residual(self):
        nodes, elements, interior = _patch()
        k = _assemble(nodes, elements, plane_strain_matrix(E, NU))
        u = np.array([c for i in range(len(nodes)) for c in _linear_field(*nodes[i])])
        r = k @ u
        dofs = [2 * i + c for i in interior for c in (0, 1)]
        assert np.abs(r[dofs]).max() < 1e-9 * np.abs(k).max() * np.abs(u).max()

    def test_b_the_boundary_alone_gives_the_field_inside(self):
        nodes, elements, interior = _patch()
        k = _assemble(nodes, elements, plane_strain_matrix(E, NU))
        u = np.array([c for i in range(len(nodes)) for c in _linear_field(*nodes[i])])
        free = [2 * i + c for i in sorted(interior) for c in (0, 1)]
        fixed = [j for j in range(len(u)) if j not in free]
        rhs = -k[np.ix_(free, fixed)] @ u[fixed]
        got = np.linalg.solve(k[np.ix_(free, free)], rhs)
        assert np.abs(got - u[free]).max() < 1e-12, np.abs(got - u[free]).max()

    def test_the_strain_is_the_constant_of_the_field(self):
        nodes, elements, _ = _patch()
        for el in elements:
            xy = [nodes[i] for i in el]
            u = [c for i in el for c in _linear_field(*nodes[i])]
            for eps in t6.strains(xy, u):
                assert abs(eps[0] - 0.002) < 1e-13
                assert abs(eps[1] - 0.003) < 1e-13
                assert abs(eps[2] - (-0.0015 + 0.0007)) < 1e-13


class TestStressAndBoundary:
    def test_a_uniform_stress_balances_the_tractions_of_its_edges(self):
        s = (-3.0, 1.5, -0.45, 0.8)        # sigma_xx, sigma_yy, sigma_zz, tau_xy
        f = t6.internal_forces(_TRI, [s] * 3)
        assert abs(sum(f[0::2])) < 1e-12 and abs(sum(f[1::2])) < 1e-12
        expected = [0.0] * 12
        for a, b, m in ((0, 1, 3), (1, 2, 4), (2, 0, 5)):
            (xa, ya), (xb, yb) = _TRI[a], _TRI[b]
            nx, ny = (yb - ya), -(xb - xa)          # outward normal x length
            tx, ty = s[0] * nx + s[3] * ny, s[3] * nx + s[1] * ny
            for node, share in ((a, 1 / 6), (m, 2 / 3), (b, 1 / 6)):
                expected[2 * node] += share * tx
                expected[2 * node + 1] += share * ty
        assert max(abs(x - y) for x, y in zip(f, expected)) < 1e-12, (f, expected)

    def test_an_inverted_element_gives_no_result(self):
        flipped = [_TRI[0], _TRI[2], _TRI[1], _TRI[5], _TRI[4], _TRI[3]]
        try:
            t6.stiffness(flipped, plane_strain_matrix(E, NU))
        except ValueError as exc:
            assert "det J" in str(exc)
        else:
            raise AssertionError("an inverted element gave a stiffness")
