"""`foresee`, one case per file, held to the knots the integration answers.

A case in `foresee/` is a belief base with an observation in hand, the pot's ranges and the flows the
domain declares. The integration is advanced from noon to the horizon as the planner advances it,
reading the case's beliefs holding at each instant, and what it answers is the knots: every crossing
of a range bound, with the number laid there on the new side, and the hour's end where the key moved,
with the number it then stands at. No forecast is written (#1000): what the knots come to is what the
planner lays a ground at.
"""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import pytest

from agent import clock
from agent.ontology import BELIEF, RECORD
from agent.prediction.foresee import SEGMENT_S, NUMBERS, foresee
from agent.prediction.ranges import ranges_of, side
from agent.store import catalogue_of, graphs_of, quads, rows

CASES_DIR = Path(__file__).parent / "foresee"
CASES = sorted(CASES_DIR.glob("*.trig"))
PROBE = "http://example.org/test#probe"
MOISTURE = "http://example.org/test#moisture"
HYGROMETER = "http://example.org/test#hygrometer"

#  WHERE THE PROBE'S KEY CROSSES A BOUND, in minutes past noon, with the minutes a crossing may be
#  placed within: a crossing is placed by division and rounded up to the whole second. The arithmetic
#  is the flow's: 0.25 less the rate per day, so the operating floor at 0.10 is met 0.15 / rate days out
#  and the survival floor at 0.02 is met 0.23 / rate days out. The shower, the corridor, the dose and
#  the room's air are read in their own files. None where no flow moves the key.
CROSSINGS = {
    "a_slow_dryer_crosses_the_floor_after_seven_hours": [(432, 0.02), (662.4, 0.02)],
    "a_fast_dryer_crosses_both_floors_within_two_hours": [(54, 0.02), (82.8, 0.02)],
    "a_reading_already_below_crosses_only_the_survival_floor": [(86.4, 0.02)],
    "a_key_no_flow_moves_is_predicted_nothing": None,
    "two_flows_moving_one_property_add": [(36, 0.02), (55.2, 0.02)],
    "a_forecast_shower_lifts_the_reading_back_inside": [(28.8, 0.02), (144, 0.02), (316.8, 0.02), (432, 0.02)],
    "a_forecast_range_opens_a_corridor_on_its_dry_side": [(28.8, 0.02), (144, 0.02)],
    "a_committed_dose_lifts_the_reading_over_its_window": [(61.2, 0.02), (90, 0.02)],
    "a_key_is_predicted_from_another_keys_prediction": [(54, 0.02)],
}


def _every_knot(store, foresight, now, until=None) -> list[tuple[float, dict[str, float]]]:
    """Every knot the integration answers from `now` to its horizon — or to `until` — as (minutes past
    `now`, the number laid per sensor), advanced as the planner advances it: to each knot, reading the
    case's beliefs holding at the instant asked."""
    graphs_at = lambda t: graphs_of(store, BELIEF, RECORD, at=t, until=t)        # noqa: E731
    out, t = [], now
    while (knot := foresight.advance(store, t, until or foresight.horizon, graphs_at)) is not None:
        when, arrival = knot
        sensors = {tr.subject: tr.object.value for tr in arrival if tr.predicate.value.endswith("madeBySensor")}
        out.append(((when - now).total_seconds() / 60,
                    {sensors[tr.subject]: float(tr.object.value) for tr in arrival if tr.predicate.value.endswith("hasSimpleResult")}))
        t = when
    return out


def _knots(store, foresight, now, sensor, until=None) -> list[tuple[float, float]]:
    """The knots of `sensor` alone, as (minutes past `now`, the number laid)."""
    return [(minute, laid[sensor]) for minute, laid in _every_knot(store, foresight, now, until) if sensor in laid]


def _sides(store, sensor, prop, number) -> tuple[int, ...]:
    return tuple(side(low, high, number) for low, high in ranges_of(store, sensor, prop))


def _reading(store, sensor) -> float:
    percepts = graphs_of(store, "http://example.org/orexis/sensing#ObservationGraph")
    (r,) = rows(store, "SELECT ?v WHERE { ?o sosa:madeBySensor $s ; sosa:hasSimpleResult ?v }", percepts, s=sensor)
    return float(r["v"])


