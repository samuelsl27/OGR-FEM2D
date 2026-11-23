# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.0.9 (spec 004, T5) — the conditions of the model on the nodes of the
mesh (RF-9, D7, D16).

Invariants protected:

* **the default of the external boundary is the model's** (rule 12): fixed
  in x and y by default, every node of the external boundary restrained,
  corners and mid-side nodes; another default, another set; no node inside
  the model restrained by it;
* **a node takes the union of its segments**: in the strip, the surface
  freed, the sides on rollers and the base by default: the top corners keep
  their roller, the bottom ones are fixed (freeing a segment does not free
  the corner of its neighbour, P14:82);
* **the vertex comes first**: a condition on a vertex replaces at its node
  what the segments gave it;
* **imposed displacements in totals** (D10): factor x value, a factor None
  does not act, an imposed component replaces the restraint of that
  component; two different values of one degree of freedom at the same
  level are an error that names both conditions; a vertex replaces a span;
  at a node with no active element, an error;
* **active flags per stage**: a restraint off in a stage is not there.
"""
from __future__ import annotations

from dataclasses import replace

import _models
from ogr_fem2d.model import conditions, translate
from ogr_fem2d.model import model as md

S = _models.meshed(_models.strip())


def _stage(m, k=0):
    e = translate.to_engine(m)
    st = e.stages[k]
    return ({r.node: (r.x, r.y) for r in st.restraints},
            {(d.node, d.component): d.value for d in st.imposed}, e)


def _nodes_of(m, boundary, k):
    ctx = translate.context(m)
    return set(conditions.segment_nodes(ctx, ctx.segment_of[(boundary, k)]))


def _vertex(m, p):
    return translate.context(m).node_of(p)


class TestTheDefault:
    def test_fixed_outside_by_default(self):
        t = _models.meshed(_models.tunnel())
        held, _imp, _e = _stage(t)
        outer = set().union(*(_nodes_of(t, "ext", k) for k in range(4)))
        assert set(held) == outer and all(v == (True, True) for v in held.values())
        assert len(outer) > 4 * 2

    def test_another_default_another_set(self):
        t = _models.meshed(_models.tunnel())
        assert _stage(replace(t, default_restraint=md.Y))[0] == {
            n: (False, True) for n in _stage(t)[0]}
        assert _stage(replace(t, default_restraint=md.FREE))[0] == {}


class TestTheUnion:
    def test_the_strip(self):
        held, _imp, _e = _stage(S)
        assert held[_vertex(S, (0.0, 0.0))] == (True, False)
        assert held[_vertex(S, (20.0, 0.0))] == (True, False)
        assert held[_vertex(S, (0.0, -20.0))] == (True, True)
        assert held[_vertex(S, (20.0, -20.0))] == (True, True)
        assert _vertex(S, (1.0, 0.0)) not in held
        top = _nodes_of(S, "ext", 2) | _nodes_of(S, "ext", 3)
        assert all(n not in held for n in top - {_vertex(S, (0.0, 0.0)), _vertex(S, (20.0, 0.0))})
        left = _nodes_of(S, "ext", 4)
        assert all(held[n] == (True, False) for n in left - {_vertex(S, (0.0, -20.0))})

    def test_two_spans_on_one_segment_join(self):
        y = md.Condition(md.Y, md.Span("ext", (20.0, -20.0), (20.0, 0.0)), active=(True,))
        held, _imp, _e = _stage(replace(S, conditions=S.conditions + (y,)))
        for n in _nodes_of(S, "ext", 1):
            assert held[n] == (True, True)


class TestTheVertex:
    def test_a_vertex_replaces_its_segments(self):
        free = md.Condition(md.FREE, vertex=(20.0, -20.0), active=(True,))
        held, _imp, _e = _stage(replace(S, conditions=S.conditions + (free,)))
        assert _vertex(S, (20.0, -20.0)) not in held
        y = md.Condition(md.Y, vertex=(0.0, 0.0), active=(True,))
        held, _imp, _e = _stage(replace(S, conditions=S.conditions + (y,)))
        assert held[_vertex(S, (0.0, 0.0))] == (False, True)


LEFT = md.Span("ext", (0.0, 0.0), (0.0, -20.0))


class TestImposed:
    def test_factor_times_value_and_it_replaces_the_restraint(self):
        push = md.Condition(md.DISPLACEMENT, LEFT, ux=0.01, factors=(0.5,))
        held, imposed, _e = _stage(replace(S, conditions=S.conditions + (push,)))
        left = _nodes_of(S, "ext", 4)
        assert {n for (n, c) in imposed} == left and all(c == 0 for (_n, c) in imposed)
        assert all(v == 0.5 * 0.01 for v in imposed.values())
        corner = _vertex(S, (0.0, -20.0))
        assert held[corner] == (False, True)                 # y from the base, x imposed
        assert all(n not in held for n in left - {corner})

    def test_a_factor_none_does_not_act(self):
        push = md.Condition(md.DISPLACEMENT, LEFT, ux=0.01, factors=(None,))
        held, imposed, _e = _stage(replace(S, conditions=S.conditions + (push,)))
        assert imposed == {} and held == _stage(S)[0]

    def test_two_values_at_one_node_are_an_error_that_names_both(self):
        a = md.Condition(md.DISPLACEMENT, LEFT, ux=0.01, factors=(1.0,), name="A")
        b = md.Condition(md.DISPLACEMENT, md.Span("ext", (0.0, -20.0), (20.0, -20.0)), ux=0.02,
                         factors=(1.0,), name="B")
        try:
            translate.to_engine(replace(S, conditions=S.conditions + (a, b)))
        except md.ModelError as err:
            p = err.problems[0]
            assert p.rule == "condition_conflict" and "(A)" in p.where and "(B)" in p.where
        else:
            raise AssertionError("two values of one degree of freedom were accepted")

    def test_a_vertex_replaces_a_span_without_conflict(self):
        a = md.Condition(md.DISPLACEMENT, LEFT, ux=0.01, factors=(1.0,))
        v = md.Condition(md.DISPLACEMENT, vertex=(0.0, -20.0), ux=0.0, uy=0.0, factors=(1.0,))
        _held, imposed, _e = _stage(replace(S, conditions=S.conditions + (a, v)))
        corner = _vertex(S, (0.0, -20.0))
        assert imposed[(corner, 0)] == 0.0 and imposed[(corner, 1)] == 0.0

    def test_at_a_node_with_no_active_element_an_error(self):
        t = _models.tunnel()
        split = md.Boundary("split", md.STAGE, ((-1.0, 0.0), (0.0, 0.0), (1.0, 0.0)), False)
        t = replace(t, boundaries=t.boundaries + (split,),
                    assignments=(t.assignments[0], md.Assignment((0.0, 0.5), "rock", (True,)),
                                 md.Assignment((0.0, -0.5), "rock", (True,))),
                    conditions=(md.Condition(md.DISPLACEMENT, vertex=(0.0, 0.0), ux=0.0,
                                             factors=(1.0,), name="Centro"),))
        try:
            translate.to_engine(_models.meshed(t))
        except md.ModelError as err:
            assert err.problems[0].rule == "condition_inactive" and "Centro" in err.problems[0].where
        else:
            raise AssertionError("a displacement at a node with no active element was accepted")


class TestStages:
    def test_a_restraint_off_in_a_stage_is_not_there(self):
        m = _models.with_stages(S, 2)
        from ogr_fem2d.model import stages
        m = stages.set_condition_active(m, 1, "2", False)               # the right side
        held1, _i, e = _stage(m, 0)
        held2 = {r.node: (r.x, r.y) for r in e.stages[1].restraints}
        right = _nodes_of(S, "ext", 1) - {_vertex(S, (20.0, -20.0))}
        assert all(held1[n] == (True, False) for n in right)
        # off: the default of the external boundary takes it again
        assert all(held2[n] == (True, True) for n in right)
