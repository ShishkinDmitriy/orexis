"""Belief's part: its deliberator, which says by its own `revised` what a pass revised; once
started, it revises every belief and every prediction written — hearing the two kinds through the
runtime — and what a package above hands it, with the kind that package says its revisions are."""

from __future__ import annotations

import pyoxigraph as ox

from agent.belief.create import create
from agent.belief.deliberator import Deliberator
from agent.ontology import BELIEF, CATALOGUE_GRAPH, PREDICTION
from agent.store import update


def test_its_part_revises_beliefs_and_predictions_as_they_are_written_and_says_so(stand_in_runtime):
    store = ox.Store()
    update(store, f"INSERT DATA {{ GRAPH <{CATALOGUE_GRAPH}> {{ <{CATALOGUE_GRAPH}> a orexis:CatalogueGraph }} }}")
    runtime = stand_in_runtime(store, "urn:test:me", None)
    part = create(runtime)
    assert isinstance(part.deliberator, Deliberator)
    heard = []
    part.deliberator.revised.connect(lambda revised: heard.extend(revised.graphs))
    part.start(runtime)
    assert [kind for kind, _ in runtime.heard] == [BELIEF, PREDICTION], \
        "an observation is no kind of belief's: sensing hands its own in (#944)"
    assert all(handler("urn:test:nothing") == [] for _, handler in runtime.heard)
    assert heard == ["urn:test:nothing"] * 2, "each pass says what it revised"


def test_a_graph_written_is_revised_beside_the_world_alone(stand_in_runtime):
    """Beside a graph written stand the public graphs and nothing else: never another testimony — a
    reading received, a peer's word, is not read beside a graph it is not — and not a state the agent
    derived, which is a premise of a transition and not of an inference, and which `trigger` hands the
    transitions itself (a-transition-changes-the-state-and-an-inference-only-concludes)."""
    store = ox.Store()
    update(store, f"INSERT DATA {{ GRAPH <{CATALOGUE_GRAPH}> {{ <{CATALOGUE_GRAPH}> a orexis:CatalogueGraph }} }}")
    rows_ = {"urn:test:world": "orexis:PublicGraph ; orexis:arrivedBy orexis:Asserted",
             "urn:test:concluded": "orexis:StateGraph ; orexis:arrivedBy orexis:Derived ; "
                                   "dcterms:temporal [ orexis:start \"2025-01-01T00:00:00Z\"^^xsd:dateTime ; "
                                   "orexis:end \"2025-01-02T00:00:00Z\"^^xsd:dateTime ]",
             "urn:test:other_reading": "orexis:StateGraph ; orexis:arrivedBy orexis:Received",
             "urn:test:said": "orexis:StateGraph ; orexis:arrivedBy orexis:Recorded"}
    update(store, f"INSERT DATA {{ GRAPH <{CATALOGUE_GRAPH}> {{ "
                  + " ".join(f"<{g}> a {said} ." for g, said in rows_.items()) + " } }")
    runtime = stand_in_runtime(store, "urn:test:me", None)
    part = create(runtime)
    asked = []
    changed = part.deliberator.changed
    part.deliberator.changed = lambda source, read=None, kind=BELIEF: \
        asked.append((source, tuple(read), kind)) or changed(source, read, kind)
    part.start(runtime)
    asked.clear()
    (written,) = [handler for kind, handler in runtime.heard if kind == BELIEF]
    written("urn:test:reading")
    assert asked == [("urn:test:reading", ("urn:test:world",), BELIEF)], asked
    #  A PACKAGE ABOVE HANDS ITS OWN IN, and says the kind their revisions are: beside the world alone too.
    asked.clear()
    assert part.revise(["urn:test:observed"], kind="urn:test:ObservedGraph") == []
    assert asked == [("urn:test:observed", ("urn:test:world",), "urn:test:ObservedGraph")], asked
