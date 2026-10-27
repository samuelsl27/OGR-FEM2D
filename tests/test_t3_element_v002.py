# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.0.2 (spec 002, T4) — the three-node triangle, and the engine with
triangles of three or six nodes in plane strain.

Against Zienkiewicz and Taylor (2000), *The Finite Element Method*, 5th ed.,
vol. 1, or against identities that need no source:

* **B is that of the source**: B_i = [[b_i, 0], [0, c_i], [c_i, b_i]] / 2 Delta
  with b_i = y_j - y_m, c_i = x_m - x_j (Eqs. 4.5b, 4.10b), and det J is
  2 Delta (Eq. 4.5c): the isoparametric route of triangle.py gives the
  explicit formula of §4.2;
* **shape functions**: partition of unity, one at their own node;
* **stiffness**: symmetric, three zero eigenvalues (two translations and a
  rotation), the rest positive; rigid-body motions strain nothing;
* **patch test** (§10.3, tests A and B) on distorted triangles around an
  interior node, assembled by the engine's own solver.stiffness: a linear
  field leaves no residual inside, and prescribing the boundary alone gives
  it back inside;
* **stress and boundary**: the internal forces of a uniform stress equal the
  consistent forces of sigma.n on the edges, half of each edge's resultant
  to each end (the term of Eq. 2.13b, "identically zero after assembly"
  inside a body);
* **a stage through the engine, T3 and T6**: a block on rollers pulled on
  top by the consistent nodal forces of a uniform traction q ends with
  sigma_yy = q, sigma_zz = nu q (Eq. 4.15) and the rest zero at every
  point, and with the linear displacement of that state in plane strain,
  eps_y = (1 - nu^2) q / E and eps_x = -nu (1 + nu) q / E (Eq. 4.16 with
  sigma_x = 0). Exact for both elements, which represent a linear field;
* **two routes to one matrix**: with elastic tangents, the stiffness
  assembled point by point (the route of the iterations and the variants,
  2n x 2n per point) is the element-by-element one;
* **one kind per model**: mixing three- and six-node triangles is refused,
  and the Rust variant says that it has only the six-node one (T13).
