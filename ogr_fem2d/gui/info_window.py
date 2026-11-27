# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The report of the model and of its results, in a window (spec 006, T33;
RF-4, RF-20; D17).

The report is ``results_report``'s (its sections, ``format="sections"``):
the same sections and rows as its text and its HTML, each line said in the
reader's language from its code (``model/report_messages.py``; what the
user wrote and the numbers as they are). It is saved as HTML or as text in
that language, with ``report.info.to_html`` and ``to_text``, the
operation's own layout; the operation writes it in English
(``results_report`` with ``path``).

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtGui import QAction
from PySide6.QtWidgets import QFileDialog, QMainWindow, QTextBrowser

from ogr_core.api import OgrApiError
from ogr_ui.i18n import tr

from ..report import info
from . import i18n as fem_i18n


def said(x) -> str:
    """A line of the report for the reader: a coded one in the reader's
    language; what the user wrote, an id or a number, as it is."""
    return fem_i18n.say(x) if getattr(x, "code", "") else str(x)


def sections_said(sections: list) -> tuple:
    """The sections of ``results_report`` in the reader's language."""
    return tuple(info.Section(s["key"], said(s["title"]),
                              tuple((said(a), said(b)) for a, b in s["rows"]))
                 for s in sections)


class InfoWindow(QMainWindow):
    """The report, read again on demand, and saved."""

    def __init__(self, session, parent=None):
        super().__init__(parent)
        self.session = session
        self.setWindowTitle(tr("Report"))
        self.browser = QTextBrowser()
        self.browser.setOpenLinks(False)
        self.setCentralWidget(self.browser)
        self.sections: tuple = ()
        self._actions: dict[str, QAction] = {}
        for key, text, slot in (("save_html", "Save as HTML...", lambda: self.act_save("html")),
                                ("save_text", "Save as Text...", lambda: self.act_save("text")),
                                ("refresh", "Read Again", self.read),
                                ("close", "Close", self.close)):
            act = QAction(tr(text), self)
            act.triggered.connect(slot)
            self._actions[key] = act
        m = self.menuBar().addMenu(tr("File"))
        for key in ("save_html", "save_text", "refresh"):
            m.addAction(self._actions[key])
        m.addSeparator()
        m.addAction(self._actions["close"])
        self.resize(820, 760)

    @property
    def actions_by_key(self) -> dict[str, QAction]:
        return dict(self._actions)

    def read(self) -> Optional[str]:
        """The report of the session's model, as it is now; the refusal's
        text, or None."""
        try:
            got = self.session.call("results_report", format="sections")
        except OgrApiError as err:
            text = fem_i18n.say(getattr(err, "message", str(err)))
            self.statusBar().showMessage(text, 15000)
            return text
        self.sections = sections_said(got["sections"])
        self.browser.setHtml(info.to_html(self.sections))
        return None

    def text(self, kind: str) -> str:
        return info.to_html(self.sections) if kind == "html" else info.to_text(self.sections)

    def save(self, path: str, kind: str) -> None:
        Path(path).write_text(self.text(kind), encoding="utf-8")
        self.statusBar().showMessage(tr("Saved: %s") % path, 10000)

    def ask_path(self, kind: str) -> Optional[str]:
        filters = "HTML (*.html)" if kind == "html" else tr("Text") + " (*.txt)"
        path, _f = QFileDialog.getSaveFileName(self, tr("Save the Report"), "", filters)
        return path or None

    def act_save(self, kind: str) -> None:
        path = self.ask_path(kind)
        if path:
            self.save(path, kind)
