"""What a chat may read, over the translator's test world: the graphs of its kinds copied into one default graph,
each vocabulary among them by the name the model loads it by, and a query run over the copy alone — refused before
it runs where it could do anything but read."""

from __future__ import annotations

import re

from pathlib import Path

import pytest

from agent.runtime import boot
from agent.translation.readable import QUERY, ROWS, VOCABULARY, Readable

WORLD = Path(__file__).parent / "world"
O = "http://example.org/orexis#"
BELIEFS = ["orexis:BeliefGraph"]


@pytest.fixture(scope="module")
def readable():
    return Readable([boot(WORLD, "seeker")], [O + "BeliefGraph"], "http://example.org/orexis/world/viewing#seeker")


def test_each_vocabulary_is_listed_by_its_prefix_and_loaded_by_it(readable):
    assert {"orexis", "speech"} <= set(readable.vocabularies), readable.listing()
    assert readable.vocabulary("speech") == readable.vocabulary("speech:")
    assert readable.vocabulary("nonesuch").startswith("no vocabulary 'nonesuch' in this chat; these are:")
    assert "closure" not in readable.listing(), "the subclass closure is derived, and no vocabulary"


def test_a_vocabulary_is_a_glossary_of_its_terms_and_the_query_reads_the_rest(readable):
    glossary = readable.vocabulary("speech").splitlines()
    assert "speech:Chat (class): Who speaks with whom, through what: a standing thing of the society, with its " \
           "`speech:participant`s - an agent and a person, or several - and its `speech:channel`, the thing their " \
           "prose goes through." in glossary
    assert any(line.startswith("speech:participant (property, speech:Chat → ") for line in glossary), glossary
    assert any(line.startswith("speech:allows (property, speech:Chat → rdf:Property): ") for line in glossary), glossary
    assert all(len(line.split(": ", 1)[-1]) <= 220 for line in glossary), "a sentence is cut, and the query reads on"
    assert re.search(r"translation \([0-9]+ terms\)", readable.listing()), readable.listing()
    whole = readable.query("SELECT ?c WHERE { speech:Chat rdfs:comment ?c }", BELIEFS)
    assert "the thing their prose goes through" in whole and len(whole) > 150


def test_a_query_reads_the_chats_graphs_as_one(readable):
    assert "flat_12" in readable.query('SELECT ?l WHERE { ?l rdfs:label ?n FILTER(CONTAINS(STR(?l), "flat")) }', BELIEFS)
    assert readable.query("ASK { ?c a speech:Chat }", BELIEFS) == "true", "the world's graphs and the vocabulary's, merged"
    assert readable.query("SELECT ?x WHERE { ?x a <http://example.org/none> }", BELIEFS) == "(no rows)"


@pytest.mark.parametrize(("text", "why"), [
    ("SELECT * WHERE { SERVICE <http://elsewhere.example/> { ?s ?p ?o } }", "it holds a SERVICE clause"),
    ("SELECT * FROM <http://elsewhere.example/> WHERE { ?s ?p ?o }", "it holds a FROM"),
    ("CONSTRUCT { ?s ?p ?o } WHERE { ?s ?p ?o }", "only a SELECT or an ASK is run"),
    ("DELETE WHERE { ?s ?p ?o }", "it does not parse"),
])
def test_a_query_that_could_do_anything_but_read_the_chats_graphs_is_refused_with_why(readable, text, why):
    assert readable.query(text, BELIEFS).startswith("refused: " + why)


def test_a_row_writes_a_name_with_its_prefix_and_the_agents_world_with_one_named_for_it(readable):
    assert "c: speech:Chat" in readable.query("SELECT ?c WHERE { ?x a ?c } VALUES ?c { speech:Chat }", BELIEFS)
    named = readable.query("SELECT ?c WHERE { ?c a speech:Chat }", BELIEFS)
    assert named.startswith("c: viewing:") and "http://" not in named, named
    assert readable.query("ASK { ?c a speech:Chat ; speech:participant viewing:seeker }", BELIEFS) == "true", "declared"
    assert "viewing: naming the agent's own world" in readable.tools()[1]["description"]


def test_a_query_reads_the_kinds_it_names_and_the_catalogue_is_never_merged_into_them(readable):
    found = readable.query("SELECT DISTINCT ?g ?how WHERE { GRAPH ?g { ?c a speech:Chat } "
                           "GRAPH ?cat { ?g orexis:arrivedBy ?how } }", BELIEFS)
    assert "g: <file://" in found and "how: orexis:Asserted" in found, found
    assert readable.query("ASK { ?g orexis:arrivedBy ?how }", BELIEFS) == "false", "statements about graphs are no data"
    assert readable.query("ASK { ?c a speech:Chat }", ["orexis:OntologyGraph"]) == "false", "a vocabulary holds no chat"
    assert "orexis:OntologyGraph (" in readable.listing() and "Kinds of graph" in readable.listing()
    assert readable.query("ASK { ?s ?p ?o }", ["planning:WantGraph"]).startswith(
        "refused: no graph of kind planning:WantGraph in this chat; these are: ")
    assert readable.query("ASK { ?s ?p ?o }", []) == "refused: name the kinds of graph the query reads"


def test_a_word_in_a_literal_is_no_clause(readable):
    assert readable.query('SELECT ?x WHERE { ?x ?p "GRAPH SERVICE FROM" }', BELIEFS) == "(no rows)"


def test_rows_past_the_cap_are_counted_and_not_handed(readable):
    answer = readable.query("SELECT ?s ?p ?o WHERE { ?s ?p ?o }", BELIEFS)
    assert answer.count("\n") == ROWS and f"(the first {ROWS} of" in answer


def test_the_two_tools_are_answered_by_call_and_nothing_else_is(readable):
    assert [t["name"] for t in readable.tools()] == [VOCABULARY, QUERY]
    assert readable.call(QUERY, {"sparql": "ASK { ?c a speech:Chat }", "kinds": BELIEFS}) == "true"
    assert readable.call(VOCABULARY, {"name": "speech"}) == readable.vocabulary("speech")
    assert readable.call("viewings_offered", {}) is None
