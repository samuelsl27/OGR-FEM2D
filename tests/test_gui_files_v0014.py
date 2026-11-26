# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.0.14 (spec 006, T28) — opening a model of OGR Slip2D and a DXF from the
menu with its report; the recent models; the preferences (RF-17; D12;
ADR-0004).

Invariants protected:

* **the report of a conversion is seen whole**: every line of what came,
  what did not, the defaults taken and what was changed, and what is still
  to do in the model, in a window beside it; File > Import reaches both
  conversions;
* **the recent models**: opening or saving a model puts it first, without
  repeats, at most ``RECENT_MAX``; a model no longer there is said and
  taken off; the list can be emptied (its action disabled when empty, and
  says why); a conversion is not a recent model (it has no file yet);
* **the preferences**: a new language is kept and the status bar says it
  applies at the next start (D12); a theme applies now and is kept. The
  test puts back the language and the theme it found (rule 5).
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import ezdxf  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

import _cases_model  # noqa: E402
from _settings import recent_kept, style_kept  # noqa: E402
from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex  # noqa: E402
from ogr_core.materials import Material  # noqa: E402
from ogr_core.materials.builtin_models import MohrCoulomb  # noqa: E402
from ogr_core.project.project import Project  # noqa: E402
from ogr_ui.themes import current_theme  # noqa: E402

from ogr_fem2d.gui import main_window as mw  # noqa: E402
from ogr_fem2d.gui.main_window import MainWindow  # noqa: E402

APP = QApplication.instance() or QApplication([])
_KEEP = []


def _window():
    w = MainWindow()
    _KEEP.append(w)
    w.confirm_discard = lambda: True
    return w


def _close(w):
    w.confirm_discard = lambda: True
    w.close()


def _slip2d(path: Path) -> None:
    p = Project("talud")
    V = Vertex
    p.add_boundary(Boundary(polyline=Polyline([V(0, 0), V(40, 0), V(40, 20), V(0, 20)],
                                              closed=True), btype=BoundaryType.EXTERNAL))
    clay = Material(name="arcilla", strength=MohrCoulomb(cohesion=10, friction_angle=25),
                    unit_weight=19)
    p.materials = [clay]
    p.assign_material_at(5, 5, clay.id)
    p.save(path)


class TestImporting:
    def test_the_report_is_seen_whole(self):
        w = _window()
        try:
            with tempfile.TemporaryDirectory() as d:
                ogr = Path(d) / "talud.ogr"
                _slip2d(ogr)
                w.ask_import_path = lambda _f: str(ogr)
                w.actions_by_key["import_slip2d"].trigger()
                got = w.session.call("project_summary")
                assert got["name"] == "talud"
                text = w.report_window.text.toPlainText()
                from ogr_fem2d.model import import_slip2d
                _m, rep = import_slip2d.open_slip2d(ogr)
                for line in rep.brought + rep.not_brought + rep.defaults + rep.changed:
                    assert line in text, line
                assert "Still to do in the model" in text
                for title in ("What came", "What did not come", "Defaults taken",
                              "What was changed"):              # every part, empty or not
                    assert title in text, title
                assert not w.report_window.isHidden()
                assert w.recent_files() == [] or str(ogr.resolve()) not in w.recent_files()
                dxf = Path(d) / "plano.dxf"
                doc = ezdxf.new()
                doc.modelspace().add_lwpolyline([(0, 0), (10, 0), (10, 10), (0, 10)], close=True,
                                                dxfattribs={"layer": "External"})
                doc.saveas(dxf)
                w.ask_import_path = lambda _f: str(dxf)
                w.actions_by_key["import_dxf"].trigger()
                assert "plano.dxf" in w.report_window.text.toPlainText()
                w.report_window.close()
        finally:
            _close(w)


class TestRecent:
    def test_open_save_repeat_missing_and_clear(self):
        with recent_kept():
            self._recent()

    def _recent(self):
        w = _window()
        try:
            w.act_clear_recent()
            assert w.recent_files() == []
            assert not w.actions_by_key["clear_recent"].isEnabled()
            assert w.actions_by_key["clear_recent"].statusTip()
            case = str(_cases_model.path("006-carga-en-faja-malla-general").resolve())
            w.open_path(case)
            assert w.recent_files() == [case]
            with tempfile.TemporaryDirectory() as d:
                copies = []
                for k in range(mw.RECENT_MAX + 1):
                    target = str(Path(d) / f"m{k}.ogrfem2d")
                    w.ask_save_path = lambda t=target: t
                    w.act_save_as()
                    copies.append(str(Path(target).resolve()))
                files = w.recent_files()
                assert len(files) == mw.RECENT_MAX and files[0] == copies[-1]
                assert case not in files                       # the oldest went
                w.open_path(copies[3])                         # again: first, once
                files = w.recent_files()
                assert files[0] == copies[3] and files.count(copies[3]) == 1
                entries = [a for a in w.recent_menu.actions() if a.toolTip() in files]
                assert len(entries) == len(files)
                missing = copies[3]
            w.open_recent(missing)                             # the folder is gone
            assert "no longer there" in w.statusBar().currentMessage()
            assert missing not in w.recent_files()
            w.act_clear_recent()
            assert w.recent_files() == []
        finally:
            _close(w)


