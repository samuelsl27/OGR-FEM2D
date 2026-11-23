# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.0.8 (spec 003, RF-11 and D11) — the same input gives the same mesh, bit
for bit, on every platform.

Found by the core (its reply of 2026-11-23): the fingerprint of the same
mesh came out different in Linux and Windows, because the input of its test
used math.sin and math.cos, and each system's mathematical library may round
the last bit differently. The nodes of FEM2D's arcs came from math.cos,
math.sin and math.atan2, and the radial mesh's from cos, sin and ``**``.
They now come from ``ogr_fem2d/mesh/_trig.py``, built from +, -, *, / and
sqrt, which IEEE 754 rounds correctly, hence alike.

Invariants protected:

* **the trigonometry is right**: sin, cos, atan, atan2 and asin agree with
  ``math`` to a few units in the last place (sin and cos 4e-16 for |t| <= 7;
  atan2 1e-15; asin 1e-14, ill-conditioned near 1), and (sin t, cos t) has
  norm 1 to 2 units;
* **nothing that decides the mesh calls the system's library**: the code
  (not the comments) of _trig, geometry, discretize, quadratic and radial has
  no math.sin, cos, tan, asin, acos, atan, atan2, hypot, dist, exp, log or
  pow, and no ``**``;
* **the fingerprint**: SHA-256 of the nodes of four discretizations (the
  tunnel, the cavity, the dented square, a fine uniform tunnel) and of a
  radial mesh. It was recorded in Windows (2026-11-23) and the CI checks it in
  Linux and macOS. It is a fingerprint of reproducibility, not a validation:
  it says that the same input gives the same bits, not that they are right.
  If it has to change, the changelog says why.
"""
from __future__ import annotations

import hashlib
import io
import math
import random
import tokenize
from dataclasses import replace
from pathlib import Path

from ogr_fem2d.mesh import _trig
from ogr_fem2d.mesh import discretize as d
from ogr_fem2d.mesh import radial
from test_mesh_input_v008 import CAVITY, DENT, TUNNEL

_MESH = Path(__file__).resolve().parents[1] / "ogr_fem2d" / "mesh"
FORBIDDEN = {"sin", "cos", "tan", "asin", "acos", "atan", "atan2", "hypot", "dist", "exp",
             "log", "log2", "log10", "pow", "sinh", "cosh", "tanh"}

#: Recorded in Windows, Python 3.14.10, on 2026-11-23.
FINGERPRINT = "0c87422a021afe5574de9456ad6880fffa6e8c9e30201a06c8f49de1ca943708"


class TestTheTrigonometry:
    def test_it_agrees_with_math_to_a_few_units(self):
        rng = random.Random(2)
        for _ in range(20000):
            t = rng.uniform(-7.0, 7.0)
            s, c = _trig.sin_cos(t)
            assert abs(s - math.sin(t)) <= 4e-16 and abs(c - math.cos(t)) <= 4e-16, t
            assert abs(math.sqrt(s * s + c * c) - 1.0) <= 2 * 2.0 ** -53, t
            y, x = rng.uniform(-3, 3), rng.uniform(-3, 3)
            assert abs(_trig.atan2(y, x) - math.atan2(y, x)) <= 1e-15, (y, x)
            u = rng.uniform(-1.0, 1.0)
            assert abs(_trig.asin(u) - math.asin(u)) <= 1e-14, u
        for x, want in ((0.0, 0.0), (1.0, math.pi / 4), (-1.0, -math.pi / 4)):
            assert abs(_trig.atan(x) - want) <= 2e-16
        assert _trig.sin_cos(0.0) == (0.0, 1.0)


def _calls_of(path: Path):
    """(name after ``math.``, line) and every ``**`` in the code of a file,
    comments and strings left out."""
    tokens = list(tokenize.generate_tokens(io.StringIO(
        path.read_bytes().decode("utf-8")).readline))
    out = []
    for k, tok in enumerate(tokens):
        if tok.type == tokenize.OP and tok.string == "**":
            out.append(("**", tok.start[0]))
        if (tok.type == tokenize.NAME and tok.string == "math" and k + 2 < len(tokens)
                and tokens[k + 1].string == "." and tokens[k + 2].string in FORBIDDEN):
            out.append((tokens[k + 2].string, tok.start[0]))
    return out


class TestNothingCallsTheSystemsLibrary:
    def test_the_modules_that_decide_the_mesh(self):
        for name in ("_trig", "geometry", "discretize", "quadratic", "radial"):
            found = _calls_of(_MESH / f"{name}.py")
            assert found == [], (name, found)

    def test_the_scanner_sees_them(self):
        found = _calls_of(Path(__file__))
        assert ("sin", 0) not in found       # what it returns: (name, line)
        assert any(name == "sin" for name, _line in found)
        assert any(name == "**" for name, _line in found)


def _fingerprint() -> str:
    parts = []
    for m in (TUNNEL, CAVITY, DENT,
              replace(TUNNEL, settings=replace(TUNNEL.settings, kind="uniform",
                                               boundary_nodes=None, size=0.3))):
        parts.append(repr(d.discretize(m).points))
    rm = radial.radial_mesh(radial.RadialSettings(1.0, 50.0, 24, 10, 1.25))
    parts.append(repr(rm.nodes))
    parts.append(repr(rm.elements))
    return hashlib.sha256("\n".join(parts).encode()).hexdigest()


class TestTheFingerprint:
    def test_the_same_bits_on_every_platform(self):
        assert _fingerprint() == FINGERPRINT
