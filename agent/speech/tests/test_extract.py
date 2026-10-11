"""`extract`: what the agent believes of one statement is what its extractions conclude of it alone — one
belief graph derived from it, the agent's own, over its period; nothing where nothing concludes."""

from __future__ import annotations

import logging

import pyoxigraph as ox
import pytest

from agent.ontology import BELIEF, CATALOGUE_GRAPH, OREXIS
from agent.speech.extract import extract
from agent.speech.ontology import believed_graph
from agent.store import graphs_of, rows, update

T = "http://example.org/test#"
ME = T + "me"
ROUND, CLAIM = T + "round", T + "claim"

#  WHAT A DOCUMENT SAYS OF WHAT IT IS ABOUT, believed: the shape of the market's extraction.
_BELIEVED = f"CONSTRUCT {{ ?s ?p ?o }} WHERE {{ ?s a ?c ; ?p ?o . VALUES ?c {{ <{T}Round> <{T}Claim> }} }}"
_ROW_Q = """SELECT ?a ?o ?from ?start WHERE { GRAPH ?cat { ?cat a orexis:CatalogueGraph .
  $g orexis:arrivedBy ?a ; orexis:beliefsOf ?o ; prov:wasDerivedFrom ?from ; dcterms:temporal ?p . ?p orexis:start ?start } }"""


@pytest.fixture
def store():
    st = ox.Store()
    update(st, f"""INSERT DATA {{
  GRAPH <{CATALOGUE_GRAPH}> {{ <{CATALOGUE_GRAPH}> a orexis:CatalogueGraph .
      <{T}rules> a sh:RulesGraph . <{T}world> a orexis:PublicGraph .
      <{ROUND}> a speech:StatementGraph , orexis:Graph ; orexis:arrivedBy orexis:Received ; orexis:beliefsOf <{ME}> ;
                dcterms:temporal [ orexis:start "2026-01-01T12:00:00+00:00"^^xsd:dateTime ] .
      <{CLAIM}> a speech:StatementGraph , orexis:Graph ; orexis:arrivedBy orexis:Received ; orexis:beliefsOf <{ME}> .
      <{T}held> a orexis:BeliefGraph ; orexis:arrivedBy orexis:Derived . }}
  GRAPH <{T}rules> {{ <{T}believed> a speech:Extraction ; sh:construct "{_BELIEVED}" . }}
  GRAPH <{T}world> {{ <{T}water> a <{T}Venue> . }}
  GRAPH <{ROUND}> {{ <{ROUND}> a <{T}Round> ; <{T}lot> 40 ; <{T}onVenue> <{T}water> . }}
  GRAPH <{CLAIM}> {{ <{CLAIM}> a <{T}Claim> ; <{T}inRound> <{ROUND}> . }}
  GRAPH <{T}held> {{ <{ROUND}> a <{T}Round> ; <{T}lot> 40 . }} }}""")
    return st


def _said(store, graph):
    return {(q.subject.value[len(T):], q.predicate.value.rsplit("#", 1)[-1], getattr(q.object, "value", ""))
            for q in store.quads_for_pattern(None, None, None, ox.NamedNode(graph))}


def test_what_a_round_says_is_believed_the_agent_s_own_over_its_period(store):
    assert extract(store, ROUND) == [believed_graph(ROUND)]
    assert _said(store, believed_graph(ROUND)) == _said(store, ROUND)
    assert believed_graph(ROUND) in graphs_of(store, BELIEF)
    (row,) = rows(store, _ROW_Q, (), g=believed_graph(ROUND))
    assert (row["a"], row["o"], row["from"]) == (OREXIS + "Derived", ME, ROUND)
    assert row["start"].startswith("2026-01-01T12:00:00"), "it holds over what was said's period"


def test_a_claim_carries_nothing_of_the_round_it_names_believed_before(store):
    """An extraction reads the statement alone: the round believed already stands beside, and none of it
    is concluded of the claim, so the claim's belief goes with the claim and not with the round."""
    extract(store, CLAIM)
    assert _said(store, believed_graph(CLAIM)) == {("claim", "type", T + "Claim"), ("claim", "inRound", ROUND)}


def test_extracting_again_replaces_and_nothing_extracted_is_no_belief(store):
    extract(store, ROUND)
    update(store, f"DELETE DATA {{ GRAPH <{ROUND}> {{ <{ROUND}> <{T}lot> 40 }} }} ; INSERT DATA {{ GRAPH <{ROUND}> {{ <{ROUND}> <{T}lot> 20 }} }}")
    extract(store, ROUND)
    assert ("round", "lot", "20") in _said(store, believed_graph(ROUND)) and ("round", "lot", "40") not in _said(store, believed_graph(ROUND))
    update(store, f"DROP GRAPH <{ROUND}>")
    assert extract(store, ROUND) == [] and believed_graph(ROUND) not in graphs_of(store, BELIEF)


def test_an_extraction_that_will_not_run_extracts_nothing_loudly(store, caplog):
    update(store, f'INSERT DATA {{ GRAPH <{T}rules> {{ <{T}broken> a speech:Extraction ; sh:construct "CONSTRUCT {{" . }} }}')
    with caplog.at_level(logging.ERROR, logger="speech"):
        assert extract(store, ROUND) == [believed_graph(ROUND)], "the rest still run"
    assert any("broken" in m for m in caplog.messages), caplog.messages


def test_a_peer_saying_a_subject_belief_makes_no_belief_where_no_extraction_concludes_it(store):
    """A peer says the agent's own bed is dry, in a graph it types as a belief. What was said is kept as
    a statement, and no extraction the agent holds is about a bed's soil, so nothing is believed of it:
    no met-test reads it, where before #958 it was read as the agent's own state of its bed."""
    said = T + "rumour"
    update(store, f"""INSERT DATA {{
  GRAPH <{CATALOGUE_GRAPH}> {{ <{said}> a speech:StatementGraph , orexis:Graph ; orexis:arrivedBy orexis:Received ; orexis:beliefsOf <{ME}> . }}
  GRAPH <{said}> {{ <{T}bed> <http://example.org/orexis/climate#soil> <http://example.org/orexis/climate#Dry> . }} }}""")
    assert extract(store, said) == []
    assert not list(store.quads_for_pattern(None, None, None, ox.NamedNode(believed_graph(said))))
