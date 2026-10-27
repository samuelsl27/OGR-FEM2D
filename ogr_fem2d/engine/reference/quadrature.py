# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The integration rules of the triangles, in one place (spec 002, T3 and D1).

Source: Zienkiewicz, O. C. and Taylor, R. L. (2000). *The Finite Element
Method*, 5th ed., vol. 1, §9.10, Table 9.2, p. 222 ("numerical integration
formulae for triangles", after Hammer et al. and Felippa). Each rule is a
list of points in area coordinates (L1, L2, L3) with their weights; the
weights add up to one, so over a straight triangle of area A

    int f dA = A sum_g w_g f(L_g),

and over a mapped one sum_g w_g f(L_g) det J(L_g) / 2 (element_t6).

The three rules used (D1):

* LINEAR, the centroid, weight 1: exact for degree 1, error O(h^2). The
  triangle of three nodes, in plane strain and in axisymmetry;
* QUADRATIC, the three mid-side points (1/2, 1/2, 0), (0, 1/2, 1/2),
  (1/2, 0, 1/2), weight 1/3 each: exact for degree 2, error O(h^3). The
  six-node triangle in plane strain, as validated in spec 001 (same points,
  same order);
* QUINTIC, seven interior points: the centroid, weight 0.225; three points
  (alpha1, beta1, beta1) and permutations, weight 0.1323941527; three
  (alpha2, beta2, beta2), weight 0.1259391805; with alpha1 = 0.0597158717,
  beta1 = 0.4701420641, alpha2 = 0.7974269853, beta2 = 0.1012865073 (ten
  decimals, as printed). Exact for degree 5, error O(h^6). The six-node
  triangle in axisymmetry, because no point lies on a side, so none on the
  axis where N_i / r cannot be evaluated (D1).

The quintic coordinates and weights are written here in closed form,

    alpha1 = (9 - 2 sqrt 15) / 21,   beta1 = (6 + sqrt 15) / 21,
    alpha2 = (9 + 2 sqrt 15) / 21,   beta2 = (6 - sqrt 15) / 21,
    w1 = (155 + sqrt 15) / 1200,     w2 = (155 - sqrt 15) / 1200,

so that the rule is exact to rounding and not to the ten decimals of the
table (whose weights add up to 0.9999999996). The closed form is not
printed in the source: it is the rule the table truncates (the table cuts
at the tenth decimal, it does not round: alpha2 = 0.79742698535... is
printed 0.7974269853, w1 = 0.13239415278... is printed 0.1323941527), and
the tests check it both ways, against every printed digit and against the
exact integral of every monomial up to degree 5 (Eq. 8.38, p. 183).

The cubic rule of the table (four points, one weight negative, -27/48) is
not used, and is not here.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math
from dataclasses import dataclass

Point = tuple[float, float, float]


@dataclass(frozen=True)
class Rule:
    """A rule of Table 9.2: its name, the polynomial degree it integrates
    exactly, and its points ((L1, L2, L3), weight)."""
    name: str
    degree: int
    points: tuple[tuple[Point, float], ...]

    def __len__(self) -> int:
        return len(self.points)


THIRD = 1.0 / 3.0

LINEAR = Rule("linear", 1, (((THIRD, THIRD, THIRD), 1.0),))

QUADRATIC = Rule("quadratic", 2, (((0.5, 0.5, 0.0), THIRD),
                                  ((0.0, 0.5, 0.5), THIRD),
                                  ((0.5, 0.0, 0.5), THIRD)))

_R15 = math.sqrt(15.0)
ALPHA1, BETA1 = (9.0 - 2.0 * _R15) / 21.0, (6.0 + _R15) / 21.0
ALPHA2, BETA2 = (9.0 + 2.0 * _R15) / 21.0, (6.0 - _R15) / 21.0
W0, W1, W2 = 0.225, (155.0 + _R15) / 1200.0, (155.0 - _R15) / 1200.0

#: points a to g of the table, in its order
QUINTIC = Rule("quintic", 5, (
    ((THIRD, THIRD, THIRD), W0),
    ((ALPHA1, BETA1, BETA1), W1), ((BETA1, ALPHA1, BETA1), W1), ((BETA1, BETA1, ALPHA1), W1),
    ((ALPHA2, BETA2, BETA2), W2), ((BETA2, ALPHA2, BETA2), W2), ((BETA2, BETA2, ALPHA2), W2),
))

#: Table 9.2 as printed, for the tests: (alpha1, beta1, alpha2, beta2, w0, w1, w2)
PRINTED_QUINTIC = (0.0597158717, 0.4701420641, 0.7974269853, 0.1012865073,
                   0.2250000000, 0.1323941527, 0.1259391805)

#: The two analyses (model.py re-exports them).
PLANE_STRAIN, AXISYMMETRIC = "plane_strain", "axisymmetric"


def rule_for(nodes_per_element: int, analysis: str) -> Rule:
    """The rule of each element and analysis (spec 002, D1)."""
    if nodes_per_element == 3 and analysis in (PLANE_STRAIN, AXISYMMETRIC):
        return LINEAR
    if nodes_per_element == 6 and analysis == PLANE_STRAIN:
        return QUADRATIC
    if nodes_per_element == 6 and analysis == AXISYMMETRIC:
        return QUINTIC
    raise ValueError(f"no rule for {nodes_per_element}-node triangles in {analysis!r}")
