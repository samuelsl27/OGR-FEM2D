# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.0.2 (spec 002, T2) — the discrete input of the engine and its validation
(RF-1, RF-2; docs/motor/entrada.md).

Invariants protected:

* **a valid input passes untouched**: the unit square split into two
  triangles, with three and six nodes, in plane strain and in axisymmetry,
  has no problem, and validate() hands the same object back;
* **every rule catches what it is for, and says where**: for each rule of
  model.RULES there is an input that breaks it and nothing else of
  consequence, and the problem reported names that rule and the stage,
  element, node or material at fault. The table of cases covers RULES
  exactly, so a rule added without its case, or a case for a rule that no
  longer exists, fails here;
* **the edges of the rules**: a zero-area element is degenerate as well as
  a reversed one; x < 0 is wrong only in axisymmetry; psi > phi is refused;
  a restraint on a node of an excavated region is accepted (it holds
  nothing) while a load there is refused (it would be lost). Every rule
  switched off, and each of these edges moved, makes a test here fail
  (checked by mutation, spec 002, tasks.md, T2);
* **all problems at once**: an input with several faults reports them all
  in one InputError, so the caller (spec 004) does not fix them one by one;
* **the axis** (spec 002, D1 bis): in axisymmetry a radial force or a
  non-zero radial displacement on a node of the axis is refused (u_r = 0
  there by symmetry), and the same input in plane strain is accepted;
* **D6**: Mohr-Coulomb is accepted only with six-node triangles in plane
  strain.
