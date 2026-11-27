# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.0.15 (spec 006, T31) — the interpretation's window: the selector, the
stage tabs, the field drawn with its legend and its options, and the value
under the cursor (RF-12, RF-19, RF-20; D11, D15).

Invariants protected:

* **the selector is the catalogue**, in its order, with the names of
  axisymmetry in an axisymmetric model;
* **the legend says** the quantity, the unit shown, the convention, the
  stage and where the values come from, and **paints with the canvas's
  colours**: the colour drawn at a point is the settings' colour of the
  field's value there;
* **each option moves the drawing**: the intervals, the palette, the mode,
  the absolute value, the range (this stage, all stages, the user's) and
  the unit system shown;
* **the value under the cursor is the query's**, in the units shown, and
  says why there is none;
* **results that are not valid are not taken for valid**: stale results
  say so above the canvas, in the legend and in the title; incomplete ones
  show only the stages written;
* **every action of the window is in a menu** (rule 3), and Interpret is
  offered only with results;
* **D15 with case 005**, measured.
"""
from __future__ import annotations

import os
import tempfile
import time
from dataclasses import replace
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np  # noqa: E402
from PySide6.QtGui import QImage, QPainter  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from ogr_ui.contours import ContourMode  # noqa: E402
from ogr_ui.testing import menus as menu_rules  # noqa: E402

import _cases_model  # noqa: E402
import _results  # noqa: E402
from _settings import recent_kept  # noqa: E402
from ogr_fem2d.gui.interpret import drawn as drawn_mod  # noqa: E402
from ogr_fem2d.gui.main_window import MainWindow  # noqa: E402
from ogr_fem2d.model import model as md  # noqa: E402
from ogr_fem2d.model import ogr_file  # noqa: E402
from ogr_fem2d.results import calculate as calc  # noqa: E402
from ogr_fem2d.results import quantities as qt  # noqa: E402

APP = QApplication.instance() or QApplication([])
SLOWER = 5.0 if os.environ.get("CI") else 1.0


class _Open:
    """A model calculated in a folder, open in a window, its results shown."""

    def __init__(self, m: md.Model, variant=None, calculated=True):
        self.m, self.variant, self.calculated = m, variant, calculated

    def __enter__(self):
        self._recent = recent_kept()
        self._recent.__enter__()
        self.dir = tempfile.TemporaryDirectory()
        self.path = Path(self.dir.name) / "modelo.ogrfem2d"
        ogr_file.write(self.m, self.path)
        if self.calculated:
            if self.variant is None:
                calc.calculate(self.m, self.path)
            else:
                calc.calculate(self.m, self.path, self.variant)
        self.w = MainWindow()
        self.w.open_path(str(self.path))
        return self

    def __exit__(self, *exc):
        self.w.confirm_discard = lambda: True
        self.w.close()
        self.dir.cleanup()
        self._recent.__exit__(*exc)

    @property
    def win(self):
        return self.w.interpret_window


def _three():
    return _results.excavated_tunnel(3)


def _render(v):
    img = QImage(v.viewport().size(), QImage.Format.Format_ARGB32)
    p = QPainter(img)
    v.render(p)
    p.end()
    return img


class TestTheSelectorAndTheStages:
    def test_the_catalogue_and_the_tabs(self):
        with _Open(_three()) as o:
            assert o.w.interpret() is None
            box = o.win.quantity_box
            ids = [box.itemData(k) for k in range(box.count()) if box.itemData(k)]
            assert ids == [q.id for q in qt.CATALOGUE]
            assert box.itemText(box.findData("sigma_xx")) == "Sigma xx"
            o.win._fill_quantities(replace(o.m, analysis=md.AXISYMMETRIC))
            assert box.itemText(box.findData("sigma_xx")) == "Sigma r (radial)"
            assert box.itemText(box.findData("u_y")) == "Axial displacement"
            o.win._fill_quantities(o.m)
            assert o.win.stage_tabs.count() == 3 and o.win.stage_tabs.currentIndex() == 2
            assert o.win.field["stage"] == o.m.stages[2].id
            o.win.set_stage(0)
            assert o.win.field["stage"] == o.m.stages[0].id
            assert o.win.view.stage == 0

    def test_every_action_in_a_menu_and_offered_with_results(self):
        with _Open(_three(), calculated=False) as o:
            act = o.w.actions_by_key["interpret"]
            assert not act.isEnabled() and "no results" in act.statusTip()
        with _Open(_three()) as o:
            assert o.w.actions_by_key["interpret"].isEnabled()
            o.w.interpret()
            assert menu_rules.unreachable(o.win, o.win.actions_by_key) == []


class TestTheLegend:
    def test_it_says_what_is_drawn(self):
        with _Open(_three()) as o:
            o.w.interpret()
            lines = o.win.legend_lines()
            assert lines[0] == "Sigma 1 (in plane) [kPa]", lines
            assert "Compression positive" in lines
            assert f"Stage: {o.m.stages[2].name}" in lines
            assert "Recovered at the nodes (SPR, material by material)" in lines
            assert "Range: This stage" in lines
            o.win.set_quantity("u_x")
            lines = o.win.legend_lines()
            assert lines[0] == "Horizontal displacement [m]" and \
                "At the nodes (the finite-element field)" in lines

    def test_it_paints_with_the_canvas_colours(self):
        with _Open(_three()) as o:
            o.w.interpret()
            win = o.win
            s = win.settings_of(win.quantity)
            item = win.view.result_item
            painted = {c.name() for c, _p in item.fills}
            assert painted <= set(s.band_colours()) and len(painted) >= 3
            f, xy, tris = win.field, win.field["xy"], win.field["triangles"]
            vals = f["values"] * win.factor()
            step = s.span / s.intervals
            checked = 0
            for t in range(0, len(tris), max(1, len(tris) // 400)):
                cx, cy = xy[tris[t]].mean(axis=0)
                v = vals[tris[t]].mean()
                if min(abs(v - lv) for lv in s.levels()) < 0.05 * step:
                    continue                          # on a band's edge
                assert item.colour_at(cx, cy) == s.colour_for(v), (t, v)
                checked += 1
            assert checked > 100


class TestInSpanish:
    def test_the_catalogue_and_what_the_legend_says(self):
        from ogr_ui import i18n as ui_i18n
        from ogr_ui.testing import texts
        from ogr_fem2d.gui import i18n as fem_i18n
        from ogr_fem2d.gui.interpret import window as iw
        table = {**ui_i18n.package_translations("es"), **fem_i18n.spanish()}
        english = [q.label for q in qt.CATALOGUE] + [q.label_axi for q in qt.CATALOGUE]
        english += list(iw.SOURCE_TEXT.values()) + list(iw.CONVENTION_TEXT.values())
        english += list(iw.STATE_TEXT.values()) + list(iw.REASON_TEXT.values())
        english += [t for _m, t in iw.RANGES]
        assert texts.missing_translations(english, table) == []
        assert set(iw.CONVENTION_TEXT) == {q.convention for q in qt.CATALOGUE}


class TestTheAtQuery:
    def test_is_the_views_value_and_needs_x_and_y(self):
        from ogr_core.api import InvalidArgument
        from ogr_fem2d.results import queries
        with _Open(_three()) as o:
            got = o.w.session.call("results_query", quantity="sigma_xx", kind="at", x=7.0, y=-3.0)
            r = calc.open_results(o.path, o.m).results
            want = queries.View(r, r.n_stages - 1).at("sigma_xx", 7.0, -3.0)
            assert [(row["value"], row["element"], row["material"]) for row in got["rows"]] == \
                [(v, e, mat) for v, e, mat, _s in want]
            assert got["what"] == "at" and got["settings"] == [["x", 7.0], ["y", -3.0]]
            try:
                o.w.session.call("results_query", quantity="sigma_xx", kind="at", x=7.0)
            except InvalidArgument as err:
                assert "needs x and y" in str(err)
            else:
                raise AssertionError("accepted without y")


class TestTheMerging:
    def test_one_vertex_per_material_and_place(self):
        rng = np.random.default_rng(7)
        p = np.round(rng.random((300, 2)) * 40.0 - 20.0, 3)
        xy = np.vstack([p, p, p])
        tris = np.arange(len(xy)).reshape(-1, 3)
        mat = (np.arange(len(tris)) // 100) % 2         # each place in both materials
        first, on = drawn_mod.merging(xy, tris, mat)
        vmat = np.zeros(len(xy), dtype=int)
        vmat[tris.ravel()] = np.repeat(mat, 3)
        rows = np.unique(np.column_stack([vmat, xy]), axis=0)
        assert len(first) == len(rows)                     # the rows' merging, by place
        assert np.array_equal(xy[first][on], xy[tris])     # every triangle where it was
        assert np.array_equal(vmat[first][on], vmat[tris])  # and of its material


class TestEachOptionMovesTheDrawing:
    def test_the_options(self):
        with _Open(_three()) as o:
            o.w.interpret()
            win = o.win
            s = win.settings_of(win.quantity)
            before = len(win.view.drawn.bands)
            win.apply_contour_settings(replace(s, intervals=4))
            assert len(win.view.drawn.bands) <= 4 < before
            colours = {c for c, _r in win.view.drawn.bands}
            win.apply_contour_settings(replace(win.settings_of(win.quantity), palette="Greyscale"))
            assert {c for c, _r in win.view.drawn.bands}.isdisjoint(colours)
            win.apply_contour_settings(replace(win.settings_of(win.quantity),
                                               mode=ContourMode.LINES))
            assert not win.view.drawn.bands and win.view.drawn.lines
            win.apply_contour_settings(replace(win.settings_of(win.quantity),
                                               mode=ContourMode.OFF))
            assert not win.view.drawn.bands and not win.view.drawn.lines
            win.apply_contour_settings(replace(win.settings_of(win.quantity),
                                               mode=ContourMode.SMOOTH))
            assert len(win.view.drawn.bands) > 40

    def test_the_range_and_the_absolute_value(self):
        with _Open(_three()) as o:
            o.w.interpret()
            win = o.win
            win.set_quantity("u_y")
            win.set_stage(0)                         # nothing excavated yet: nothing moves
            here = tuple(win.field["range"])
            win.set_range("auto_all")
            everywhere = tuple(win.field["range"])
            assert everywhere != here and everywhere[0] <= here[0] and everywhere[1] >= here[1]
            win.set_range("auto_stage")
            win.apply_contour_settings(replace(win.settings_of("u_y"), auto_range=False,
                                               vmin=-0.001, vmax=0.0005))
            assert win.range_mode == "custom" and win.field["range"] == [-0.001, 0.0005]
            assert "Range: Custom (Contour Options)" in win.legend_lines()
            win.set_range("auto_stage")
            win.set_stage(2)
            assert win.field["range"][0] < 0.0 < win.field["range"][1]
            win._actions["absolute"].trigger()
            assert win.absolute and win.field["range"][0] >= 0.0
            assert "Absolute value" in win.legend_lines()

    def test_fit_to_results_is_the_drawings_range(self):
        """OGR GUI 0.1.1: «Fit to results» with the whole range
        (``fit_percentile=1``) gives the range the drawing takes, in the
        units shown, the peak included; with the absolute value too."""
        with _Open(_three()) as o:
            o.w.interpret()
            win = o.win
            for absolute in (False, True):
                if absolute:
                    win._actions["absolute"].trigger()
                win.set_range("auto_stage")
                drawn = tuple(v * win.factor() for v in win.field["range"])
                dlg = win.contour_dialog()
                assert not dlg.btn_fit.isHidden() and dlg.btn_fit.isEnabled()
                assert dlg._fit_percentile() == 1.0
                probe = dlg._collect()
                probe.fit_to(dlg._values, percentile=dlg._fit_percentile())
                assert (probe.vmin, probe.vmax) == drawn, ((probe.vmin, probe.vmax), drawn)
                dlg.btn_fit.click()                       # what the button puts in the boxes
                step = 10.0 ** -dlg.sp_min.decimals()
                assert abs(dlg.sp_min.value() - drawn[0]) <= step
                assert abs(dlg.sp_max.value() - drawn[1]) <= step
                assert not dlg.chk_auto.isChecked()
                win.apply_contour_settings(dlg._collect())
                assert win.range_mode == "custom"
                dlg.deleteLater()

    def test_a_narrow_range_still_paints_the_whole_model(self):
        with _Open(_three()) as o:
            o.w.interpret()
            win = o.win
            s = win.settings_of(win.quantity)
            lo, hi = s.vmin + 0.4 * s.span, s.vmin + 0.6 * s.span
            win.apply_contour_settings(replace(s, auto_range=False, vmin=lo, vmax=hi))
            s = win.settings_of(win.quantity)
            item, xy, tris = win.view.result_item, win.field["xy"], win.field["triangles"]
            vals = win.field["values"] * win.factor()
            ends = 0
            for t in range(0, len(tris), max(1, len(tris) // 300)):
                cx, cy = xy[tris[t]].mean(axis=0)
                v = vals[tris[t]].mean()
                if v > hi + 0.05 * s.span or v < lo - 0.05 * s.span:
                    assert item.colour_at(cx, cy) == s.colour_for(v), (t, v)   # its end's colour
                    ends += 1
            assert ends > 20

    def test_the_units_shown(self):
        with _Open(_three()) as o:
            o.w.interpret()
            win = o.win
            lo, hi = win.settings_of("sigma_1").vmin, win.settings_of("sigma_1").vmax
            o.w.session.call("project_settings", units="metric_mpa")
            o.w.session.call("project_save")
            win.open()
            s = win.settings_of("sigma_1")
            assert np.isclose(s.vmin, lo / 1000) and np.isclose(s.vmax, hi / 1000)
            assert win.legend_lines()[0] == "Sigma 1 (in plane) [MPa]"


class TestTheValueUnderTheCursor:
    def test_is_the_querys(self):
        with _Open(_three()) as o:
            o.w.interpret()
            win = o.win
            x, y = 7.0, -3.0
            row = o.w.session.call("results_query", quantity="sigma_1", kind="at",
                                   stage=win.stage_id, x=x, y=y)["rows"][0]
            said = win.value_at(x, y)
            assert f"Sigma 1 (in plane) = {row['value']:.4g} kPa" in said, said
            assert "outside the mesh" in win.value_at(1e4, 1e4)


class TestNotValid:
    def test_stale_is_said(self):
        with _Open(_three()) as o:
            o.w.interpret()
            assert o.win.banner.isHidden()
            o.w.session.call("material_set", material="rock", E=2.0e7)
            assert o.win.state == calc.STALE                  # said at once, by the edit
            assert not o.win.banner.isHidden() and "another model" in o.win.banner.text()
            assert o.win.legend_lines()[0] == "NOT VALID: Stale"
            assert "Stale" in o.win.windowTitle()

    def test_incomplete_shows_the_stages_written(self):
        free = md.Condition(md.FREE, md.Span("ext"), active=(False, True, True))
        with _Open(replace(_three(), conditions=(free,))) as o:
            o.w.interpret()
            assert o.win.state == "incomplete" and o.win.stage_tabs.count() == 1
            assert "Incomplete" in o.win.banner.text()


class TestD15:
    def test_case_005(self):
        from ogr_fem2d.engine.compiled import RUST
        m = ogr_file.read(_cases_model.path("005-kirsch-malla-general"))
        with _Open(m, RUST) as o:
            win = o.w.interpret_window
            win.resize(1600, 1000)
            win.show()
            import matplotlib.figure  # noqa: F401 - the program imports it at start (warm_up)
            import matplotlib.tri  # noqa: F401
            t = time.perf_counter()
            o.w.interpret()
            _render(win.view)
            first = time.perf_counter() - t
            t = time.perf_counter()
            win.set_quantity("sigma_3")
            _render(win.view)
            other = time.perf_counter() - t
            t = time.perf_counter()
            win.set_quantity("u")
            _render(win.view)
            displacement = time.perf_counter() - t
            APP.processEvents()                  # what the window does once it has drawn
            moves = []
            for move in (lambda: win.view.zoom_by(1.5), lambda: win.view.translate_pixels(40, 0),
                         lambda: win.show_value(1.5, 1.5)):
                t = time.perf_counter()
                move()
                _render(win.view)
                moves.append(time.perf_counter() - t)
            print(f"D15 case 005: first {first:.2f} s, "
                  f"another quantity {other:.2f} s, a displacement {displacement:.2f} s, "
                  f"moves {[round(x, 3) for x in moves]} s")
            assert other <= 1.0 * SLOWER and displacement <= 1.0 * SLOWER, (other, displacement)
            assert max(moves) <= 0.1 * SLOWER, moves
            # the first drawing of a stage: 1.3 s while it recovered the stresses (T32's
            # finding); with them written when calculating and the model's fingerprint
            # quicker (T36), 0.6 s measured on a quiet machine
            assert first <= 1.0 * SLOWER, first

    def test_the_start_imports_the_contouring(self):
        import sys
        import threading
        from ogr_fem2d.gui import app
        app.warm_up()
        for th in threading.enumerate():
            if th.name == "warm-up":
                th.join(60)
        assert "matplotlib.tri" in sys.modules and "matplotlib.figure" in sys.modules
