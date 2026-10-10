"""Prediction over a pot, with sensing and the rules beside it: bytes become a percept the rules
revise to its quantity, predictions are the instants the reading changes range, and a second reading
follows the first and replaces its predictions.

Held to `worlds/a_pot_and_its_probe.trig`. The story crosses three packages — sensing's
`received` and its rule set, this package's `predict`, the belief package's `revise` — which a
TEST here may import and the code may not; the loop through the planner and the executor
waits for the neighbours to read a percept's revisions.
"""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import pytest

from agent import clock
from agent.belief.revise import revise
from agent.ontology import PUBLIC
from agent.prediction.predict import predict
from agent.sensing.received import received
from agent.store import close_catalogue, document, graphs_of, put_document, revisions_of, rows

WORLD = Path(__file__).parent / "worlds" / "a_pot_and_its_probe.trig"
SENSING_RULES = Path(__file__).parents[2] / "sensing" / "rules.ttl"
BELIEF = Path(__file__).parents[2] / "belief" / "ontology.ttl"
PROBE = "http://example.org/test#probe"

#  THE POT'S RANGES, as its world states them: operating 0.1 to 0.3, surviving 0.02 to 0.45.
OPERATING, SURVIVAL = (0.1, 0.3), (0.02, 0.45)

_NUMBER_Q = "SELECT ?v WHERE { ?o sosa:hasSimpleResult ?v }"
_PREDICTIONS_Q = """
SELECT ?g ?start WHERE { GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?g a orexis:PredictionGraph ; dcterms:temporal/orexis:start ?start } }
ORDER BY ?start"""


def _number(store, graph) -> float:
    (r,) = rows(store, _NUMBER_Q, [graph, *revisions_of(store, graph)])
    return float(r["v"])


@pytest.fixture
def pot(monkeypatch, snapshots):
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    store = snapshots.stand_in(WORLD)
    put_document(store, document(SENSING_RULES))
    put_document(store, document(BELIEF))          # what a revision is, so its row closes as a boot's does
    return store, PROBE


def _reading(store, snapshots, probe, value, minutes=0):
    """Bytes arrive: received, the reading revised — the rules conclude what it is of and its
    quantity — then the stretches are rewritten from it: the order a container keeps, belief's part
    hearing a graph before prediction's."""
    at = snapshots.NOW + timedelta(minutes=minutes)
    read = graphs_of(store, PUBLIC, at=at)          # beside what the world states, as belief's part revises
    [graph] = received(store, snapshots.ME, probe, f'{{"value": {value}}}'.encode(), at)
    revise(store, graph, read=read)
    close_catalogue(store)
    return graph, predict(store, snapshots.ME, probe, now=at)


def test_a_reading_under_the_floor_is_revised_to_its_quantity(pot, snapshots):
    store, probe = pot
    graph, _ = _reading(store, snapshots, probe, 0.05)
    assert _number(store, graph) == 0.05


def test_a_reading_inside_is_predicted_to_meet_the_floor_within_the_hour_and_each_stretch_lies_on_its_side(pot, snapshots):
    store, probe = pot
    _, written = _reading(store, snapshots, probe, 0.25)
    opened = [(snapshots.NOW.fromisoformat(r["start"]) - snapshots.NOW).total_seconds() / 60 for r in rows(store, _PREDICTIONS_Q, ())]
    assert len(written) == 3 and abs(opened[1] - 54) <= 1 and abs(opened[2] - 83) <= 4, opened
    numbers = [_number(store, g) for g in written]
    assert OPERATING[0] <= numbers[0] <= OPERATING[1], numbers
    assert SURVIVAL[0] <= numbers[1] < OPERATING[0], numbers
    assert numbers[2] < SURVIVAL[0], numbers


def test_a_second_reading_follows_the_first_and_replaces_its_predictions(pot, snapshots):
    """The first percept is kept, as what the sensor said then; what was predicted from it is not, since
    the second is the observation in hand now — every stretch of the first goes whole (#944)."""
    store, probe = pot
    before, first = _reading(store, snapshots, probe, 0.25)
    graph, second = _reading(store, snapshots, probe, 0.09, minutes=16)
    standing = [r["g"] for r in rows(store, _PREDICTIONS_Q, ())]
    assert standing == second and len(first) == 3 and first[2] not in standing, "the first stretches went whole"
    assert _number(store, graph) == 0.09 and _number(store, before) == 0.25, "and the first percept is kept"
