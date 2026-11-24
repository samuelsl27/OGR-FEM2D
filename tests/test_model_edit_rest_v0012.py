# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.0.12 (spec 006, T5) — the edits of materials, field, conditions, loads,
mesh settings and project, as pure functions (RF-1, RF-7).

Invariants protected:

* **an edit is judged by what it breaks**: it is refused, with the model's
  own rule, when it adds a problem; a model being drawn (no external yet, a
  region still without its material) is edited all the same, also by the
  edits of the stages and the assignments of spec 004, which until now
  asked the whole model to be valid;
* **an argument that does not exist is refused by name** (a field of a
  material, of a condition, of a load, of the mesh settings, of the
  summary), and so is an index or an id that does not exist;
* **a new material has no E and no nu until they are given** (spec 004,
  D16): the document is valid, and the engine is refused naming it;
* **what depends on the stages is written for every stage** when it is new:
  a restraint active, an imposed displacement or a load with factor 1;
* **a material in use is not deleted**;
* **the mesh settings are checked by the mesher's own rules**, and changing
  them leaves the mesh, which then is of other settings: calculating says so;
* **the units shown change nothing else** (spec 004, D5); the kind of
  analysis is refused where the geometry does not allow it.
"""
from __future__ import annotations

from dataclasses import replace

import _models
from ogr_fem2d.engine.initial_stress import Stratum
from ogr_fem2d.engine.reference.quadrature import AXISYMMETRIC
from ogr_fem2d.model import edit, stages, translate
from ogr_fem2d.model import model as md
from ogr_fem2d.model.history import Document


def _refused(fn, rule: str, *words: str):
    try:
        fn()
    except md.ModelError as err:
        p = err.problems[0]
        assert p.rule == rule, (p.rule, rule, str(err))
        for w in words:
            assert w in f"{p.where} {p.message}", (w, str(err))
    else:
        raise AssertionError(f"accepted; expected {rule!r}")


class TestABeingDrawnModel:
    def test_edits_work_before_the_model_is_finished(self):
        m = edit.add_boundary(md.Model(), md.EXCAVATION, ((0, 0), (1, 0), (1, 1)))
        assert "external" in {p.rule for p in md.problems(m)}
        m = edit.add_material(m, name="Roca", E=1.0e6, nu=0.25)
        m = edit.add_condition(m, md.X, md.Span("exc1"))
        m = edit.add_distributed_load(m, md.Span("exc1"), 10.0)
        m = edit.set_field(m, md.ConstantField(100.0, 50.0, 75.0, 0.0))
        assert [x.id for x in m.materials] == ["m1"] and len(m.conditions) == len(m.loads) == 1

    def test_the_stage_edits_too(self):
        # the layers with the bottom region not assigned yet: a stage edit
        # used to need the whole model valid
        lay = _models.layers()
        m = replace(lay, assignments=lay.assignments[:1])
        assert "region_unassigned" in {p.rule for p in md.problems(m)}
        out = stages.insert_stage(m, 1, "2", "Dos")
        assert len(out.stages) == 2 and out.assignments[0].excavated == (False, False)
        out = stages.set_condition_active(out, 0, "2", False)
        assert out.conditions[0].active == (True, False)

    def test_what_it_breaks_is_refused(self):
        m = edit.add_material(md.Model(), name="Roca")
        _refused(lambda: edit.set_material(m, "m1", nu=0.5), "material", "nu")
        _refused(lambda: edit.add_condition(m, md.X, md.Span("nope")), "condition", "'nope'")


class TestMaterials:
    def test_no_e_nor_nu_until_given(self):
        m = edit.add_material(_models.strip(), name="Nuevo", unit_weight=19.0)
        mat = m.material("m1")
        assert (mat.E, mat.nu, mat.unit_weight) == (None, None, 19.0)
        assert md.problems(m) == []
        m = stages.assign_material(m, (10.0, -10.0), "m1")
        try:
            translate.to_engine(_models.meshed(m))
        except md.ModelError as err:
            assert err.problems[0].rule == "material_incomplete" and "'m1'" in str(err)
        else:
            raise AssertionError("a material without E went to the engine")
        done = edit.set_material(m, "m1", E=5.0e4, nu=0.3)
        assert translate.to_engine(_models.meshed(done)).materials[1].law.young == 5.0e4

    def test_names_and_ids(self):
        m = _models.strip()
        _refused(lambda: edit.add_material(m, young=1.0), "argument", "'young'", "E")
        _refused(lambda: edit.set_material(m, "rock", E=1.0), "material_unknown", "'rock'", "'soil'")
        _refused(lambda: edit.add_material(m, "soil"), "material_id", "repeated")
        m2 = edit.add_material(edit.add_material(m), name="B")
        assert [x.id for x in m2.materials] == ["soil", "m1", "m2"]

    def test_delete_only_what_no_region_has(self):
        m = edit.add_material(_models.strip())
        _refused(lambda: edit.delete_material(m, "soil"), "in_use", "assignment at")
        assert [x.id for x in edit.delete_material(m, "m1").materials] == ["soil"]


class TestFieldConditionsLoads:
    def test_field(self):
        m = _models.layers()
        _refused(lambda: edit.set_field(m, md.GravityField(0.0, (Stratum(-20.0, -1.0, 0.5, 0.5),))),
                 "field")
        out = edit.set_field(m, md.ConstantField(300.0, 100.0, 200.0, 30.0))
        assert out.field == md.ConstantField(300.0, 100.0, 200.0, 30.0)

    def test_conditions_for_every_stage(self):
        m = _models.with_stages(_models.strip(), 3)
        m = edit.add_condition(m, md.Y, md.Span("ext", (20.0, -20.0), (20.0, 0.0)))
        assert m.conditions[-1].active == (True, True, True)
        m = edit.add_condition(m, md.DISPLACEMENT, vertex=(1.0, 0.0), uy=-0.01)
        assert m.conditions[-1].factors == (1.0, 1.0, 1.0) and m.conditions[-1].active == ()
        _refused(lambda: edit.add_condition(m, md.X, vertex=(3.0, 3.0)), "condition",
                 "not a vertex")
        out = edit.set_condition(m, len(m.conditions) - 1, uy=-0.02)
        assert out.conditions[-1].uy == -0.02
        _refused(lambda: edit.set_condition(m, 0, direction="x"), "argument", "'direction'")
        _refused(lambda: edit.delete_condition(m, 99), "condition_unknown", "99")
        assert len(edit.delete_condition(m, 0).conditions) == len(m.conditions) - 1
        _refused(lambda: edit.set_default_restraint(m, "z"), "default_restraint")
        assert edit.set_default_restraint(m, md.X).default_restraint == md.X

    def test_loads(self):
        m = _models.with_stages(_models.strip(), 2)
        m = edit.add_distributed_load(m, md.Span("ext", (20.0, 0.0), (1.0, 0.0)), 50.0)
        ld = m.loads[-1]
        assert (ld.start_value, ld.end_value, ld.factors) == (50.0, 50.0, (1.0, 1.0))
        m = edit.add_distributed_load(m, md.Span("ext", (20.0, -20.0), (20.0, 0.0)), 0.0, 30.0,
                                      md.HORIZONTAL)
        assert (m.loads[-1].start_value, m.loads[-1].end_value) == (0.0, 30.0)
        _refused(lambda: edit.add_distributed_load(m, md.Span("ext"), 1.0, angle=10.0), "load",
                 "angle", "rule 7")
        m = edit.add_point_load(m, (20.0, 0.0), 12.0)
        assert m.loads[-1].factors == (1.0, 1.0)
        _refused(lambda: edit.add_point_load(m, (2.0, 2.0), 1.0), "load", "not a vertex")
        assert edit.set_load(m, 0, start_value=80.0).loads[0].start_value == 80.0
        _refused(lambda: edit.set_load(m, 0, magnitude=1.0), "argument", "'magnitude'")
        assert len(edit.delete_load(m, 0).loads) == len(m.loads) - 1


class TestSettings:
    def test_mesh_settings_by_the_mesher_rules(self):
        m = _models.meshed(_models.strip())
        _refused(lambda: edit.set_mesh_settings(m, nodes_per_element=4), "element_kind")
        _refused(lambda: edit.set_mesh_settings(m, size=1.0), "uniform_size", "rule 7")
        _refused(lambda: edit.set_mesh_settings(m, nodes=4), "argument", "'nodes'")
        out = edit.set_mesh_settings(m, boundary_nodes=80)
        assert out.mesh == m.mesh
        try:
            translate.context(out)
        except md.ModelError as err:
            assert err.problems[0].rule == "mesh_stale"
        else:
            raise AssertionError("the mesh of other settings was taken")

    def test_units_and_analysis(self):
        m = _models.strip()
        out = edit.set_units(m, "metric_mpa")
        assert out.units == "metric_mpa" and replace(out, units=m.units) == m
        _refused(lambda: edit.set_units(m, "furlongs"), "units", "'furlongs'")
        _refused(lambda: edit.set_analysis(_models.tunnel(), AXISYMMETRIC), "left_of_axis")
        assert edit.set_analysis(m, AXISYMMETRIC).analysis == AXISYMMETRIC
        assert edit.set_summary(m, title="Faja").summary.title == "Faja"
        _refused(lambda: edit.set_summary(m, company="UPCT"), "argument", "'company'")

    def test_free_ids_and_undo(self):
        m = _models.with_stages(_models.strip(), 2)
        assert edit.next_stage_id(m) == "3"
        # from the count of stages on: a gap below it is not filled
        assert edit.next_stage_id(stages.rename_stage(replace(m, stages=(
            md.Stage("1"), md.Stage("7"))), "1", "Uno")) == "3"
        doc = Document(m)
        assert doc.edit(lambda x: edit.add_material(x, name="B"), "material")
        assert doc.undo() and doc.model == m
