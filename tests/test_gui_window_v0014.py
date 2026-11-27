# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.0.14 (spec 006, T20) — the main window: its menus, its actions, its
texts, and the model it shows through the operations (RF-13, RF-21; D3, D4,
D13; rules 2 and 3).

Invariants protected:

* **the menus are in the order of the work** (RF-13); the menus of later
  phases are there with ONE disabled entry that says when it comes (D4);
  the menus of this phase still without entries are exactly those
  ``menus.PENDING`` names, and the list only gets shorter;
* **rule 3**: every action is in a menu (``ogr_ui.testing.menus``), and
  every disabled entry says why;
* **D13**: every action has its operation in ``inventory``, or why it has
  none, and every operation it names exists; no entry for an action that
  does not;
* **rule 2**: no visible text outside ``tr()`` but the exceptions below,
  each with its reason (``ogr_ui.testing.texts``); every text handed to
  ``tr()``, and every action's, has its Spanish; none of the suite's
  Spanish is changed by this program's; a message of an operation (coded)
  comes out in Spanish;
* **the window shows the session's model**: new, open, save; its title says
  the model, whether it has unsaved changes and the kind of analysis
  (P17); undo and redo are enabled when there is something to undo, and
  say what; closing with unsaved changes asks, and keeping the model keeps
  the window;
* **only the interface imports Qt** (the layers of the plan).
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from ogr_ui import i18n as ui_i18n  # noqa: E402
from ogr_ui.testing import menus as menu_rules  # noqa: E402
from ogr_ui.testing import texts  # noqa: E402

import _cases_model  # noqa: E402
from _settings import recent_kept  # noqa: E402
from ogr_fem2d import api  # noqa: E402
from ogr_fem2d.api.messages import FEM_MESSAGES  # noqa: E402
from ogr_fem2d.gui import i18n as fem_i18n  # noqa: E402
from ogr_fem2d.gui import inventory, menus  # noqa: E402
from ogr_fem2d.gui.main_window import MainWindow  # noqa: E402

APP = QApplication.instance() or QApplication([])
GUI = Path(__file__).resolve().parents[1] / "ogr_fem2d" / "gui"

#: the texts on screen outside tr(), each a decision
EXCEPTIONS = {
    ("help/__init__.py", "caso-{}.ogrfem2d"): "the name of the copy of a case's model: a file",
    ("main_window.py", "{}{} — {} — OGR FEM2D"):
        "the window's title: the model's name, its star and the kind of analysis (each through "
        "tr()) joined with the program's name, which is not translated",
    ("main_window.py", "OGR FEM2D {}\n\n"): "the program's name and its version in About",
    ("interpret/queries.py", "x ({})"): "a column of a query: the coordinate's symbol and its unit",
    ("interpret/queries.py", "y ({})"): "a column of a query: the coordinate's symbol and its unit",
    ("interpret/window.py", "x = {}, y = {} {}: "):
        "the interpretation's cursor: its coordinates in symbols, with the unit shown, before "
        "the values (each said through tr())",
}
#: Spanish words that are the English ones
SAME = {"Material", "X (%s)", "Y (%s)", "General", "K", "Kz", "Material %d", "vertical",
        "horizontal",
        # the catalogue's names that are the same in Spanish (T31)
        "Sigma xx", "Sigma r (radial)", "Sigma yy", "Sigma z (axial)", "Tau xy", "Tau rz",
        # the report's lines that are the same in Spanish (T33)
        "m, kN, kPa, kN/m3", "material", "no", "spec 003", "{stage}: {value}", "{state}",
        "{state}: {message}", "{value} ({why})"}

_WINDOWS = []


def _window():
    w = MainWindow()
    _WINDOWS.append(w)
    return w


def _close(w):
    w.confirm_discard = lambda: True
    w.close()


class TestMenus:
    def test_the_order_and_the_later_phases(self):
        w = _window()
        try:
            titles = [a.text() for a in w.menuBar().actions()]
            # RF-13, as the spec writes it (and the reference program has it)
            assert titles == ["File", "Edit", "View", "Analysis", "Boundaries", "Mesh", "Loading",
                              "Displacements", "Support", "Groundwater", "Statistics", "Properties",
                              "Tools", "Window", "Help"]
            for menu, (key, _text, why) in menus.FUTURE.items():
                entries = [a for a in w._menus[menu].actions() if not a.isSeparator()]
                assert entries == [w.actions_by_key[key]], menu
                assert not entries[0].isEnabled() and entries[0].statusTip() == why
            empty = {t for t, m in w._menus.items() if not m.actions()}
            assert empty == set(menus.PENDING), empty ^ set(menus.PENDING)
        finally:
            _close(w)

    def test_rule_3(self):
        w = _window()
        try:
            assert menu_rules.unreachable(w, w.actions_by_key) == []
            assert menu_rules.silent_disabled(w, w.actions_by_key) == []
        finally:
            _close(w)

    def test_d13_every_action_and_its_operation(self):
        w = _window()
        try:
            keys = set(w.actions_by_key)
            listed = set(inventory.MAPPED) | set(inventory.UI_ONLY)
            assert keys == listed, keys ^ listed
            assert not set(inventory.MAPPED) & set(inventory.UI_ONLY)
            assert set(inventory.MAPPED.values()) <= set(api.OPERATIONS)
            assert all(why.strip() for why in inventory.UI_ONLY.values())
        finally:
            _close(w)


