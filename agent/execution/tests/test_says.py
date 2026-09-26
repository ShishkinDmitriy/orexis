"""`says`: what taking a step tells a peer, as documents made from the present. A graph is an IRI
the result says is `execution:to` an agent; its kind and whom it is to are rows about it, and
everything else said of it is its content."""

from __future__ import annotations

from datetime import datetime, timezone

import pyoxigraph as ox
import pytest

from agent import clock
from agent.execution.says import says
from agent.store import kinds_in, update

NOW = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
T = "http://example.org/test#"


@pytest.fixture
def store(monkeypatch):
    monkeypatch.setattr(clock, "now", lambda: NOW)
    st = ox.Store()
    update(st, f"""INSERT DATA {{
  GRAPH <{T}vocabulary> {{ <{T}NoteGraph> rdfs:subClassOf orexis:StateGraph , orexis:Graph . }}
  GRAPH <{T}actions> {{
    <{T}Noting> a orexis:Action ; orexis:takes <{T}topic> ;
      orexis:implementation [ orexis:operation [ a execution:Saying ; sh:construct \"\"\"CONSTRUCT {{ ?note a <{T}Note> , <{T}NoteGraph> ; <{T}about> $topic ; <{T}at> $now ;
                                              execution:to ?peer }}
          WHERE {{ ?peer <{T}reads> $topic . BIND(IRI(CONCAT(STR($topic), "-note")) AS ?note) }}\"\"\" ] ] .
    <{T}Looking> a orexis:Action ; orexis:takes <{T}topic> . }}
  GRAPH <{T}world> {{ <{T}ann> <{T}reads> <{T}rain> . <{T}bob> <{T}reads> <{T}rain> . }}
  GRAPH <{T}catalogue> {{
    <{T}catalogue> a orexis:CatalogueGraph .
    <{T}vocabulary> a orexis:OntologyGraph , orexis:PublicGraph .
    <{T}actions> a orexis:ActionGraph , orexis:PublicGraph .
    <{T}world> a orexis:PublicGraph . }} }}""")
    return st


def test_a_step_tells_one_document_to_every_agent_it_is_to(store):
    told = says(store, {"step": T + "s", "fills": T + "Noting", "topic": T + "rain"}, T + "me")
    assert len(told) == 1
    agents, doc = told[0]
    assert agents == [T + "ann", T + "bob"]
    assert kinds_in(doc) == {T + "rain-note": {T + "NoteGraph"}}, "the kind is a row, the note its own graph"
    content = {(q.predicate.value.rsplit("#", 1)[-1], q.object.value.rsplit("#", 1)[-1])
               for q in doc.quads_for_pattern(None, None, None, ox.NamedNode(T + "rain-note"))}
    assert content == {("type", "Note"), ("about", "rain"), ("at", NOW.isoformat().replace("+00:00", "Z"))} or \
        content == {("type", "Note"), ("about", "rain"), ("at", NOW.isoformat())}
    assert not list(doc.quads_for_pattern(None, ox.NamedNode("http://example.org/orexis/execution#to"), None, None)), \
        "whom it is to addresses the document and is no part of it"


def test_a_step_whose_action_says_nothing_tells_nothing(store):
    assert says(store, {"step": T + "s", "fills": T + "Looking", "topic": T + "rain"}, T + "me") == []
