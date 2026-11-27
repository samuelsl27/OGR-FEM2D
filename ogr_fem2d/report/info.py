# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The report of a model and of its results, as text or HTML (spec 006, RF-4,
D17), without Qt.

``report(model, opened=None)`` gives its sections, in this order:

1. the summary of the project (title, author, date, notes);
2. the analysis: its kind, the units shown and those kept, the stages;
3. the field stress, compression positive (spec 004, D6);
4. the boundaries: their kind, vertices, arcs and forced divisions;
5. the materials: E, nu, unit weight, initial loading; and the
   assignments, region by region and stage by stage;
6. the conditions and the loads, with their state in every stage;
7. the mesh: its settings, nodes and elements, the bound B and the angle it
   guarantees, the worst angles, the nodes the mesher added on the
   segments, whether its ending with arcs is proven, and its warnings; or
   that there is none, or that it is of another geometry;
8. **what decides the result** (``translate.deciding_values``, rule 12):
   every value that was not drawn, with why;
9. the results: their state (valid, stale, incomplete, cancelled, missing,
   damaged), who wrote them and with which engine, and by stage whether it
   was solved, the greatest displacement, the extremes of sigma_1 and
   sigma_3 at the points and at the nodes, and the reactions, in total and
   (with valid results) by boundary (spec 005, D14).

A section is a key, a title and its rows (a label and a value); the titles,
the labels and the fixed words are coded lines (``model/report_messages``,
spec 006 T33): the same English text, which the window says in the
reader's language (rule 2). Values are in the units the model shows
(``ogr_core.units``), with their label; the model keeps m, kN and kPa, and
the report says so. ``to_text`` and ``to_html`` say the same.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import html
from dataclasses import dataclass

import numpy as np
from ogr_core.units import Quantity as Q
from ogr_core.units.unit_system import get_system

from ogr_core.messages import as_nested

from ..model import model as md
from ..model import translate
from ..model.report_messages import part, say, word


#: the quantities whose extremes the report gives, stage by stage
EXTREMES = ("sigma_1", "sigma_3")


@dataclass(frozen=True)
class Section:
    key: str
    title: str
    rows: tuple[tuple[str, str], ...]


def _n(v) -> str:
    """A number as a person reads it: six significant figures."""
    if v is None:
        return "-"
    if isinstance(v, bool):
        return "yes" if v else "no"
    if isinstance(v, (int, np.integer)):
        return str(int(v))
    return f"{float(v):.6g}"


class _Units:
    def __init__(self, m: md.Model):
        self.system = get_system(m.units)

    def __call__(self, value, quantity: Q) -> str:
        if value is None:
            return "-"
        return f"{_n(self.system.to_user(value, quantity))} {self.system.label_for(quantity)}"

    def point(self, p) -> str:
        return "(" + ", ".join(_n(self.system.to_user(c, Q.LENGTH)) for c in p) + ")"


def _stages_row(m: md.Model, values) -> list:
    """A value per stage, each ``{stage}: {value}``, joined as before."""
    return [part("fem.report.by_stage", stage=s.id, value=v) for s, v in zip(m.stages, values)]


def _yes(flag: bool):
    return word("yes" if flag else "no")


def _summary(m) -> Section:
    s = m.summary
    return Section("summary", say("fem.report.title.summary"),
                   ((say("fem.report.title_"), s.title or "-"),
                    (say("fem.report.author"), s.author or "-"),
                    (say("fem.report.date"), s.date or "-"),
                    (say("fem.report.notes"), s.notes or "-")))


def _analysis(m, u) -> Section:
    rows = [(say("fem.report.analysis"), say("fem.report.state.value", state=word(m.analysis))),
            (say("fem.report.units_shown"), f"{m.units}"),
            (say("fem.report.units_kept"), say("fem.report.units_kept.value")),
            (say("fem.report.stages"), str(len(m.stages)))]
    rows += [(say("fem.report.stage_n", n=k + 1), f"{s.id}: {s.name or '-'}")
             for k, s in enumerate(m.stages)]
    return Section("analysis", say("fem.report.title.analysis"), tuple(rows))


