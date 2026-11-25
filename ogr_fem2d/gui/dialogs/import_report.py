# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The report of a conversion (spec 006, T28; RF-17; ADR-0004): what opening a
``.ogr`` of OGR Slip2D or a DXF brought, what it did not, the defaults it
took, what it changed, and what is still unfinished in the model (its
problems), **whole**, in a window that stays open beside the model.

Every line is shown; none is summarised away (the reference program's
import said nothing of what it left behind).

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import html

from PySide6.QtCore import QSize
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QTextBrowser, QVBoxLayout

from ogr_ui.dialog_size import open_at_content_size
from ogr_ui.i18n import tr

#: the parts of the report, in the order shown
PARTS = (("brought", "What came"), ("not_brought", "What did not come"),
         ("defaults", "Defaults taken (they change the result: check them)"),
         ("changed", "What was changed"))


def report_html(source: str, report: dict, problems: list) -> str:
    out = [f"<h3>{html.escape(tr('Converted from %s') % source)}</h3>"]
    for key, title in PARTS:
        lines = report.get(key) or []
        out.append(f"<h4>{html.escape(tr(title))} ({len(lines)})</h4>")
        out.append("<ul>" + "".join(f"<li>{html.escape(str(x))}</li>" for x in lines) + "</ul>"
                   if lines else f"<p>{html.escape(tr('Nothing.'))}</p>")
    out.append(f"<h4>{html.escape(tr('Still to do in the model'))} ({len(problems)})</h4>")
    out.append("<ul>" + "".join(
        f"<li>{html.escape(p['where'])}: {html.escape(p['message'])}</li>" for p in problems)
        + "</ul>" if problems else f"<p>{html.escape(tr('Nothing.'))}</p>")
    return "".join(out)


class ImportReportDialog(QDialog):
    def __init__(self, source: str, report: dict, problems: list, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("Conversion Report"))
        lay = QVBoxLayout(self)
        self.text = QTextBrowser()
        self.text.setHtml(report_html(source, report, problems))
        lay.addWidget(self.text)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.close)
        lay.addWidget(buttons)
        open_at_content_size(self, QSize(560, 420))