class TestPreferences:
    def test_language_and_theme(self):
        with style_kept(APP):
            self._preferences()

    def _preferences(self):
        w = _window()
        lang, theme, saved = mw.PREFERENCES.saved_language(), current_theme(),             mw.PREFERENCES.saved_theme()
        try:
            dlg = w.preferences_dialog()
            dlg.language_changed.emit("es")
            assert mw.PREFERENCES.saved_language() == "es"
            assert "next time" in w.statusBar().currentMessage()
            other = "dark" if theme != "dark" else "light"
            dlg.theme_changed.emit(other)
            assert current_theme() == other and mw.PREFERENCES.saved_theme() == other
        finally:
            w.change_theme(theme)
            s = mw.PREFERENCES.settings()
            for key, value in (("language", lang), ("theme", saved)):
                if value:
                    s.setValue(key, value)
                else:
                    s.remove(key)
            s.sync()
            _close(w)
        assert current_theme() == theme and mw.PREFERENCES.saved_language() == lang
        assert mw.PREFERENCES.saved_theme() == saved


class TestTheReportInSpanish:
    """Decided on 2026-11-25: the report says every line in the reader's
    language, its own lines by their code and the problems by their rule."""

    def test_every_line_has_its_spanish(self):
        from ogr_fem2d.gui import i18n as fem_i18n
        from ogr_fem2d.gui import problems
        from ogr_fem2d.model import model as md
        from ogr_fem2d.model import regions
        from ogr_fem2d.model.import_messages import IMPORT_MESSAGES
        table = fem_i18n.spanish()
        english = [s.english for s in IMPORT_MESSAGES.values()]
        english += [s.one for s in IMPORT_MESSAGES.values() if s.one]
        assert [e for e in english if e not in table] == []
        rules = set(md.RULES) | set(regions.RULES)
        assert sorted(rules - set(problems.RULE_TEXT)) == []
        said = list(problems.RULE_TEXT.values()) + [t for _p, t in problems._WHERE]
        said += list(problems._PLAIN.values())
        assert [e for e in said if e not in table] == []

    def test_a_conversion_in_spanish(self):
        from ogr_ui import i18n as ui_i18n
        w = _window()
        ui_i18n.set_language("es")
        try:
            with tempfile.TemporaryDirectory() as d:
                ogr = Path(d) / "talud.ogr"
                _slip2d(ogr)
                w.open_path(str(ogr))
                text = w.report_window.text.toPlainText()
                for spanish in ("Lo que vino", "1 material (nombre, color, peso específico)",
                                "condiciones: los lados y la base del contorno externo",
                                "la resistencia de los materiales"):
                    assert spanish in text, spanish
                assert "materials (name" not in text and "the strength" not in text
                dxf = Path(d) / "plano.dxf"
                doc = ezdxf.new()
                doc.modelspace().add_lwpolyline([(0, 0), (10, 0), (10, 10), (0, 10)], close=True,
                                                dxfattribs={"layer": "External"})
                doc.modelspace().add_line((0, 0), (1, 1), dxfattribs={"layer": "Notas"})
                doc.saveas(dxf)
                w.open_path(str(dxf))
                text = w.report_window.text.toPlainText()
                for spanish in ("1 contorno: externos: 1; 0 trozos de arco",
                                "capa 'Notas' (1 entidad): no es de ninguno",
                                "Una región todavía no tiene material",
                                "la región cuyo contorno pasa por"):
                    assert spanish in text, (spanish, text)
                w.report_window.close()
        finally:
            ui_i18n.set_language("en")
            _close(w)

    def test_the_orientations_of_a_line_load(self):
        from types import SimpleNamespace

        from ogr_core.loads.loads import LoadOrientation
        from ogr_fem2d.gui import i18n as fem_i18n
        from ogr_fem2d.model import import_messages as im
        from ogr_fem2d.model import import_slip2d
        from ogr_ui import i18n as ui_i18n
        ui_i18n.set_language("es")
        try:
            for o in LoadOrientation:
                nested = import_slip2d._orientation(SimpleNamespace(orientation=o))
                line = im.say("fem.import.point_turned", name="q", orientation=nested,
                              angle="30")
                assert o.value not in str(line) or o.value in ("vertical", "horizontal"), line
                said = fem_i18n.say(line)
                assert said.startswith("carga lineal q: ") and "convertida" in said, said
        finally:
            ui_i18n.set_language("en")
