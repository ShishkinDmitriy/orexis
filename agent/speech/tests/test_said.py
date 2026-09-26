"""`said`: what this agent told a peer, it believes it told — recorded and its own — and it may say
again only what it said before."""

from __future__ import annotations

import pyoxigraph as ox
import pytest

from agent.ontology import CATALOGUE_GRAPH, OREXIS
from agent.speech.said import said
from agent.store import DocumentRefused, rows, update

T = "http://example.org/test#"
ME = T + "me"
_ARRIVAL_Q = "SELECT ?a ?o WHERE { GRAPH ?cat { ?cat a orexis:CatalogueGraph . $g orexis:arrivedBy ?a ; orexis:beliefsOf ?o } }"


@pytest.fixture
def store():
    st = ox.Store()
    update(st, f"""INSERT DATA {{ GRAPH <{CATALOGUE_GRAPH}> {{ <{CATALOGUE_GRAPH}> a orexis:CatalogueGraph .
        <{T}heard> a orexis:StateGraph ; orexis:arrivedBy orexis:Received ; orexis:beliefsOf <{ME}> . }} }}""")
    return st


def _doc(graph, fact):
    doc = ox.Store()
    doc.add(ox.Quad(ox.NamedNode(graph), ox.NamedNode(T + "says"), ox.Literal(fact), ox.NamedNode(graph)))
    doc.add(ox.Quad(ox.NamedNode(graph), ox.NamedNode("http://www.w3.org/1999/02/22-rdf-syntax-ns#type"),
                    ox.NamedNode(OREXIS + "StateGraph"), ox.DefaultGraph()))
    return doc


def test_what_the_agent_said_is_recorded_and_its_own_and_may_be_said_again(store):
    assert said(store, ME, _doc(T + "round", "open")) == [T + "round"]
    assert rows(store, _ARRIVAL_Q, (), g=T + "round") == [{"a": OREXIS + "Recorded", "o": ME}]
    said(store, ME, _doc(T + "round", "cleared"))
    assert [q.object.value for q in store.quads_for_pattern(None, None, None, ox.NamedNode(T + "round"))] == ["cleared"]


def test_the_agent_cannot_say_again_what_a_peer_told_it(store):
    with pytest.raises(DocumentRefused):
        said(store, ME, _doc(T + "heard", "overwritten"))
