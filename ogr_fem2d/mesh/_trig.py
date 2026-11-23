# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Trigonometry that gives the same bits on every platform (spec 003, RF-11 and
D11: the same input, the same mesh, bit for bit).

``math.sin``, ``math.cos``, ``math.atan2``, ``math.asin`` and ``math.hypot``
come from each system's mathematical library, and those are not required to
round the last bit alike: the core found its fingerprint of the same mesh
different in Linux and Windows because its test's input used sin and cos
(OGR-Core, reply of 2026-11-23). Where a function decides a coordinate of the
mesh or a number of divisions, the mesher uses these instead. They are built
from +, -, *, / and sqrt only, which IEEE 754 rounds correctly, hence alike,
everywhere; and from Python's ``round`` and ``math.pi``, which are exact.

Nothing here is a new formula; they are the textbook series and identities:

* sin and cos: t = n pi/2 + r with |r| <= pi/4 (n by Python's round), the
  Taylor series of r summed from its smallest term, and the quadrant n mod 4
  as an exact exchange of sign and order;
* atan: atan(x) = pi/2 - atan(1/x) for |x| > 1, and the half-angle identity
  atan(x) = 2 atan(x / (1 + sqrt(1 + x^2))) until |x| < 0.1, then the
  series x - x^3/3 + x^5/5 - ...;
* atan2 by quadrants; asin(s) = atan2(s, sqrt(1 - s^2));
* length(a, b) = sqrt(dx^2 + dy^2).

They agree with ``math`` to a few units in the last place; tests check both
that and that they never call it.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math

_PI = math.pi
_HALF_PI = 0.5 * math.pi
_TWO_PI = 2.0 * math.pi


def length(a, b) -> float:
    """The distance between two points, sqrt(dx^2 + dy^2)."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    return math.sqrt(dx * dx + dy * dy)


def norm(dx: float, dy: float) -> float:
    return math.sqrt(dx * dx + dy * dy)


def _sin_cos_small(x: float) -> tuple[float, float]:
    """Taylor series of sin and cos for |x| <= pi/4, summed from the
    smallest term up (the last terms are below 1e-30)."""
    x2 = x * x
    s_terms, c_terms = [x], [1.0]
    for k in range(1, 14):
        s_terms.append(-s_terms[-1] * x2 / ((2 * k) * (2 * k + 1)))
        c_terms.append(-c_terms[-1] * x2 / ((2 * k - 1) * (2 * k)))
    s = c = 0.0
    for a, b in zip(reversed(s_terms), reversed(c_terms)):
        s += a
        c += b
    return s, c


def sin_cos(t: float) -> tuple[float, float]:
    """(sin t, cos t): t reduced by quadrants, t = n pi/2 + r with
    |r| <= pi/4, the series of r, and the exact rotation of the quadrant."""
    n = round(t / _HALF_PI)
    r = t - n * _HALF_PI
    s, c = _sin_cos_small(r)
    q = n % 4
    if q == 0:
        return s, c
    if q == 1:
        return c, -s
    if q == 2:
        return -s, -c
    return -c, s


def sin(t: float) -> float:
    return sin_cos(t)[0]


def cos(t: float) -> float:
    return sin_cos(t)[1]


def atan(x: float) -> float:
    if x != x:
        return x
    if x < 0.0:
        return -atan(-x)
    if x > 1.0:
        return _HALF_PI - atan(1.0 / x)
    halvings = 0
    while x >= 0.1:
        x = x / (1.0 + math.sqrt(1.0 + x * x))
        halvings += 1
    x2 = x * x
    total, power = 0.0, x
    for k in range(12):
        total += power / (2 * k + 1) if k % 2 == 0 else -power / (2 * k + 1)
        power *= x2
    return total * (1 << halvings)


def atan2(y: float, x: float) -> float:
    if x > 0.0:
        return atan(y / x)
    if x < 0.0:
        return atan(y / x) + (_PI if y >= 0.0 else -_PI)
    if y > 0.0:
        return _HALF_PI
    if y < 0.0:
        return -_HALF_PI
    return 0.0


def asin(s: float) -> float:
    s = max(-1.0, min(1.0, s))
    return atan2(s, math.sqrt(1.0 - s * s))
