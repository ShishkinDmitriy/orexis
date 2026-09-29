"""Belief's `start`: once started it revises every belief and every prediction written — hearing both
kinds through the runtime — and reports its gauges; what it answers is its deliberator."""

from __future__ import annotations

import pyoxigraph as ox

from agent.belief.deliberator import Deliberator
from agent.belief.start import start
from agent.ontology import BELIEF, CATALOGUE_GRAPH, PREDICTION
from agent.store import update


def test_started_it_revises_beliefs_and_predictions_as_they_are_written(stand_in_runtime):
    store = ox.Store()
    update(store, f"INSERT DATA {{ GRAPH <{CATALOGUE_GRAPH}> {{ <{CATALOGUE_GRAPH}> a orexis:CatalogueGraph }} }}")
    runtime = stand_in_runtime(store, "urn:test:me", None)
    assert isinstance(start(runtime), Deliberator)
    assert [kind for kind, _ in runtime.heard] == [BELIEF, PREDICTION] and len(runtime.gauges) == 1
    assert all(handler("urn:test:nothing") == [] for _, handler in runtime.heard)
