# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.0.12 (spec 006, T7) — the report of a model and of its results (RF-4,
D17).

Invariants protected:

* **every section, in its order**, with and without results;
* **rule 12: every value that decides the result is in it**, each of
  ``translate.deciding_values`` with its why;
* **it says the state of what it reports**: no mesh, the mesh of another
  geometry, results missing, stale or incomplete; with results that are not
  valid it does not give them by boundary (the mesh may be another's);
* **its numbers are the model's and the results'**, in the units shown:
  the same model in MPa shows E / 1000; the greatest vertical stress of a
  laterally restrained column of two strata under a uniform load is
  q + sum(gamma h) = 100 + 18 x 4 + 24 x 6 = 316 kPa, at the points and at
  the nodes (the field is linear in each stratum, and the T6 holds it
  exactly); the reactions by boundary add up to the total;
* **the text and the HTML say the same**, every label and every value.
"""
from __future__ import annotations

import html
import re
import tempfile
from dataclasses import replace
from pathlib import Path

import _models
import _results
from ogr_fem2d.model import edit, ogr_file, translate
from ogr_fem2d.model import model as md
from ogr_fem2d.report import info
from ogr_fem2d.results import calculate as calc

KEYS = ["summary", "analysis", "field", "boundaries", "materials", "conditions", "mesh",
        "deciding", "results"]


def _opened(m, change=None):
    """The results of ``m`` opened against ``change(m)`` (or ``m``)."""
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "modelo.ogrfem2d"
        ogr_file.write(m, p)
        calc.calculate(m, p)
        other = m if change is None else change(m)
        opened = calc.open_results(p, other)
        sections = info.report(other, opened)
    return opened, sections


def _rows(sections, key) -> dict:
    return dict(next(s for s in sections if s.key == key).rows)


class TestSections:
    def test_every_section_in_order(self):
        m = _results.loaded_layers()
        assert [s.key for s in info.report(m)] == KEYS
        _, sections = _opened(m)
        assert [s.key for s in sections] == KEYS

    def test_every_deciding_value(self):
        m = _results.loaded_layers()
        rows = _rows(info.report(m), "deciding")
        for what, _value, why in translate.deciding_values(m):
            assert what in rows and why in rows[what], what


class TestStates:
    def test_mesh_none_and_of_another_geometry(self):
        assert "none" in _rows(info.report(_models.layers()), "mesh")["Mesh"]
        m = edit.set_mesh_settings(_results.loaded_layers(), boundary_nodes=30)
        assert "another geometry" in _rows(info.report(m), "mesh")["State"]

    def test_results_missing_stale_incomplete(self):
        m = _results.loaded_layers()
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "modelo.ogrfem2d"
            ogr_file.write(m, p)
            rows = _rows(info.report(m, calc.open_results(p, m)), "results")
            assert rows["State"].startswith(calc.MISSING)
        moved = lambda x: edit.set_material(x, "top", E=4.0e4)
        opened, sections = _opened(m, moved)
        rows = _rows(sections, "results")
        assert opened.status == calc.STALE and rows["State"].startswith(calc.STALE)
        assert not any("reactions on" in label for label in rows)
        two = replace(_results.excavated_tunnel(2),
                      conditions=(md.Condition(md.FREE, md.Span("ext"), active=(False, True)),))
        opened, sections = _opened(two)
        rows = _rows(sections, "results")
        assert opened.status == calc.INCOMPLETE and "InsufficientRestraintError" in rows["State"]
        assert sum(1 for label in rows if label.startswith("Stage") and ":" not in label) == 1


class TestNumbers:
    def test_units_shown(self):
        m = edit.set_units(_results.loaded_layers(), "metric_mpa")
        rows = _rows(info.report(m), "materials")
        assert rows["top (Arcilla)"].startswith("E 30 MPa, nu 0.3, unit weight 0.018 MN/m³")

    def test_the_column_and_its_reactions(self):
        _, sections = _opened(_results.loaded_layers())
        rows = _rows(sections, "results")
        for at in ("points", "nodes"):
            assert rows[f"Stage 1 (Stage 1): sigma_1 at the {at}"].startswith("max 316 kPa"), at
        total = re.findall(r"[-+0-9.e]+(?= kN)", rows["Stage 1 (Stage 1): reactions"])
        by = [re.findall(r"[-+0-9.e]+(?= kN)", v) for k, v in rows.items() if "reactions on" in k]
        assert abs(float(total[1]) - 6320.0) <= 1e-6 * 6320.0
        assert abs(sum(float(b[1]) for b in by) - float(total[1])) <= 1e-6 * 6320.0


class TestTextAndHtml:
    def test_they_say_the_same(self):
        _, sections = _opened(_results.loaded_layers())
        text, page = info.to_text(sections), info.to_html(sections)
        for s in sections:
            assert s.title in text and html.escape(s.title) in page
            for label, value in s.rows:
                assert label in text and value in text, label
                assert f"<th>{html.escape(label)}</th><td>{html.escape(value)}</td>" in page, label
