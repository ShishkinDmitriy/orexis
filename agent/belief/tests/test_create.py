"""Belief's part: its deliberator, which says by its own `revised` what a pass revised; once
started, it revises every belief and every prediction written — hearing both kinds through the
runtime."""

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
    assert [kind for kind, _ in runtime.heard] == [BELIEF, PREDICTION]
    assert all(handler("urn:test:nothing") == [] for _, handler in runtime.heard)
    assert heard == ["urn:test:nothing", "urn:test:nothing"], "each pass says what it revised"
