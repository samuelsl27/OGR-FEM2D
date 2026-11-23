# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The quality of a mesh, element by element and in summary (spec 003, RF-12,
D7).

Per element, on its three corners (the straight triangle; the curved sides
of a six-node triangle are judged by its jacobian, ``checks.py``, RF-13):

* its smallest and largest angles (law of cosines);
* its circumradius-to-shortest-edge ratio, the quantity the refinement
  bounds by B: a triangle within B has no angle below arcsin(1/2B)
  (Shewchuk 2002a, §2, p. 5);
* the two measures of Shewchuk (2002b) chosen in D7, the exact
  scale-invariant ones of his table 4 (p. 44) with the constants of table 6
  (p. 53) that make them one on the equilateral triangle, zero on a
  degenerate one and negative on an inverted one: one tied to the error of
  the interpolated gradient and one to the conditioning of the stiffness
  matrix. They are the core's (``ogr_core.fem.mesh``, v0.2.5), which tests
  them against the source; they are not written again here.

The summary gives, for each, the worst value, the mean and the
distribution (how many elements fall in each interval), and the elements
whose ratio is above B: "bad" is below the guarantee of the refinement and
nothing else (D7; no source read gives other thresholds). With input angles
of 60 degrees or less, or with arcs, some may be left above B (theorem 12;
D15), and the summary says which.

These are notes (rule 12): they use acos and sqrt, and nothing in the mesh
depends on them.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math
from collections.abc import Sequence

from ogr_core.fem.mesh import triangle_conditioning_quality, triangle_gradient_quality

Point = tuple[float, float]

#: The intervals of the distributions: smallest angle, in degrees, and the
#: measures, which go from 0 to 1 (below 0, inverted).
ANGLE_EDGES = (0.0, 5.0, 10.0, 15.0, 20.0, 25.0, 30.0, 40.0, 50.0, 60.0)
MEASURE_EDGES = (0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0)


def element_quality(a: Point, b: Point, c: Point) -> dict:
    """The measures of the triangle (a, b, c)."""
    la2 = (b[0] - c[0]) ** 2 + (b[1] - c[1]) ** 2       # opposite a
    lb2 = (c[0] - a[0]) ** 2 + (c[1] - a[1]) ** 2
    lc2 = (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2
    la, lb, lc = math.sqrt(la2), math.sqrt(lb2), math.sqrt(lc2)
    twice_area = (b[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (b[1] - a[1])
    angles = []
    for opp2, s1, s2 in ((la2, lb, lc), (lb2, lc, la), (lc2, la, lb)):
        if s1 == 0.0 or s2 == 0.0:
            angles.append(0.0)
            continue
        cos = (s1 * s1 + s2 * s2 - opp2) / (2.0 * s1 * s2)
        angles.append(math.degrees(math.acos(max(-1.0, min(1.0, cos)))))
    shortest = min(la, lb, lc)
    if twice_area == 0.0 or shortest == 0.0:
        ratio = math.inf
    else:
        ratio = la * lb * lc / (2.0 * abs(twice_area)) / shortest     # R = abc / 4A
    # the three add up to 180: the smallest is at most 60 and the largest at
    # least 60, which the rounding of acos may cross by a unit
    return {"min_angle": min(min(angles), 60.0), "max_angle": max(max(angles), 60.0),
            "ratio": ratio,
            "gradient": triangle_gradient_quality(a, b, c),
            "conditioning": triangle_conditioning_quality(a, b, c)}


def _distribution(values: Sequence[float], edges: Sequence[float]) -> tuple[int, ...]:
    """How many values fall below edges[0], in [edges[k], edges[k+1]) for
    every k (the last one closed), and above edges[-1]."""
    counts = [0] * (len(edges) + 1)
    for v in values:
        if v < edges[0]:
            counts[0] += 1
        elif v > edges[-1]:
            counts[-1] += 1
        else:
            k = 1
            while k < len(edges) - 1 and v >= edges[k]:
                k += 1
            counts[k] += 1
    return tuple(counts)


def summary(nodes: Sequence[Point], elements: Sequence[tuple[int, ...]], bound: float) -> dict:
    """RF-12: the worst value, the mean and the distribution of every
    measure over the elements (their corners), and the elements whose ratio
    is above ``bound`` (B), with their ratio."""
    per = [element_quality(nodes[e[0]], nodes[e[1]], nodes[e[2]]) for e in elements]
    n = len(per)
    out: dict = {"elements": n, "bound": bound,
                 "angle_guaranteed": math.degrees(math.asin(1.0 / (2.0 * bound)))}
    if not n:
        return out
    for key, worst, edges in (("min_angle", min, ANGLE_EDGES), ("max_angle", max, None),
                              ("gradient", min, MEASURE_EDGES),
                              ("conditioning", min, MEASURE_EDGES)):
        values = [q[key] for q in per]
        out[key] = {"worst": worst(values), "mean": sum(values) / n}
        if edges is not None:
            out[key]["edges"] = edges
            out[key]["counts"] = _distribution(values, edges)
    out["above_bound"] = tuple((e, q["ratio"]) for e, q in enumerate(per)
                               if q["ratio"] > bound * (1.0 + 1e-12))
    out["inverted"] = sum(1 for q in per if q["gradient"] < 0.0)
    return out