def _field(m, u) -> Section:
    f = m.field
    if isinstance(f, md.ConstantField):
        rows = [(say("fem.report.field"), say("fem.report.field.constant")),
                ("sigma_1", u(f.sigma_1, Q.PRESSURE)), ("sigma_3", u(f.sigma_3, Q.PRESSURE)),
                ("sigma_z", u(f.sigma_z, Q.PRESSURE)),
                (say("fem.report.angle_sigma1"), say("fem.report.degrees", value=_n(f.angle)))]
    else:
        rows = [(say("fem.report.field"), say("fem.report.field.gravity")),
                (say("fem.report.surface"), u(f.surface, Q.LENGTH))]
        for k, s in enumerate(f.strata):
            rows.append((say("fem.report.stratum", n=k + 1),
                         say("fem.report.stratum.value", bottom=u(s.bottom, Q.LENGTH),
                             gamma=u(s.unit_weight, Q.UNIT_WEIGHT), k=_n(s.k), kz=_n(s.kz))))
    return Section("field", say("fem.report.title.field"), tuple(rows))


def _boundaries(m, u) -> Section:
    rows = []
    for b in m.boundaries:
        arcs = sum(1 for s in b.segments if s.arc is not None)
        divided = [f"{s.index}: {s.divisions}" for s in b.segments if s.divisions is not None]
        args = {"kind": word(b.kind), "closed": word("closed" if b.closed else "open"),
                "vertices": len(b.vertices), "arcs": arcs}
        text = (say("fem.report.boundary.divided", divisions="; ".join(divided), **args)
                if divided else say("fem.report.boundary", **args))
        rows.append((f"{b.id}" + (f" ({b.name})" if b.name else ""), text))
        rows.append((say("fem.report.boundary.vertices", boundary=b.id),
                     " ".join(u.point(v) for v in b.vertices)))
    return Section("boundaries", say("fem.report.title.boundaries"),
                   tuple(rows) or ((say("fem.report.title.boundaries"),
                                    say("fem.report.state.value", state=word("none"))),))


def _materials(m, u) -> Section:
    rows = []
    for mat in m.materials:
        rows.append((f"{mat.id}" + (f" ({mat.name})" if mat.name else ""),
                     say("fem.report.material.value", E=u(mat.E, Q.PRESSURE), nu=_n(mat.nu),
                         gamma=u(mat.unit_weight, Q.UNIT_WEIGHT), loading=mat.initial_loading)))
    for a in m.assignments:
        rows.append((say("fem.report.region_at", point=u.point(a.point)),
                     say("fem.report.region.value", material=a.material,
                         stages=_stages_row(m, [_yes(e) for e in a.excavated]))))
    return Section("materials", say("fem.report.title.materials"),
                   tuple(rows) or ((say("fem.report.materials"),
                                    say("fem.report.state.value", state=word("none"))),))


def _where(c, u):
    if getattr(c, "vertex", None) is not None:
        return part("fem.report.at_vertex", point=u.point(c.vertex))
    s = c.span
    if s.start is None and s.end is None:
        return part("fem.report.all_of", boundary=s.boundary)
    return part("fem.report.from_to", boundary=s.boundary, start=u.point(s.start),
                end=u.point(s.end))


