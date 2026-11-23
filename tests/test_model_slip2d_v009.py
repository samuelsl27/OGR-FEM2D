# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.0.9 (spec 004, T12) — opening a ``.ogr`` of OGR Slip2D (RF-14, D1, D16;
ADR-0004).

The Slip2D model is made in the test with the API of the core this program
pins (``ogr_core.project``), saved to a ``.ogr`` and opened: no file of
Slip2D's repository is read.

Invariants protected:

* **the regions are Slip2D's**: the same number, and the same areas as the
  core's planar subdivision (``Project.resolve_regions``), to the core's
  rounding (it gives its vertices back moved ~1e-9 of the model's size; the
  drawn vertices are taken as they are);
* **the boundaries meet only at shared vertices** (D15): the model is valid
  and meshes;
* **the materials come without E nor nu** (D16): the model is not translated
  to the engine until they are given, and then it is;
* **the loads come on the external boundary**, a vertex inserted at each end
  that was not one; a distributed load's normal pushes into the ground, its
  sign changed where Slip2D's pointed out, and the report says so; a line
  load at a corner with no one direction does not come, and the report says
  why;
* **the conditions are the reference's**: the sides and the bottom fixed,
  the surface free;
* **the report is complete**: what came, what did not (the water table, the
  strength, the analysis settings), what was put by default, what changed.
