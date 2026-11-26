# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The fingerprints of a model (spec 004, RF-16, D12; ADR-0003).

A fingerprint is the SHA-256 (FIPS 180-4, ``hashlib``) of a canonical JSON:
keys sorted, fixed separators, ASCII, no NaN or infinity, floats as Python
writes them (the shortest text that reads back to the same number).

* ``model_fingerprint``: what changes the result and nothing else. The
  file's content (``ogr_file.to_dict``) without the summary, the unit system
  shown (D5: the values do not depend on it), the names and colours, the
  notes and warnings of the mesh (they say how the mesh was made; the mesh
  itself, its nodes, elements and regions, is in; the fingerprint of the
  mesher input it was made from is not, as that input is the model's own
  and the mesh is in), and the ids: a boundary,
  a material and a stage are named by their place (their order is part of
  the model), so renaming an id everywhere does not move it. A refinement
  window is taken in one form (``mesh.geometry.canonical_polygon``): the
  same rectangle written from another corner, or the other way round, is
  the same model (spec 006, T29). The results of
  spec 005 will carry it (ADR-0003).
* ``document_fingerprint``: everything in the file but ``written_by``, which
  is who wrote it, not what it holds.
* ``digest``: the fingerprint of any value made of dataclasses, tuples,
  lists, dictionaries and numbers (the mesher input of a stored mesh, D3).

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import dataclasses
import hashlib
import json


def _plain(value):
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return {f.name: _plain(getattr(value, f.name)) for f in dataclasses.fields(value)}
    if isinstance(value, (list, tuple)):
        return [_plain(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _plain(v) for k, v in value.items()}
    return value


def canonical(value) -> str:
    return json.dumps(_plain(value), sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False)


def digest(value) -> str:
    return hashlib.sha256(canonical(value).encode("ascii")).hexdigest()


#: what the model's fingerprint leaves out, by section
_NAMES = {"boundaries": ("name",), "materials": ("name", "color"), "stages": (),
          "conditions": ("name",), "loads": ("name",)}


def _by_place(d: dict) -> dict:
    """The content of a file with its ids replaced by places."""
    stages = [s["id"] for s in d["stages"]]
    boundary = {b["id"]: k for k, b in enumerate(d["boundaries"])}
    material = {x["id"]: k for k, x in enumerate(d["materials"])}

    def per_stage(value):
        return None if value is None else [value[s] for s in stages]

    def span(s):
        return None if s is None else {**s, "boundary": boundary.get(s["boundary"], s["boundary"])}

    d["stages"] = len(stages)
    for b in d["boundaries"]:
        b.pop("id")
    for x in d["materials"]:
        x.pop("id")
    for a in d["assignments"]:
        a["material"] = material.get(a["material"], a["material"])
        a["excavated"] = per_stage(a["excavated"])
    for c in d["conditions"]:
        c["span"] = span(c["span"])
        c["active"], c["factors"] = per_stage(c["active"]), per_stage(c["factors"])
    for ld in d["loads"]:
        if "span" in ld:
            ld["span"] = span(ld["span"])
        ld["factors"] = per_stage(ld["factors"])
    return d


def model_fingerprint(m) -> str:
    from . import ogr_file
    d = ogr_file.to_dict(m)
    for key in ("format", "format_version", "written_by", "summary", "units"):
        d.pop(key)
    for section, keys in _NAMES.items():
        for item in d[section]:
            for key in keys:
                item.pop(key)
    if d["mesh"] is not None:
        d["mesh"].pop("notes")
        d["mesh"].pop("warnings")
        d["mesh"].pop("source")
    from ..mesh.geometry import canonical_polygon
    for w in d["mesh_settings"]["windows"]:
        w["polygon"] = [list(p) for p in canonical_polygon(w["polygon"])]
    return digest(_by_place(d))


def document_fingerprint(m) -> str:
    from . import ogr_file
    d = ogr_file.to_dict(m)
    d.pop("written_by")
    return digest(d)
