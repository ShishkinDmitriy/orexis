"""Prediction over a pot, with sensing and the rules beside it: bytes become an observation
the rules revise to its sides, predictions are the instants the reading changes range, revised
the same, and a second reading replaces the first and its predictions.

Held to `worlds/a_pot_and_its_probe.trig`. The story crosses three packages — sensing's
`received` and its rule set, this package's `predict`, the belief package's `revise` — which a
TEST here may import and the code may not; the loop through the planner and the executor
waits for the neighbours to read an observation's revisions.
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
from agent.store import close_catalogue, document, graphs_of, put_document, rows

WORLD = Path(__file__).parent / "worlds" / "a_pot_and_its_probe.trig"
SENSING_RULES = Path(__file__).parents[2] / "sensing" / "rules.ttl"
BELIEF = Path(__file__).parents[2] / "belief" / "ontology.ttl"
PROBE = "http://example.org/test#probe"

_SIDES_Q = "SELECT ?p ?range WHERE { GRAPH $g { ?obs ?p ?range VALUES ?p { sensing:below sensing:inside sensing:above } } }"
_PREDICTIONS_Q = """
SELECT ?g ?start WHERE { GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?g a orexis:PredictionGraph ; dcterms:temporal/orexis:start ?start } }
ORDER BY ?start"""


def _sides(store, graph):
    return {(r["p"].rsplit("#", 1)[-1], r["range"].rsplit("#", 1)[-1]) for r in rows(store, _SIDES_Q, (), g=graph + "/revisions")}


@pytest.fixture
def pot(monkeypatch, snapshots):
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    store = snapshots.stand_in(WORLD)
    put_document(store, document(SENSING_RULES))
    put_document(store, document(BELIEF))          # what a revision is, so its row closes as a boot's does
    return store, PROBE


def _reading(store, snapshots, probe, value, minutes=0):
    """Bytes arrive: received, the reading revised — the rules conclude what it is of, its quantity
    and its sides — then the stretches are rewritten from it and revised in turn: the order a
    container keeps, belief's part hearing a graph before prediction's."""
    at = snapshots.NOW + timedelta(minutes=minutes)
    read = graphs_of(store, PUBLIC, at=at)          # beside what the world states, as belief's part revises
    [graph] = received(store, snapshots.ME, probe, f'{{"value": {value}}}'.encode(), at)
    revise(store, graph, read=read)
    close_catalogue(store)
    written = predict(store, snapshots.ME, probe, now=at)
    for g in written:
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
    assert standing == second and len(first) == 3 and first[2] not in standing, "the first stretches went whole"
    assert _sides(store, graph) >= {("below", "zamioculcas.operating"), ("inside", "zamioculcas.survival")}


#  THE PREDICT CASES WHOSE RANGES STATE A MARGIN, and the side of the operating range each stretch is
#  on: the shower's dip, held below until 0.11 — its number, 0.107389, short of the floor and its
#  margin and over the floor — and the reading held below, walked from that side.
MARGINED = [
    ("a_shower_lifts_the_reading_inside_only_past_the_floor_and_its_margin", ["inside", "below", "inside", "below", "below"]),
    ("a_reading_held_below_is_predicted_below_until_it_clears_the_margin", ["below", "inside", "above"]),
]


@pytest.mark.parametrize("case, sides", MARGINED, ids=[case for case, _ in MARGINED])
def test_the_rules_conclude_of_every_predicted_observation_the_side_its_stretch_is_on(monkeypatch, snapshots, case, sides):
    """`predict` places a stretch on a side by its own walk and writes the number and the side carried;
    sensing's rules, run over what it wrote, conclude the side on their own. They agree, the stretch
    whose number lies between the floor and its margin included — read alone, that number is inside."""
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    store = snapshots.stand_in(Path(__file__).parent / "predict" / f"{case}.trig")
    put_document(store, document(SENSING_RULES))
    written = predict(store, snapshots.ME, PROBE)
    read = graphs_of(store, PUBLIC, at=snapshots.NOW)
    for graph in written:
        revise(store, graph, read=read)
    concluded = [[p for p, r in _sides(store, graph) if r == "zamioculcas.operating"] for graph in written]
    assert concluded == [[side] for side in sides], concluded
