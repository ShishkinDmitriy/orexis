"""What a person may state, over the translator's test world: the words a chat allows, read off the vocabularies with
their domain and range; a statement held to them, one graph per subject and word; and what it says, believed as the
world's word."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pyoxigraph as ox

from agent.runtime import boot
from agent.speech.heard import heard
from agent.store import NAMESPACES, document_of, graphs_of, rows
from agent.translation.stated import PROPERTY, believe, listing, rendered, statement_of, words

WORLD = Path(__file__).parent / "world"
V = "http://example.org/orexis/world/viewing#"
NOW = datetime(2026, 11, 1, 9, 0, tzinfo=timezone.utc)
PREFIXES = {**NAMESPACES, "viewing": V}


def test_a_chat_allows_the_properties_it_names_or_every_one_a_vocabulary_declares():
    store = boot(WORLD, "seeker")
    named = words(store, (V + "viewingAt",))
    assert [(w.iri, w.domain, w.range) for w in named] == [
        (V + "viewingAt", V + "Listing", "http://www.w3.org/2001/XMLSchema#dateTime")]
    every = {w.iri for w in words(store, (PROPERTY,))}
    assert {V + "viewingAt", V + "refused", V + "viewingAsked", "http://example.org/orexis/speech#allows"} <= every
    assert words(store, ()) == [], "a chat allowing none hears questions alone"


def test_the_briefing_names_each_word_and_the_things_it_may_be_said_of():
    store = boot(WORLD, "seeker")
    said = listing(store, words(store, (V + "refused",)), False, PREFIXES, things=True)
    assert said.splitlines() == [
        "A person may state here, in these words alone:",
        " - viewing:refused (application refused), of a viewing:Listing, a xsd:boolean: "
        "Whether the application for the listing was refused.",
        "     viewing:flat_12 (the two-room flat on Kastanienallee)",
        "     viewing:flat_7 (the studio on Rigaer Straße)"], said


def test_a_statement_is_one_graph_per_subject_and_word_and_believed_by_nobody_as_the_world_states():
    store = boot(WORLD, "seeker")
    allowed = words(store, (PROPERTY,))
    payload, why = statement_of(store, allowed, True, PREFIXES,
                                {"says": 'viewing:flat_12 viewing:viewingAt "2026-11-02T18:00:00+00:00" ; viewing:refused false .'},
                                by=V + "clara", prose="Tuesday at six, and you are not refused", at=NOW)
    assert why == []
    doc = document_of(payload)
    named = {q.graph_name for q in doc if q.graph_name != ox.DefaultGraph()}
    assert len(named) == 2, "one per subject and word, so each is replaced alone"
    believed = [g for s in heard(store, V + "seeker", payload) for g in believe(store, s)]
    assert len(believed) == 2 and set(believed) <= set(graphs_of(store, "http://example.org/orexis#BeliefGraph", common=True))
    assert rows(store, "PREFIX v: <http://example.org/orexis/world/viewing#>\nSELECT ?at WHERE { v:flat_12 v:viewingAt ?at }",
                believed) == [{"at": "2026-11-02T18:00:00Z"}], "a plain text said of an instant, believed as one"


def test_a_statement_the_agent_makes_is_read_with_its_words_labels():
    store = boot(WORLD, "seeker")
    doc = document_of(b'<urn:x:a> { <http://example.org/orexis/world/viewing#flat_7> '
                      b'<http://example.org/orexis/world/viewing#refused> true . }\n'
                      b'<urn:x:a> a <http://example.org/orexis/speech#StatementGraph> .\n')
    text = rendered(store, doc, PREFIXES)
    assert "viewing:flat_7 viewing:refused true" in text
    assert " - refused: application refused — Whether the application for the listing was refused" in text
    assert " - flat_7: the studio on Rigaer Straße" in text
