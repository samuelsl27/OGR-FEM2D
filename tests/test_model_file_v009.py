# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.0.9 (spec 004, T9) — the ``.ogrfem2d`` file (RF-13, ADR-0004;
docs/modelo/formato.md).

Invariants protected:

* **saving and opening is an identity**: the model read back is the model
  written (``==``), its text written again is the same, byte for byte, and
  the engine input of the two is the same; with a mesh, conditions, loads,
  several stages, a gravitational field and a material without E;
* **the sections, in their order, every key always written**;
* **readable and comparable with git** (D3): one node and one element per
  line, a vertex per line, one key per line;
* **nothing is dropped in silence**: a key the file does not have, a key it
  should not have, a value of another type, a later ``format_version``,
  another ``format``, or text that is not JSON is a FileFormatError that
  names it; stage maps keyed by other stages too; then the model's own rules
  (ModelError).
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import _models
from dataclasses import replace
from ogr_fem2d.model import model as md
from ogr_fem2d.model import ogr_file, stages, translate


def _rich():
    m = _models.with_stages(_models.layers(), 2)
    m = stages.set_load_factor(replace(m, loads=(md.DistributedLoad(
        md.Span("ext", (20.0, 0.0), (0.0, 0.0)), 5.0, 2.5, md.ANGLE_TO_BOUNDARY, 15.0, (1.0, 1.0), "Q"),
        md.PointLoad((0.0, 0.0), 3.0, md.ANGLE_FROM_HORIZONTAL, -45.0, (0.0, 1.0), "P"))), 0, "2", 2.0)
    m = replace(m, conditions=m.conditions + (md.Condition(
        md.DISPLACEMENT, md.Span("ext", (0.0, 0.0), (0.0, -10.0)), ux=0.002, factors=(None, 1.0)),),
        summary=md.Summary("Estratos", "S. Sáez", "2026-11-23", "dos fases"), units="metric_mpa")
    return translate.mesh(m)


MODELS = {"rich": _rich(), "tunnel": translate.mesh(_models.tunnel()),
          "no mesh, no E": replace(_models.strip(), materials=(md.Material("soil", "Suelo"),))}


class TestTheIdentity:
    def test_saving_and_opening(self):
        for name, m in MODELS.items():
            text = ogr_file.dumps(m)
            back = ogr_file.loads(text)
            assert back == m, name
            assert ogr_file.dumps(back) == text, name

    def test_the_engine_input_is_the_same(self):
        for name in ("rich", "tunnel"):
            m = MODELS[name]
            assert translate.to_engine(ogr_file.loads(ogr_file.dumps(m))) == translate.to_engine(m)

    def test_through_a_file_on_disk(self):
        m = MODELS["rich"]
        with tempfile.TemporaryDirectory() as tmp:
            path = ogr_file.write(m, Path(tmp) / ("modelo" + ogr_file.SUFFIX))
            assert ogr_file.read(path) == m
            assert path.read_bytes() == ogr_file.dumps(m).encode("utf-8")


class TestTheShape:
    def test_the_sections_in_their_order(self):
        d = json.loads(ogr_file.dumps(MODELS["rich"]))
        assert tuple(d) == ogr_file._TOP
        assert d["format"] == "ogr-fem2d" and d["format_version"] == 1
        assert d["written_by"].startswith("OGR FEM2D ")
        assert d["conditions"][-1]["active"] is None and d["conditions"][0]["factors"] is None
        assert d["assignments"][0]["excavated"] == {"1": False, "2": False}

    def test_one_node_one_element_one_vertex_per_line(self):
        text = ogr_file.dumps(MODELS["tunnel"])
        lines = text.splitlines()
        m = MODELS["tunnel"]
        first_node = json.dumps(list(m.mesh.nodes[0]))
        assert sum(1 for line in lines if line.strip().rstrip(",") == first_node) >= 1
        assert len(lines) > len(m.mesh.nodes) + len(m.mesh.elements)
        assert '        [-10.0, -10.0],' in lines
        # the sides of a piece of a boundary of the mesh, on one line too
        piece = [list(s) for s in m.mesh.boundaries[0].sides[0]]
        assert any(line.strip().rstrip(",") == json.dumps(piece) for line in lines)


def _broken(change):
    d = json.loads(ogr_file.dumps(MODELS["rich"]))
    change(d)
    return d


class TestNothingDroppedInSilence:
    def _refused(self, data, rule, where):
        try:
            ogr_file.from_dict(data)
        except ogr_file.FileFormatError as err:
            assert any(p.rule == rule and where in p.where for p in err.problems), err.problems
        else:
            raise AssertionError(f"{rule} at {where} was read")

    def test_a_later_version(self):
        self._refused(_broken(lambda d: d.update(format_version=2)), "format_version", "file")

    def test_another_format(self):
        self._refused(_broken(lambda d: d.update(format="ogr")), "format", "file")

    def test_a_key_that_is_not_known(self):
        self._refused(_broken(lambda d: d.update(results=[])), "key", "file")
        self._refused(_broken(lambda d: d["materials"][0].update(c=10.0)), "key", "materials, 0")

    def test_a_key_that_is_missing(self):
        self._refused(_broken(lambda d: d["boundaries"][1].pop("segments")), "key", "boundaries, 1")

    def test_a_value_of_another_type(self):
        self._refused(_broken(lambda d: d["materials"][0].update(E="mucho")), "type", "materials, 0, E")
        self._refused(_broken(lambda d: d["boundaries"][0].update(closed=1)), "type", "boundaries, 0, closed")
        self._refused(_broken(lambda d: d["stages"][0].update(id=1)), "type", "stages, 0, id")
        self._refused(_broken(lambda d: d["mesh_settings"].update(nodes_per_element=True)), "type",
                      "mesh_settings, nodes_per_element")

    def test_a_stage_map_of_other_stages(self):
        self._refused(_broken(lambda d: d["loads"][0].update(factors={"1": 1.0})), "key",
                      "loads, 0, factors")

    def test_not_json(self):
        try:
            ogr_file.loads("{ not json")
        except ogr_file.FileFormatError as err:
            assert err.problems[0].rule == "format"
        else:
            raise AssertionError("text that is not JSON was read")

    def test_then_the_model_s_own_rules(self):
        d = _broken(lambda d: d["materials"][0].update(nu=0.7))
        try:
            ogr_file.from_dict(d)
        except md.ModelError as err:
            assert err.problems[0].rule == "material"
        else:
            raise AssertionError("a material with nu = 0.7 was read")
