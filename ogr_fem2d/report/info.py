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
the labels and the fixed words are the English text that the interface
passes through ``tr()`` (rule 2). Values are in the units the model shows
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

from ..model import model as md
from ..model import translate


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


def _stages_row(m: md.Model, values) -> str:
    return ", ".join(f"{s.id}: {v}" for s, v in zip(m.stages, values))


def _summary(m) -> Section:
    s = m.summary
    return Section("summary", "Project summary",
                   (("Title", s.title or "-"), ("Author", s.author or "-"),
                    ("Date", s.date or "-"), ("Notes", s.notes or "-")))


def _analysis(m, u) -> Section:
    rows = [("Analysis", m.analysis), ("Units shown", f"{m.units}"),
            ("Units kept", "m, kN, kPa, kN/m3 (the values do not change with the units shown)"),
            ("Stages", str(len(m.stages)))]
    rows += [(f"Stage {k + 1}", f"{s.id}: {s.name or '-'}") for k, s in enumerate(m.stages)]
    return Section("analysis", "Analysis", tuple(rows))


def _field(m, u) -> Section:
    f = m.field
    if isinstance(f, md.ConstantField):
        rows = [("Field stress", "constant (compression positive)"),
                ("sigma_1", u(f.sigma_1, Q.PRESSURE)), ("sigma_3", u(f.sigma_3, Q.PRESSURE)),
                ("sigma_z", u(f.sigma_z, Q.PRESSURE)), ("Angle of sigma_1 from x", f"{_n(f.angle)} deg")]
    else:
        rows = [("Field stress", "gravitational, horizontal strata (compression positive)"),
                ("Surface", u(f.surface, Q.LENGTH))]
        for k, s in enumerate(f.strata):
            rows.append((f"Stratum {k + 1}",
                         f"down to {u(s.bottom, Q.LENGTH)}, unit weight "
                         f"{u(s.unit_weight, Q.UNIT_WEIGHT)}, K {_n(s.k)}, Kz {_n(s.kz)}"))
    return Section("field", "Field stress", tuple(rows))


def _boundaries(m, u) -> Section:
    rows = []
    for b in m.boundaries:
        arcs = sum(1 for s in b.segments if s.arc is not None)
        divided = [f"{s.index}: {s.divisions}" for s in b.segments if s.divisions is not None]
        text = (f"{b.kind}, {'closed' if b.closed else 'open'}, {len(b.vertices)} vertices, "
                f"{arcs} arcs" + (f", divisions {'; '.join(divided)}" if divided else ""))
        rows.append((f"{b.id}" + (f" ({b.name})" if b.name else ""), text))
        rows.append((f"{b.id}: vertices", " ".join(u.point(v) for v in b.vertices)))
    return Section("boundaries", "Boundaries", tuple(rows) or (("Boundaries", "none"),))


def _materials(m, u) -> Section:
    rows = []
    for mat in m.materials:
        rows.append((f"{mat.id}" + (f" ({mat.name})" if mat.name else ""),
                     f"E {u(mat.E, Q.PRESSURE)}, nu {_n(mat.nu)}, unit weight "
                     f"{u(mat.unit_weight, Q.UNIT_WEIGHT)}, initial loading {mat.initial_loading}"))
    for a in m.assignments:
        rows.append((f"Region at {u.point(a.point)}",
                     f"{a.material}; excavated: {_stages_row(m, ['yes' if e else 'no' for e in a.excavated])}"))
    return Section("materials", "Materials and assignments", tuple(rows) or (("Materials", "none"),))


def _where(c, u) -> str:
    if getattr(c, "vertex", None) is not None:
        return f"vertex {u.point(c.vertex)}"
    s = c.span
    if s.start is None and s.end is None:
        return f"all of {s.boundary}"
    return f"{s.boundary} from {u.point(s.start)} to {u.point(s.end)}"


def _conditions_loads(m, u) -> Section:
    rows = [("Default of the external boundary", m.default_restraint)]
    for k, c in enumerate(m.conditions):
        label = f"Condition {k}" + (f" ({c.name})" if c.name else "")
        if c.kind == md.DISPLACEMENT:
            what = (f"imposed ux {u(c.ux, Q.LENGTH)}, uy {u(c.uy, Q.LENGTH)}; factors: "
                    f"{_stages_row(m, [_n(f) for f in c.factors])}")
        else:
            what = f"{c.kind}; active: {_stages_row(m, ['yes' if a else 'no' for a in c.active])}"
        rows.append((label, f"{_where(c, u)}: {what}"))
    for k, ld in enumerate(m.loads):
        label = f"Load {k}" + (f" ({ld.name})" if ld.name else "")
        if isinstance(ld, md.DistributedLoad):
            what = (f"distributed {ld.orientation}, from {u(ld.start_value, Q.PRESSURE)} to "
                    f"{u(ld.end_value, Q.PRESSURE)}")
        else:
            what = f"point {ld.orientation}, {u(ld.magnitude, Q.FORCE)} (per metre out of plane)"
        if ld.orientation == md.ANGLE_FROM_HORIZONTAL or (
                isinstance(ld, md.DistributedLoad) and ld.orientation == md.ANGLE_TO_BOUNDARY):
            what += f", angle {_n(ld.angle)} deg"
        rows.append((label, f"{_where(ld, u)}: {what}; factors: "
                            f"{_stages_row(m, [_n(f) for f in ld.factors])}"))
    return Section("conditions", "Conditions and loads", tuple(rows))


