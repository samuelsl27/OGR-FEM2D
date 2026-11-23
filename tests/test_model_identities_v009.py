# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.0.9 (spec 004, T14) — the identities of the model, from its definition to
the engine's answer.

Invariants protected:

* **dimensional homogeneity**: the same model with every stress-like value
  times 1000 (E, the field, the loads, the unit weights; the lengths and nu
  unchanged), as if written in another unit of stress, gives the same
  displacements and its stresses times 1000, to rounding, in a strip load
  and in a tunnel excavated under a field stress (D5: the model hides no
  constant with units), and in two strata under their own weight and a
  surface load;
* **the signs end to end** (spec 001, D1; D6): a positive strip load pushes
  the surface down; a compressive field stress, with the excavation, moves
  the wall of the tunnel inwards; a positive pressure on the wall pushes it
  outwards against the same excavation; the unit system shown changes
  nothing of it (D5).
"""
from __future__ import annotations

import math
from dataclasses import replace

import _models
from ogr_fem2d.engine import analysis
from ogr_fem2d.model import model as md
from ogr_fem2d.model import translate


def _scaled(m, k=1000.0):
    f = m.field
    if isinstance(f, md.ConstantField):
        field = md.ConstantField(k * f.sigma_1, k * f.sigma_3, k * f.sigma_z, f.angle)
    else:
        field = replace(f, strata=tuple(replace(s, unit_weight=k * s.unit_weight) for s in f.strata))
    loads = tuple(replace(ld, start_value=k * ld.start_value, end_value=k * ld.end_value)
                  if isinstance(ld, md.DistributedLoad) else replace(ld, magnitude=k * ld.magnitude)
                  for ld in m.loads)
    return replace(m, materials=tuple(replace(x, E=k * x.E, unit_weight=k * x.unit_weight)
                                      for x in m.materials), field=field, loads=loads)


def _run(m):
    return analysis.run(translate.to_engine(m))[-1]


def _hole_nodes(m):
    return [n for n, (x, y) in enumerate(m.mesh.nodes) if abs(math.hypot(x, y) - 1.0) < 1e-9]


def _radial(m, out, n):
    x, y = m.mesh.nodes[n]
    return (out.displacement[2 * n] * x + out.displacement[2 * n + 1] * y) / math.hypot(x, y)


TUNNEL = _models.meshed(_models.tunnel())
STRIP = _models.meshed(_models.strip())
# two strata under their own weight, with a load on the surface (with the
# weight alone the field is in equilibrium and nothing moves)
LAYERS = _models.meshed(replace(_models.layers(), loads=(
    md.DistributedLoad(md.Span("ext", (20.0, 0.0), (0.0, 0.0)), 40.0, 10.0, factors=(1.0,)),)))


class TestHomogeneity:
    def test_stresses_times_1000_displacements_the_same(self):
        for name, m in (("strip", STRIP), ("tunnel", TUNNEL), ("layers", LAYERS)):
            a, b = _run(m), _run(_scaled(m))
            big = max(abs(u) for u in a.displacement)
            assert big > 0.0, name
            assert all(abs(u - v) <= 1e-9 * big for u, v in zip(a.displacement, b.displacement)), name
            top = max(abs(c) for s in a.stresses if s is not None for c in s)
            for sa, sb in zip(a.stresses, b.stresses):
                if sa is None:
                    assert sb is None
                    continue
                assert all(abs(1000.0 * x - y) <= 1e-9 * 1000.0 * top for x, y in zip(sa, sb)), name


class TestTheSigns:
    def test_a_strip_load_pushes_the_surface_down(self):
        out = _run(STRIP)
        n = translate.context(STRIP).node_of((0.0, 0.0))
        assert out.displacement[2 * n + 1] < 0.0

    def test_the_wall_moves_in_and_a_pressure_pushes_it_out(self):
        out = _run(TUNNEL)
        inward = [_radial(TUNNEL, out, n) for n in _hole_nodes(TUNNEL)]
        assert inward and all(u < 0.0 for u in inward)
        pressure = md.DistributedLoad(md.Span("hole"), 10000.0, 10000.0, factors=(1.0,))
        held = _run(replace(TUNNEL, loads=(pressure,)))
        for n, u in zip(_hole_nodes(TUNNEL), inward):
            assert _radial(TUNNEL, held, n) > u

    def test_the_units_shown_change_nothing(self):
        a = translate.to_engine(TUNNEL)
        assert translate.to_engine(replace(TUNNEL, units="metric_mpa")) == a
        assert translate.to_engine(replace(TUNNEL, units="imperial_psf")) == a
