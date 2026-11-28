# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.0.15 (spec 006, T37; D12) — the numbers on the screen with the
language's decimal separator, a comma in Spanish, and a point or a comma
taken whatever the language.

Invariants protected:

* **a number box shows the language's separator and takes both**, with no
  thousands separator: in Spanish «2.5» is 2.5, not 25, and «1.000» is 1
  (Qt's box follows the machine's locale, not the program's language);
* **what the interpretation shows is written in Spanish with a comma**: the
  value under the cursor (its two coordinates parted by a semicolon, as a
  typed point), the legend's figures, the range of what decided it, the
  rows of a query and its settings; the figures of its table are aligned to
  the right;
* **the CSV table keeps the point** in Spanish (005, D15), and in English
  nothing changes.
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from ogr_ui import i18n as ui_i18n  # noqa: E402
from ogr_core.units import Quantity as Q  # noqa: E402

import _results  # noqa: E402
from _settings import recent_kept  # noqa: E402
from ogr_fem2d.gui import units  # noqa: E402
from ogr_fem2d.gui.dialogs.fields import DecimalBox, Number  # noqa: E402
from ogr_fem2d.gui.main_window import MainWindow  # noqa: E402
from ogr_fem2d.model import ogr_file  # noqa: E402
from ogr_fem2d.results import calculate as calc  # noqa: E402

APP = QApplication.instance() or QApplication([])
LINE = ((2.0, 0.0), (10.0, 0.0))


class _Spanish:
    def __enter__(self):
        ui_i18n.set_language("es")

    def __exit__(self, *exc):
        ui_i18n.set_language("en")


def _typed(box, text):
    box.lineEdit().setText(text)
    box.interpretText()
    return box.value()


class TestTheBox:
    def test_shows_the_comma_and_takes_both(self):
        with _Spanish():
            box = DecimalBox()
            box.setDecimals(3)
            box.setRange(-1e6, 1e6)
            box.setValue(2.5)
            assert box.text() == "2,500"
            assert _typed(box, "3,25") == 3.25
            assert _typed(box, "3.25") == 3.25
            assert _typed(box, "1.000") == 1.0                 # not a thousand
            assert _typed(box, "-1,5e2") == -150.0
        box = DecimalBox()
        box.setDecimals(3)
        box.setValue(2.5)
        assert box.text() == "2.500"
        assert _typed(box, "4,5") == 4.5

    def test_a_dialogs_number_with_its_unit(self):
        m = _results.excavated_tunnel(1)
        with _Spanish():
            n = Number(m, 12.5, Q.LENGTH)
            assert n.box.text() == "12,500 m" and n.value() == 12.5
            _typed(n.box, "7.25 m")
            assert n.value() == 7.25


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


class TestTheInterpretation:
    def test_in_spanish_with_a_comma(self):
        with _Open() as o:
            win = o.w.interpret_window
            english = win.value_at(7.25, -3.0)
            assert "x = 7.25, y = -3 m: " in english, english
            ui_i18n.set_language("es")
            win.redraw()
            said = win.value_at(7.25, -3.0)
            assert said.startswith("x = 7,25; y = -3 m: "), said
            value = said.split(" = ")[-1].split()[0]
            assert "," in value and "." not in value, said
            labels = win.legend._labels
            assert labels and all("." not in t for t in labels), labels
            assert any("," in t for t in labels), labels
            _label, rng = win.decided_parts()[3][1][1]          # the drawing's range
            assert "," in rng and "." not in rng, rng
            qw = win.query_line(LINE, 5)
            cell = qw.table.item(2, 1).text()                 # the distance of the third point
            assert cell == "4", cell                          # 8 m in 5 points: 0, 2, 4...
            values = [qw.table.item(r, 4).text() for r in range(qw.table.rowCount())]
            assert all("." not in v for v in values) and any("," in v for v in values), values
            assert qw.table.item(0, 4).textAlignment() & Qt.AlignmentFlag.AlignRight
            assert not qw.table.item(0, 5).textAlignment() & Qt.AlignmentFlag.AlignRight
            bounded = win.query_boundary("hole", 2, 0.5, "outside")
            assert "Distancia: 0,5 m" in bounded.header_lines(), bounded.header_lines()
            csv, english_csv = Path(o.dir.name) / "tabla.csv", Path(o.dir.name) / "table.csv"
            assert qw.export(str(csv)) is None
            ui_i18n.set_language("en")
            assert qw.export(str(english_csv)) is None
            assert csv.read_bytes() == english_csv.read_bytes()   # the table keeps the point
            assert "," in csv.read_text(encoding="utf-8")
