# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.0.9 (spec 004, T7 and T8) — from the model to the input of the mesher
and of the engine (RF-11, RF-12, D3).

Invariants protected:

* **the mesher input is the geometry, canonical and deterministic**: the
  same model gives the same ``MeshInput`` twice; the tunnel of case 005
  gives exactly the one tests/_kirsch_mesh.py writes by hand; the label of
  every region is the index of the region (D3); the arcs, the forced
  divisions and the excavation mark go to their segments;
* **a mesh is the model's** (RF-11): the stored mesh is what the mesher
  gives, with the fingerprint of its input; moving a vertex or changing a
  mesh setting makes it another model's, refused; changing a material, a
  stage, a condition or a load does not; no mesh, refused;
* **the engine input is deterministic** (RF-12): twice the same, bit for
  bit; one engine material per material, the material of every element its
  region's; the active elements of every stage those of the regions not
  excavated in it;
* **a material without E or nu is not translated** (D16), and the error
  names it;
* **the errors name the model** (RF-12): a problem of the mesher at a
  segment of its input comes back with the boundary and the segment it is;
  one of the engine at a node of a stage, with the stage's id and the
  vertex.
"""
from __future__ import annotations

from dataclasses import replace

import _kirsch_mesh as km
import _models
from ogr_fem2d.mesh import geometry as g
from ogr_fem2d.mesh import mesher
from ogr_fem2d.model import fingerprint, translate
from ogr_fem2d.model import model as md

T = _models.tunnel()


def _case_005(h=0.4, max_size=20.0):
    t = _models.tunnel(half=km.HALF, h=h)
    return replace(t, mesh_settings=replace(t.mesh_settings, boundary_nodes=km.hole_nodes(h),
                                            max_size=max_size))


class TestTheMesherInput:
    def test_case_005_is_the_one_written_by_hand(self):
        assert translate.to_mesh_input(_case_005()) == km.geometry(0.4, 20.0)

    def test_twice_the_same(self):
        for m in (T, _models.layers(), _models.strip()):
            assert translate.to_mesh_input(m) == translate.to_mesh_input(m)

    def test_the_label_of_a_region_is_its_index(self):
        mi = translate.to_mesh_input(_models.layers())
        assert [r.material for r in mi.regions] == list(range(len(mi.regions)))

    def test_the_attributes_of_the_segments(self):
        b = replace(T.boundaries[0], segments=(md.SegmentAttr(2, divisions=7),))
        mi = translate.to_mesh_input(replace(T, boundaries=(b, T.boundaries[1])))
        specs = {(s.a, s.b): s for s in mi.segments}
        assert specs[(2, 3)].divisions == 7 and specs[(2, 3)].arc is None and not specs[(2, 3)].excavation
        for key in ((4, 5), (5, 6), (6, 7), (7, 4)):
            assert specs[key].arc == g.Arc((0.0, 0.0)) and specs[key].excavation


class TestTheMesh:
    def test_the_stored_mesh_is_the_mesher_s(self):
        m = translate.mesh(T)
        mi = translate.to_mesh_input(T)
        out = mesher.mesh(mi)
        assert m.mesh.nodes == out.nodes and m.mesh.elements == out.elements
        assert m.mesh.element_region == out.element_region and m.mesh.boundaries == out.boundaries
        assert m.mesh.source == fingerprint.digest(mi)

    def test_another_geometry_or_mesh_setting_is_another_model(self):
        m = translate.mesh(T)
        ext = m.boundaries[0]
        moved = replace(ext, vertices=((-10.0, -10.0), (10.0, -10.0), (10.0, 10.0), (-10.0, 10.5)))
        for other in (replace(m, boundaries=(moved, m.boundaries[1])),
                      replace(m, mesh_settings=replace(m.mesh_settings, boundary_nodes=40))):
            try:
                translate.to_engine(other)
            except md.ModelError as err:
                assert err.problems[0].rule == "mesh_stale"
            else:
                raise AssertionError("the mesh of another model was used")

    def test_a_material_a_stage_a_load_do_not_change_the_mesh(self):
        m = translate.mesh(_models.strip())
        others = (replace(m, materials=(replace(m.materials[0], E=5.0e4),)),
                  _models.with_stages(m, 2),
                  replace(m, loads=(replace(m.loads[0], start_value=1.0),)),
                  replace(m, conditions=m.conditions[:1]))
        for other in others:
            assert translate.to_engine(other).nodes == m.mesh.nodes

    def test_no_mesh(self):
        try:
            translate.to_engine(T)
        except md.ModelError as err:
            assert err.problems[0].rule == "mesh"
        else:
            raise AssertionError("a model without a mesh was translated")


class TestTheEngineInput:
    def test_twice_the_same_bit_for_bit(self):
        for m in (translate.mesh(T), translate.mesh(_models.layers())):
            assert translate.to_engine(m) == translate.to_engine(m)

    def test_the_material_of_every_element_is_its_region_s(self):
        m = translate.mesh(_models.layers())
        e = translate.to_engine(m)
        assert len(e.materials) == 2
        for el, k in zip(e.elements, e.element_material):
            y = sum(e.nodes[n][1] for n in el[:3]) / 3.0
            assert k == (0 if y > -4.0 else 1)
            assert e.materials[k].law.young == m.materials[k].E

    def test_the_active_elements_of_every_stage(self):
        t = _models.with_stages(T, 2)
        t = replace(t, assignments=(t.assignments[0], md.Assignment((0.0, 0.0), "rock", (False, True))))
        e = translate.to_engine(translate.mesh(t))
        hole = [r == 1 for r in translate.mesh(t).mesh.element_region]
        assert all(e.stages[0].active)
        assert e.stages[1].active == tuple(not x for x in hole) and any(hole)

    def test_a_material_without_e(self):
        m = translate.mesh(replace(T, materials=(md.Material("rock", "Roca", None, 0.2),)))
        try:
            translate.to_engine(m)
        except md.ModelError as err:
            p = err.problems[0]
            assert p.rule == "material_incomplete" and "'rock'" in p.where and "(Roca)" in p.where
        else:
            raise AssertionError("a material without E was translated")


class TestTheNames:
    def test_a_mesher_problem_names_the_boundary(self):
        hole = replace(T.boundaries[1], segments=tuple(
            md.SegmentAttr(k, (0.0, 0.0), 2 if k == 1 else None) for k in range(4)))
        try:
            translate.mesh(replace(T, boundaries=(T.boundaries[0], hole)))
        except md.ModelError as err:
            p = next(p for p in err.problems if p.rule == "divisions")
            assert "segment 1 of boundary 'hole'" in p.where and "[mesher: segment 5-6]" in p.where
        else:
            raise AssertionError("an arc of 90 degrees in 2 pieces was meshed")

    def test_an_engine_problem_names_the_stage_and_the_vertex(self):
        ext = md.Boundary("ext", md.EXTERNAL, ((0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)), True)
        m = md.Model(analysis=md.AXISYMMETRIC, boundaries=(ext,),
                     materials=(md.Material("m", "", 1e4, 0.25),),
                     stages=(md.Stage("carga", "Carga"),),
                     assignments=(md.Assignment((5.0, 5.0), "m", (False,)),),
                     loads=(md.PointLoad((0.0, 10.0), 100.0, md.HORIZONTAL, 0.0, (1.0,)),),
                     mesh_settings=g.MeshSettings(boundary_nodes=16))
        try:
            translate.to_engine(translate.mesh(m))
        except md.ModelError as err:
            p = err.problems[0]
            assert p.rule == "load_on_axis"
            assert "stage 'carga' (Carga)" in p.where and "vertex (0.0, 10.0)" in p.where
            assert "[engine: stage 0, nodal load on node 3]" in p.where
        else:
            raise AssertionError("a radial force on the axis was accepted")
