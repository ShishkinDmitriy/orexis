"""Prediction over a pot, with sensing and the rules beside it: bytes become a percept the rules
revise to its quantity, the foresight from it is the instants the reading changes range, and a second
reading follows the first and is what the next foresight is made from.

Held to `worlds/a_pot_and_its_probe.trig`. The story crosses three packages — sensing's
`received` and its rule set, this package's `foresee`, the belief package's `revise` — which a
TEST here may import and the code may not; the loop through the planner, which lays a ground at
each knot, is the planner's own tests'.
"""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import pytest

from agent import clock
from agent.belief.revise import revise
from agent.ontology import BELIEF, RECORD
from agent.prediction.foresee import foresee
from agent.sensing.ontology import OBSERVATION_GRAPH
from agent.sensing.received import received
from agent.store import close_catalogue, document, graphs_of, put_document, revisions_of, rows

WORLD = Path(__file__).parent / "worlds" / "a_pot_and_its_probe.trig"
SENSING_RULES = Path(__file__).parents[2] / "sensing" / "rules.ttl"
BELIEF_VOCABULARY = Path(__file__).parents[2] / "belief" / "ontology.ttl"
PROBE = "http://example.org/test#probe"

#  THE POT'S RANGES, as its world states them: operating 0.1 to 0.3, surviving 0.02 to 0.45.
OPERATING, SURVIVAL = (0.1, 0.3), (0.02, 0.45)

_NUMBER_Q = "SELECT ?v WHERE { ?o sosa:hasSimpleResult ?v }"


def _sides(number: float) -> tuple[int, int]:
    """Which side of each of the pot's ranges a number lies on, as the rules read it."""
    return tuple(-1 if number < low else 1 if number > high else 0 for low, high in (OPERATING, SURVIVAL))


def _number(store, graph) -> float:
    """The number a percept holds, in what the rules concluded of it, which is of sensing's kind."""
    (r,) = rows(store, _NUMBER_Q, [graph, *revisions_of(store, graph, kind=OBSERVATION_GRAPH)])
    return float(r["v"])


@pytest.fixture
def pot(monkeypatch, snapshots):
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    store = snapshots.stand_in(WORLD)
    put_document(store, document(SENSING_RULES))
    put_document(store, document(BELIEF_VOCABULARY))          # what a revision is, so its row closes as a boot's does
    return store, PROBE


def _reading(store, snapshots, probe, value, minutes=0):
    """Bytes arrive: received, the reading revised — the rules conclude what it is of and its
    quantity — then the foresight is made from it, as a pass makes it: the order a container keeps,
    belief's part hearing a graph before the planner lays its grounds."""
    at = snapshots.NOW + timedelta(minutes=minutes)
    read = graphs_of(store, BELIEF, at=at, common=True)          # beside what the world states, as belief's part revises
    [graph] = received(store, snapshots.ME, probe, f'{{"value": {value}}}'.encode(), at)
    revise(store, graph, read=read, kind=OBSERVATION_GRAPH)      # as sensing has belief's part revise it
    close_catalogue(store)
    return graph, foresee(store, at)


def _knots(store, foresight, at) -> list[tuple[float, float]]:
    """What the foresight answers from `at` to its horizon, as (minutes past `at`, the number laid)."""
    graphs_at = lambda t: graphs_of(store, BELIEF, RECORD, at=t, until=t)        # noqa: E731
    out, t = [], at
    while (knot := foresight.advance(store, t, foresight.horizon, graphs_at)) is not None:
        when, arrival = knot
        numbers = [float(tr.object.value) for tr in arrival if tr.predicate.value.endswith("hasSimpleResult")]
        out.append(((when - at).total_seconds() / 60, numbers[0]))
        t = when
    return out


def test_a_reading_under_the_floor_is_revised_to_its_quantity(pot, snapshots):
    store, probe = pot
    graph, _ = _reading(store, snapshots, probe, 0.05)
    assert _number(store, graph) == 0.05


def test_a_reading_inside_is_foreseen_to_meet_the_floor_within_the_hour_and_each_number_lies_on_its_side(pot, snapshots):
    store, probe = pot
    _, foresight = _reading(store, snapshots, probe, 0.25)
    knots = _knots(store, foresight, snapshots.NOW)
    sides = [_sides(0.25)] + [_sides(n) for _, n in knots]
    crossings = [(m, n) for (m, n), before, after in zip(knots, sides, sides[1:]) if before != after]
    assert len(crossings) == 2 and abs(crossings[0][0] - 54) <= 1 and abs(crossings[1][0] - 83) <= 4, knots
    assert SURVIVAL[0] <= crossings[0][1] < OPERATING[0], knots
    assert crossings[1][1] < SURVIVAL[0], knots


def test_a_second_reading_follows_the_first_and_the_foresight_is_made_from_it(pot, snapshots):
    """The first percept is kept, as what the sensor said then; the foresight is made from the second,
    the observation in hand now, and nothing of the first's is written anywhere to go (#1000)."""
    store, probe = pot
    before, first = _reading(store, snapshots, probe, 0.25)
    graph, second = _reading(store, snapshots, probe, 0.09, minutes=16)
    assert first.keys[0].lo == 0.25 and second.keys[0].lo == 0.09, "each foresight from the reading in hand"
    assert _number(store, graph) == 0.09 and _number(store, before) == 0.25, "and the first percept is kept"
    assert not graphs_of(store, "http://example.org/orexis#ForecastGraph"), "no forecast of the predictor's own"