def _conditions_loads(m, u) -> Section:
    rows = [(say("fem.report.default_external"), m.default_restraint)]
    for k, c in enumerate(m.conditions):
        label = (say("fem.report.condition_named", n=k, name=c.name) if c.name
                 else say("fem.report.condition", n=k))
        if c.kind == md.DISPLACEMENT:
            what = say("fem.report.imposed", where=_where(c, u), ux=u(c.ux, Q.LENGTH),
                       uy=u(c.uy, Q.LENGTH), factors=_stages_row(m, [_n(f) for f in c.factors]))
        else:
            what = say("fem.report.restraint", where=_where(c, u), kind=c.kind,
                       active=_stages_row(m, [_yes(a) for a in c.active]))
        rows.append((label, what))
    for k, ld in enumerate(m.loads):
        label = (say("fem.report.load_named", n=k, name=ld.name) if ld.name
                 else say("fem.report.load", n=k))
        angled = ld.orientation == md.ANGLE_FROM_HORIZONTAL or (
            isinstance(ld, md.DistributedLoad) and ld.orientation == md.ANGLE_TO_BOUNDARY)
        args = {"where": _where(ld, u), "orientation": ld.orientation,
                "factors": _stages_row(m, [_n(f) for f in ld.factors])}
        if angled:
            args["angle"] = _n(ld.angle)
        if isinstance(ld, md.DistributedLoad):
            what = say("fem.report.distributed_angle" if angled else "fem.report.distributed",
                       start=u(ld.start_value, Q.PRESSURE), end=u(ld.end_value, Q.PRESSURE),
                       **args)
        else:
            what = say("fem.report.point_load_angle" if angled else "fem.report.point_load",
                       force=u(ld.magnitude, Q.FORCE), **args)
        rows.append((label, what))
    return Section("conditions", say("fem.report.title.conditions"), tuple(rows))


def _mesh(m, u) -> Section:
    if m.mesh is None:
        return Section("mesh", say("fem.report.title.mesh"),
                       ((say("fem.report.mesh"), say("fem.report.mesh.none")),))
    notes = m.mesh.notes
    q = notes.get("quality", {})
    rows = []
    if m.mesh.source != translate.source_of(m):
        rows.append((say("fem.report.state"), say("fem.report.mesh.stale")))
    rows += [(say("fem.report.kind"), say("fem.report.state.value",
                                          state=word(str(notes.get("kind"))))),
             (say("fem.report.nodes_per_element"), _n(notes.get("nodes_per_element"))),
             (say("fem.report.nodes"), str(len(m.mesh.nodes))),
             (say("fem.report.elements"), str(len(m.mesh.elements))),
             (say("fem.report.bound_b"), say("fem.report.bound_b.value",
                                             b=_n(notes.get("quality_bound")),
                                             angle=_n(notes.get("angle_guaranteed")))),
             (say("fem.report.smallest_angle"),
              say("fem.report.degrees", value=_n(q.get("min_angle", {}).get("worst")))),
             (say("fem.report.largest_angle"),
              say("fem.report.degrees", value=_n(q.get("max_angle", {}).get("worst")))),
             (say("fem.report.boundary_nodes"), _n(notes.get("boundary_nodes")))]
    for added in notes.get("added_on_segments", ()):
        rows.append((say("fem.report.added_on", segment=added["segment"]),
                     " ".join(u.point(p) for p in added["points"])))
    if m.analysis == md.AXISYMMETRIC:
        # the engine restrains them itself (spec 002, D1 bis): a value that
        # decides the result and is not drawn (rule 12; spec 006, RF-20)
        on_axis = sum(1 for x, _y in m.mesh.nodes if x == 0.0)
        rows.append((say("fem.report.axis_nodes"), say("fem.report.axis_nodes.value", n=on_axis)))
    if notes.get("arc_termination_proven") is False:
        rows.append((say("fem.report.arcs"), str(notes.get("arc_unproven"))))
    rows += [(say("fem.report.warning"), w) for w in m.mesh.warnings]
    return Section("mesh", say("fem.report.title.mesh"), tuple(rows))


def _deciding(m) -> Section:
    rows = tuple((what, say("fem.report.deciding.value",
                            value=_n(value) if not isinstance(value, str) else value,
                            why=as_nested(why)))
                 for what, value, why in translate.deciding_values(m))
    return Section("deciding", say("fem.report.title.deciding"), rows)


#: the messages of the results' state, said by their code
_MESSAGES = {"no results: calculate the model": "fem.report.message.no_results",
             "the model changed after the calculation": "fem.report.message.changed"}


