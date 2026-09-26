"""`heard`: a peer's document is believed as it stands, where every graph it holds is a state of
the world and a graph of its name, where one stands, was a peer's word too."""

from __future__ import annotations

import pyoxigraph as ox
import pytest

from agent.ontology import CATALOGUE_GRAPH, OREXIS
from agent.speech.heard import heard
from agent.store import graphs_of, rows, update

T = "http://example.org/test#"
ME = T + "me"
_ARRIVAL_Q = "SELECT ?a ?o WHERE { GRAPH ?cat { ?cat a orexis:CatalogueGraph . $g orexis:arrivedBy ?a ; orexis:beliefsOf ?o } }"


@pytest.fixture
def store():
    st = ox.Store()
    update(st, f"""INSERT DATA {{
  GRAPH <{CATALOGUE_GRAPH}> {{ <{CATALOGUE_GRAPH}> a orexis:CatalogueGraph . <{T}vocabulary> a orexis:OntologyGraph .
                               <{T}mine> a orexis:StateGraph ; orexis:arrivedBy orexis:Recorded . }}
  GRAPH <{T}vocabulary> {{ <{T}RoundGraph> rdfs:subClassOf orexis:StateGraph , orexis:BeliefGraph , orexis:Graph . }} }}""")
    return st


def _doc(graph, kind, fact):
    return f"<{graph}> {{ <{graph}> <{T}says> \"{fact}\" }}\n<{graph}> a <{kind}> .".encode()


def test_a_round_heard_is_believed_the_agent_s_own_and_received(store):
    assert heard(store, ME, _doc(T + "round", T + "RoundGraph", "open")) == [T + "round"]
    assert T + "round" in graphs_of(store, OREXIS + "StateGraph"), "its kinds are closed on its row"
    assert rows(store, _ARRIVAL_Q, (), g=T + "round") == [{"a": OREXIS + "Received", "o": ME}]


def test_a_round_said_again_replaces_the_one_before(store):
    heard(store, ME, _doc(T + "round", T + "RoundGraph", "open"))
    heard(store, ME, _doc(T + "round", T + "RoundGraph", "cleared"))
    said = [q.object.value for q in store.quads_for_pattern(None, ox.NamedNode(T + "says"), None, ox.NamedNode(T + "round"))]
    assert said == ["cleared"]


def test_a_peer_cannot_say_a_desire(store):
    assert heard(store, ME, _doc(T + "wish", OREXIS + "DesireGraph", "want")) == []
    assert not list(store.quads_for_pattern(None, None, None, ox.NamedNode(T + "wish")))


def test_a_peer_cannot_rewrite_what_this_agent_said(store):
    assert heard(store, ME, _doc(T + "mine", T + "RoundGraph", "forged")) == []


def test_what_is_no_document_is_not_believed(store):
    assert heard(store, ME, b"this is not TriG {") == []
