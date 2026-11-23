# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.0.9 (spec 004, T11) — undo and redo of the edits of a model (RF-15), on
the core's ``CommandStack``.

Invariants protected:

* **undo puts back the model before, redo the one after**: a sequence of
  edits (a stage inserted, a material assigned, a load's factor, a mesh)
  undone to the start gives the first model, the same object and the same
  fingerprint, and redone to the end the last one;
* **an edit that changes nothing leaves no step**;
* **a new edit after undoing drops what could be redone**;
* **nothing to undo or redo does nothing**;
* **a refused edit leaves the document as it was** (RF-4 inside an edit).
"""
from __future__ import annotations

from dataclasses import replace

import _models
from ogr_fem2d.model import fingerprint as fp
from ogr_fem2d.model import history, stages, translate
from ogr_fem2d.model import model as md

S = _models.strip()


def _edits(doc):
    doc.edit(lambda m: stages.insert_stage(m, 1, "2", "Carga"), "Insert stage")
    doc.edit(lambda m: stages.set_load_factor(m, 0, "2", 3.0), "Load factor")
    doc.edit(lambda m: replace(m, materials=(replace(m.materials[0], E=4.0e4),)), "E")
    doc.edit(translate.mesh, "Mesh")


class TestUndoRedo:
    def test_to_the_start_and_back(self):
        doc = history.Document(S)
        models = [doc.model]
        for step in (lambda m: stages.insert_stage(m, 1, "2", "Carga"),
                     lambda m: stages.set_load_factor(m, 0, "2", 3.0),
                     lambda m: replace(m, materials=(replace(m.materials[0], E=4.0e4),)),
                     translate.mesh):
            assert doc.edit(step)
            models.append(doc.model)
        for k in range(4, 0, -1):
            assert doc.undo()
            assert doc.model is models[k - 1]
        assert fp.document_fingerprint(doc.model) == fp.document_fingerprint(S)
        for k in range(1, 5):
            assert doc.redo()
            assert doc.model is models[k]
        assert doc.model.mesh is not None and doc.model.loads[0].factors == (1.0, 3.0)

    def test_an_edit_that_changes_nothing_leaves_no_step(self):
        doc = history.Document(S)
        assert not doc.edit(lambda m: replace(m))
        assert not doc.history.can_undo

    def test_a_new_edit_drops_the_redo(self):
        doc = history.Document(S)
        _edits(doc)
        doc.undo()
        doc.undo()
        assert doc.history.can_redo
        doc.edit(lambda m: replace(m, default_restraint=md.Y))
        assert not doc.history.can_redo

    def test_nothing_to_undo_or_redo(self):
        doc = history.Document(S)
        assert not doc.undo() and not doc.redo() and doc.model is S

    def test_a_refused_edit_leaves_the_document(self):
        doc = history.Document(_models.with_stages(_models.tunnel(), 2))
        before = doc.model
        try:
            doc.edit(lambda m: stages.set_excavated(m, (0.0, 0.0), "2", False))
        except md.ModelError:
            pass
        else:
            raise AssertionError("an excavated region came back")
        assert doc.model is before and not doc.history.can_undo