"""
from __future__ import annotations

import tempfile
from dataclasses import replace
from pathlib import Path

from ogr_core.geometry.boundary import Boundary
from ogr_core.geometry.boundary_type import BoundaryType
from ogr_core.geometry.primitives import Polyline, Vertex
from ogr_core.loads.loads import DistributedLoad, LineLoad, LoadOrientation
from ogr_core.materials import Material
from ogr_core.materials.builtin_models import MohrCoulomb
from ogr_core.project.project import Project

from ogr_fem2d.model import import_slip2d, regions, translate
from ogr_fem2d.model import model as md

V = Vertex


def _project():
    p = Project("talud")
    for b in (Boundary(polyline=Polyline([V(0, 0), V(40, 0), V(40, 10), V(25, 10), V(15, 20), V(0, 20)],
                                         closed=True), btype=BoundaryType.EXTERNAL),
              Boundary(polyline=Polyline([V(0, 10), V(25, 10)], closed=False), btype=BoundaryType.MATERIAL),
              Boundary(polyline=Polyline([V(0, 15), V(40, 5)], closed=False), btype=BoundaryType.WATER_TABLE)):
        p.add_boundary(b)
    clay = Material(name="arcilla", strength=MohrCoulomb(cohesion=10, friction_angle=25), unit_weight=19)
    rock = Material(name="roca", strength=MohrCoulomb(cohesion=50, friction_angle=40), unit_weight=24)
    p.materials = [clay, rock]
    p.assign_material_at(5, 15, clay.id)
    p.assign_material_at(20, 5, rock.id)
    p.distributed_loads.append(DistributedLoad(start=V(2, 20), end=V(8, 20), magnitude_1=50, name="Q"))
    p.distributed_loads.append(DistributedLoad(start=V(32, 10), end=V(28, 10), magnitude_1=20, name="R"))
    p.line_loads.append(LineLoad(point=V(30, 10), magnitude=100, name="P"))
    p.line_loads.append(LineLoad(point=V(25, 10), magnitude=10, name="K",
                                 orientation=LoadOrientation.NORMAL_TO_BOUNDARY))
    return p


def _open(project=None):
    project = project or _project()
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "talud.ogr"
        project.save(path)
        model, report = import_slip2d.open_slip2d(path)
    return project, model, report


PROJECT, MODEL, REPORT = _open()


class TestTheGeometry:
    def test_the_regions_and_their_areas_are_slip2d_s(self):
        geo = regions.build(MODEL)
        ours = sorted(regions.region_area(geo, r) for r in range(len(geo.regions)))
        theirs = sorted(r.area for r in PROJECT.resolve_regions())
        assert len(ours) == len(theirs) == 2
        assert all(abs(a - b) <= 1e-7 * b for a, b in zip(ours, theirs)), (ours, theirs)
        assert ours == [200.0, 400.0]                         # the drawn vertices, exactly

    def test_valid_and_it_meshes(self):
        assert md.problems(MODEL) == []
        m = replace(MODEL, mesh_settings=replace(MODEL.mesh_settings, boundary_nodes=60))
        assert translate.mesh(m).mesh.elements


class TestTheMaterials:
    def test_no_e_nor_nu_until_given(self):
        assert [(x.name, x.E, x.nu, x.unit_weight) for x in MODEL.materials] == [
            ("arcilla", None, None, 19.0), ("roca", None, None, 24.0)]
        m = translate.mesh(replace(MODEL, mesh_settings=replace(MODEL.mesh_settings, boundary_nodes=60)))
        try:
            translate.to_engine(m)
        except md.ModelError as err:
            assert {p.rule for p in err.problems} == {"material_incomplete"} and len(err.problems) == 2
        else:
            raise AssertionError("a material without E was translated")
        given = replace(m, materials=tuple(replace(x, E=1e5, nu=0.3) for x in m.materials))
        assert translate.to_engine(given).materials[0].law.young == 1e5

    def test_every_region_has_its_material(self):
        by_id = {x.id: x.name for x in PROJECT.materials}
        got = sorted((a.point[1] > 10.0, by_id[a.material]) for a in MODEL.assignments)
        assert got == [(False, "roca"), (True, "arcilla")]


class TestTheLoads:
    def test_on_the_external_boundary_with_their_vertices(self):
        ext = MODEL.boundaries[0].vertices
        for p in ((2.0, 20.0), (8.0, 20.0), (28.0, 10.0), (32.0, 10.0), (30.0, 10.0)):
            assert p in ext, p
        names = {ld.name: ld for ld in MODEL.loads}
        assert set(names) == {"Q", "R", "P"}
        assert names["Q"].start_value == 50.0 and names["Q"].orientation == md.NORMAL
        assert names["P"].vertex == (30.0, 10.0) and names["P"].orientation == md.VERTICAL

    def test_the_normal_pushes_into_the_ground(self):
        """Q is drawn left to right, Slip2D's normal into the ground: it
        pushes down here as there. R is drawn right to left, Slip2D's normal
        out of the ground: it keeps pulling up, as there, with its sign
        changed in this program's normal (into the ground), and the report
        says so."""
        m = translate.mesh(replace(MODEL, materials=tuple(replace(x, E=1e5, nu=0.3) for x in MODEL.materials),
                                   mesh_settings=replace(MODEL.mesh_settings, boundary_nodes=60)))
        from ogr_fem2d.engine import analysis
        for name, magnitude in (("Q", 50.0 * 6.0), ("R", -20.0 * 4.0)):
            only = replace(m, loads=tuple(ld for ld in m.loads if ld.name == name))
            f = analysis.stage_load(translate.to_engine(only), 0)
            assert abs(sum(f[1::2]) + magnitude) < 1e-9, name
        assert any("R" in c and "sign changed" in c for c in REPORT.changed)

    def test_a_line_load_at_a_corner_does_not_come(self):
        assert any("line load K" in x and "corner" in x for x in REPORT.not_brought)


class TestTheConditions:
    def test_sides_and_bottom_fixed_the_surface_free(self):
        (surface,) = MODEL.conditions
        assert surface.kind == md.FREE and surface.span == md.Span("external", (40, 10), (0, 20))
        assert MODEL.default_restraint == md.XY


class TestTheReport:
    def test_what_came_what_did_not_what_was_put(self):
        assert any("1 boundaries of type WATER_TABLE" in x for x in REPORT.not_brought)
        assert any("strength" in x for x in REPORT.not_brought)
        assert any("analysis settings" in x for x in REPORT.not_brought)
        assert any("E and nu not given" in x for x in REPORT.defaults)
        assert any("sides and the bottom" in x for x in REPORT.defaults)
        assert sum("vertex inserted" in x for x in REPORT.changed) == 5
        assert any("2 regions" in x for x in REPORT.brought)
