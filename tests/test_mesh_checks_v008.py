# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.0.8 (spec 003, T6) — the checks of a mesh before it is delivered (RF-13,
RF-14; ogr_fem2d/mesh/checks.py).

Invariants protected:

* **the middle half** (Zienkiewicz and Taylor 2000, §9.2, fig. 9.6): on a
  straight side, a mid-side node at a fraction t of the side gives
  dx/dxi = L (4t - 1) and L (3 - 4t) at the two corners, so det J > 0 at the
  nodes exactly for 1/4 < t < 3/4; the check accepts t = 0.26 and 0.74 and
  refuses 0.25, 0.2, 0.75 and 0.8, and says which element and why;
* **a straight six-node element** has det J = 2 A everywhere, and the
  six-node meshes made in T5 (arcs included) pass;
* **flat and inverted elements** are refused, three- and six-node alike;
* **the topology of a plane triangulation**: Euler's V - E + T = C - H gives
  no hole for a rectangle and for the quarter annulus, one for the square
  around the excavation, and two pieces with no side between them are
  counted as such; a node joining two of them is a pinch;
* **a conforming mesh**: a side of three elements and a hanging node (a node
  inside a boundary side) are refused; pieces and pinches are warnings, not
  errors.
"""
from __future__ import annotations

import math

from ogr_fem2d.engine.reference import element_t6
from ogr_fem2d.mesh import checks as c
from ogr_fem2d.mesh import quadratic as q
from test_mesh_quadratic_v008 import _annulus, _core_tunnel

TRI = ((0.0, 0.0), (2.0, 0.0), (0.0, 1.0))


def _t6_with_side_node_at(t: float):
    """The triangle TRI with the mid-side node of side 0-1 at a fraction t of
    the side from corner 0; the other mid-side nodes in the middle."""
    a, b, e = TRI
    nodes = [a, b, e, (t * b[0], 0.0), (0.5 * (b[0] + e[0]), 0.5 * (b[1] + e[1])),
             (0.5 * e[0], 0.5 * e[1])]
    return nodes, [(0, 1, 2, 3, 4, 5)]


class TestTheMiddleHalf:
    def test_det_j_at_the_corners_is_l_times_4t_minus_1_and_3_minus_4t(self):
        for t in (0.3, 0.5, 0.7):
            nodes, el = _t6_with_side_node_at(t)
            dets = dict(c.jacobian_dets(nodes, "plane_strain"))
            # det J = (dx/dxi)(dy/deta) - (dy/dxi)(dx/deta). At both corners of
            # side 0-1 (length 2), dy/dxi = 0 and dy/deta = 1 (worked out from
            # the shape functions of p. 182: at corner 1 only N3 and N5 carry
            # y, with -1 x 1 + 4 x 1/2), so det J = 2 (4t - 1) and 2 (3 - 4t)
            assert math.isclose(dets["node 0"], 2.0 * (4 * t - 1), rel_tol=1e-14), dets
            assert math.isclose(dets["node 1"], 2.0 * (3 - 4 * t), rel_tol=1e-14), dets

    def test_inside_the_middle_half_passes_outside_is_refused(self):
        for t in (0.26, 0.5, 0.74):
            nodes, el = _t6_with_side_node_at(t)
            assert c.element_problems(nodes, el, "plane_strain") == [], t
        for t in (0.25, 0.2, 0.75, 0.8):
            nodes, el = _t6_with_side_node_at(t)
            found = c.element_problems(nodes, el, "plane_strain")
            assert [p.rule for p in found] == ["jacobian"], (t, found)
            assert found[0].where.startswith("element 0, node"), found


#: Found by a random search in T6: det J > 0 at the six nodes (min 0.167),
#: -0.055 at an interior integration point of the seven-point rule.
FOLDED = [(2.0, 0.0), (3.0, 0.0), (2.0, 1.0), (2.3222815106282666, -0.05412996162380279),
          (2.8635354452333504, 0.44301928832862114), (2.5511148857754424, 0.0863658777823022)]


def _sampled_min(xy, n=300):
    """det J by the engine's own jacobian on a fine grid of the parent
    triangle: an outside view of the minimum."""
    from ogr_fem2d.engine.reference import triangle
    best = math.inf
    for i in range(n + 1):
        for j in range(n + 1 - i):
            xi, eta = i / n, j / n
            best = min(best, triangle.jacobian(element_t6, list(xy), 1 - xi - eta, xi, eta)[1])
    return best


class TestTheWholeElement:
    def test_a_fold_inside_is_refused_in_both_analyses(self):
        dets = dict(c.jacobian_dets(FOLDED, "plane_strain"))
        assert min(v for k, v in dets.items()) > 0.0          # what the engine would see
        for analysis in ("plane_strain", "axisymmetric"):
            found = c.element_problems(FOLDED, [(0, 1, 2, 3, 4, 5)], analysis)
            assert [p.rule for p in found] == ["jacobian"], (analysis, found)

    def test_the_minimum_is_that_of_a_fine_sampling(self):
        # INSIDE: an element whose det J has its minimum inside the triangle
        # (found by a random search; the sampling below confirms where)
        inside = [(0.0, 0.0), (1.0, 0.0), (0.0, 1.0), (0.706, 0.6903), (0.9507, 0.1984),
                  (-0.1599, 0.7361)]
        _, (xi, eta) = c.minimum_det(inside)
        assert min(xi, eta, 1.0 - xi - eta) > 0.1, (xi, eta)
        cases = [inside, FOLDED, _t6_with_side_node_at(0.3)[0], _t6_with_side_node_at(0.5)[0]]
        m, arcs = _annulus()
        mesh = q.promote(m.nodes, m.elements, arcs)
        cases += [[mesh.nodes[i] for i in e] for e in mesh.elements[:5]]
        for xy in cases:
            exact, (xi, eta) = c.minimum_det(xy)
            sampled = _sampled_min(xy)
            assert exact <= sampled + 1e-13, (exact, sampled)
            # a grid of step 1/300 comes within O(h^2) of the minimum of a quadratic
            assert sampled - exact <= 1e-3 * max(1.0, abs(exact)), (exact, sampled)
            assert xi >= 0.0 and eta >= 0.0 and xi + eta <= 1.0 + 1e-15


class TestValidElements:
    def test_a_straight_six_node_element_has_det_j_twice_its_area(self):
        nodes, _ = _t6_with_side_node_at(0.5)
        for analysis in ("plane_strain", "axisymmetric"):
            for where, det in c.jacobian_dets(nodes, analysis):
                assert math.isclose(det, 2.0 * 1.0, rel_tol=1e-14), (where, det)

    def test_the_meshes_of_t5_pass(self):
        m, arcs = _annulus()
        nodes, tris, tunnel_arcs = _core_tunnel()
        for corners, triangles, a in ((m.nodes, m.elements, arcs), (nodes, tris, tunnel_arcs)):
            mesh = q.promote(corners, triangles, a)
            for analysis in ("plane_strain",):
                assert c.element_problems(mesh.nodes, mesh.elements, analysis) == []
        mesh = q.promote(m.nodes, m.elements, arcs)       # x >= 0: axisymmetric too
        assert c.element_problems(mesh.nodes, mesh.elements, "axisymmetric") == []


class TestFlatAndInverted:
    def test_three_and_six_node(self):
        flat3 = [(0.0, 0.0), (1.0, 0.0), (2.0, 0.0)]
        inverted3 = [TRI[0], TRI[2], TRI[1]]
        for pts in (flat3, inverted3):
            assert [p.rule for p in c.element_problems(pts, [(0, 1, 2)], "plane_strain")] == \
                ["jacobian"]
        nodes, el = _t6_with_side_node_at(0.5)
        inverted6 = [(0, 2, 1, 5, 4, 3)]
        assert [p.rule for p in c.element_problems(nodes, inverted6, "plane_strain")] == ["jacobian"]


def _two_squares_at_a_corner():
    nodes = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0), (2.0, 1.0), (2.0, 2.0), (1.0, 2.0)]
    return nodes, [(0, 1, 2), (0, 2, 3), (2, 4, 5), (2, 5, 6)]


class TestTopology:
    def test_euler_counts_the_holes(self):
        m, _ = _annulus()
        assert c.topology(m.nodes, m.elements).holes == 0
        nodes, tris, _ = _core_tunnel()
        # rock only (the excavation region left out): one hole
        rock = [t for t in tris if sum(math.hypot(*nodes[i]) for i in t) / 3 > 1.0]
        topo = c.topology(nodes, rock)
        assert (topo.components, topo.holes, topo.over_shared, topo.hanging) == (1, 1, (), ())
        # and with the excavation, none
        assert c.topology(nodes, tris).holes == 0

    def test_the_boundary_is_the_perimeter(self):
        from ogr_fem2d.engine import mesh_structured
        xs, ys = [0.0, 1.0, 2.5, 4.0], [0.0, 0.5, 2.0]
        rect = mesh_structured.rectangle(xs, ys, nodes_per_element=3)
        n = rect.nodes
        on_perimeter = set()
        for t in rect.elements:
            for k in range(3):
                i, j = t[k], t[(k + 1) % 3]
                same_line = any(n[i][d] == n[j][d] == v for d, v in
                                ((0, xs[0]), (0, xs[-1]), (1, ys[0]), (1, ys[-1])))
                if same_line:
                    on_perimeter.add(q.edge_key(i, j))
        assert set(c.topology(n, rect.elements).boundary) == on_perimeter
        assert len(on_perimeter) == 2 * (len(xs) - 1) + 2 * (len(ys) - 1)

    def test_pieces_and_pinches(self):
        nodes, tris = _two_squares_at_a_corner()
        topo = c.topology(nodes, tris)
        assert topo.components == 2 and topo.pinches == (2,)
        report = c.check(nodes, tris, "plane_strain")
        assert len(report.warnings) == 2, report.warnings


class TestConforming:
    def test_a_side_of_three_elements(self):
        nodes = [(0.0, 0.0), (1.0, 0.0), (0.5, 1.0), (0.5, -1.0), (0.5, 0.5)]
        tris = [(0, 1, 2), (1, 0, 3), (0, 1, 4)]
        try:
            c.check(nodes, tris, "plane_strain")
        except c.MeshError as e:
            assert "over_shared" in {p.rule for p in e.problems}, e.problems
        else:
            raise AssertionError("not refused")

    def test_a_hanging_node(self):
        # the left square is one triangle pair; the right one has node 6 in the
        # middle of the left one's side 1-2
        nodes = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0), (2.0, 0.0), (2.0, 1.0),
                 (1.0, 0.5)]
        tris = [(0, 1, 2), (0, 2, 3), (1, 4, 6), (6, 4, 5), (6, 5, 2)]
        try:
            c.check(nodes, tris, "plane_strain")
        except c.MeshError as e:
            assert [p.where for p in e.problems if p.rule == "hanging_node"] == ["node 6"], \
                e.problems
        else:
            raise AssertionError("not refused")

    def test_a_good_mesh_has_no_warning(self):
        m, arcs = _annulus()
        mesh = q.promote(m.nodes, m.elements, arcs)
        assert c.check(mesh.nodes, mesh.elements, "plane_strain").warnings == ()
