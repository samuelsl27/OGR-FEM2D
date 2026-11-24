# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.0.12 (spec 006, T2) — the edits of the boundaries and of their vertices,
as pure functions (RF-1, RF-7, RF-8).

Invariants protected:

* **a new boundary is as its kind asks**: closed by default when it is an
  external or an excavation, open otherwise; its id is the first free one of
  its kind; it is refused, with the rule and the boundary named, when it
  breaks a rule of its own (too few vertices, a repeated one, an open
  external, x < 0 in axisymmetry) or when its id is taken. A model being
  drawn (no external yet) takes it: the edits do not ask the whole model to
  be valid;
* **shared geometry stays shared**: moving a vertex moves it in every
  boundary that has it, and every span end, vertex condition and point load
  that names it follows; a vertex inserted on a side goes into every
  boundary that has that side; translating a boundary that shares a vertex,
  or deleting a vertex next to a shared side, is refused naming the other;
* **nothing changes shape or goes away unasked**: moving or deleting the end
  of an arc is refused; a side with forced divisions is not split; deleting
  a boundary or a vertex that conditions or loads depend on is refused,
  unless the boundary is deleted with its dependents (rule 7: the option
  moves the result);
* **inserting a vertex and deleting it is the identity**, segment attributes
  renumbered and back, also on the closing side of a closed boundary; an arc
  split keeps its centre in both halves and the model stays valid;
* **an arc is checked when it is put**: off its circle or with the centre on
  the chord, refused;
* **an edit never changes the model it was given**, and through
  ``Document.edit`` it is one step to undo.
