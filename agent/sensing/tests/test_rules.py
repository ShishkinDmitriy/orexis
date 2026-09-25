"""`rules.ttl`: this layer's rule set, a document saying it is a `sh:RulesGraph`, put in the
store as a boot puts every document, and held — through the belief package's `revise`, which a
test here may import and the code may not — to what it concludes of an observation against its
subject's ranges.
"""

from __future__ import annotations

from datetime import timezone
from pathlib import Path

import pytest

from agent import clock
from agent.belief.revise import revise
from agent.ontology import KNOWN
from agent.belief.ontology import RULES_GRAPH
from agent.sensing.ontology import ABOVE, BELOW, INSIDE
from agent.sensing.received import received
from agent.store import document, graphs_of, put_document, rows

WORLD = Path(__file__).parent / "worlds" / "a_pot_and_its_probe.trig"
RULES = Path(__file__).parents[1] / "rules.ttl"
TEST = "http://example.org/test#"
PROBE = TEST + "probe"

_SIDES_Q = "SELECT ?p ?range WHERE { GRAPH $g { ?obs ?p ?range } }"


def _sides(store, graph: str) -> set[tuple[str, str]]:
    return {(r["p"].rsplit("#", 1)[-1], r["range"].rsplit("#", 1)[-1])
            for r in rows(store, _SIDES_Q, (), g=graph + "/revisions")}


@pytest.fixture
def world(monkeypatch, snapshots):
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    store = snapshots.stand_in(WORLD)
    put_document(store, document(RULES))
    return store


def _read(store, snapshots, sensor, value: float) -> str:
    graph = received(store, snapshots.ME, sensor, f'{{"value": {value}}}'.encode(), snapshots.NOW)
    revise(store, graph, read=graphs_of(store, *KNOWN, at=snapshots.NOW))
    return graph


def test_the_rules_graph_is_the_drafts_kind_and_named_by_its_document(world):
    assert graphs_of(world, RULES_GRAPH) == [RULES.resolve().as_uri()]
    assert put_document(world, document(RULES)) == graphs_of(world, RULES_GRAPH), "put again, one graph"


def test_a_reading_under_the_floor_is_below_the_operating_range_and_inside_the_survival_one(world, snapshots):
    graph = _read(world, snapshots, PROBE, 0.05)
    assert _sides(world, graph) == {("below", "zamioculcas.operating"), ("inside", "zamioculcas.survival"), ("inside", "probe.operating")}


def test_a_reading_inside_is_inside_every_range(world, snapshots):
    graph = _read(world, snapshots, PROBE, 0.2)
    assert {p for p, _ in _sides(world, graph)} == {"inside"}


def test_a_reading_over_the_ceiling_is_above(world, snapshots):
    graph = _read(world, snapshots, PROBE, 0.5)
    assert _sides(world, graph) == {("above", "zamioculcas.operating"), ("above", "zamioculcas.survival"), ("inside", "probe.operating")}


def test_a_bound_is_inside(world, snapshots):
    graph = _read(world, snapshots, PROBE, 0.1)
    assert ("inside", "zamioculcas.operating") in _sides(world, graph)


def test_a_samples_observation_is_judged_by_its_subjects_ranges(monkeypatch, snapshots):
    """A probe mounted in a patch of the pot — `sosa:isHostedBy` a `sosa:Sample` that
    `sosa:isSampleOf` it, the received case's world — keys its node by the patch and is judged
    by the pot's ranges."""
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    world = snapshots.stand_in(Path(__file__).parent / "received" / "a_probes_sample_keys_the_node.trig")
    put_document(world, document(RULES))
    graph = _read(world, snapshots, PROBE, 0.05)
    assert graph.endswith("/patch_moisture")
    assert ("below", "zamioculcas.operating") in _sides(world, graph)
