# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Help > Help Topics (F1): the help of this program, in its own window, with
the validation cases (spec 006, RF-21, T36).

* **No network**: every page is written here, through ``tr()`` (rule 2:
  its Spanish is in ``i18n/es_help.py``), and the window's browser loads
  no resource it was not given (``LocalBrowser``): a link goes to another
  page, to a case, or to a case's sheet, and nothing else is followed.
* **The pages say what the program does in this phase**, with the names
  of its menus and keys, and the two things that change a number without
  being drawn: the conventions (rule 10) and the values that decided a
  result (rule 12).
* **The cases** are read from the folder of the validation cases
  (``validacion/casos``: in the source tree, or inside the frozen
  program): each with its sheet, its source, its tolerance, and, for those
  that have a model, a link that opens a COPY of it in a folder the person
  chooses (the case's own file is never the one edited). Without the
  folder (an installed wheel), the page says where the cases are.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import json
import shutil
import sys
from dataclasses import dataclass
from html import escape
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QUrl
from PySide6.QtWidgets import (QDialog, QFileDialog, QHBoxLayout, QListWidget, QListWidgetItem,
                               QTextBrowser)
from ogr_ui.i18n import tr

#: the program's name, which is not translated
NAME = "OGR FEM2D"
#: the schemes of the help's links: a page, a case's model, a case's sheet
SCHEMES = ("page", "case", "sheet")


# ------------------------------------------------------------------ the cases
@dataclass(frozen=True)
class Case:
    id: str              # the folder's name, "005-kirsch-malla-general"
    title: str           # the first heading of its caso.md
    sheet: str           # its working sheet ("VER-STR-01")
    source: str          # its scientific source, as its esperado.json says it
    reference: str       # "analitica", "publicado", "identidad"
    tolerance: str       # "0.5 % relative", "0.01 absolute"
    folder: Path

    @property
    def model(self) -> Optional[Path]:
        p = self.folder / "modelo.ogrfem2d"
        return p if p.exists() else None


def cases_folder() -> Optional[Path]:
    """The folder of the validation cases: inside the frozen program, or in
    the source tree; None when neither has it."""
    here = [Path(getattr(sys, "_MEIPASS", "")) / "validacion" / "casos"] \
        if getattr(sys, "frozen", False) else []
    here.append(Path(__file__).resolve().parents[3] / "validacion" / "casos")
    return next((p for p in here if p.is_dir()), None)


def cases(folder: Optional[Path] = None) -> list[Case]:
    """The cases of the folder, in order; the template (000) left out."""
    folder = cases_folder() if folder is None else folder
    if folder is None:
        return []
    out = []
    for d in sorted(p for p in folder.iterdir() if p.is_dir()):
        sheet, expected = d / "caso.md", d / "esperado.json"
        if d.name.startswith("000") or not (sheet.exists() and expected.exists()):
            continue
        e = json.loads(expected.read_text(encoding="utf-8"))
        first = sheet.read_text(encoding="utf-8").splitlines()[0]
        if e.get("tolerancia_relativa") is not None:
            tol = tr("%s %% relative") % f"{100 * float(e['tolerancia_relativa']):g}"
        else:
            tol = tr("%s absolute (over the case's scale)") % f"{float(e['tolerancia_absoluta']):g}"
        out.append(Case(d.name, first.lstrip("# ").strip(), str(e.get("ficha", "")),
                        str(e.get("fuente", "")), str(e.get("tipo_referencia", "")), tol, d))
    return out


# ------------------------------------------------------------------ the pages
def _p(*texts: str) -> str:
    return "".join(f"<p>{t}</p>" for t in texts)


def _ul(*items: str) -> str:
    return "<ul>" + "".join(f"<li>{i}</li>" for i in items) + "</ul>"


def _start() -> str:
    return (f"<h1>{NAME}</h1>"
            + _p(tr("2-D geotechnical analysis by finite elements: stresses and displacements "
                    "in plane strain or axisymmetry, by stages of construction."),
                 tr("In this phase the materials are linear elastic and isotropic and the "
                    "elements are triangles of three or six nodes. Plasticity, water, supports "
                    "and joints come in later phases: their menus are there, disabled, saying "
                    "when."))
            + f"<h2>{tr('The work, in order')}</h2>"
            + _ul(f"<a href='page:model'>{tr('Drawing the model')}</a>",
                  f"<a href='page:mesh'>{tr('Meshing')}</a>",
                  f"<a href='page:compute'>{tr('Calculating')}</a>",
                  f"<a href='page:interpret'>{tr('Interpreting the results')}</a>",
                  f"<a href='page:conventions'>{tr('Units, signs and what decided a result')}</a>",
                  f"<a href='page:bridge'>{tr('The agent bridge')}</a>",
                  f"<a href='page:cases'>{tr('The validation cases')}</a>"))


def _model() -> str:
    return (f"<h1>{tr('Drawing the model')}</h1>"
            + _p(tr("Analysis > Project Settings sets the analysis (plane strain or axisymmetry), "
                    "the units shown and the title. Every value is kept in m, kN and kPa; the "
                    "units shown only change how they are written."))
            + f"<h2>{tr('Boundaries')}</h2>"
            + _p(tr("Boundaries > Add External, Add Excavation, Add Material Boundary, Add Stage "
                    "Boundary and Add Circular Excavation draw by clicks or by typed points. In "
                    "the X, Y field of the status bar: x, y (or x; y with decimal commas), @dx, dy "
                    "from the last point, or @distance<angle in degrees, then Enter. A (Arc) "
                    "draws an arc through a point; T (Enter Coordinates) takes a table; Enter "
                    "finishes, Esc cancels, Backspace undoes the last vertex."),
                 tr("Where a boundary cuts another, a vertex is put in both."))
            + f"<h2>{tr('Materials, stages, loads and conditions')}</h2>"
            + _p(tr("Properties > Define Materials gives E, nu, the unit weight and the initial "
                    "loading of each material; Assign Properties puts one in a region by a "
                    "click, or excavates or fills a region, from the stage shown on or in that "
                    "stage only."),
                 tr("Analysis > Add Stage, Rename Stage and Delete Stage make the stages; the "
                    "tabs below the canvas choose the one shown."),
                 tr("Loading > Field Stress gives the initial stresses; Add Distributed Load and "
                    "Add Point Load go on segments or vertices, with Factors by Stage. "
                    "Displacements restrains or imposes them on the boundaries; External "
                    "Default is what the external boundary has where nothing else is said."),
                 tr("Loads and imposed displacements are given in totals for each stage: the "
                    "program works out what changes from one stage to the next.")))


def _mesh() -> str:
    return (f"<h1>{tr('Meshing')}</h1>"
            + _p(tr("Mesh > Mesh Setup chooses the mesh type (graded or uniform), the element "
                    "type (triangles of three or six nodes), the quality bound, the nodes on the "
                    "excavations or the element size, and the refinement windows. "
                    "Segment Divisions fixes the nodes of a segment."),
                 tr("Meshing is two steps: Discretize puts the nodes on the boundaries, and "
                    "Discretize and Mesh (Ctrl+M) makes the elements. A mesh is part of the "
                    "model and is saved with it; Reset Mesh removes it."),
                 tr("A case fixes its mesh: a different mesh is a different case.")))


def _compute() -> str:
    return (f"<h1>{tr('Calculating')}</h1>"
            + _p(tr("Analysis > Compute (F9) calculates the saved model (it asks to save it "
                    "first if it has changes) in a process of its own: the window goes on, and Window > Calculation shows the "
                    "queue, the stage being solved, the log and the summary. Cancel stops it "
                    "between two stages, or stops the process."),
                 tr("The results go to a file next to the model, with the same name and .h5. "
                    "It carries the fingerprint of the model it is of: results of a model that "
                    "changed since are said to be of another model, and shown as such, never "
                    "as valid. A calculation that stopped keeps the stages it solved, and says "
                    "so.")))


def _interpret() -> str:
    return (f"<h1>{tr('Interpreting the results')}</h1>"
            + _p(tr("Analysis > Interpret (F10) opens the results: a tab per stage, the quantity "
                    "chosen in the list, its contours and its legend. The legend says the "
                    "quantity, its unit, its convention, the stage and where the values come "
                    "from."),
                 tr("Stresses and strains are recovered at the nodes, material by material "
                    "(superconvergent patch recovery, Zienkiewicz and Taylor 2000, §14.4): a "
                    "contact between two materials keeps a value on each side. Displacements are "
                    "the finite-element field."),
                 tr("Results > Contour Options sets the intervals, the palette and the range; "
                    "the range is that of the stage, that of all stages, or one of your own, and "
                    "always the whole range: a peak is never cut. Absolute Value draws the "
                    "absolute value."),
                 tr("The value under the cursor is interpolated exactly at the point, not read "
                    "off the colours."),
                 tr("Query: along a line or a polyline, on a boundary (or at a distance to one "
                    "side of it), at every node, or at a point through the stages. Each query "
                    "has its table, its chart and its export, and says what decided it."),
                 tr("Analysis > Report (F11) writes the model, the mesh, what decided the result "
                    "and the results, and saves them as HTML or text.")))


def _conventions() -> str:
    return (f"<h1>{tr('Units, signs and what decided a result')}</h1>"
            + _ul(tr("Units: kept in m, kN and kPa; shown in the units of Project Settings."),
                  tr("Stresses and strains are shown compression positive and shortening "
                     "positive, as is the custom in geotechnics; displacements are positive "
                     "along +x and +y. The engine works tension positive: the change is made "
                     "in one place."),
                  tr("In axisymmetry x is the radius and y the axis; the circumferential "
                     "stress is sigma z, and reactions are of the whole ring."))
            + _p(tr("A value that changes the result without being drawn (the analysis, the "
                    "default restraint, the initial loading, the settings of the mesh and of "
                    "the engine) is said with the result: in the panel What decided it of the "
                    "interpretation, in each query and in the report.")))


def _bridge() -> str:
    return (f"<h1>{tr('The agent bridge')}</h1>"
            + _p(tr("Tools > Agent Bridge (MCP) lets the MCP server of this program work on the "
                    "model of this window: what an agent does is drawn here and is undone with "
                    "Edit > Undo. The bridge listens only on this computer, and only to who "
                    "has its key, which is in a file only you can read."),
                 tr("While a calculation is running an agent can ask and follow it, but not "
                    "edit: the results being written are of the model as it was.")))


def _cases() -> str:
    found = cases()
    head = (f"<h1>{tr('The validation cases')}</h1>"
            + _p(tr("Each case is checked against an external reference (a closed solution, a "
                    "published case or an identity), with a tolerance fixed before measuring. "
                    "Their sheets are written in Spanish.")))
    if not found:
        return head + _p(tr("The cases are not with this copy of the program: they are in the "
                            "folder validacion/casos of its source repository."))
    rows = []
    for c in found:
        links = [f"<a href='sheet:{escape(c.id)}'>{tr('Sheet')}</a>"]
        if c.model is not None:
            links.append(f"<a href='case:{escape(c.id)}'>{tr('Open a copy of the model')}</a>")
        rows.append(f"<tr><td><b>{escape(c.title)}</b><br>{escape(c.sheet)}</td>"
                    f"<td>{escape(c.source)}</td><td>{escape(c.tolerance)}</td>"
                    f"<td>{' · '.join(links)}</td></tr>")
    return (head + "<table border='1' cellspacing='0' cellpadding='4'>"
            f"<tr><th>{tr('Case')}</th><th>{tr('Source')}</th><th>{tr('Tolerance')}</th>"
            f"<th></th></tr>" + "".join(rows) + "</table>")


#: the pages, in the order of the list: (key, title, body)
PAGES = (("start", NAME, _start), ("model", "Drawing the model", _model),
         ("mesh", "Meshing", _mesh), ("compute", "Calculating", _compute),
         ("interpret", "Interpreting the results", _interpret),
         ("conventions", "Units, signs and what decided a result", _conventions),
         ("bridge", "The agent bridge", _bridge), ("cases", "The validation cases", _cases))


def page(key: str) -> str:
    """The HTML of a page, in the reader's language."""
    for k, _title, body in PAGES:
        if k == key:
            return body()
    raise KeyError(f"no help page {key!r}")


# ------------------------------------------------------------------ the window
class LocalBrowser(QTextBrowser):
    """A browser that follows no link itself and loads no resource it was
    not given: no network (RF-21)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setOpenLinks(False)
        self.setOpenExternalLinks(False)
        self.refused: list[str] = []

    def loadResource(self, kind, url):  # noqa: N802 - Qt's name
        self.refused.append(url.toString())
        return None


class HelpWindow(QDialog):
    """The pages on the left, the page on the right."""

    def __init__(self, main):
        super().__init__(main)
        self.main = main
        self.setWindowTitle(tr("Help"))
        lay = QHBoxLayout(self)
        self.list = QListWidget()
        for key, title, _body in PAGES:
            item = QListWidgetItem(tr(title))
            item.setData(256, key)                       # Qt.UserRole
            self.list.addItem(item)
        self.list.setMaximumWidth(240)
        self.list.currentRowChanged.connect(lambda k: self.show_page(PAGES[k][0]))
        self.browser = LocalBrowser()
        self.browser.anchorClicked.connect(self.follow)
        lay.addWidget(self.list)
        lay.addWidget(self.browser, 1)
        self.resize(900, 640)
        self.key = ""
        self.list.setCurrentRow(0)

    def show_page(self, key: str) -> None:
        self.key = key
        self.browser.setHtml(page(key))
        k = [p[0] for p in PAGES].index(key)
        if self.list.currentRow() != k:
            self.list.blockSignals(True)
            self.list.setCurrentRow(k)
            self.list.blockSignals(False)

    def show_sheet(self, case_id: str) -> None:
        c = next(c for c in cases() if c.id == case_id)
        self.key = "sheet:" + case_id
        self.browser.setMarkdown((c.folder / "caso.md").read_text(encoding="utf-8"))

    def follow(self, url: QUrl) -> Optional[str]:
        """A link: a page, a sheet, or a copy of a case's model; anything
        else is not followed (said). What was said, or None."""
        scheme, what = url.scheme(), url.path() or url.toString().split(":", 1)[-1]
        if scheme == "page":
            self.show_page(what)
        elif scheme == "sheet":
            self.show_sheet(what)
        elif scheme == "case":
            return self.open_case(what)
        else:
            said = tr("The help follows no link out of it: %s") % url.toString()
            self.main.statusBar().showMessage(said, 15000)
            return said
        return None

    def ask_folder(self) -> Optional[str]:
        return QFileDialog.getExistingDirectory(self, tr("Where the copy of the case goes")) \
            or None

    def open_case(self, case_id: str) -> Optional[str]:
        """A copy of the case's model, in a folder asked for, opened in the
        window; the case's own file is never opened. What was said, or None."""
        c = next(c for c in cases() if c.id == case_id)
        folder = self.ask_folder()
        if not folder:
            return None
        target = Path(folder) / f"caso-{c.id.split('-')[0]}.ogrfem2d"
        if target.exists():
            said = tr("There is already a file %s: choose another folder.") % target.name
            self.main.statusBar().showMessage(said, 15000)
            return said
        shutil.copyfile(c.model, target)
        self.main.open_path(str(target))
        return None
