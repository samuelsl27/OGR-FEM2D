# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.0.8 (spec 003, T12, RF-12 and D7) — the quality of a mesh, element by
element and in summary (ogr_fem2d/mesh/quality.py).

Sources: Shewchuk (2002a), §2, p. 5 (circumradius over shortest edge B, no
angle below arcsin(1/2B)); Shewchuk (2002b), table 4 (p. 44), table 6 (p.
53) and §6.3 (p. 51): a fair measure is one on the equilateral triangle,
zero on a degenerate one, negative on an inverted one, and the same at any
scale. The measures themselves are the core's, tested there against the
source; here, what FEM2D builds on them.

Invariants protected:

* **the equilateral triangle**: angles 60 and 60, ratio 1/sqrt 3, both
  measures 1;
* **the right isosceles triangle**: angles 45 and 90, ratio sqrt(2)/2 (R is
  half the hypotenuse, the shortest edge is a leg);
* **degenerate and inverted**: a flat triangle has measures 0 and ratio
  infinite; the same triangle clockwise has them negative and the same
  angles and ratio;
* **scale and position**: the same triangle ten times larger and moved
  gives the same measures;
* **the summary**: the worst and the mean of each, the distribution adding
  up to the number of elements and put in the right interval (a 45 degree
  angle in [40, 50)), the elements above B named with their ratio, the
  inverted ones counted, and the angle B guarantees, arcsin(1/2B).
"""
from __future__ import annotations

import math

from ogr_fem2d.mesh import quality

EQ = ((0.0, 0.0), (1.0, 0.0), (0.5, math.sqrt(3.0) / 2.0))
RIGHT = ((0.0, 0.0), (1.0, 0.0), (0.0, 1.0))


class TestOneElement:
    def test_the_equilateral_triangle(self):
        q = quality.element_quality(*EQ)
        assert abs(q["min_angle"] - 60.0) < 1e-9 and abs(q["max_angle"] - 60.0) < 1e-9
        assert abs(q["ratio"] - 1.0 / math.sqrt(3.0)) < 1e-12
        assert abs(q["gradient"] - 1.0) < 1e-12 and abs(q["conditioning"] - 1.0) < 1e-12

    def test_the_right_isosceles_triangle(self):
        q = quality.element_quality(*RIGHT)
        assert abs(q["min_angle"] - 45.0) < 1e-9 and abs(q["max_angle"] - 90.0) < 1e-9
        assert abs(q["ratio"] - math.sqrt(2.0) / 2.0) < 1e-12
        assert 0.0 < q["gradient"] < 1.0 and 0.0 < q["conditioning"] < 1.0

    def test_degenerate_and_inverted(self):
        flat = quality.element_quality((0.0, 0.0), (1.0, 0.0), (2.0, 0.0))
        assert flat["gradient"] == 0.0 and flat["conditioning"] == 0.0
        assert flat["ratio"] == math.inf
        up, down = quality.element_quality(*RIGHT), quality.element_quality(RIGHT[0], RIGHT[2],
                                                                            RIGHT[1])
        assert down["gradient"] < 0.0 and down["conditioning"] < 0.0
        assert math.isclose(down["gradient"], -up["gradient"], rel_tol=1e-12)
        assert (down["min_angle"], down["max_angle"]) == (up["min_angle"], up["max_angle"])
        assert math.isclose(down["ratio"], up["ratio"], rel_tol=1e-12)

    def test_scale_and_position(self):
        a = quality.element_quality((0.0, 0.0), (3.0, 0.2), (1.0, 2.0))
        b = quality.element_quality((7.0, -5.0), (37.0, -3.0), (17.0, 15.0))
        for key in a:
            assert math.isclose(a[key], b[key], rel_tol=1e-9), key


class TestTheSummary:
    def test_worst_mean_distribution_and_above_b(self):
        nodes = [*EQ, *RIGHT, (5.0, 0.0), (6.0, 0.0), (5.5, 0.05)]
        elements = [(0, 1, 2), (3, 4, 5), (6, 7, 8), (6, 8, 7)]       # last: inverted
        s = quality.summary(nodes, elements, math.sqrt(2.0))
        assert s["elements"] == 4 and s["inverted"] == 1
        assert abs(s["angle_guaranteed"] - math.degrees(math.asin(1 / (2 * math.sqrt(2))))) < 1e-12
        assert abs(s["min_angle"]["worst"] - math.degrees(math.atan(0.1))) < 1e-9
        assert abs(s["max_angle"]["worst"] - (180.0 - 2 * math.degrees(math.atan(0.1)))) < 1e-9
        per = [quality.element_quality(*(nodes[i] for i in e)) for e in elements]
        assert math.isclose(s["gradient"]["mean"], sum(q["gradient"] for q in per) / 4)
        assert s["gradient"]["worst"] == min(q["gradient"] for q in per) < 0.0
        counts = dict(zip(("below",) + tuple(s["min_angle"]["edges"]), s["min_angle"]["counts"]))
        assert sum(s["min_angle"]["counts"]) == 4
        assert counts[40.0] == 1 and counts[50.0] == 1 and counts[5.0] == 2, counts
        assert [e for e, _r in s["above_bound"]] == [2, 3]
        assert s["above_bound"][0][1] == per[2]["ratio"] > math.sqrt(2.0)

    def test_an_empty_mesh(self):
        assert quality.summary([], [], 2.0)["elements"] == 0