@pytest.mark.parametrize("case", CASES, ids=[c.stem for c in CASES])
def test_foresee_answers_the_crossings_the_case_says_and_a_knot_an_hour_at_most_apart(case, monkeypatch, snapshots):
    """The knots whose number lies on a side the knot before did not are the crossings, placed where the
    table says; between two knots an hour at most passes while the key moves; and the working graph the
    flows read the numbers off is gone once the integration is finished."""
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    store = snapshots.stand_in(case)
    foresight = foresee(store, snapshots.NOW)
    if CROSSINGS[case.stem] is None:
        assert foresight is None or _every_knot(store, foresight, snapshots.NOW) == [], \
            "no flow moves the key, so nothing is foreseen and nothing is laid"
        return
    every = _every_knot(store, foresight, snapshots.NOW)
    knots = [(minute, laid[PROBE]) for minute, laid in every if PROBE in laid]
    sides = [_sides(store, PROBE, MOISTURE, _reading(store, PROBE))] + [_sides(store, PROBE, MOISTURE, n) for _, n in knots]
    crossings = [minute for (minute, _), before, after in zip(knots, sides, sides[1:]) if before != after]
    assert len(crossings) == len(CROSSINGS[case.stem]), (knots, crossings)
    for got, (minute, within) in zip(crossings, CROSSINGS[case.stem]):
        assert abs(got - minute) <= within + 1e-9, (crossings, CROSSINGS[case.stem])
    assert all(b - a <= SEGMENT_S / 60 + 1e-9 for (a, _), (b, _) in zip(every, every[1:])), every
    foresight.finish(store)
    assert not list(quads(store, NUMBERS)), "the numbers are the integration's, and go with it"


def test_two_keys_advance_together_and_one_reads_the_other_as_it_stands(monkeypatch, snapshots):
    """THE SOIL DRIES BY THE AIR (#996, as #1000 keeps it). The room's air gains 0.4 an hour until it is
    saturated and crosses its ceiling at 0.9 at one; the soil's flow reads the air's number off the
    working graph at every instant it is asked at — 0.5 at noon, so four fractions a day for the hour
    the rate is held — and meets its floor at 12:54. The two are advanced at the same instants over
    the same graphs, nothing orders them, and no forecast of either is written anywhere."""
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    store = snapshots.stand_in(CASES_DIR / "a_key_is_predicted_from_another_keys_prediction.trig")
    foresight = foresee(store, snapshots.NOW)
    assert sorted(k.sensor.rsplit("#", 1)[-1] for k in foresight.keys) == ["hygrometer", "probe"]
    graphs_at = lambda t: graphs_of(store, BELIEF, RECORD, at=t, until=t)        # noqa: E731
    first = foresight.advance(store, snapshots.NOW, foresight.horizon, graphs_at)
    assert first is not None and abs((first[0] - snapshots.NOW).total_seconds() - 54 * 60) <= 1, first
    second = foresight.advance(store, first[0], foresight.horizon, graphs_at)
    assert second is not None and abs((second[0] - snapshots.NOW).total_seconds() - 3601) <= 1, "the air at its ceiling"
    [(n,)] = [[float(tr.object.value) for tr in second[1] if tr.predicate.value.endswith("hasSimpleResult")]]
    assert n >= 0.9, n
    assert not graphs_of(store, "http://example.org/orexis#ForecastGraph"), "nothing is written"


def test_the_horizon_is_the_agents_stance_where_its_self_graph_states_one(monkeypatch, snapshots):
    """`prediction:horizonS 28800` in the keeper's self graph (knowledge/domain/kernel/stance.md):
    the slow dryer is foreseen for eight hours past its observation, so the floor at seven hours
    and twelve minutes is foreseen and the survival floor at eleven is not."""
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    store = snapshots.stand_in(CASES_DIR / "a_slow_dryer_crosses_the_floor_after_seven_hours.trig")
    store.update(f"""PREFIX orexis: <http://example.org/orexis#> PREFIX prediction: <http://example.org/orexis/prediction#>
INSERT DATA {{ GRAPH <urn:test:self> {{ <{snapshots.ME}> a orexis:Self ; prediction:horizonS 28800 }}
               GRAPH <{catalogue_of(store)}> {{ <urn:test:self> a orexis:SelfGraph , orexis:BeliefGraph , orexis:Graph ;
                                                       orexis:ownedBy <{snapshots.ME}> }} }}""")
    foresight = foresee(store, snapshots.NOW)
    assert foresight.horizon == snapshots.NOW + timedelta(hours=8)
    knots = _knots(store, foresight, snapshots.NOW, PROBE)
    assert knots and all(m <= 480 for m, _ in knots) and any(abs(m - 432) <= 0.02 for m, _ in knots), knots
    assert not any(abs(m - 662.4) <= 0.02 for m, _ in knots), "the survival floor lies past the horizon"


def test_every_case_is_read(snapshots):
    assert len(CASES) >= 3, [c.name for c in CASES]
    assert set(CROSSINGS) == {c.stem for c in CASES}