class TestRule2:
    def test_no_text_outside_tr(self):
        assert texts.counted(GUI, EXCEPTIONS) == []
        assert texts.ghost_exceptions(GUI, EXCEPTIONS) == []
        assert texts.field_census(GUI) == {}

    def test_every_text_has_its_spanish(self):
        table = {**ui_i18n.package_translations("es"), **fem_i18n.spanish()}
        assert texts.missing_translations(texts.wrapped_keys(GUI), table) == []
        assert texts.identical_translations(fem_i18n.spanish(), SAME) == []
        assert fem_i18n.install() == []                 # the suite's Spanish, untouched
        w = _window()
        try:
            english = [a.text() for a in w.actions_by_key.values()] + list(menus.ORDER)
            english += [why for _k, _t, why in menus.FUTURE.values()]
            # every message of the operations, both forms of one with a count
            english += [s.english for s in FEM_MESSAGES.values()]
            english += [s.one for s in FEM_MESSAGES.values() if s.one]
            # every template of the core PINNED (v0.2.9) that say() renders: ogr_ui's Spanish
            # is written for the core v0.2.12 (OGR GUI 0.1.2), and a template that changed
            # between them would have none; one of words and fields only is the same in
            # every language (OGR GUI 0.1.2)
            import re
            worded = lambda t: re.search(r"[A-Za-z]{2,}", re.sub(r"\{[^}]*\}", "", t))
            english += [t for s in fem_i18n.catalogues().values() for t in (s.english, s.one)
                        if t and worded(t)]
            # the errors of a typed point and of drawing, said through tr()
            import ast
            tree = ast.parse((GUI / "canvas" / "tools.py").read_text(encoding="utf-8"))
            english += [n.args[0].value for n in ast.walk(tree) if isinstance(n, ast.Call)
                        and getattr(n.func, "id", "") == "EntryError" and n.args
                        and isinstance(n.args[0], ast.Constant)]
            assert texts.missing_translations(english, table) == []
        finally:
            _close(w)

    def test_in_spanish(self):
        w = _window()
        try:
            ui_i18n.set_language("es")
            w.act_new()
            w.session.call("project_settings", title="Túnel")
            assert w.actions_by_key["undo"].text() == "Deshacer: Ajustes del proyecto"
            w.session.call("project_history", action="undo")
            assert w.actions_by_key["redo"].text() == "Rehacer: Ajustes del proyecto"
            assert fem_i18n.say(api.messages.say("fem.close.unsaved", model="p1")) == \
                "El modelo p1 tiene cambios sin guardar."
            two = api.messages.say("fem.model.invalid", count=2, first="x")
            one = api.messages.say("fem.model.invalid", count=1, first="x")
            assert (fem_i18n.say(two), fem_i18n.say(one)) == (
                "El modelo lo rechaza (2 problemas): x", "El modelo lo rechaza: x")
            # a message of the mesher (the core's REFINE_MESSAGES), in Spanish (OGR GUI 0.1.2)
            import string
            from ogr_core.fem.messages import REFINE_MESSAGES
            from ogr_core.messages import coded
            spec = next(iter(REFINE_MESSAGES.values()))
            fields = {f for _l, f, _s, _c in string.Formatter().parse(spec.english) if f}
            line = coded(REFINE_MESSAGES, spec.code, **{f: 7 for f in fields})
            spanish = ui_i18n.package_translations("es")[spec.english]
            assert fem_i18n.say(line) == spanish.format(**{f: 7 for f in fields}),                 (fem_i18n.say(line), spanish)
        finally:
            ui_i18n.set_language("en")
            _close(w)


class TestTheModel:
    def test_new_open_save_and_the_title(self):
        with recent_kept():
            self._new_open_save()

    def _new_open_save(self):
        w = _window()
        try:
            assert w.windowTitle() == "OGR FEM2D" and not w.actions_by_key["save"].isEnabled()
            w.act_new()
            assert w.windowTitle() == "Untitled* — Plane strain — OGR FEM2D"
            assert w.actions_by_key["save"].isEnabled()
            assert not w.actions_by_key["undo"].isEnabled()
            w.session.call("project_settings", analysis="axisymmetric", title="Esfera")
            assert w.windowTitle() == "Esfera* — Axisymmetric — OGR FEM2D"
            assert w.actions_by_key["undo"].text() == "Undo: Project settings"
            w.act_undo()
            assert w.windowTitle() == "Untitled* — Plane strain — OGR FEM2D"
            assert w.actions_by_key["redo"].isEnabled()
            with tempfile.TemporaryDirectory() as d:
                target = str(Path(d) / "caso.ogrfem2d")
                w.confirm_discard = lambda: True
                w.open_path(str(_cases_model.path("006-carga-en-faja-malla-general")))
                assert w.windowTitle().startswith("Caso 006") and "*" not in w.windowTitle()
                w.ask_save_path = lambda: target
                w.act_save_as()
                assert Path(target).exists() and w.session.path == Path(target).resolve()
        finally:
            _close(w)

    def test_closing_with_unsaved_changes_asks(self):
        w = _window()
        w.act_new()
        asked = []
        w.confirm_discard = lambda: asked.append(1) or False
        w.close()
        assert asked and w.session.model is not None          # kept: the window stays
        _close(w)
        assert len(asked) == 1
