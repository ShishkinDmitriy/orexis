"""`sayable`: the shapes a person's prose may become, read off the world — and a statement made of one.

**A SAYABLE IS A SHAPE WITH NO ACTION IN IT.** A domain declares what a person may say to its agents
as `speech:Sayable` node shapes beside its extraction, in its rules graph: `sh:targetClass` the kind of
statement, and `sh:property` for each thing it may carry — `sh:path`, a `sh:datatype` for a literal or a
`sh:class` for a thing of the world, `sh:minCount` for what it must carry, `sh:description` for what
the model is told. That is all the model is handed, and all it may fill: `tool_of` turns one into a
tool whose input schema is the shape's fields and nothing else, and `document_of` makes a statement of
what the model filled, dropping any field the shape does not declare, refusing one that lacks a field
the shape requires or fills it with a value its datatype does not take. So prose becomes at most a
statement of a declared shape (knowledge/domain/speech/sayable.md).

**A THING OF THE WORLD IS CHOSEN BY ITS LABEL.** A field with `sh:class` is filled from the instances
the world states of that class, offered to the model as choices by `rdfs:label` where there is one and
by local name where not, and written back as the IRI; a label the world does not state is no value.

**THE STATEMENT IS A DOCUMENT AS ANY PEER'S.** One graph, named by a URN, typed `speech:StatementGraph`
in the default graph with the period it holds from; inside it the node of the sayable's class with
the fields filled, the prose it was made from (`speech:prose`) and who said it (`speech:saidBy`), so
the agent's journal keeps the words with the statement and the extraction reads the fields.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime

import pyoxigraph as ox

from agent.ontology import BELIEF, local_of
from agent.store import graphs_of, rows

log = logging.getLogger("translation")

SPEECH = "http://example.org/orexis/speech#"
XSD = "http://www.w3.org/2001/XMLSchema#"
RULES_GRAPH = "http://www.w3.org/ns/shacl#RulesGraph"
_TYPE = ox.NamedNode("http://www.w3.org/1999/02/22-rdf-syntax-ns#type")

#  THE TOOL THE MODEL CALLS WHERE NO SAYABLE FITS, beside the sayables.
NOTHING = "nothing_sayable"

_SAYABLES_Q = """
SELECT ?shape ?class ?description WHERE {
  ?shape a speech:Sayable ; sh:targetClass ?class .
  OPTIONAL { ?shape sh:description ?description } } ORDER BY ?shape"""
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


@dataclass(frozen=True)
class Sayable:
    shape: str
    cls: str
    description: str
    fields: tuple[Field, ...]

    @property
    def name(self) -> str:
        return local_of(self.cls)


def sayables(store: ox.Store) -> list[Sayable]:
    """Every sayable the world's rules graphs declare, its fields read with the choices the world states."""
    rules, stated = graphs_of(store, RULES_GRAPH), graphs_of(store, BELIEF, common=True)
    out = []
    for s in rows(store, _SAYABLES_Q, rules):
        fields = []
        for f in rows(store, _FIELDS_Q, rules, shape=s["shape"]):
            choices = tuple((r.get("label") or local_of(r["i"]), r["i"])
                            for r in rows(store, _CHOICES_Q, stated, **{"class": f["class"]})) if f.get("class") else ()
            fields.append(Field(f["path"], f.get("datatype"), f.get("class"), int(f.get("min") or 0) > 0,
                                f.get("description") or "", choices))
        out.append(Sayable(s["shape"], s["class"], s.get("description") or "", tuple(fields)))
    return out


def _schema(field: Field) -> dict:
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


def tool_of(sayable: Sayable) -> dict:
    """The sayable as a tool the model may call: its fields, and no other input."""
    return {"name": sayable.name, "description": sayable.description or sayable.name,
            "input_schema": {"type": "object",
                             "properties": {f.name: _schema(f) for f in sayable.fields},
                             "required": [f.name for f in sayable.fields if f.required],
                             "additionalProperties": False}}


def nothing_tool() -> dict:
    """The tool the model calls where the prose states nothing sayable, or asks for anything else."""
    return {"name": NOTHING, "description": "The message states none of the shapes above, or asks for "
                                            "something no shape carries. Say why in one line.",
            "input_schema": {"type": "object", "properties": {"why": {"type": "string"}}, "required": ["why"]}}


def _term(field: Field, value) -> ox.NamedNode | ox.Literal | None:
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


def document_of(sayable: Sayable, inputs: dict, *, by: str, prose: str, at: datetime) -> bytes | None:
    """A statement of `sayable` made from what the model filled, as the TriG a peer's document is: None,
    said in the log, where a required field is missing or holds what its datatype does not take. A field
    the shape does not declare is dropped and said."""
    graph = ox.NamedNode(f"urn:uuid:{uuid.uuid4()}")
    doc = ox.Store()
    declared = {f.name: f for f in sayable.fields}
    for name in sorted(set(inputs) - set(declared)):
        log.warning("%s: the model filled %r, which the shape does not declare — dropped", sayable.name, name)
    for field in sayable.fields:
        if field.name not in inputs or inputs[field.name] in (None, ""):
            if field.required:
                log.warning("%s: %s is required and the message does not say it", sayable.name, field.name)
                return None
            continue
        term = _term(field, inputs[field.name])
        if term is None:
            log.warning("%s: %s does not take %r", sayable.name, field.name, inputs[field.name])
            if field.required:
                return None
            continue
        doc.add(ox.Quad(graph, ox.NamedNode(field.path), term, graph))
    doc.add(ox.Quad(graph, _TYPE, ox.NamedNode(sayable.cls), graph))
    doc.add(ox.Quad(graph, ox.NamedNode(SPEECH + "prose"), ox.Literal(prose), graph))
    doc.add(ox.Quad(graph, ox.NamedNode(SPEECH + "saidBy"), ox.NamedNode(by), graph))
    period = ox.BlankNode()
    doc.add(ox.Quad(graph, _TYPE, ox.NamedNode(SPEECH + "StatementGraph"), ox.DefaultGraph()))
    doc.add(ox.Quad(graph, ox.NamedNode("http://purl.org/dc/terms/temporal"), period, ox.DefaultGraph()))
    doc.add(ox.Quad(period, _TYPE, ox.NamedNode("http://purl.org/dc/terms/PeriodOfTime"), ox.DefaultGraph()))
    doc.add(ox.Quad(period, ox.NamedNode("http://example.org/orexis#start"),
                    ox.Literal(at.isoformat(), datatype=ox.NamedNode(XSD + "dateTime")), ox.DefaultGraph()))
    return doc.dump(format=ox.RdfFormat.TRIG)


def said_in(doc: ox.Store, known: list[Sayable]) -> tuple[Sayable, dict[str, str]] | None:
    """The sayable a document is a statement of, and what it says, field by field — a thing of the world
    by its label, a literal by its value; None where no graph of it is a node of a sayable's class."""
    by_class = {s.cls: s for s in known}
    for q in doc.quads_for_pattern(None, _TYPE, None):
        if isinstance(q.object, ox.NamedNode) and q.object.value in by_class and q.graph_name != ox.DefaultGraph():
            sayable, node, graph = by_class[q.object.value], q.subject, q.graph_name
            values: dict[str, str] = {}
            for field in sayable.fields:
                for row in doc.quads_for_pattern(node, ox.NamedNode(field.path), None, graph):
                    labels = {iri: label for label, iri in field.choices}
                    values[field.name] = (labels.get(row.object.value, local_of(row.object.value))
                                          if isinstance(row.object, ox.NamedNode) else row.object.value)
            return sayable, values
    return None
