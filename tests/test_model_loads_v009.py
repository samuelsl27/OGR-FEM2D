# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.0.9 (spec 004, T6) — the loads of the model on the sides and nodes of
the mesh (RF-10, D6, D10).

The forces are read as the engine makes them (``analysis.stage_load``, the
consistent nodal forces of spec 002), in models without self weight.

Invariants protected:

* **a linear load along a span of several segments** keeps its resultant and
  its moment exactly (the integral of a linear traction on straight sides):
  from v0 at the start to v1 at the end, along the length of the span;
* **every orientation pushes where it says** (D6, the core's directions), on
  an inclined surface where they all differ (rule 7): NORMAL into the ground,
  vertical down, horizontal along +x, at an angle from the horizontal, at an
  angle to the span (its tangent, in its direction, turned anticlockwise);
* **on a curved side the normal is exact**: a pressure on the wall of a
  tunnel, after excavation, pushes into the rock, radially, with the
  resultant of the pressure over the wall (2 pi a p, to the difference of
  the parabolic sides) and nought in total;
* **factor x value in each stage** (D10): the factor scales the forces, a
  factor 0 puts nothing;
* **a load on a contact between two active regions is an error** that names
  the load, the boundary and the stage (RF-10); on an excavated part, too;
* **a point load at a vertex** is a nodal force there, the force of the
  whole ring in axisymmetry (spec 002, D2).
"""
from __future__ import annotations

import math
from dataclasses import replace

import _models
from ogr_fem2d.engine import analysis
from ogr_fem2d.mesh import geometry as g
from ogr_fem2d.model import model as md
from ogr_fem2d.model import stages, translate

TOP = md.Span("ext", (20.0, 0.0), (0.0, 0.0))


def _forces(m, k=0):
    e = translate.to_engine(m)
    return e, analysis.stage_load(e, k)


def _resultant(e, f):
    fx = sum(f[0::2])
    fy = sum(f[1::2])
    moment = sum(x * f[2 * n + 1] - y * f[2 * n] for n, (x, y) in enumerate(e.nodes))
    return fx, fy, moment


def _strip(load):
    return _models.meshed(replace(_models.strip(), loads=(load,)))


class TestALinearLoad:
    def test_resultant_and_moment_over_two_segments(self):
        v0, v1 = 30.0, 10.0          # at (20, 0) and at (0, 0); q(x) = 10 + x
        e, f = _forces(_strip(md.DistributedLoad(TOP, v0, v1, factors=(1.0,))))
        fx, fy, mz = _resultant(e, f)
        assert abs(fx) < 1e-9
        assert abs(fy + 0.5 * (v0 + v1) * 20.0) < 1e-9                    # pushes down: -400
        # moment about the origin of q(x) = 10 + x down: -int x (10 + x) dx
        assert abs(mz + (10.0 * 200.0 + 8000.0 / 3.0)) < 1e-8

    def test_uniform_is_the_strip(self):
        e, f = _forces(_models.meshed(_models.strip()))
        _fx, fy, mz = _resultant(e, f)
        assert abs(fy + 100.0) < 1e-10 and abs(mz + 100.0 * 0.5) < 1e-10


def _slope(orientation, angle=0.0):
    ext = md.Boundary("ext", md.EXTERNAL, ((0.0, -10.0), (10.0, -10.0), (10.0, 0.0), (0.0, 5.0)), True)
    load = md.DistributedLoad(md.Span("ext", (10.0, 0.0), (0.0, 5.0)), 10.0, 10.0, orientation, angle,
                              (1.0,))
    m = md.Model(boundaries=(ext,), materials=(md.Material("m", "", 1e4, 0.3),),
                 assignments=(md.Assignment((5.0, -5.0), "m", (False,)),), loads=(load,),
                 mesh_settings=g.MeshSettings(boundary_nodes=24))
    return _models.meshed(m)


class TestOrientations:
    def test_each_pushes_where_it_says(self):
        length = math.hypot(10.0, 5.0)
        tx, ty = -10.0 / length, 5.0 / length                     # the span's tangent
        a = math.radians(30.0)
        cases = {
            md.NORMAL: (-ty, tx),                                  # into the ground, down-left
            md.VERTICAL: (0.0, -1.0),
            md.HORIZONTAL: (1.0, 0.0),
            md.ANGLE_FROM_HORIZONTAL: (math.cos(a), math.sin(a)),
            md.ANGLE_TO_BOUNDARY: (tx * math.cos(a) - ty * math.sin(a), tx * math.sin(a) + ty * math.cos(a)),
        }
        got = {}
        for orientation, (dx, dy) in cases.items():
            angle = 30.0 if orientation in (md.ANGLE_FROM_HORIZONTAL, md.ANGLE_TO_BOUNDARY) else 0.0
            e, f = _forces(_slope(orientation, angle))
            fx, fy, _m = _resultant(e, f)
            assert abs(fx - 10.0 * length * dx) < 1e-9 and abs(fy - 10.0 * length * dy) < 1e-9, orientation
            got[orientation] = (round(fx, 9), round(fy, 9))
        assert len(set(got.values())) == len(cases)

    def test_the_same_load_whichever_way_the_boundary_runs(self):
        """A linear normal load, 30 at (10, 0) and 10 at (0, 5): along a
        boundary drawn anticlockwise, and along the same one drawn clockwise
        (the span, and its values, the other way round). The mesh runs its
        segments one way only, so one of the two reads its chains backwards."""
        m = _slope(md.NORMAL)
        m = _models.meshed(replace(m, loads=(replace(m.loads[0], start_value=30.0, end_value=10.0),),
                                   mesh=None))
        b = m.boundaries[0]
        flipped = replace(b, vertices=b.vertices[::-1])
        load = replace(m.loads[0], span=md.Span("ext", (0.0, 5.0), (10.0, 0.0)), start_value=10.0,
                       end_value=30.0)
        m2 = _models.meshed(replace(m, boundaries=(flipped,), loads=(load,), mesh=None))
        r1 = _resultant(*_forces(m))
        r2 = _resultant(*_forces(m2))
        assert all(abs(a - b) < 1e-9 for a, b in zip(r1, r2)), (r1, r2)
        assert r1[1] < 0.0


class TestACurvedWall:
    def test_a_pressure_on_the_tunnel_wall_pushes_into_the_rock(self):
        t = _models.tunnel()
        load = md.DistributedLoad(md.Span("hole"), 50.0, 50.0, factors=(1.0,), name="Presión")
        e, f = _forces(_models.meshed(replace(t, loads=(load,), field=md.ConstantField())))
        fx, fy, _m = _resultant(e, f)
        assert abs(fx) < 1e-9 and abs(fy) < 1e-9
        radial = 0.0
        for n, (x, y) in enumerate(e.nodes):
            r = math.hypot(x, y)
            if abs(r - 1.0) < 1e-9:
                radial += (f[2 * n] * x + f[2 * n + 1] * y) / r
                assert (f[2 * n] * x + f[2 * n + 1] * y) >= -1e-12
        assert abs(radial - 2.0 * math.pi * 50.0) < 1e-4 * 2.0 * math.pi * 50.0


    def test_a_linear_load_along_an_arc_goes_by_its_length(self):
        """On the upper half of the wall, from (1, 0) to (-1, 0), a pressure
        rising from 0 to v along the arc, p = v phi / pi: its resultant is
        (-2 v / pi, v) (the integrals of phi cos phi and phi sin phi)."""
        t = _models.tunnel()
        v = 60.0
        load = md.DistributedLoad(md.Span("hole", (1.0, 0.0), (-1.0, 0.0)), 0.0, v, factors=(1.0,))
        e, f = _forces(_models.meshed(replace(t, loads=(load,), field=md.ConstantField())))
        fx, fy, _m = _resultant(e, f)
        assert abs(fx + 2.0 * v / math.pi) < 1e-3 * v and abs(fy - v) < 1e-3 * v, (fx, fy)


class TestFactors:
    def test_the_factor_of_each_stage(self):
        m = _models.with_stages(_models.strip(), 3)
        m = stages.set_load_factor(m, 0, "2", 2.5)
        m = stages.set_load_factor(m, 0, "3", 0.0)
        m = _models.meshed(m)
        e = translate.to_engine(m)
        fy = [sum(analysis.stage_load(e, k)[1::2]) for k in range(3)]
        assert abs(fy[0] + 100.0) < 1e-10 and abs(fy[1] + 250.0) < 1e-10
        assert e.stages[2].edge_loads == ()


class TestWhereALoadCannotBe:
    def test_on_a_contact_between_two_active_regions(self):
        L = _models.layers(loading=md.NO_LOADING)
        load = md.DistributedLoad(md.Span("contact", (0.0, -4.0), (20.0, -4.0)), 5.0, 5.0,
                                  factors=(1.0,), name="Mal")
        try:
            translate.to_engine(_models.meshed(replace(L, loads=(load,))))
        except md.ModelError as err:
            p = err.problems[0]
            assert p.rule == "load_not_on_boundary"
            assert "(Mal)" in p.where and "'contact'" in p.where and "stage '1'" in p.where
        else:
            raise AssertionError("a load on a contact was accepted")

    def test_on_the_wall_before_it_is_excavated(self):
        t = _models.with_stages(_models.tunnel(), 2)
        t = replace(t, assignments=(t.assignments[0], md.Assignment((0.0, 0.0), "rock", (False, True))),
                    loads=(md.DistributedLoad(md.Span("hole"), 50.0, 50.0, factors=(1.0, 1.0)),))
        try:
            translate.to_engine(_models.meshed(t))
        except md.ModelError as err:
            assert err.problems[0].rule == "load_not_on_boundary" and "stage '1'" in err.problems[0].where
        else:
            raise AssertionError("a load on a contact was accepted")
        ok = replace(t, loads=(replace(t.loads[0], factors=(0.0, 1.0)),))
        assert translate.to_engine(_models.meshed(ok)).stages[1].edge_loads


class TestPointLoads:
    def test_a_point_load_at_a_vertex(self):
        s = _models.strip()
        load = md.PointLoad((1.0, 0.0), 40.0, md.ANGLE_FROM_HORIZONTAL, -60.0, (0.5,))
        m = _models.meshed(replace(s, loads=(load,)))
        e = translate.to_engine(m)
        (nl,) = e.stages[0].nodal_loads
        assert e.nodes[nl.node] == (1.0, 0.0)
        assert abs(nl.fx - 20.0 * math.cos(math.radians(-60.0))) < 1e-12
        assert abs(nl.fy - 20.0 * math.sin(math.radians(-60.0))) < 1e-12

    def test_in_axisymmetry_the_force_of_the_whole_ring(self):
        ext = md.Boundary("ext", md.EXTERNAL, ((0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (2.0, 10.0),
                                               (0.0, 10.0)), True)
        m = md.Model(analysis=md.AXISYMMETRIC, boundaries=(ext,),
                     materials=(md.Material("m", "", 1e4, 0.25),),
                     assignments=(md.Assignment((5.0, 5.0), "m", (False,)),),
                     loads=(md.PointLoad((2.0, 10.0), 100.0, md.VERTICAL, 0.0, (1.0,)),),
                     mesh_settings=g.MeshSettings(boundary_nodes=20))
        e = translate.to_engine(_models.meshed(m))
        (nl,) = e.stages[0].nodal_loads
        assert (nl.fx, nl.fy) == (0.0, -100.0)                # not 2 pi r times it
