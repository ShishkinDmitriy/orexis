"""Prediction over a pot, with sensing and the rules beside it: bytes become an observation
the rules revise to its sides, predictions are the instants the reading changes range, revised
the same, and a second reading replaces the first and its predictions.

Held to `worlds/a_pot_and_its_probe.trig`. The story crosses three packages — sensing's
`received` and `register`, this package's `predict`, the belief package's `revise` — which a
TEST here may import and the code may not; the loop through the planner and the executor
waits for the neighbours to read an observation's revisions.
"""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import pytest

from agent import clock
from agent.belief.revise import revise
from agent.ontology import KNOWN
from agent.prediction.predict import predict
from agent.sensing.received import received
from agent.sensing.register import register
from agent.store import graphs_of, rows

WORLD = Path(__file__).parent / "worlds" / "a_pot_and_its_probe.trig"
PROBE = "http://example.org/test#probe"

_SIDES_Q = "SELECT ?p ?range WHERE { GRAPH $g { ?obs ?p ?range } }"
_PREDICTIONS_Q = """
SELECT ?g ?start WHERE { GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?g a orexis:PredictionGraph ; dcterms:temporal/orexis:start ?start } }
ORDER BY ?start"""


def _sides(store, graph):
    return {(r["p"].rsplit("#", 1)[-1], r["range"].rsplit("#", 1)[-1]) for r in rows(store, _SIDES_Q, (), g=graph + "/revisions")}


@pytest.fixture
def pot(monkeypatch, snapshots):
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    store = snapshots.stand_in(WORLD)
    register(store)
    return store, PROBE


def _reading(store, snapshots, probe, value, minutes=0):
    """Bytes arrive: received, then the stretches are rewritten, and every graph written is
    revised — the order a container would keep."""
    at = snapshots.NOW + timedelta(minutes=minutes)
    read = graphs_of(store, *KNOWN, at=at)
    graph = received(store, snapshots.ME, probe, f'{{"value": {value}}}'.encode(), at)
    written = predict(store, snapshots.ME, probe, now=at)
    for g in (graph, *written):
        revise(store, g, read=read)
    return graph, written


def test_a_reading_under_the_floor_is_revised_to_its_sides(pot, snapshots):
    store, probe = pot
    graph, _ = _reading(store, snapshots, probe, 0.05)
    assert _sides(store, graph) >= {("below", "zamioculcas.operating"), ("inside", "zamioculcas.survival")}


def test_a_reading_inside_is_predicted_to_meet_the_floor_within_the_hour_and_each_stretch_has_its_side(pot, snapshots):
    store, probe = pot
    _, written = _reading(store, snapshots, probe, 0.25)
    opened = [(snapshots.NOW.fromisoformat(r["start"]) - snapshots.NOW).total_seconds() / 60 for r in rows(store, _PREDICTIONS_Q, ())]
    assert len(written) == 3 and abs(opened[1] - 54) <= 1 and abs(opened[2] - 83) <= 4, opened
    assert ("inside", "zamioculcas.operating") in _sides(store, written[0])
    assert {("below", "zamioculcas.operating"), ("inside", "zamioculcas.survival")} <= _sides(store, written[1])
    assert {("below", "zamioculcas.operating"), ("below", "zamioculcas.survival")} <= _sides(store, written[2])


def test_a_second_reading_replaces_the_first_and_its_predictions(pot, snapshots):
    store, probe = pot
    _, first = _reading(store, snapshots, probe, 0.25)
    graph, second = _reading(store, snapshots, probe, 0.09, minutes=16)
    standing = [r["g"] for r in rows(store, _PREDICTIONS_Q, ())]
    assert standing == second and len(first) == 3 and first[2] not in standing, "the first ladder went whole"
    assert _sides(store, graph) >= {("below", "zamioculcas.operating"), ("inside", "zamioculcas.survival")}
