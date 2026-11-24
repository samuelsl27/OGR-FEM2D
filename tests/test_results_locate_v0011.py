# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.0.11 (spec 005, T6) — a point in its element (RF-10; D11).

Invariants protected:

* **inside**: a point inside one element is found in it alone, and its area
  coordinates map back to the point;
* **on a side, on a node**: every element that has it, in the order of
  their indices;
* **the curved side** of a T6 on an arc: a point between the chord and the
  arc belongs to the element whose side is the arc (in the hole, when the
  hole is excavated: no active element, although the neighbour's corner
  triangle contains it); a point just outside the arc, to the rock;
* **excavated and outside** are said apart.
"""
from __future__ import annotations

import math

import _models
from ogr_fem2d.engine import mesh_structured as ms
from ogr_fem2d.engine.reference import solver
from ogr_fem2d.results import locate as lo

RECT = ms.rectangle([0.0, 1.0, 2.0], [0.0, 1.0, 2.0], 6)


def _tunnel():
    m = _models.meshed(_models.tunnel())
    return m.mesh


class TestStraightElements:
    def test_inside_one_element(self):
        loc = lo.Locator(RECT.nodes, RECT.elements)
        status, hits = loc.find(0.7, 0.2)
        assert status == lo.IN and len(hits) == 1
        e, lc = hits[0]
        n = solver.SHAPES[6].shape_functions(*lc)
        xy = [RECT.nodes[k] for k in RECT.elements[e]]
        assert math.isclose(sum(n[a] * xy[a][0] for a in range(6)), 0.7, abs_tol=1e-13)
        assert math.isclose(sum(n[a] * xy[a][1] for a in range(6)), 0.2, abs_tol=1e-13)

    def test_on_a_side_and_on_a_node(self):
        loc = lo.Locator(RECT.nodes, RECT.elements)
        status, hits = loc.find(1.0, 0.5)                    # the grid line x = 1
        assert status == lo.IN and len(hits) == 2 and [e for e, _ in hits] == sorted(e for e, _ in hits)
        status, hits = loc.find(1.0, 1.0)                    # the middle node
        around = [e for e, el in enumerate(RECT.elements) if any(RECT.nodes[k] == (1.0, 1.0) for k in el[:3])]
        assert sorted(e for e, _ in hits) == sorted(around)

    def test_excavated_and_outside(self):
        loc = lo.Locator(RECT.nodes, RECT.elements)
        active = [True] * len(RECT.elements)
        _, hits = loc.find(0.7, 0.2)
        active[hits[0][0]] = False
        assert loc.find(0.7, 0.2, active) == (lo.EXCAVATED, [])
        assert loc.find(2.5, 0.5, active) == (lo.OUTSIDE, [])
        assert loc.find(-1e-6, 0.5)[0] == lo.OUTSIDE


class TestTheArc:
    def test_between_the_chord_and_the_arc(self):
        mesh = _tunnel()
        loc = lo.Locator(mesh.nodes, mesh.elements)
        on_arc = sorted(math.atan2(y, x) for x, y in mesh.nodes[:]
                        if abs(math.hypot(x, y) - 1.0) < 1e-12 and 0.0 <= math.atan2(y, x) < 0.5)
        a, b = on_arc[0], on_arc[2]                          # the corners of one piece (a mid node between)
        mid = 0.5 * (a + b)
        sagitta = 1.0 - math.cos(0.5 * (b - a))
        assert sagitta > 1e-4
        inner = (1.0 - 0.5 * sagitta) * math.cos(mid), (1.0 - 0.5 * sagitta) * math.sin(mid)
        outer = (1.0 + 1e-6) * math.cos(mid), (1.0 + 1e-6) * math.sin(mid)
        hole = [r == 1 for r in mesh.element_region]          # the hole is the second region
        assert any(hole)
        status, hits = loc.find(*inner)
        assert status == lo.IN and all(hole[e] for e, _ in hits), hits
        rock = [not h for h in hole]
        assert loc.find(*inner, rock) == (lo.EXCAVATED, [])
        status, hits = loc.find(*outer, rock)
        assert status == lo.IN and all(not hole[e] for e, _ in hits)
        # the corner triangle of the rock element would have taken the inner point
        e = hits[0][0]
        (x1, y1), (x2, y2), (x3, y3) = (mesh.nodes[k] for k in mesh.elements[e][:3])
        det = (x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1)
        x, y = inner
        l1 = ((x2 - x) * (y3 - y) - (x3 - x) * (y2 - y)) / det
        l2 = ((x3 - x) * (y1 - y) - (x1 - x) * (y3 - y)) / det
        assert min(l1, l2, 1.0 - l1 - l2) > 0.0
