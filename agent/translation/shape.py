"""`shape`: what a person may fill, read off a node shape — the fields a sayable or an askable declares, the
schema each is offered to the model under, and the term a value the model filled is taken as.

**A FIELD IS A PROPERTY SHAPE.** `sh:path` names it, a `sh:datatype` says the literal it takes or a `sh:class`
the thing of the world it is chosen from, `sh:minCount` whether it must be filled and `sh:description` what the
model is told. A field of a class is offered as the labels of the instances the world states of it, by
`rdfs:label` where there is one and by local name where not, and taken back as the IRI; a label the world does
not state is no value. A sayable's fields are what a statement carries; an askable's are what its select is
asked with (knowledge/domain/speech/sayable.md, knowledge/domain/speech/askable.md).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import pyoxigraph as ox

from agent.ontology import BELIEF, local_of
from agent.store import graphs_of, rows

XSD = "http://www.w3.org/2001/XMLSchema#"
#  THE TOOL THE MODEL CALLS WHERE NOTHING FITS, beside the sayables and the askables.
NOTHING = "nothing_fits"

_FIELDS_Q = """
SELECT ?path ?datatype ?class ?min ?description WHERE {
  $shape sh:property ?p . ?p sh:path ?path .
  OPTIONAL { ?p sh:datatype ?datatype } OPTIONAL { ?p sh:class ?class }
  OPTIONAL { ?p sh:minCount ?min } OPTIONAL { ?p sh:description ?description } } ORDER BY ?path"""
_CHOICES_Q = """
SELECT ?i ?label WHERE { ?i a $class . OPTIONAL { ?i rdfs:label ?label } } ORDER BY ?i"""


@dataclass(frozen=True)
class Field:
    path: str
    datatype: str | None
    cls: str | None
    required: bool
    description: str
    #  THE CHOICES a field of a class takes: each instance's label, and the IRI it stands for.
    choices: tuple[tuple[str, str], ...] = ()

    @property
    def name(self) -> str:
        return local_of(self.path)


def fields_of(store: ox.Store, shape: str, graphs) -> tuple[Field, ...]:
    """The fields `shape` declares in `graphs`, each of a class with the choices the world states."""
    stated = graphs_of(store, BELIEF, common=True)
    out = []
    for f in rows(store, _FIELDS_Q, graphs, shape=shape):
        choices = tuple((r.get("label") or local_of(r["i"]), r["i"])
                        for r in rows(store, _CHOICES_Q, stated, **{"class": f["class"]})) if f.get("class") else ()
        out.append(Field(f["path"], f.get("datatype"), f.get("class"), int(f.get("min") or 0) > 0,
                         f.get("description") or "", choices))
    return tuple(out)


def schema_of(field: Field) -> dict:
    """The JSON schema of one field: by its datatype, or the choices of its class."""
    if field.choices:
        return {"type": "string", "enum": [label for label, _ in field.choices], "description": field.description}
    kind = local_of(field.datatype) if field.datatype else "string"
    if kind in ("integer", "int", "long"):
        out: dict = {"type": "integer"}
    elif kind in ("decimal", "double", "float"):
        out = {"type": "number"}
    elif kind == "boolean":
        out = {"type": "boolean"}
    else:
        out = {"type": "string"}
    if kind == "dateTime":
        out["description"] = (field.description + "; " if field.description else "") + "an instant, ISO 8601 with its offset"
    elif field.description:
        out["description"] = field.description
    return out


def nothing_tool() -> dict:
    """The tool the model calls where the words state no sayable's shape and ask no askable's question."""
    return {"name": NOTHING, "description": "The message states none of the shapes above and asks none of the "
                                            "questions. Say why in one line.",
            "input_schema": {"type": "object", "properties": {"why": {"type": "string"}}, "required": ["why"]}}


def tool(name: str, description: str, fields) -> dict:
    """A tool the model may call by `name`: the fields, and no other input."""
    return {"name": name, "description": description,
            "input_schema": {"type": "object",
                             "properties": {f.name: schema_of(f) for f in fields},
                             "required": [f.name for f in fields if f.required],
                             "additionalProperties": False}}


def term_of(field: Field, value) -> ox.NamedNode | ox.Literal | None:
    """`value` as the term the field takes, or None where it does not take it."""
    if field.choices:
        return next((ox.NamedNode(iri) for label, iri in field.choices if label == value), None)
    kind = local_of(field.datatype) if field.datatype else "string"
    try:
        if kind in ("integer", "int", "long"):
            return ox.Literal(str(int(value)), datatype=ox.NamedNode(XSD + "integer"))
        if kind in ("decimal", "double", "float"):
            return ox.Literal(repr(float(value)), datatype=ox.NamedNode(XSD + kind))
        if kind == "boolean":
            return ox.Literal("true" if value is True else "false" if value is False else str(value).lower(),
                              datatype=ox.NamedNode(XSD + "boolean"))
        if kind == "dateTime":
            return ox.Literal(datetime.fromisoformat(str(value)).isoformat(), datatype=ox.NamedNode(XSD + "dateTime"))
        if kind == "date":
            return ox.Literal(datetime.fromisoformat(str(value)).date().isoformat(), datatype=ox.NamedNode(XSD + "date"))
        if kind == "string":
            return ox.Literal(str(value))
        return ox.Literal(str(value), datatype=ox.NamedNode(field.datatype))
    except (TypeError, ValueError):
        return None
