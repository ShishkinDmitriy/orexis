"""What a chat may read, over the translator's test world: the graphs of its kinds copied into one default graph,
each vocabulary among them by the name the model loads it by, and a query run over the copy alone — refused before
it runs where it could do anything but read."""

from __future__ import annotations

from pathlib import Path

import pytest

from agent.runtime import boot
from agent.translation.readable import QUERY, ROWS, VOCABULARY, Readable

WORLD = Path(__file__).parent / "world"
O = "http://example.org/orexis#"


@pytest.fixture(scope="module")
def readable():
    return Readable([boot(WORLD, "seeker")], [O + "BeliefGraph"])


def test_each_vocabulary_is_listed_by_its_prefix_and_loaded_by_it(readable):
    assert {"orexis", "speech"} <= set(readable.vocabularies), readable.listing()
    assert "speech:Chat" in readable.vocabulary("speech") and "rdfs:comment" in readable.vocabulary("speech:")
    assert readable.vocabulary("nonesuch").startswith("no vocabulary 'nonesuch' in this chat; these are:")
    assert "closure" not in readable.listing(), "the subclass closure is derived, and no vocabulary"


def test_a_query_reads_the_chats_graphs_as_one(readable):
    assert "flat_12" in readable.query("SELECT ?l WHERE { ?l rdfs:label ?n }")
    assert readable.query("ASK { ?c a speech:Chat }") == "true", "the world's graphs and the vocabulary's, merged"
    assert readable.query("SELECT ?x WHERE { ?x a <http://example.org/none> }") == "(no rows)"


@pytest.mark.parametrize(("text", "why"), [
    ("SELECT * WHERE { GRAPH ?g { ?s ?p ?o } }", "it holds a GRAPH clause"),
    ("SELECT * WHERE { SERVICE <http://elsewhere.example/> { ?s ?p ?o } }", "it holds a SERVICE clause"),
    ("SELECT * FROM <http://elsewhere.example/> WHERE { ?s ?p ?o }", "it holds a FROM"),
    ("CONSTRUCT { ?s ?p ?o } WHERE { ?s ?p ?o }", "only a SELECT or an ASK is run"),
    ("DELETE WHERE { ?s ?p ?o }", "it does not parse"),
])
def test_a_query_that_could_do_anything_but_read_the_chats_graphs_is_refused_with_why(readable, text, why):
    assert readable.query(text).startswith("refused: " + why)


def test_a_word_in_a_literal_is_no_clause(readable):
    assert readable.query('SELECT ?x WHERE { ?x ?p "GRAPH SERVICE FROM" }') == "(no rows)"


def test_rows_past_the_cap_are_counted_and_not_handed(readable):
    answer = readable.query("SELECT ?s ?p ?o WHERE { ?s ?p ?o }")
    assert answer.count("\n") == ROWS and f"(the first {ROWS} of" in answer


def test_the_two_tools_are_answered_by_call_and_nothing_else_is(readable):
    assert [t["name"] for t in readable.tools()] == [VOCABULARY, QUERY]
    assert readable.call(QUERY, {"sparql": "ASK { ?c a speech:Chat }"}) == "true"
    assert readable.call(VOCABULARY, {"name": "speech"}) == readable.vocabulary("speech")
    assert readable.call("viewings_offered", {}) is None
