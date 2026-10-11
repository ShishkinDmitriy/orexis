"""`heard`: a peer's document is kept as what was said — every graph a statement, whatever kind it says —
where a graph of its name, where one stands, was a peer's word too (#958)."""

from __future__ import annotations

import pyoxigraph as ox
import pytest

from agent.ontology import ACTION, BELIEF, CATALOGUE_GRAPH, OREXIS
from agent.speech.heard import heard
from agent.speech.ontology import STATEMENT_GRAPH as STATEMENT
from agent.store import graphs_of, rows, update

T = "http://example.org/test#"
ME = T + "me"
_ARRIVAL_Q = "SELECT ?a ?o WHERE { GRAPH ?cat { ?cat a orexis:CatalogueGraph . $g orexis:arrivedBy ?a ; orexis:beliefsOf ?o } }"


@pytest.fixture
def store():
    st = ox.Store()
    update(st, f"""INSERT DATA {{
  GRAPH <{CATALOGUE_GRAPH}> {{ <{CATALOGUE_GRAPH}> a orexis:CatalogueGraph . <{T}vocabulary> a orexis:OntologyGraph .
                               <{T}mine> a orexis:BeliefGraph ; orexis:arrivedBy orexis:Recorded . }}
  GRAPH <{T}vocabulary> {{ <{T}RoundGraph> rdfs:subClassOf <{STATEMENT}> , orexis:Graph .
                           <{STATEMENT}> rdfs:subClassOf orexis:Graph . }} }}""")
    return st


def _doc(graph, kind, fact):
    return f"<{graph}> {{ <{graph}> <{T}says> \"{fact}\" }}\n<{graph}> a <{kind}> .".encode()


def test_a_round_heard_is_kept_as_a_statement_the_agent_s_own_and_received(store):
    assert heard(store, ME, _doc(T + "round", T + "RoundGraph", "open")) == [T + "round"]
    assert T + "round" in graphs_of(store, STATEMENT), "a statement, its kinds closed on its row"
    assert T + "round" in graphs_of(store, T + "RoundGraph"), "a kind of statement it said is kept"
    assert T + "round" not in graphs_of(store, BELIEF), "and no belief: what was said is not what is believed"
    assert rows(store, _ARRIVAL_Q, (), g=T + "round") == [{"a": OREXIS + "Received", "o": ME}]


def test_a_round_said_again_replaces_the_one_before(store):
    heard(store, ME, _doc(T + "round", T + "RoundGraph", "open"))
    heard(store, ME, _doc(T + "round", T + "RoundGraph", "cleared"))
    said = [q.object.value for q in store.quads_for_pattern(None, ox.NamedNode(T + "says"), None, ox.NamedNode(T + "round"))]
    assert said == ["cleared"]


@pytest.mark.parametrize("kind", [ACTION, "http://example.org/orexis/planning#DesireGraph", BELIEF,
                                  OREXIS + "WorldGraph"], ids=["action", "desire", "belief", "world"])
def test_whatever_kind_a_peer_says_what_is_kept_is_what_was_said(store, kind):
    """No kind is refused and none is kept that is not a statement: a peer typing its graph an action
    graph, a desire, a belief or the world is kept as what it said, read by no planner, no executor and
    no rule as any of those — what the agent comes to believe of it is what its extractions conclude."""
    assert heard(store, ME, _doc(T + "wish", kind, "want")) == [T + "wish"]
    assert graphs_of(store, kind) == ([T + "mine"] if kind == BELIEF else []), "the kind it said is not kept"
    assert graphs_of(store, STATEMENT) == [T + "wish"]


def test_a_peer_cannot_rewrite_what_this_agent_said(store):
    assert heard(store, ME, _doc(T + "mine", T + "RoundGraph", "forged")) == []


def test_what_is_no_document_is_not_believed(store):
    assert heard(store, ME, b"this is not TriG {") == []


def test_a_peer_cannot_say_who_the_self_is(store):
    """A round the peer may say, and in it the one thing no peer tells this agent: that somebody is
    its self. The whole document is refused, as the loader refuses a file saying it."""
    doc = (f"<{T}round> {{ <{T}round> <{T}says> \"open\" . <{T}someone> a <{OREXIS}Self> }}\n"
           f"<{T}round> a <{T}RoundGraph> .").encode()
    assert heard(store, ME, doc) == []
    assert not list(store.quads_for_pattern(None, None, ox.NamedNode(OREXIS + "Self"), None))
    assert not list(store.quads_for_pattern(None, None, None, ox.NamedNode(T + "round"))), "refused whole"


def test_a_peer_cannot_say_whose_a_graph_is(store):
    """The hearer owns what it hears: a peer naming an owner would be a peer saying whose beliefs
    this agent holds. Refused whole, as the loader refuses it from anything but a world's file."""
    doc = (f"<{T}round> {{ <{T}round> <{T}says> \"open\" }}\n"
           f"<{T}round> a <{T}RoundGraph> ; <{OREXIS}beliefsOf> <{T}someone> .").encode()
    assert heard(store, ME, doc) == []
    assert not list(store.quads_for_pattern(ox.NamedNode(T + "round"), None, None)), "refused whole, and no row"