"""
from __future__ import annotations

import math
from dataclasses import replace

import _models
from ogr_fem2d.engine.reference.quadrature import AXISYMMETRIC
from ogr_fem2d.model import edit
from ogr_fem2d.model import model as md
from ogr_fem2d.model.history import Document

SQUARE = ((0.0, 0.0), (4.0, 0.0), (4.0, 3.0), (0.0, 3.0))


def _refused(fn, rule: str, *words: str):
    """``fn()`` raises ModelError whose first problem has ``rule`` and names
    every word of ``words``."""
    try:
        fn()
    except md.ModelError as err:
        p = err.problems[0]
        assert p.rule == rule, (p.rule, rule, str(err))
        text = f"{p.where} {p.message}"
        for w in words:
            assert w in text, (w, text)
    else:
        raise AssertionError(f"accepted; expected a refusal with rule {rule!r}")


class TestAddBoundary:
    def test_closed_as_its_kind_asks_and_ids_of_its_kind(self):
        m = edit.add_boundary(md.Model(), md.EXTERNAL, SQUARE)
        m = edit.add_boundary(m, md.MATERIAL, ((0.0, 1.0), (4.0, 1.0)))
        m = edit.add_boundary(m, md.MATERIAL, ((0.0, 2.0), (4.0, 2.0)))
        ext, mat1, mat2 = m.boundaries
        assert (ext.id, ext.closed) == ("ext1", True)
        assert (mat1.id, mat1.closed, mat2.id) == ("mat1", False, "mat2")
        assert all(isinstance(c, float) for v in ext.vertices for c in v)

    def test_a_model_being_drawn_takes_it(self):
        # no external boundary yet: the model is not valid, the edit is
        m = edit.add_boundary(md.Model(), md.EXCAVATION, SQUARE)
        assert "external" in [p.rule for p in md.problems(m)]
        assert m.boundaries[0].id == "exc1"

    def test_its_own_rules_refuse_it(self):
        _refused(lambda: edit.add_boundary(md.Model(), md.EXTERNAL, SQUARE[:2]), "boundary",
                 "ext1", "too few")
        _refused(lambda: edit.add_boundary(md.Model(), md.MATERIAL, SQUARE + SQUARE[:1]),
                 "boundary", "repeated")
        _refused(lambda: edit.add_boundary(md.Model(), md.EXTERNAL, SQUARE, closed=False),
                 "boundary", "must be closed")
        axi = md.Model(analysis=AXISYMMETRIC)
        _refused(lambda: edit.add_boundary(axi, md.EXTERNAL, ((-1.0, 0.0), (1.0, 0.0), (1.0, 1.0))),
                 "left_of_axis", "x = r < 0")
        m = edit.add_boundary(md.Model(), md.EXTERNAL, SQUARE)
        _refused(lambda: edit.add_boundary(m, md.MATERIAL, ((0.0, 1.0), (4.0, 1.0)),
                                           boundary_id="ext1"), "boundary_id", "repeated")

    def test_one_step_to_undo(self):
        doc = Document()
        before = doc.model
        assert doc.edit(lambda m: edit.add_boundary(m, md.EXTERNAL, SQUARE), "add")
        assert len(doc.model.boundaries) == 1
        assert doc.undo() and doc.model == before
        assert doc.redo() and doc.model.boundaries[0].id == "ext1"


class TestBoundaryEdits:
    def test_delete_with_its_dependents_or_not(self):
        m = _models.layers()
        _refused(lambda: edit.delete_boundary(m, "ext"), "in_use", "condition 0", "condition 2")
        out = edit.delete_boundary(m, "ext", with_dependents=True)
        assert [b.id for b in out.boundaries] == ["contact"]
        assert out.conditions == ()
        # one with nothing on it goes alone
        out = edit.delete_boundary(m, "contact")
        assert [b.id for b in out.boundaries] == ["ext"] and out.conditions == m.conditions
        _refused(lambda: edit.delete_boundary(m, "nope"), "boundary_unknown", "'nope'", "'ext'")

    def test_the_option_moves_the_result(self):
        # rule 7: with and without the dependents, two different models
        m = replace(_models.layers(), conditions=())
        m = replace(m, conditions=(md.Condition(md.X, md.Span("contact"), active=(True,)),))
        _refused(lambda: edit.delete_boundary(m, "contact"), "in_use", "condition 0")
        assert edit.delete_boundary(m, "contact", with_dependents=True).conditions == ()

    def test_close_open_and_kind(self):
        m = edit.add_boundary(md.Model(), md.MATERIAL, SQUARE)
        assert not m.boundaries[0].closed
        closed = edit.set_closed(m, "mat1", True)
        assert closed.boundaries[0].n_segments == 4
        arc = edit.set_arc(closed, "mat1", 3, (2.0, 1.5))
        assert arc.boundaries[0].attr(3).arc == (2.0, 1.5)
        opened = edit.set_closed(arc, "mat1", False)
        assert opened.boundaries[0].segments == ()          # the last side went
        _refused(lambda: edit.set_boundary_kind(m, "mat1", md.EXTERNAL), "boundary",
                 "must be closed")
        assert edit.set_boundary_kind(closed, "mat1", md.EXCAVATION).boundaries[0].kind == \
            md.EXCAVATION
        ext = _models.tunnel()
        _refused(lambda: edit.set_closed(ext, "ext", False), "boundary", "must be closed")

    def test_translate_moves_arcs_and_references(self):
        m = _models.tunnel()
        m = replace(m, conditions=(md.Condition(md.X, vertex=(1.0, 0.0), active=(True,)),))
        out = edit.translate_boundary(m, "hole", 2.0, 1.0)
        hole = out.boundary("hole")
        assert hole.vertices[0] == (3.0, 1.0)
        assert all(s.arc == (2.0, 1.0) for s in hole.segments)
        assert out.conditions[0].vertex == (3.0, 1.0)
        assert md.problems(replace(out, assignments=(
            m.assignments[0], replace(m.assignments[1], point=(2.0, 1.0))))) == []

    def test_translate_refuses_shared_vertices(self):
        _refused(lambda: edit.translate_boundary(_models.layers(), "contact", 0.0, 1.0),
                 "shared_vertex", "'contact'", "'ext'")


class TestVertices:
    def test_move_a_shared_vertex_everywhere(self):
        m = _models.layers()                       # contact at y = -4, shared with ext
        out = edit.move_vertex(m, (0.0, -4.0), (0.0, -5.0))
        assert (0.0, -5.0) in out.boundary("ext").vertices
        assert out.boundary("contact").vertices[0] == (0.0, -5.0)
        assert (0.0, -4.0) not in {v for b in out.boundaries for v in b.vertices}
        assert md.problems(out) == []

    def test_references_follow_the_vertex(self):
        m = _models.strip()                        # the strip load ends at (1, 0)
        m = replace(m, loads=m.loads + (md.PointLoad((1.0, 0.0), 5.0, factors=(1.0,)),))
        out = edit.move_vertex(m, (1.0, 0.0), (2.0, 0.0))
        assert out.loads[0].span.start == (2.0, 0.0)
        assert out.loads[1].vertex == (2.0, 0.0)
        assert md.problems(out) == []

    def test_move_refusals(self):
        m = _models.tunnel()
        _refused(lambda: edit.move_vertex(m, (1.0, 0.0), (1.5, 0.0)), "arc_vertex", "'hole'",
                 "arc")
        _refused(lambda: edit.move_vertex(m, (10.0, 10.0), (-10.0, 10.0)), "vertex_taken")
        _refused(lambda: edit.move_vertex(m, (7.0, 7.0), (8.0, 8.0)), "vertex_unknown", "(7.0, 7.0)")

    def test_insert_on_an_arc_keeps_its_centre(self):
        m = _models.tunnel()
        c = math.sqrt(0.5)
        out = edit.insert_vertex(m, "hole", 0, (c, c))
        hole = out.boundary("hole")
        assert hole.vertices[:3] == ((1.0, 0.0), (c, c), (0.0, 1.0))
        assert [(s.index, s.arc) for s in hole.segments] == [(k, (0.0, 0.0)) for k in range(5)]
        assert md.problems(out) == []

    def test_insert_into_every_boundary_with_the_side(self):
        m = _models.tunnel()
        bottom = md.Boundary("base", md.MATERIAL, ((-10.0, -10.0), (10.0, -10.0)), False)
        m = replace(m, boundaries=m.boundaries + (bottom,))
        out = edit.insert_vertex(m, "ext", 0, (0.0, -10.0))
        assert out.boundary("ext").vertices[1] == (0.0, -10.0)
        assert out.boundary("base").vertices == ((-10.0, -10.0), (0.0, -10.0), (10.0, -10.0))

    def test_insert_refusals(self):
        m = _models.strip()                        # segment 3, under the strip, divided
        m = edit.set_divisions(m, "ext", 3, 8)
        _refused(lambda: edit.insert_vertex(m, "ext", 3, (0.5, 0.0)), "divisions_vertex",
                 "segment 3")
        _refused(lambda: edit.insert_vertex(m, "ext", 0, (5.0, -19.0)), "not_on_segment",
                 "segment 0")
        _refused(lambda: edit.insert_vertex(m, "ext", 0, (0.0, -20.0)), "not_on_segment")
        _refused(lambda: edit.insert_vertex(m, "ext", 0, (25.0, -20.0)), "not_on_segment")
        _refused(lambda: edit.insert_vertex(m, "ext", 9, (5.0, -20.0)), "segment_unknown")

    def test_insert_then_delete_is_the_identity(self):
        m = edit.set_divisions(_models.strip(), "ext", 3, 8)
        # a straight side before the divided one: the attribute goes 3 -> 4 -> 3
        out = edit.insert_vertex(m, "ext", 1, (20.0, -10.0))
        assert out.boundary("ext").attr(4).divisions == 8
        assert edit.delete_vertex(out, "ext", 2) == m
        # the closing side of a closed boundary
        out = edit.insert_vertex(m, "ext", 4, (0.0, -10.0))
        assert out.boundary("ext").vertices[-1] == (0.0, -10.0)
        assert edit.delete_vertex(out, "ext", 5) == m

    def test_delete_the_first_vertex_of_a_closed_boundary(self):
        m = edit.add_boundary(md.Model(), md.EXTERNAL, SQUARE + ((0.0, 1.5),))
        m = edit.set_divisions(m, "ext1", 2, 5)
        out = edit.delete_vertex(m, "ext1", 0)
        b = out.boundary("ext1")
        assert b.vertices == SQUARE[1:] + ((0.0, 1.5),)
        assert [(s.index, s.divisions) for s in b.segments] == [(1, 5)]

    def test_delete_refusals(self):
        _refused(lambda: edit.delete_vertex(_models.tunnel(), "hole", 0), "arc_vertex")
        _refused(lambda: edit.delete_vertex(_models.strip(), "ext", 3), "in_use", "load 0")
        _refused(lambda: edit.delete_vertex(_models.strip(), "ext", 2), "in_use", "condition 0",
                 "condition 1")
        m = _models.tunnel()
        bottom = md.Boundary("base", md.MATERIAL, ((-10.0, -10.0), (10.0, -10.0)), False)
        m = replace(m, boundaries=m.boundaries + (bottom,))
        _refused(lambda: edit.delete_vertex(m, "ext", 1), "shared_side", "'base'")
        tri = edit.add_boundary(md.Model(), md.EXTERNAL, SQUARE[:3])
        _refused(lambda: edit.delete_vertex(tri, "ext1", 0), "boundary", "too few")
        _refused(lambda: edit.delete_vertex(tri, "ext1", 3), "vertex_unknown")


class TestSegments:
    def test_arcs_are_checked_when_put(self):
        m = edit.add_boundary(md.Model(), md.EXTERNAL, SQUARE)
        _refused(lambda: edit.set_arc(m, "ext1", 0, (1.0, 5.0)), "arc", "not on one circle")
        _refused(lambda: edit.set_arc(m, "ext1", 0, (2.0, 0.0)), "arc", "on the chord")
        out = edit.set_arc(m, "ext1", 0, (2.0, 1.0))
        assert edit.set_arc(out, "ext1", 0, None) == m

    def test_arc_and_divisions_together(self):
        m = edit.add_boundary(md.Model(), md.EXTERNAL, SQUARE)
        out = edit.set_divisions(edit.set_arc(m, "ext1", 0, (2.0, 1.0)), "ext1", 0, 6)
        assert out.boundaries[0].segments == (md.SegmentAttr(0, (2.0, 1.0), 6),)
        back = edit.set_divisions(edit.set_arc(out, "ext1", 0, None), "ext1", 0, None)
        assert back == m
        _refused(lambda: edit.set_divisions(m, "ext1", 0, 0), "segment_attr", "divisions")


class TestValues:
    def test_no_edit_changes_what_it_was_given(self):
        m = _models.layers()
        copy = replace(m)
        edit.move_vertex(m, (0.0, -4.0), (0.0, -5.0))
        edit.delete_boundary(m, "ext", with_dependents=True)
        edit.insert_vertex(m, "contact", 0, (10.0, -4.0))
        edit.translate_boundary(_models.tunnel(), "hole", 1.0, 0.0)
        assert m == copy
