# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.0.2 (spec 002, T5) — axisymmetry of the three- and six-node triangles.

Against Zienkiewicz and Taylor (2000), *The Finite Element Method*, 5th ed.,
vol. 1, §5.2, pp. 112-119, or identities that need no source:

* **D is that of the source**: Eq. (5.12), and its rows (r, z, rz) are the
  plane-strain matrix of Eq. (4.16), which is the same law with the hoop
  strain zero;
* **B is that of the source**: for the three-node triangle, the hoop row of
  Eq. (5.6), (a_i + b_i r + c_i z) / (r 2 Delta), with a_i, b_i, c_i of
  Eq. (5.4); and the stiffness with the centroid is Eq. (5.14),
  2 pi B^T D B r_bar Delta;
* **the ring**: the volume by the quadrature is 2 pi r_bar A, the area
  times the path of its centroid (p. 118), for both elements;
* **rigid body** (§5.2.2): only the translation along the axis strains
  nothing; a six-node element off the axis has ONE zero-energy mode, not
  three. The three-node one with the centroid (Eq. 5.14) has a second,
  spurious one, because B is 4 x 6 at a single point; an assembled mesh,
  held only against the axial translation (and on the axis), has no
  mechanism with either element. A constant radial displacement is NOT
  rigid: it stretches every ring, eps_theta = u / r at each point;
* **patch test**: "if u is proportional to r ... the strains will all be
  constant" and v linear adds constant eps_z (p. 115). The field u = a r,
  v = b z + c is in equilibrium without body force (sigma_r = sigma_theta),
  so on distorted patches touching the axis, T3 and T6, its nodal values
  leave no residual inside and the boundary alone gives it back inside;
* **a stage through the engine**: a cylinder pulled along its axis by the
  consistent ring forces of a uniform traction q, 2 pi int N q r ds on the
  top, ends with sigma_z = q, sigma_r = sigma_theta = tau_rz = 0 at every
  point and the displacement u = -nu q r / E, v = q z / E;
* **two routes to one matrix**: the stiffness assembled point by point,
  with the hoop column of B, is the element-by-element one;
* **the axis** (D1): no integration point of an element with a side on the
  axis is at r = 0, while the quadratic rule of plane strain would put one
  there, and the engine says so instead of dividing by zero;
* **D6**: Mohr-Coulomb in axisymmetry is refused; Rust says it has no
  axisymmetry yet (T13).