"""
from __future__ import annotations

import math
from dataclasses import replace

from ogr_fem2d.engine import model as m
from ogr_fem2d.engine.reference.elastic import Elastic
from ogr_fem2d.engine.reference.mohr_coulomb import MohrCoulomb

ROCK = m.Material(Elastic(20000.0, 0.2), unit_weight=0.027)
MC = m.Material(MohrCoulomb(20000.0, 0.2, 1.0, math.radians(30.0), 0.0))

# Unit square, corners 0..3 anticlockwise, diagonal 0-2; mid-side nodes 4..8.
CORNERS = ((0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0))
MIDS = ((0.5, 0.0), (1.0, 0.5), (0.5, 0.5), (0.5, 1.0), (0.0, 0.5))
T3 = ((0, 1, 2), (0, 2, 3))
T6 = ((0, 1, 2, 4, 5, 6), (0, 2, 3, 6, 7, 8))   # side k: corner k -> k+1, mid k+3


def square(nodes_per_element: int = 3, analysis: str = m.PLANE_STRAIN,
           **stage) -> m.EngineModel:
    """The base model: bottom held in y, left side in x, one stage with a
    load on the top corner and everything active."""
    six = nodes_per_element == 6
    base = dict(active=(True, True),
                restraints=(m.Restraint(0, True, True), m.Restraint(1, False, True),
                            m.Restraint(3, True, False)),
                nodal_loads=(m.NodalLoad(2, 0.0, -1.0),))
    base.update(stage)
    return m.EngineModel(
        analysis=analysis,
        nodes=CORNERS + MIDS if six else CORNERS,
        elements=T6 if six else T3,
        materials=(ROCK,),
        element_material=(0, 0),
        stages=(m.Stage(**base),))


def with_stage(model: m.EngineModel, **changes) -> m.EngineModel:
    return replace(model, stages=(replace(model.stages[0], **changes),))


AXI = m.AXISYMMETRIC

#: rule -> (input that breaks it, text the place must contain)
CASES = {
    "analysis": (replace(square(), analysis="plane_stress"), "model"),
    "nodes": (replace(square(), nodes=((0.0, 0.0), (math.nan, 0.0)) + CORNERS[2:]), "node 1"),
    "node_left_of_axis": (replace(square(analysis=AXI),
                                  nodes=CORNERS[:3] + ((-0.5, 1.0),)), "node 3"),
    "unused_node": (replace(square(), nodes=CORNERS + ((2.0, 2.0),)), "node 4"),
    "element_kind": (replace(square(), elements=((0, 1, 2), (0, 2, 3, 1))), "model"),
    "element_node": (replace(square(), elements=((0, 1, 2), (0, 2, 9))), "element 1"),
    "repeated_node": (replace(square(), elements=((0, 1, 1), (0, 2, 3))), "element 0"),
    "degenerate_element": (replace(square(), elements=((0, 2, 1), (0, 2, 3))), "element 0"),
    "element_material": (replace(square(), element_material=(0, 5)), "element 1"),
    "material": (replace(square(), materials=(m.Material(Elastic(-1.0, 0.2)),)), "material 0"),
    "plasticity_not_validated": (replace(square(3), materials=(MC,)), "material 0"),
    "initial_stresses": (replace(square(), initial_stresses=((0.0,) * 4,)), "model"),
    "no_stage": (replace(square(), stages=()), "model"),
    "active": (with_stage(square(), active=(True,)), "stage 0"),
    "no_active_element": (with_stage(square(), active=(False, False)), "stage 0"),
    "node": (with_stage(square(), restraints=(m.Restraint(99, True, True),)), "node 99"),
    # node 3 belongs only to element 1
    "inactive_node": (with_stage(square(), active=(True, False),
                                 nodal_loads=(m.NodalLoad(3, 1.0, 0.0),)), "node 3"),
    "restrained_and_imposed": (with_stage(square(), imposed=(
        m.ImposedDisplacement(0, 0, 0.01),)), "node 0"),
    "imposed_twice": (with_stage(square(), imposed=(
        m.ImposedDisplacement(2, 0, 0.01), m.ImposedDisplacement(2, 0, 0.02))), "node 2"),
    "component": (with_stage(square(), imposed=(m.ImposedDisplacement(2, 2, 0.01),)), "node 2"),
    "load_on_axis": (with_stage(square(analysis=AXI),
                                nodal_loads=(m.NodalLoad(3, 1.0, 0.0),)), "node 3"),
    "imposed_on_axis": (with_stage(square(analysis=AXI), restraints=(), imposed=(
        m.ImposedDisplacement(3, 0, 0.01),)), "node 3"),
    "element": (with_stage(square(), point_loads=(m.PointLoad(7, 0.5, 0.2, 0.0, -1.0),)),
                "element 7"),
    "inactive_element": (with_stage(square(), active=(True, False), nodal_loads=(),
                                    edge_loads=(m.EdgeLoad(1, 1, (0.0, -1.0), (0.0, -1.0)),)),
                         "element 1"),
    "side": (with_stage(square(), edge_loads=(m.EdgeLoad(0, 3, (0.0, -1.0), (0.0, -1.0)),)),
             "element 0"),
    "finite": (with_stage(square(), nodal_loads=(m.NodalLoad(2, math.inf, 0.0),)), "node 2"),
    "stage_settings": (with_stage(square(), steps=0), "stage 0"),
}



class TestValidInput:
    def test_valid_inputs_pass_untouched(self):
        for kind in (3, 6):
            for analysis in m.ANALYSES:
                model = square(kind, analysis)
                assert m.problems(model) == [], (kind, analysis, m.problems(model))
                assert m.validate(model) is model
        # with every kind of load, restraint and setting the schema has
        loaded = with_stage(square(6, m.AXISYMMETRIC),
                            imposed=(m.ImposedDisplacement(2, 1, -0.001),),
                            point_loads=(m.PointLoad(0, 0.6, 0.2, 0.5, -1.0),),
                            edge_loads=(m.EdgeLoad(1, 1, (-1.0, 0.0), (0.0, 0.0), normal=True),),
                            steps=4, tolerance=1e-10, max_iterations=10, max_cuts=2)
        assert m.problems(replace(loaded, initial_stresses=((-1.0, -1.0, -1.0, 0.0),) * 14)) == []
        assert m.problems(replace(square(6), materials=(MC,))) == []

    def test_points_per_element_follow_d1(self):
        # Zienkiewicz and Taylor (2000), table 9.2: 1, 3 and 7 points
        assert square(3).n_points == 2
        assert square(6).n_points == 6
        assert square(6, m.AXISYMMETRIC).n_points == 14
        assert square(3, m.AXISYMMETRIC).n_points == 2


class TestRules:
    def test_every_rule_is_caught_where_it_is_broken(self):
        for rule, (model, place) in CASES.items():
            found = m.problems(model)
            mine = [p for p in found if p.rule == rule]
            assert mine, f"{rule}: not reported; got {[str(p) for p in found]}"
            assert any(place in p.where for p in mine), (rule, [str(p) for p in mine])

    def test_the_cases_cover_the_rules_exactly(self):
        assert set(CASES) == set(m.RULES), set(CASES) ^ set(m.RULES)
        assert len(m.RULES) == len(set(m.RULES))

    def test_all_problems_come_at_once(self):
        model = with_stage(replace(square(), element_material=(0, 5)), steps=0,
                           nodal_loads=(m.NodalLoad(42, 0.0, -1.0),))
        try:
            m.validate(model)
        except m.InputError as err:
            rules = {p.rule for p in err.problems}
            assert {"element_material", "stage_settings", "node"} <= rules, rules
            for p in err.problems:
                assert str(p) in str(err)
        else:
            raise AssertionError("an invalid input was accepted")


class TestAxisAndPlasticity:
    def test_the_axis_rules_are_only_for_axisymmetry(self):
        # The same radial force and radial displacement on x = 0 are fine in
        # plane strain, where x = 0 is just a line of the model.
        for rule in ("load_on_axis", "imposed_on_axis"):
            model, _ = CASES[rule]
            assert m.problems(replace(model, analysis=m.PLANE_STRAIN)) == [], rule
        # and on the axis a vertical force or displacement is fine
        axi = with_stage(square(analysis=m.AXISYMMETRIC),
                         nodal_loads=(m.NodalLoad(3, 0.0, -1.0),),
                         imposed=(m.ImposedDisplacement(2, 1, -0.001),))
        assert m.problems(axi) == []

    def test_the_edges_of_three_rules(self):
        # zero area (collinear corners) is degenerate too, not only reversed
        flat = replace(square(), nodes=CORNERS[:2] + ((2.0, 0.0), (0.0, 1.0)))
        assert "degenerate_element" in {p.rule for p in m.problems(flat)}
        # x < 0 is only wrong in axisymmetry
        left = replace(square(), nodes=CORNERS[:3] + ((-0.5, 1.0),))
        assert m.problems(left) == []
        # the source's 0 <= psi <= phi (de Souza Neto et al. 2008, §8.2)
        law = MohrCoulomb(20000.0, 0.2, 1.0, math.radians(30.0), math.radians(35.0))
        bad = replace(square(6), materials=(m.Material(law),))
        assert {p.rule for p in m.problems(bad)} == {"material"}

    def test_a_restraint_on_an_excavated_node_is_harmless(self):
        # node 3 belongs only to element 1: excavated, its restraint holds
        # nothing and is accepted; a load there would be lost and is not
        model = with_stage(square(), active=(True, False))
        assert m.problems(model) == []
        assert {p.rule for p in m.problems(with_stage(
            model, nodal_loads=(m.NodalLoad(3, 0.0, -1.0),)))} == {"inactive_node"}

    def test_mohr_coulomb_only_where_validated(self):
        for kind, analysis in ((3, m.PLANE_STRAIN), (3, m.AXISYMMETRIC), (6, m.AXISYMMETRIC)):
            found = {p.rule for p in m.problems(replace(square(kind, analysis), materials=(MC,)))}
            assert found == {"plasticity_not_validated"}, (kind, analysis, found)
