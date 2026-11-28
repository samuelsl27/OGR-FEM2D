# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.0.15 (spec 006, T37; D12 as the owner modified it on 2026-11-28) — the
decimal mark is always a point, in English and in Spanish, and a comma is
refused: it lends itself to confusion and to errors.

Invariants protected:

* **a number box shows a point and takes only a point**, whatever the
  language and the machine's locale (Qt's own box follows the locale: with
  Spain's it showed «2,500» and took «2.5» as 25); a comma typed is not
  written, and «1.000» is 1, with no thousands separator;
* **a table of numbers refuses a comma**: the coordinates, saying the row;
* **what the interpretation shows in Spanish is written with a point**: the
  value under the cursor, the legend's figures, the range of what decided
  it and the rows of a query, the same figures as in English; the figures
  of a query's table are aligned to the right;
* the CSV table is the same in both languages.
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QLocale, Qt  # noqa: E402
from PySide6.QtGui import QValidator  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from ogr_ui import i18n as ui_i18n  # noqa: E402
from ogr_core.units import Quantity as Q  # noqa: E402

import _results  # noqa: E402
from _settings import recent_kept  # noqa: E402
from ogr_fem2d.gui.dialogs.coordinates import TableError, read_number, read_rows  # noqa: E402
from ogr_fem2d.gui.dialogs.fields import DecimalBox, Number  # noqa: E402
from ogr_fem2d.gui.main_window import MainWindow  # noqa: E402
from ogr_fem2d.model import ogr_file  # noqa: E402
from ogr_fem2d.results import calculate as calc  # noqa: E402

APP = QApplication.instance() or QApplication([])
LINE = ((2.0, 0.0), (10.0, 0.0))


class _Spanish:
    """Spanish, on a machine whose locale is Spain's."""

    def __enter__(self):
        self._locale = QLocale()
        QLocale.setDefault(QLocale(QLocale.Language.Spanish, QLocale.Country.Spain))
        ui_i18n.set_language("es")

    def __exit__(self, *exc):
        ui_i18n.set_language("en")
        QLocale.setDefault(self._locale)


def _typed(box, text):
    box.lineEdit().setText(text)
    box.interpretText()
    return box.value()


def _state(box, text):
    return box.validate(text, len(text))[0]


class TestTheBox:
    def test_a_point_always_and_a_comma_refused(self):
        with _Spanish():
            box = DecimalBox()
            box.setDecimals(3)
            box.setRange(-1e6, 1e6)
            box.setValue(2.5)
            assert box.text() == "2.500"
            assert _typed(box, "3.25") == 3.25
            assert _typed(box, "1.000") == 1.0                 # not a thousand
            assert _typed(box, "-1.5e2") == -150.0
            for text in ("3,25", "1,", ",5"):
                assert _state(box, text) == QValidator.State.Invalid, text
        box = DecimalBox()
        box.setDecimals(3)
        box.setValue(2.5)
        assert box.text() == "2.500"
        assert _state(box, "4,5") == QValidator.State.Invalid

    def test_a_dialogs_number_with_its_unit(self):
        m = _results.excavated_tunnel(1)
        with _Spanish():
            n = Number(m, 12.5, Q.LENGTH)
            assert n.box.text() == "12.500 m" and n.value() == 12.5
            _typed(n.box, "7.25 m")
            assert n.value() == 7.25
            assert _state(n.box, "7,25 m") == QValidator.State.Invalid


class TestTheTables:
    def test_a_comma_is_refused(self):
        assert read_number("2.5") == 2.5
        for text in ("2,5", "1,000"):
            try:
                read_number(text)
            except TableError:
                pass
            else:
                raise AssertionError(f"{text!r} was taken")
        try:
            read_rows([("0", "0"), ("2,5", "0")])
        except TableError as err:
            assert "Row 2" in str(err)
        else:
            raise AssertionError("a decimal comma was taken")


class _Open:
    def __enter__(self):
        self._recent = recent_kept()
        self._recent.__enter__()
        self.dir = tempfile.TemporaryDirectory()
        self.path = Path(self.dir.name) / "modelo.ogrfem2d"
        m = _results.excavated_tunnel(3)
        ogr_file.write(m, self.path)
        calc.calculate(m, self.path)
        self.w = MainWindow()
        self.w.open_path(str(self.path))
        self.w.interpret()
        return self

    def __exit__(self, *exc):
        ui_i18n.set_language("en")
        self.w.confirm_discard = lambda: True
        self.w.close()
        self.dir.cleanup()
        self._recent.__exit__(*exc)


def _figures(text):
    return [t for t in text.replace(",", " ").replace(";", " ").split()
            if any(c.isdigit() for c in t)]


class TestTheInterpretation:
    def test_in_spanish_with_a_point(self):
        with _Open() as o:
            win = o.w.interpret_window
            english = win.value_at(7.25, -3.0)
            labels_en = list(win.legend._labels)
            qw_en = win.query_line(LINE, 5)
            rows_en = [[qw_en.table.item(r, c).text() for c in range(5)]
                       for r in range(qw_en.table.rowCount())]
            with _Spanish():
                win.redraw()
                said = win.value_at(7.25, -3.0)
                assert said.startswith("x = 7.25, y = -3 m: "), said
                assert _figures(said) == _figures(english), (said, english)
                assert win.legend._labels == labels_en and any("." in t for t in labels_en)
                _label, rng = win.decided_parts()[3][1][1]      # the drawing's range
                assert "." in rng and "," not in rng, rng
                qw = win.query_line(LINE, 5)
                rows = [[qw.table.item(r, c).text() for c in range(5)]
                        for r in range(qw.table.rowCount())]
                assert rows == rows_en and any("." in v for row in rows for v in row)
                assert qw.table.item(0, 4).textAlignment() & Qt.AlignmentFlag.AlignRight
                assert not qw.table.item(0, 5).textAlignment() & Qt.AlignmentFlag.AlignRight
                bounded = win.query_boundary("hole", 2, 0.5, "outside")
                assert "Distancia: 0.5 m" in bounded.header_lines(), bounded.header_lines()
                csv = Path(o.dir.name) / "tabla.csv"
                assert qw.export(str(csv)) is None
            english_csv = Path(o.dir.name) / "table.csv"
            assert qw.export(str(english_csv)) is None
            assert csv.read_bytes() == english_csv.read_bytes()
