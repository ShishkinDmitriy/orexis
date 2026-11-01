"""`askable`: the questions a person may ask an agent about itself, read off its store — and each answered from it.

**AN ASKABLE IS A QUESTION A PACKAGE DECLARES.** A package with something to say of itself ships an
`speech:AskableGraph` beside its ontology — sensing what each sensor last read, execution what the agent is
doing — and a domain or a world may ship one too. Each `speech:Askable` is a node shape: `sh:description` what
the model is told it answers, `sh:property` each field the asker may fill (`shape`), `speech:reads` the kinds of
graph its select is handed as the default graph, and `speech:select` the text, each filled field bound into it
as the `$` token of its local name (knowledge/domain/speech/askable.md).

**IT IS ANSWERED, AND IT WRITES NOTHING.** `answered` runs the askable's own select over every store the agent
holds that has graphs of a kind it reads, with what the asker filled, and hands back the rows; the asker never
writes the text nor sees it. Every other act is a sayable, kept as a statement
(knowledge/decisions/a-question-is-answered-and-every-other-act-is-kept.md). `status` is the rows of every
askable that takes no field, which `/status` answers with and asks no model for.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import datetime

import pyoxigraph as ox

from agent.ontology import local_of
from agent.speech.ontology import ASKABLE_GRAPH
from agent.store import Unbound, graphs_of, rows

from .shape import Field, fields_of, term_of, tool

log = logging.getLogger("translation")

_ASKABLES_Q = """
SELECT ?shape ?description ?select WHERE {
  ?shape a speech:Askable ; speech:select ?select .
  OPTIONAL { ?shape sh:description ?description } } ORDER BY ?shape"""
_READS_Q = "SELECT ?kind WHERE { $shape speech:reads ?kind } ORDER BY ?kind"
_INSTANT = re.compile(r"^(\d{4}-\d\d-\d\dT\d\d:\d\d)(:\d\d(\.\d+)?)?(Z|[+-]\d\d:\d\d)?$")


@dataclass(frozen=True)
class Askable:
    shape: str
    description: str
    fields: tuple[Field, ...]
    reads: tuple[str, ...]
    select: str

    @property
    def name(self) -> str:
        return local_of(self.shape)


def askables(store: ox.Store) -> list[Askable]:
    """Every askable the agent's askable graphs declare: the loaded packages', its domains' and its world's."""
    graphs = graphs_of(store, ASKABLE_GRAPH)
    return [Askable(a["shape"], a.get("description") or "", fields_of(store, a["shape"], graphs),
                    tuple(r["kind"] for r in rows(store, _READS_Q, graphs, shape=a["shape"])), a["select"])
            for a in rows(store, _ASKABLES_Q, graphs)]


def tool_of(askable: Askable) -> dict:
    """The askable as a tool the model may call: its fields, and no other input."""
    return tool(askable.name, askable.description or askable.name, askable.fields)


def answered(stores, askable: Askable, inputs: dict | None = None) -> list[dict] | None:
    """The rows `askable` answers with, over every store of `stores` holding graphs of a kind it reads, with what
    the asker filled bound into its select: None, said in the log, where a field it requires is not filled or
    holds what the field does not take. A field it does not declare is dropped."""
    inputs, values = inputs or {}, {}
    declared = {f.name: f for f in askable.fields}
    for name in sorted(set(inputs) - set(declared)):
        log.warning("%s: the model filled %r, which the askable does not declare — dropped", askable.name, name)
    for field in askable.fields:
        filled = inputs.get(field.name)
        term = term_of(field, filled) if filled not in (None, "") else None
        if term is None:
            log.warning("%s: %s is not filled with a value it takes (%r)", askable.name, field.name, filled)
            return None
        values[field.name] = term
    out, seen = [], set()
    for store in {id(s): s for s in stores if s is not None}.values():
        graphs = graphs_of(store, *askable.reads)
        if not graphs:
            continue
        try:
            found = rows(store, askable.select, graphs, **values)
        except Unbound as exc:
            log.warning("%s: its select %s", askable.name, exc)
            return None
        for row in found:
            key = tuple(sorted(row.items()))
            if key not in seen:
                seen.add(key)
                out.append(row)
    return out


def said(value: str) -> str:
    """A value as a person reads it: an IRI by its local name, an instant to the minute."""
    if value.startswith(("http://", "https://", "urn:")):
        return local_of(value)
    found = _INSTANT.match(value)
    return found.group(1).replace("T", " ") + (" UTC" if found.group(4) in ("Z", "+00:00") else "") if found else value


def lines(found: list[dict]) -> list[str]:
    """Each row as one line, `name: value`, the values as a person reads them."""
    return [", ".join(f"{name}: {said(value)}" for name, value in row.items() if value is not None) for row in found]


def status(stores, known: list[Askable], me: str, now: datetime) -> str:
    """What the agent says of itself at `now`: who and when, then the rows of every askable that takes no field,
    a section each under its name, or that there is nothing to say yet."""
    sections = []
    for askable in known:
        if askable.fields:
            continue
        found = [line for line in lines(answered(stores, askable) or []) if line]
        if found:
            sections.append(f"{askable.name}:\n" + "\n".join(f" - {line}" for line in found))
    head = f"{local_of(me)} at {now.strftime('%Y-%m-%d %H:%M')} UTC"
    return head + "\n" + ("\n".join(sections) if sections else "nothing to say yet")