def _mesh(m, u) -> Section:
    if m.mesh is None:
        return Section("mesh", "Mesh", (("Mesh", "none: Mesh > Mesh"),))
    notes = m.mesh.notes
    q = notes.get("quality", {})
    rows = []
    if m.mesh.source != translate.source_of(m):
        rows.append(("State", "of another geometry or other settings: mesh again before "
                              "calculating"))
    rows += [("Kind", str(notes.get("kind"))),
             ("Nodes per element", _n(notes.get("nodes_per_element"))),
             ("Nodes", str(len(m.mesh.nodes))), ("Elements", str(len(m.mesh.elements))),
             ("Bound B", f"{_n(notes.get('quality_bound'))}, guarantees angles above "
                         f"{_n(notes.get('angle_guaranteed'))} deg"),
             ("Smallest angle", f"{_n(q.get('min_angle', {}).get('worst'))} deg"),
             ("Largest angle", f"{_n(q.get('max_angle', {}).get('worst'))} deg"),
             ("Nodes on the excavations (or on the external, without any)",
              _n(notes.get("boundary_nodes")))]
    for added in notes.get("added_on_segments", ()):
        rows.append((f"Added on {added['segment']}",
                     " ".join(u.point(p) for p in added["points"])))
    if notes.get("arc_termination_proven") is False:
        rows.append(("Arcs", str(notes.get("arc_unproven"))))
    rows += [("Warning", w) for w in m.mesh.warnings]
    return Section("mesh", "Mesh", tuple(rows))


def _deciding(m) -> Section:
    rows = tuple((what, f"{_n(value) if not isinstance(value, str) else value} ({why})")
                 for what, value, why in translate.deciding_values(m))
    return Section("deciding", "What decides the result (rule 12)", rows)


def _results(m, u, opened) -> Section:
    if opened is None:
        return Section("results", "Results", (("State", "not opened"),))
    rows = [("State", opened.status + (f": {opened.message}" if opened.message else ""))]
    if opened.other_version:
        rows.append(("Written by", opened.other_version))
    try:
        r = opened.read_anyway()
    except Exception:                                          # missing, damaged
        return Section("results", "Results", tuple(rows))
    from ..results import queries
    h = r.header
    rows += [("Engine", h.engine_variant), ("Kept as", f"{h.units_stored}; {h.sign_convention}")]
    valid = opened.status == "valid"
    for k in range(r.n_stages):
        view = queries.View(r, k)
        info = view.info
        label = f"Stage {info['id']}" + (f" ({info['name']})" if info["name"] else "")
        s = queries.summary(view, m if valid else None, EXTREMES)
        rows.append((label, ("solved" if info["solved"] else "not solved (it changes nothing)")
                     + f"; greatest displacement {u(s.max_displacement, Q.LENGTH)} at node "
                       f"{s.max_displacement_node}"))
        for e in s.extremes:
            rows.append((f"{label}: {e.quantity} at the {e.at}",
                         f"max {u(e.maximum, Q.PRESSURE)} at {u.point(e.max_where)}, "
                         f"min {u(e.minimum, Q.PRESSURE)} at {u.point(e.min_where)}"))
        rows.append((f"{label}: reactions", f"({u(s.reactions[0], Q.FORCE)}, "
                                            f"{u(s.reactions[1], Q.FORCE)}) per metre out of plane"))
        for bid, rx, ry in s.reactions_by_boundary:
            rows.append((f"{label}: reactions on {bid}",
                         f"({u(rx, Q.FORCE)}, {u(ry, Q.FORCE)})"))
    return Section("results", "Results", tuple(rows))


def report(m: md.Model, opened=None) -> tuple[Section, ...]:
    """The sections of the report of ``m`` and, with ``opened`` (what
    ``results.calculate.open_results`` gives), of its results."""
    u = _Units(m)
    return (_summary(m), _analysis(m, u), _field(m, u), _boundaries(m, u), _materials(m, u),
            _conditions_loads(m, u), _mesh(m, u), _deciding(m), _results(m, u, opened))


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