"""
from __future__ import annotations

import math

import numpy as np

import _blocks
from ogr_fem2d.engine.compiled import RUST
from ogr_fem2d.engine.reference import element_t3 as t3
from ogr_fem2d.engine.reference import element_t6 as t6
from ogr_fem2d.engine.reference import mohr_coulomb as mc
from ogr_fem2d.engine.reference import quadrature as q
from ogr_fem2d.engine.reference import solver, triangle
from ogr_fem2d.engine.reference.elastic import (Elastic, axisymmetric_matrix,
                                                plane_strain_matrix)

E, NU = 20000.0, 0.2
AXI = q.AXISYMMETRIC
TRI = [(0.7, -0.2), (2.1, 0.4), (1.2, 1.7)]          # off the axis


def straight_t6(corners):
    (x1, y1), (x2, y2), (x3, y3) = corners
    return list(corners) + [((x1 + x2) / 2, (y1 + y2) / 2), ((x2 + x3) / 2, (y2 + y3) / 2),
                            ((x3 + x1) / 2, (y3 + y1) / 2)]


def k_axi(shape, xy):
    rule = q.rule_for(len(shape.NODES_L), AXI)
    return np.array(triangle.stiffness(shape, xy, axisymmetric_matrix(E, NU), rule, True))


class TestTheSource:

    def test_d_is_eq_5_12_and_contains_plane_strain(self):
        d = axisymmetric_matrix(E, NU)
        f = E / ((1 + NU) * (1 - 2 * NU))
        want = [[1 - NU, NU, NU, 0], [NU, 1 - NU, NU, 0], [NU, NU, 1 - NU, 0],
                [0, 0, 0, (1 - 2 * NU) / 2]]
        assert max(abs(d[i][j] - f * want[i][j]) for i in range(4) for j in range(4)) < 1e-9
        ps = plane_strain_matrix(E, NU)
        keep = (0, 1, 3)
        assert max(abs(ps[i][j] - d[keep[i]][keep[j]]) for i in range(3) for j in range(3)) < 1e-9

    def test_b_of_the_three_node_triangle_is_eq_5_6(self):
        l = q.LINEAR.points[0][0]
        b, det = triangle.b_matrix(t3, TRI, *l, axisymmetric=True)
        r_c = sum(x for x, _ in TRI) / 3
        z_c = sum(y for _, y in TRI) / 3
        for i in range(3):
            j, m = (i + 1) % 3, (i + 2) % 3
            (ri, zi), (rj, zj), (rm, zm) = TRI[i], TRI[j], TRI[m]
            a_i, b_i, c_i = rj * zm - rm * zj, zj - zm, rm - rj           # Eq. (5.4)
            want = [[b_i, 0], [0, c_i], [(a_i + b_i * r_c + c_i * z_c) / r_c, 0], [c_i, b_i]]
            for row in range(4):
                for col in range(2):
                    assert abs(b[row][2 * i + col] - want[row][col] / det) < 1e-13, (i, row, col)

    def test_the_centroid_stiffness_is_eq_5_14(self):
        l = q.LINEAR.points[0][0]
        b = np.array(triangle.b_matrix(t3, TRI, *l, axisymmetric=True)[0])
        delta = 0.5 * np.linalg.det(np.array([[1, x, y] for x, y in TRI]))
        r_c = sum(x for x, _ in TRI) / 3
        want = 2 * math.pi * b.T @ np.array(axisymmetric_matrix(E, NU)) @ b * r_c * delta
        assert np.abs(k_axi(t3, TRI) - want).max() < 1e-12 * np.abs(want).max()

    def test_the_volume_is_area_times_the_path_of_the_centroid(self):
        area = 0.5 * np.linalg.det(np.array([[1, x, y] for x, y in TRI]))
        r_c = sum(x for x, _ in TRI) / 3
        for shape, xy in ((t3, TRI), (t6, straight_t6(TRI))):
            for rule in (q.LINEAR, q.QUADRATIC, q.QUINTIC):
                assert abs(triangle.volume(shape, xy, rule) - 2 * math.pi * r_c * area) < 1e-12


class TestRigidBody:

    def test_only_the_axial_translation_is_free(self):
        # T6 with seven points: one zero-energy mode. T3 with the centroid,
        # Eq. (5.14): B is 4 x 6 at one point, so K has rank 4 and a second,
        # spurious zero mode (the source's one-point formula, reproduced
        # above); the assembled mesh has none (next test).
        for shape, xy, zeros in ((t3, TRI, 2), (t6, straight_t6(TRI), 1)):
            k = k_axi(shape, xy)
            eig = np.sort(np.linalg.eigvalsh(0.5 * (k + k.T)))
            tol = 1e-10 * eig[-1]
            assert np.all(np.abs(eig[:zeros]) < tol) and eig[zeros] > tol, (shape.__name__, eig[:3])
            n = len(xy)
            axial = np.array([0.0, 1.0] * n)
            radial = np.array([1.0, 0.0] * n)
            assert np.abs(k @ axial).max() < 1e-10 * np.abs(k).max()
            assert radial @ k @ radial > 1e-3 * np.abs(k).max()

    def test_an_assembled_mesh_has_no_mechanism(self):
        # held only against the axial translation (one v), plus u = 0 on the
        # axis when the block touches it: the stiffness is positive definite,
        # T3 included (its element mode is not shared by the neighbours)
        for six in (False, True):
            for x0 in (0.0, 0.5):
                for nx, ny in ((1, 1), (3, 2)):
                    b = _blocks.block(six, nx=nx, ny=ny, w=2.0, h=1.5, x0=x0)
                    m = solver.Model(b.nodes, b.elements, [Elastic(E, NU)] * len(b.elements),
                                     frozenset(), analysis=AXI)
                    k = solver.stiffness(m).toarray()
                    fixed = {1} | ({2 * n for n in b.left()} if x0 == 0.0 else set())
                    free = [i for i in range(len(k)) if i not in fixed]
                    eig = np.linalg.eigvalsh(k[np.ix_(free, free)])
                    assert eig[0] > 1e-7 * eig[-1], (six, x0, nx, ny, eig[0] / eig[-1])

    def test_a_constant_radial_displacement_stretches_the_rings(self):
        c = 1e-3
        for shape, xy in ((t3, TRI), (t6, straight_t6(TRI))):
            rule = q.rule_for(len(xy), AXI)
            u = [c, 0.0] * len(xy)
            for (l1, l2, l3), eps in zip((p for p, _ in rule.points),
                                         triangle.strains(shape, xy, u, rule, True)):
                r = triangle.radius(shape, xy, l1, l2, l3)
                assert abs(eps[2] - c / r) < 1e-15 and max(abs(eps[i]) for i in (0, 1, 3)) < 1e-15


def _patch(six: bool):
    """Distorted triangles around the interior node 5, with nodes 3 and 4 ON
    the axis (r = 0): sides on the axis, as in a meridian section."""
    corners = [(0.4, 0.0), (2.0, 0.1), (2.3, 1.8), (0.0, 2.0), (0.0, 0.7), (1.1, 0.9)]
    tris = [(0, 1, 5), (1, 2, 5), (2, 3, 5), (3, 4, 5), (4, 0, 5)]
    if not six:
        return corners, tris, [5]
    nodes, mids, elements = list(corners), {}, []

    def mid(i, j):
        key = tuple(sorted((i, j)))
        if key not in mids:
            (xa, ya), (xb, yb) = corners[i], corners[j]
            shift = 0.04 if 5 in key else 0.0                 # curved inside
            mids[key] = len(nodes)
            nodes.append(((xa + xb) / 2 + shift, (ya + yb) / 2 - shift))
        return mids[key]

    for a, b, c in tris:
        elements.append((a, b, c, mid(a, b), mid(b, c), mid(c, a)))
    return nodes, elements, [5] + [n for key, n in mids.items() if 5 in key]


def _field(r, z):
    return 0.002 * r, -0.01 + 0.003 * z            # u = a r, v = b z + c


class TestPatch:

    def _k(self, six):
        nodes, elements, interior = _patch(six)
        m = solver.Model(nodes, elements, [Elastic(E, NU)] * len(elements), frozenset(),
                         analysis=AXI)
        return nodes, interior, solver.stiffness(m).toarray()

    def test_a_exact_values_leave_no_interior_residual(self):
        for six in (False, True):
            nodes, interior, k = self._k(six)
            u = np.array([c for xy in nodes for c in _field(*xy)])
            dofs = [2 * n + c for n in interior for c in (0, 1)]
            r = (k @ u)[dofs]
            assert np.abs(r).max() < 1e-12 * np.abs(k).max() * np.abs(u).max(), (six, r)

    def test_b_the_boundary_alone_gives_the_field_inside(self):
        for six in (False, True):
            nodes, interior, k = self._k(six)
            u = np.array([c for xy in nodes for c in _field(*xy)])
            free = [2 * n + c for n in interior for c in (0, 1)]
            fixed = [i for i in range(len(u)) if i not in free]
            got = np.linalg.solve(k[np.ix_(free, free)], -k[np.ix_(free, fixed)] @ u[fixed])
            assert np.abs(got - u[free]).max() < 1e-13, (six, np.abs(got - u[free]).max())

    def test_no_point_on_the_axis(self):
        for six in (False, True):
            nodes, elements, _ = _patch(six)
            m = solver.Model(nodes, elements, [Elastic(E, NU)] * len(elements), frozenset(),
                             analysis=AXI)
            points = solver.integration_points(m)
            assert len(points) == len(elements) * (7 if six else 1)
            assert min(p.xy[0] for p in points) > 0.0
        # the quadratic rule puts a point on side (3, 4), which lies on the axis
        nodes, elements, _ = _patch(True)
        xy = [nodes[n] for n in elements[3]]
        try:
            triangle.b_matrix(t6, xy, 0.5, 0.5, 0.0, axisymmetric=True)
        except ValueError as exc:
            assert "r = 0" in str(exc)
        else:
            raise AssertionError("a point on the axis gave a B")


class TestStageThroughTheEngine:

    def test_a_pulled_cylinder(self):
        qz = 2.5
        for six in (False, True):
            b = _blocks.block(six, nx=3, ny=2, w=2.0, h=1.5)          # 0 <= r <= 2
            restrained = {2 * n for n in b.left()} | {2 * n + 1 for n in b.bottom()}
            load = [0.0] * (2 * len(b.nodes))
            for edge in b.top_edges():
                r = [b.nodes[n][0] for n in edge]
                length = r[-1] - r[0]
                # 2 pi int N r ds: T3 ends (2 r1 + r2)/6, (r1 + 2 r2)/6; T6
                # ends r1/6, r2/6 and middle (r1 + r2)/3 (exact integrals)
                shares = ((r[0] / 6, (r[0] + r[2]) / 3, r[2] / 6) if six else
                          ((2 * r[0] + r[1]) / 6, (r[0] + 2 * r[1]) / 6))
                for n, share in zip(edge, shares):
                    load[2 * n + 1] += 2 * math.pi * qz * share * length
            m = solver.Model(b.nodes, b.elements, [Elastic(E, NU)] * len(b.elements),
                             frozenset(restrained), analysis=AXI)
            n_points = len(b.elements) * (7 if six else 1)
            res = solver.solve_stage(m, [(0.0,) * 4] * n_points, load, 1, 1e-12, 3)
            for s in res.stresses:
                assert abs(s[1] - qz) < 1e-11 and max(abs(s[i]) for i in (0, 2, 3)) < 1e-11, (six, s)
            for i, (r, z) in enumerate(b.nodes):
                assert abs(res.displacement[2 * i] + NU * qz * r / E) < 1e-15, (six, i)
                assert abs(res.displacement[2 * i + 1] - qz * z / E) < 1e-15, (six, i)

    def test_point_by_point_equals_element_by_element(self):
        # with elastic tangents, K_T assembled point by point (the route of
        # the iterations) is the element-by-element stiffness, hoop row too
        for six in (False, True):
            nodes, elements, _ = _patch(six)
            m = solver.Model(nodes, elements, [Elastic(E, NU)] * len(elements), frozenset(),
                             analysis=AXI)
            points = solver.integration_points(m)
            d = axisymmetric_matrix(E, NU)
            kt = solver.tangent_stiffness(points, [d] * len(points), 2 * len(nodes)).toarray()
            k = solver.stiffness(m).toarray()
            assert np.abs(kt - k).max() < 1e-12 * np.abs(k).max(), six

    def test_the_hoop_stress_does_work(self):
        # internal forces of a uniform sigma_theta alone: only radial, and
        # their sum is sigma_theta times int dA over the section (B^T row
        # N/r times the 2 pi r of the ring: 2 pi int N dA, summed over N)
        b = _blocks.block(True, nx=2, ny=1, w=1.0, h=1.0, x0=0.5)
        m = solver.Model(b.nodes, b.elements, [Elastic(E, NU)] * len(b.elements), frozenset(),
                         analysis=AXI)
        points = solver.integration_points(m)
        f = solver.internal_forces(points, [(0.0, 0.0, 3.0, 0.0)] * len(points), 2 * len(b.nodes))
        assert abs(sum(f[0::2]) - 3.0 * 2 * math.pi * 1.0) < 1e-12
        assert max(abs(x) for x in f[1::2]) < 1e-15


class TestRefused:

    def test_mohr_coulomb_and_rust(self):
        law = mc.MohrCoulomb(E, NU, 1.0, math.radians(30.0), 0.0)
        try:
            solver.update_stress(law, (0.0,) * 4, (1e-4, 0.0, 0.0, 0.0))
        except ValueError as exc:
            assert "D6" in str(exc)
        else:
            raise AssertionError("Mohr-Coulomb ran in axisymmetry")
        nodes, elements, _ = _patch(True)
        m = solver.Model(nodes, elements, [Elastic(E, NU)] * len(elements), frozenset(),
                         analysis=AXI)
        try:
            RUST.prepare(solver.geometry(m, solver.integration_points(m)))
        except NotImplementedError as exc:
            assert "T13" in str(exc)
        else:
            raise AssertionError("Rust took an axisymmetric model")
