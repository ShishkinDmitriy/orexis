"""`register`: this layer's rules put where the deliberator runs them, and held — through the
belief package's `revise`, which a test here may import and the code may not — to what they
conclude of an observation against its subject's ranges.
"""

from __future__ import annotations

from datetime import timezone
from pathlib import Path

import pytest

from agent import clock
from agent.belief.revise import revise
from agent.ontology import KNOWN
from agent.sensing.ontology import ABOVE, BELOW, INSIDE, RULES_GRAPH
from agent.sensing.received import received
from agent.sensing.register import register
from agent.store import graphs_of, rows

WORLD = Path(__file__).parent / "worlds" / "a_pot_and_its_probe.trig"
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
    register(store)
    return store


def _read(store, snapshots, sensor, value: float) -> str:
    graph = received(store, snapshots.ME, sensor, f'{{"value": {value}}}'.encode(), snapshots.NOW)
    revise(store, graph, read=graphs_of(store, *KNOWN, at=snapshots.NOW))
    return graph


def test_the_rules_graph_is_the_drafts_kind(world):
    assert graphs_of(world, RULES_GRAPH) == ["http://example.org/orexis/graph/rules/sensing"]
    assert register(world) == graphs_of(world, RULES_GRAPH)[0], "registered again, one graph"


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
    register(world)
    graph = _read(world, snapshots, PROBE, 0.05)
    assert graph.endswith("/patch_moisture")
    assert ("below", "zamioculcas.operating") in _sides(world, graph)
