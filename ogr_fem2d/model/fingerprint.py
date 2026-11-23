# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The fingerprints of a model (spec 004, RF-16, D12; ADR-0003).

A fingerprint is the SHA-256 (FIPS 180-4, ``hashlib``) of a canonical JSON:
keys sorted, fixed separators, ASCII, no NaN or infinity, floats as Python
writes them (the shortest text that reads back to the same number).

* ``model_fingerprint``: what changes the result and nothing else. The
  file's content (``ogr_file.to_dict``) without the summary, the unit system
  shown (D5: the values do not depend on it), the names and colours, and the
  notes and warnings of the mesh (they say how the mesh was made; the mesh
  itself, its nodes, elements and regions, is in). The results of spec 005
  will carry it (ADR-0003).
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
_NAMES = {"boundaries": ("name",), "materials": ("name", "color"), "stages": ("name",),
          "conditions": ("name",), "loads": ("name",)}


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
    return digest(d)


def document_fingerprint(m) -> str:
    from . import ogr_file
    d = ogr_file.to_dict(m)
    d.pop("written_by")
    return digest(d)
