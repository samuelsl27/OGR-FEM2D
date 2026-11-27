# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.0.15 (spec 006, T33) — the report in a window, and what decided a
result beside it (RF-4, RF-20; D17; rule 12).

Invariants protected:

* **the report of the window is the operation's**: in English, its text
  and its HTML are ``results_report``'s, character for character;
* **every line of the report is coded** and has its Spanish: in Spanish the
  window says it all in Spanish (what the user wrote, ids and numbers as
  they are); the English of the report, and what the ``.h5`` keeps of what
  decides the result, did not change (``test_report_info_v0012.py``, and
  here the rows of the results against the model's);
* saved as HTML or as text, it is what the window shows;
* **the interpretation shows what decided the field** (RF-20): the state
  and the engine of the results, the mesh (its bound B, the nodes on the
  axis the engine restrains), what decides the result as written with the
  results (so stale results show theirs, not the model's), and the
  drawing's settings, which move with them.
"""
from __future__ import annotations

import os
import tempfile
from dataclasses import replace
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from ogr_ui import i18n as ui_i18n  # noqa: E402

import _models  # noqa: E402
import _results  # noqa: E402
from _settings import recent_kept  # noqa: E402
from ogr_fem2d.engine import analysis  # noqa: E402
from ogr_fem2d.gui.main_window import MainWindow  # noqa: E402
from ogr_fem2d.model import model as md  # noqa: E402
from ogr_fem2d.model import ogr_file, translate  # noqa: E402
from ogr_fem2d.results import calculate as calc  # noqa: E402

APP = QApplication.instance() or QApplication([])

#: report lines whose Spanish is the English (symbols, layouts, ids)
SAME = {"material", "no", "m, kN, kPa, kN/m3", "{value} ({why})", "{state}",
        "{state}: {message}", "spec 003", "{stage}: {value}"}


class _Open:
    def __init__(self, m, calculated=True):
        self.m, self.calculated = m, calculated

    def __enter__(self):
        self._recent = recent_kept()
        self._recent.__enter__()
        self.dir = tempfile.TemporaryDirectory()
        self.path = Path(self.dir.name) / "modelo.ogrfem2d"
        ogr_file.write(self.m, self.path)
        if self.calculated:
            calc.calculate(self.m, self.path)
        self.w = MainWindow()
        self.w.open_path(str(self.path))
        return self

    def __exit__(self, *exc):
        ui_i18n.set_language("en")
        self.w.confirm_discard = lambda: True
        self.w.close()
        self.dir.cleanup()
        self._recent.__exit__(*exc)


def _three():
    return _results.excavated_tunnel(3)


class TestTheReport:
    def test_is_the_operations(self):
        with _Open(_three()) as o:
            assert o.w.act_report() is None
            win = o.w.info_window
            for kind in ("text", "html"):
                theirs = o.w.session.call("results_report", format=kind)["report"]
                assert win.text(kind) == theirs
            assert [s.key for s in win.sections] == [
                "summary", "analysis", "field", "boundaries", "materials", "conditions", "mesh",
                "deciding", "results"]
            for kind in ("html", "text"):
                path = Path(o.dir.name) / f"informe.{'html' if kind == 'html' else 'txt'}"
                win.save(str(path), kind)
                assert path.read_text(encoding="utf-8") == win.text(kind)

    def test_in_spanish(self):
        with _Open(_three()) as o:
            ui_i18n.set_language("es")
            o.w.act_report()
            text = o.w.info_window.text("text")
            for spanish in ("Resumen del proyecto", "Lo que decide el resultado (regla 12)",
                            "malla: cota de calidad", "Cota B", "Fase 2 (Stage 2): reacciones",
                            "resuelta; mayor desplazamiento", "excavada: 1: no, 2: sí, 3: sí"):
                assert spanish in text, spanish
            for english in ("What decides", "greatest displacement", "Units kept", "solver:"):
                assert english not in text, english

    def test_every_line_has_its_spanish(self):
        from ogr_ui.testing import texts
        from ogr_fem2d.gui import i18n as fem_i18n
        from ogr_fem2d.model.report_messages import REPORT_MESSAGES
        table = {**ui_i18n.package_translations("es"), **fem_i18n.spanish()}
        english = [s.english for s in REPORT_MESSAGES.values()]
        assert texts.missing_translations(english, table) == []
        same = sorted(e for e in english if table.get(e) == e)
        assert set(same) <= SAME, same

    def test_the_rules_unchanged_in_the_h5(self):
        with _Open(_three()) as o:
            got = o.w.session.call("results_open")["deciding"]
            want = [[str(w), v, str(y)] for w, v, y in translate.deciding_values(o.m)]
            assert got == want

    def test_the_nodes_on_the_axis(self):
        m = _models.meshed(replace(_models.layers(), analysis=md.AXISYMMETRIC,
                                   field=md.ConstantField(50.0, 50.0, 50.0, 0.0)))
        with _Open(m, calculated=False) as o:
            o.w.act_report()
            rows = dict(o.w.info_window.sections[6].rows)
            n = len(analysis.axis_nodes(translate.to_engine(m)))
            assert n > 3 and rows["Nodes on the axis"].startswith(f"{n}: u_r = 0 there")


class TestWhatDecidedTheField:
    def test_beside_the_field(self):
        with _Open(_three()) as o:
            o.w.interpret()
            win = o.w.interpret_window
            parts = dict(win.decided_parts())
            assert list(parts) == ["The results", "The mesh", "What decides the result",
                                   "The drawing"]
            assert dict(parts["The results"])["State"] == "Valid"
            assert any(a == "Bound B" for a, _b in parts["The mesh"])
            assert len(parts["What decides the result"]) == len(translate.deciding_values(o.m))
            assert dict(parts["The drawing"])["Intervals"] == "8"
            s = win.settings_of(win.quantity)
            win.apply_contour_settings(replace(s, intervals=5))
            assert dict(dict(win.decided_parts())["The drawing"])["Intervals"] == "5"
            assert "Bound B" in win.decided.toPlainText()

    def test_of_the_results_not_of_the_model(self):
        with _Open(_three()) as o:
            o.w.interpret()
            win = o.w.interpret_window
            before = dict(dict(win.decided_parts())["What decides the result"])
            o.w.session.call("mesh_settings", boundary_nodes=48)
            assert win.state == calc.STALE
            after = dict(dict(win.decided_parts())["What decides the result"])
            assert after["mesh: boundary_nodes"] == before["mesh: boundary_nodes"]
            assert after["mesh: boundary_nodes"].startswith("36 ")
            assert dict(dict(win.decided_parts())["The results"])["State"] == "Stale"

    def test_in_spanish(self):
        with _Open(_three()) as o:
            ui_i18n.set_language("es")
            o.w.interpret()
            parts = dict(o.w.interpret_window.decided_parts())
            assert list(parts)[2] == "Lo que decide el resultado"
            rows = dict(parts["Lo que decide el resultado"])
            assert "malla: nudos del contorno" in rows
            assert rows["malla: nudos del contorno"] == "36 (malla graduada (spec 003, D5))"