"""
from __future__ import annotations

import math
import random

import numpy as np

import _blocks
from ogr_fem2d.engine import interface
from ogr_fem2d.engine.compiled import RUST
from ogr_fem2d.engine.reference import element_t3 as t3
from ogr_fem2d.engine.reference import solver
from ogr_fem2d.engine.reference.elastic import Elastic, plane_strain_matrix

E, NU = 10000.0, 0.2
TRI = [(0.3, -0.2), (2.1, 0.4), (0.8, 1.7)]


def area2(xy):
    (x1, y1), (x2, y2), (x3, y3) = xy
    return (x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1)


class TestTheElement:

    def test_b_is_the_explicit_one_of_the_source(self):
        b, det = t3.b_matrix(TRI)
        delta2 = area2(TRI)
        assert abs(det - delta2) < 1e-14
        for i in range(3):
            j, m = (i + 1) % 3, (i + 2) % 3
            bi = TRI[j][1] - TRI[m][1]                 # Eq. (4.5b)
            ci = TRI[m][0] - TRI[j][0]
            want = [[bi, 0.0], [0.0, ci], [ci, bi]]
            for r in range(3):
                for c in range(2):
                    assert abs(b[r][2 * i + c] - want[r][c] / delta2) < 1e-14, (i, r, c)

    def test_shape_functions(self):
        rng = random.Random(3)
        for _ in range(20):
            a, c = rng.random(), rng.random()
            if a + c > 1:
                a, c = 1 - a, 1 - c
            assert abs(sum(t3.shape_functions(1 - a - c, a, c)) - 1.0) < 1e-15
        for i, l in enumerate(t3.NODES_L):
            assert t3.shape_functions(*l) == [1.0 if j == i else 0.0 for j in range(3)]

    def test_stiffness_symmetric_with_three_rigid_modes(self):
        k = np.array(t3.stiffness(TRI, plane_strain_matrix(E, NU)))
        assert np.allclose(k, k.T, rtol=0, atol=1e-12 * abs(k).max())
        eig = np.sort(np.linalg.eigvalsh(k))
        tol = 1e-10 * eig[-1]
        assert np.all(np.abs(eig[:3]) < tol) and np.all(eig[3:] > tol), eig
        rot = [c for x, y in TRI for c in (-y, x)]
        for mode in ([1, 0] * 3, [0, 1] * 3, rot):
            assert max(abs(e) for e in t3.strains(TRI, mode)[0]) < 1e-14
            assert np.abs(k @ np.array(mode, dtype=float)).max() < 1e-10 * abs(k).max()

    def test_a_uniform_stress_balances_the_tractions_of_its_edges(self):
        s = (-3.0, 1.5, -0.45, 0.8)
        f = t3.internal_forces(TRI, [s])
        want = [0.0] * 6
        for a, b in ((0, 1), (1, 2), (2, 0)):
            (xa, ya), (xb, yb) = TRI[a], TRI[b]
            nx, ny = yb - ya, -(xb - xa)           # outward normal x length
            tx, ty = s[0] * nx + s[3] * ny, s[3] * nx + s[1] * ny
            for node in (a, b):
                want[2 * node] += tx / 2
                want[2 * node + 1] += ty / 2
        assert max(abs(x - y) for x, y in zip(f, want)) < 1e-13, (f, want)

    def test_an_inverted_element_gives_no_result(self):
        try:
            t3.stiffness([TRI[0], TRI[2], TRI[1]], plane_strain_matrix(E, NU))
        except ValueError as exc:
            assert "det J" in str(exc)
        else:
            raise AssertionError("an inverted element gave a stiffness")


def _patch():
    """Five distorted triangles around interior node 5 (§10.3)."""
    nodes = [(0.0, 0.0), (2.0, 0.0), (2.3, 1.8), (0.1, 2.0), (-0.4, 1.0), (0.9, 0.8)]
    elements = [(0, 1, 5), (1, 2, 5), (2, 3, 5), (3, 4, 5), (4, 0, 5)]
    return nodes, elements


def _field(x, y):
    return 0.01 + 0.002 * x - 0.0015 * y, -0.02 + 0.0007 * x + 0.003 * y


class TestPatch:

    def _k(self):
        nodes, elements = _patch()
        m = solver.Model(nodes, elements, [Elastic(E, NU)] * 5, frozenset())
        return nodes, solver.stiffness(m).toarray()

    def test_a_exact_values_leave_no_interior_residual(self):
        nodes, k = self._k()
        u = np.array([c for xy in nodes for c in _field(*xy)])
        r = k @ u
        assert np.abs(r[10:12]).max() < 1e-12 * np.abs(k).max() * np.abs(u).max()

    def test_b_the_boundary_alone_gives_the_field_inside(self):
        nodes, k = self._k()
        u = np.array([c for xy in nodes for c in _field(*xy)])
        free, fixed = [10, 11], list(range(10))
        got = np.linalg.solve(k[np.ix_(free, free)], -k[np.ix_(free, fixed)] @ u[fixed])
        assert np.abs(got - u[free]).max() < 1e-14


def _block(six: bool):
    """The block of _blocks.py on rollers (left in x, bottom in y), and the
    consistent forces of a unit traction on its top edge: per edge of length
    dx, 1/2 to each end (T3); 1/6, 2/3, 1/6 (T6)."""
    b = _blocks.block(six)
    restrained = {2 * n for n in b.left()} | {2 * n + 1 for n in b.bottom()}
    shares = (1 / 6, 2 / 3, 1 / 6) if six else (0.5, 0.5)
    top = {}
    for edge in b.top_edges():
        dx = b.nodes[edge[-1]][0] - b.nodes[edge[0]][0]
        for n, share in zip(edge, shares):
            top[n] = top.get(n, 0.0) + share * dx
    return b.nodes, b.elements, top, frozenset(restrained)


class TestStageThroughTheEngine:

    def test_a_pulled_block_has_the_uniform_stress(self):
        q = 2.5
        for six in (False, True):
            nodes, elements, top, restrained = _block(six)
            m = solver.Model(nodes, elements, [Elastic(E, NU)] * len(elements), restrained)
            n_points = len(elements) * (3 if six else 1)
            load = [0.0] * (2 * len(nodes))
            for n, length in top.items():
                load[2 * n + 1] = q * length
            r = solver.solve_stage(m, [(0.0,) * 4] * n_points, load, 1, 1e-12, 3)
            for s in r.stresses:
                assert abs(s[1] - q) < 1e-12 and abs(s[0]) < 1e-12 and abs(s[3]) < 1e-12, (six, s)
                assert abs(s[2] - NU * q) < 1e-12                     # Eq. (4.15)
            ey, ex = (1 - NU ** 2) * q / E, -NU * (1 + NU) * q / E
            for (x, y), i in zip(nodes, range(len(nodes))):
                assert abs(r.displacement[2 * i] - ex * x) < 1e-15, (six, i)
                assert abs(r.displacement[2 * i + 1] - ey * y) < 1e-15, (six, i)


class TestTwoRoutesToOneMatrix:

    def test_point_by_point_equals_element_by_element(self):
        # with elastic tangents, K_T assembled point by point (the route of
        # the iterations and of the variants) is the elastic stiffness
        nodes, elements = _patch()
        m = solver.Model(nodes, elements, [Elastic(E, NU)] * 5, frozenset())
        points = solver.integration_points(m)
        d = plane_strain_matrix(E, NU)
        kt = solver.tangent_stiffness(points, [d] * len(points), 2 * len(nodes)).toarray()
        k = solver.stiffness(m).toarray()
        assert np.abs(kt - k).max() < 1e-12 * np.abs(k).max()
        update = solver.REFERENCE.prepare(solver.geometry(m, points)).update(
            np.zeros((len(points), 4)), np.zeros(2 * len(nodes)))
        assert update.stiffness.shape == (len(points), 36)


class TestOneKind:

    def test_mixed_elements_are_refused(self):
        nodes, elements = _patch()
        m = solver.Model(nodes + [(1.0, 1.0)] * 3, [elements[0], (1, 2, 5, 6, 7, 8)],
                         [Elastic(E, NU)] * 2, frozenset())
        try:
            solver.integration_points(m)
        except ValueError as exc:
            assert "[3, 6]" in str(exc)
        else:
            raise AssertionError("a mixed mesh was accepted")

    def test_the_pattern_follows_the_element_and_rust_says_what_it_lacks(self):
        nodes, elements = _patch()
        m = solver.Model(nodes, elements, [Elastic(E, NU)] * 5, frozenset())
        g = solver.geometry(m, solver.integration_points(m))
        rows, cols = interface.stiffness_pattern(g)
        assert len(rows) == len(elements) * 36
        assert rows[6] == 2 * elements[0][0] + 1 and cols[6] == 2 * elements[0][0]
        try:
            RUST.prepare(g)
        except NotImplementedError as exc:
            assert "T13" in str(exc)
        else:
            raise AssertionError("Rust took a three-node mesh")
