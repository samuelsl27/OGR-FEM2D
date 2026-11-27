# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.0.15 (spec 006, T36; RF-21) — Help > Help Topics (F1): the help, in the
program, with the validation cases.

Invariants protected:

* **no network**: no page has a link or a resource out of the help (its
  links are pages, cases and sheets), the window's browser loads none it
  was not given, a link of another kind is said and not followed, and no
  socket is opened while every page is shown and every link followed;
* **in the reader's language**: every page in Spanish has its Spanish
  (the census of rule 2 covers the texts; here, what a page says);
* **the cases are the folder's**: every case of ``validacion/casos`` but
  the template, with its sheet, its source and its tolerance as its
  esperado.json says them; a case with a model opens as a COPY in the
  folder asked for, and the case's own file is not touched; without the
  folder, the page says where the cases are;
* the entry is in the Help menu, with F1.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import socket
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QUrl  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from _settings import recent_kept  # noqa: E402
from ogr_fem2d.gui import help as hp  # noqa: E402
from ogr_fem2d.gui.main_window import MainWindow  # noqa: E402

APP = QApplication.instance() or QApplication([])
ROOT = Path(__file__).resolve().parents[1]
CASES = ROOT / "validacion" / "casos"


class _Window:
    def __enter__(self):
        self._recent = recent_kept()
        self._recent.__enter__()
        self.w = MainWindow()
        self.w._actions["help"].trigger()
        self.h = self.w.help_window
        return self

    def __exit__(self, *exc):
        self.w.confirm_discard = lambda: True
        self.w.close()
        self._recent.__exit__(*exc)


def _links(html: str) -> list[str]:
    return re.findall(r"""(?:href|src)\s*=\s*['"]([^'"]*)['"]""", html)


class TestNoNetwork:
    def test_every_page_and_every_link(self):
        real = socket.socket.connect
        opened = []
        socket.socket.connect = lambda self, *a: opened.append(a) or real(self, *a)
        try:
            with _Window() as o:
                for key, _t, _b in hp.PAGES:
                    o.h.show_page(key)
                    for link in _links(hp.page(key)):
                        assert link.split(":", 1)[0] in hp.SCHEMES, (key, link)
                        if link.startswith("case:"):
                            continue                       # asks for a folder (below)
                        assert o.h.follow(QUrl(link)) is None, link
                said = o.h.follow(QUrl("https://example.org/x"))
                assert said and "follows no link" in said
                assert o.w.statusBar().currentMessage() == said
                assert o.h.browser.refused == []           # nothing it was not given
                o.h.browser.loadResource(2, QUrl("https://example.org/a.png"))
                assert o.h.browser.refused == ["https://example.org/a.png"]
        finally:
            socket.socket.connect = real
        assert opened == []

    def test_the_entry_and_its_key(self):
        from ogr_fem2d.gui import menus
        with _Window() as o:
            assert "help" in menus.MENUS["Help"]
            assert o.w.actions_by_key["help"].shortcut().toString() == "F1"
            assert not o.h.isHidden() and o.h.key == "start"


class TestInSpanish:
    def test_a_page_says_it_in_spanish(self):
        from ogr_ui import i18n as ui_i18n
        from ogr_fem2d.gui import i18n as fem_i18n
        fem_i18n.install()                       # as the program does when it starts
        try:
            ui_i18n.set_language("es")
            assert "Los casos de validación" in hp.page("start")
            assert "Análisis > Calcular (F9)" in hp.page("compute")
            assert "compresión y el acortamiento" in hp.page("conventions")
        finally:
            ui_i18n.set_language("en")
        assert "Analysis > Compute (F9)" in hp.page("compute")


class TestTheCases:
    def test_are_the_folders(self):
        got = hp.cases()
        want = sorted(d.name for d in CASES.iterdir()
                      if d.is_dir() and not d.name.startswith("000"))
        assert [c.id for c in got] == want and len(want) >= 7
        for c in got:
            e = json.loads((c.folder / "esperado.json").read_text(encoding="utf-8"))
            assert c.sheet == e["ficha"] and c.source == e["fuente"]
            assert c.title == (c.folder / "caso.md").read_text(encoding="utf-8") \
                .splitlines()[0].lstrip("# ").strip()
            if e.get("tolerancia_relativa") is not None:
                assert c.tolerance == f"{100 * e['tolerancia_relativa']:g} % relative"
            else:
                assert c.tolerance.startswith(f"{e['tolerancia_absoluta']:g} absolute")
        with_model = [c.id for c in got if c.model is not None]
        assert with_model == [c for c in want if (CASES / c / "modelo.ogrfem2d").exists()]
        html = hp.page("cases")
        assert all(f"sheet:{c}" in html for c in want)
        assert [x for x in want if f"case:{x}" in html] == with_model

    def test_a_copy_is_opened_and_the_case_is_not_touched(self):
        case = next(c for c in hp.cases() if c.model is not None)
        before = hashlib.sha256(case.model.read_bytes()).hexdigest()
        with _Window() as o, tempfile.TemporaryDirectory() as d:
            o.h.ask_folder = lambda: d
            assert o.h.follow(QUrl(f"case:{case.id}")) is None
            copy = Path(d) / f"caso-{case.id.split('-')[0]}.ogrfem2d"
            assert copy.exists()
            assert Path(o.w.session.path).resolve() == copy.resolve()
            assert o.w.session.model.mesh is not None
            said = o.h.follow(QUrl(f"case:{case.id}"))       # a second time: not over it
            assert said and copy.name in said
            o.h.ask_folder = lambda: None                      # cancelled: nothing
            assert o.h.follow(QUrl(f"case:{case.id}")) is None
        assert hashlib.sha256(case.model.read_bytes()).hexdigest() == before

    def test_a_sheet_and_no_folder(self):
        with _Window() as o:
            c = hp.cases()[0]
            o.h.follow(QUrl(f"sheet:{c.id}"))
            assert o.h.key == f"sheet:{c.id}" and c.title in o.h.browser.toPlainText()
        real = hp.cases_folder
        hp.cases_folder = lambda: None
        try:
            assert hp.cases() == []
            assert "validacion/casos" in hp.page("cases") and "case:" not in hp.page("cases")
        finally:
            hp.cases_folder = real