def _state(opened):
    state = word(opened.status)
    if not opened.message:
        return say("fem.report.state.value", state=state)
    code = _MESSAGES.get(opened.message)
    return say("fem.report.state.said", state=state,
               message=part(code) if code else opened.message)


def _results(m, u, opened) -> Section:
    title = say("fem.report.title.results")
    if opened is None:
        return Section("results", title, ((say("fem.report.state"),
                                           say("fem.report.state.value",
                                               state=word("not_opened"))),))
    rows = [(say("fem.report.state"), _state(opened))]
    if opened.other_version:
        rows.append((say("fem.report.written_by"), opened.other_version))
    try:
        r = opened.read_anyway()
    except Exception:                                          # missing, damaged
        return Section("results", title, tuple(rows))
    from ..results import queries
    h = r.header
    rows += [(say("fem.report.engine"), h.engine_variant),
             (say("fem.report.kept_as"), f"{h.units_stored}; {h.sign_convention}")]
    valid = opened.status == "valid"
    for k in range(r.n_stages):
        view = queries.View(r, k)
        info = view.info
        label = part("fem.report.stage_named", stage=info["id"], name=info["name"]) \
            if info["name"] else part("fem.report.stage", stage=info["id"])
        s = queries.summary(view, m if valid else None, EXTREMES)
        rows.append((say("fem.report.state.value", state=label),
                     say("fem.report.stage.value",
                         solved=word("solved" if info["solved"] else "not_solved"),
                         u=u(s.max_displacement, Q.LENGTH), node=s.max_displacement_node)))
        for e in s.extremes:
            rows.append((say("fem.report.extreme", stage=label, quantity=e.quantity,
                             at=word(e.at)),
                         say("fem.report.extreme.value", max=u(e.maximum, Q.PRESSURE),
                             max_at=u.point(e.max_where), min=u(e.minimum, Q.PRESSURE),
                             min_at=u.point(e.min_where))))
        rows.append((say("fem.report.reactions", stage=label),
                     say("fem.report.reactions.value", rx=u(s.reactions[0], Q.FORCE),
                         ry=u(s.reactions[1], Q.FORCE))))
        for bid, rx, ry in s.reactions_by_boundary:
            rows.append((say("fem.report.reactions_on", stage=label, boundary=bid),
                         f"({u(rx, Q.FORCE)}, {u(ry, Q.FORCE)})"))
    return Section("results", title, tuple(rows))


def report(m: md.Model, opened=None) -> tuple[Section, ...]:
    """The sections of the report of ``m`` and, with ``opened`` (what
    ``results.calculate.open_results`` gives), of its results."""
    u = _Units(m)
    return (_summary(m), _analysis(m, u), _field(m, u), _boundaries(m, u), _materials(m, u),
            _conditions_loads(m, u), _mesh(m, u), _deciding(m), _results(m, u, opened))


def decided(m: md.Model) -> tuple[Section, Section]:
    """The mesh and what decides the result, without the results: what the
    interpretation shows beside a field (spec 006, RF-20)."""
    return _mesh(m, _Units(m)), _deciding(m)


def to_text(sections) -> str:
    out = []
    for s in sections:
        out += [s.title, "-" * len(s.title)]
        width = max((len(label) for label, _ in s.rows), default=0)
        out += [f"{label.ljust(width)}  {value}" for label, value in s.rows]
        out.append("")
    return "\n".join(out)


def to_html(sections) -> str:
    e = html.escape
    out = ['<!DOCTYPE html>', '<html><head><meta charset="utf-8"><title>OGR FEM2D</title></head>',
           "<body>"]
    for s in sections:
        out.append(f'<h2 id="{e(s.key)}">{e(s.title)}</h2>')
        out.append("<table>")
        out += [f"<tr><th>{e(label)}</th><td>{e(value)}</td></tr>" for label, value in s.rows]
        out.append("</table>")
    out.append("</body></html>")
    return "\n".join(out)
