"""`received`, one case per file, held to a PATCH of the store it leaves.

A case in `received/` is a belief base as bytes find it — the world with the pot's ranges and
the probe's frequency, whatever percept of the sensor already stands — and the diff is what the
bytes leave: a percept of the reading, named for its sensor and its instant, in a graph of its own
holding the number it gave, who made it, when, and the percept before it, and the catalogue's
account of it — or, for a sensor reading a series, a forecast graph per stretch ahead. What the
observation is OF, its quantity and whether its sensor is stuck are the rules' to conclude
(test_rules.py).

And the chain, held by code: each percept names the one before it, a message's readings oldest
first; the latest is the one holding now, every older one's period ended where its successor's
began; and a sensor's last `sensing:stuckAfter` are kept, the rest forgotten (#944).
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import pytest

from agent import clock
from agent.ontology import PERCEPT, STATE
from agent.sensing.ontology import STUCK_AFTER_TERM
from agent.sensing.received import STUCK_AFTER, received
from agent.store import graphs_of, rows

CASES_DIR = Path(__file__).parent / "received"
WORLD = Path(__file__).parent / "worlds" / "a_pot_and_its_probe.trig"
BOARD = Path(__file__).parent / "worlds" / "a_board_and_its_peripherals.trig"
CASES = sorted(p for p in CASES_DIR.glob("*.trig") if "." not in p.stem)
TEST = "http://example.org/test#"
PROBE = TEST + "probe"
CADENCE = timedelta(seconds=900)
OBSERVED = "http://example.org/orexis/graph/observed/keeper/"     # the writer's name, for eyes

FORECAST = "http://example.org/orexis/graph/forecast/keeper/"     # the writer's name, for eyes

#  WHAT EACH CASE'S BYTES SAY, and which graphs they land in.
BYTES = {
    "a_first_reading_becomes_an_observation": (b'{"value": 0.22}', [OBSERVED + "probe_20260101T120000Z"]),
    "a_second_reading_follows_the_first": (b'{"value": 0.08}', [OBSERVED + "probe_20260101T120000Z"]),
    "a_forecast_is_a_graph_per_stretch_ahead": (
        b'{"hourly": {"time": ["2026-01-01T11:00", "2026-01-01T12:00", "2026-01-01T13:00", "2026-01-01T14:00",'
        b' "2026-01-01T15:00"], "precipitation": [0.5, 0.0, 1.2, null, 0.3]}}',
        [FORECAST + "weather_20260101T120000Z", FORECAST + "weather_20260101T140000Z"]),
}


@pytest.mark.parametrize("case", CASES, ids=[c.stem for c in CASES])
def test_received_leaves_the_observation_the_patch_says(case, monkeypatch, request, snapshots):
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    store = snapshots.stand_in(case)
    payload, expected = BYTES[case.stem]
    sensor = TEST + ("weather" if "forecast" in case.stem else "probe")
    written = received(store, snapshots.ME, sensor, payload, snapshots.NOW)
    assert written == expected
    snapshots.held_to_diff(case, request, "received", snapshots.snapshot_of(store))


def test_bytes_that_hold_no_reading_write_nothing(monkeypatch, snapshots, caplog):
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    store = snapshots.stand_in(CASES_DIR / "a_first_reading_becomes_an_observation.trig")
    before = set(snapshots.graph_names(store))
    with caplog.at_level("WARNING", logger="pipeline"):
        assert received(store, snapshots.ME, PROBE, b'{"temperature": 21}', snapshots.NOW) == []
    assert set(snapshots.graph_names(store)) == before
    assert "unread" in caplog.text


def test_a_sensor_mounted_nowhere_keeps_its_number_and_is_of_nothing(monkeypatch, snapshots):
    """What an observation is OF is the rules' to conclude from what hosts the sensor; the board's
    light sensor is mounted nowhere, so its number is kept, as every sensor's is, and nothing here
    says what it is of."""
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    store = snapshots.stand_in(BOARD)
    assert received(store, snapshots.ME, TEST + "loose", b'{"value": 0.2}', snapshots.NOW) == [OBSERVED + "loose_20260101T120000Z"]
    assert not rows(store, "SELECT ?f WHERE { GRAPH ?g { ?o sosa:hasFeatureOfInterest ?f } }", ())


def test_one_message_for_two_sensors_is_two_observations(monkeypatch, snapshots):
    """A board carrying two peripherals publishes one message; a transport hands it to sensing
    once per sensor that owns the channel, and each keeps the number its pointer finds."""
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    store = snapshots.stand_in(BOARD)
    message = b'{"temperature": 21.5, "soil": {"moisture": 0.22}}'
    written = [g for sensor in (PROBE, TEST + "thermo") for g in received(store, snapshots.ME, sensor, message, snapshots.NOW)]
    assert written == [OBSERVED + "probe_20260101T120000Z", OBSERVED + "thermo_20260101T120000Z"]
    found = rows(store, "SELECT ?s ?v WHERE { GRAPH ?g { ?o a sosa:Observation ; sosa:madeBySensor ?s ; sensing:rawResult ?v } } ORDER BY ?s", ())
    assert [(r["s"].rsplit("#", 1)[-1], float(r["v"])) for r in found] == [("probe", 0.22), ("thermo", 21.5)]


def test_a_sensor_stating_no_frequency_stands_until_the_next(monkeypatch, snapshots):
    """The board's probe states no frequency: the world made no promise about the next reading, so
    the percept has no end until the next arrives, and then ends where it begins."""
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    store = snapshots.stand_in(BOARD)
    [first] = received(store, snapshots.ME, PROBE, b'{"soil": {"moisture": 0.2}}', snapshots.NOW)
    assert _period(store, first) == (snapshots.NOW, None)
    later = snapshots.NOW + timedelta(days=1)
    [second] = received(store, snapshots.ME, PROBE, b'{"soil": {"moisture": 0.3}}', later)
    assert (_period(store, first), _period(store, second)) == ((snapshots.NOW, later), (later, None))


def test_every_case_is_read_and_no_diff_is_orphaned(snapshots):
    assert set(BYTES) == {c.stem for c in CASES}, [c.name for c in CASES]
    assert not snapshots.orphans_in(CASES_DIR)


#  ── the chain ─────────────────────────────────────────────────────────────────────────────────

#  EVERY PERCEPT KEPT OF A SENSOR, oldest first: its node, its number, and the one it names before it.
_CHAIN_Q = """
SELECT ?o ?n ?t ?previous WHERE {
  GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?g a sensing:ObservationGraph }
  GRAPH ?g { ?o sosa:madeBySensor $sensor ; sensing:rawResult ?n ; sosa:resultTime ?t
             OPTIONAL { ?o sensing:previous ?previous } } }
ORDER BY ?t"""

_PERIOD_Q = """SELECT ?start ?end WHERE { GRAPH ?cat { ?cat a orexis:CatalogueGraph . $g dcterms:temporal ?p .
               ?p orexis:start ?start . OPTIONAL { ?p orexis:end ?end } } }"""


def _chain(store, sensor=PROBE) -> list[tuple[str, float, str | None]]:
    return [(r["o"], float(r["n"]), r.get("previous")) for r in rows(store, _CHAIN_Q, (), sensor=sensor)]


def _period(store, graph) -> tuple:
    (r,) = rows(store, _PERIOD_Q, (), g=graph)
    return datetime.fromisoformat(r["start"]), datetime.fromisoformat(r["end"]) if r.get("end") else None


def _every_cadence(store, snapshots, numbers, start: datetime | None = None) -> datetime:
    """One reading of each of `numbers` by the probe, a cadence apart from `start`; the last one's instant."""
    at = start or snapshots.NOW
    for number in numbers:
        received(store, snapshots.ME, PROBE, f'{{"value": {number}}}'.encode(), at)
        at += CADENCE
    return at - CADENCE


def test_each_reading_names_the_one_before_it_and_only_the_last_stuck_after_are_kept(monkeypatch, snapshots):
    """Eight readings a cadence apart: each is a percept of its own, naming the one before it, and the
    sensor keeps its last `STUCK_AFTER` — the oldest kept names one that is gone, and what was concluded
    of a forgotten one goes with it."""
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    store = snapshots.stand_in(WORLD)
    numbers = [round(0.20 + n / 100, 2) for n in range(STUCK_AFTER + 2)]
    _every_cadence(store, snapshots, numbers)
    chain = _chain(store)
    assert [n for _, n, _ in chain] == numbers[-STUCK_AFTER:], "the last six, oldest first"
    assert all(previous == before for (_, _, previous), (before, _, _) in zip(chain[1:], chain)), chain
    assert chain[0][2] is not None and chain[0][2] not in {o for o, _, _ in chain}, "the oldest kept names one forgotten"
    assert len(graphs_of(store, PERCEPT)) == STUCK_AFTER


def test_the_depth_kept_is_the_agents_where_its_self_graph_states_one(monkeypatch, snapshots):
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    store = snapshots.stating(snapshots.stand_in(WORLD), {STUCK_AFTER_TERM: 2})
    _every_cadence(store, snapshots, [0.2, 0.21, 0.22, 0.23])
    assert [n for _, n, _ in _chain(store)] == [0.22, 0.23]


def test_the_latest_is_the_one_holding_now_and_every_older_one_has_ended(monkeypatch, snapshots):
    """A reader standing at an instant is handed one percept of a sensor: the latest holds from its
    instant until the next is due and a grace past it, and each older one ended where the next began."""
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    store = snapshots.stand_in(WORLD)
    last = _every_cadence(store, snapshots, [0.2, 0.21, 0.22])
    [(latest, _, _)] = [c for c in _chain(store) if c[1] == 0.22]
    holding = graphs_of(store, PERCEPT, at=last, now=last)
    assert holding == [OBSERVED + "probe_" + last.strftime("%Y%m%dT%H%M%SZ")], holding
    assert graphs_of(store, PERCEPT, at=last - timedelta(seconds=1), now=last) == [OBSERVED + "probe_" + (last - CADENCE).strftime("%Y%m%dT%H%M%SZ")]
    assert _period(store, holding[0]) == (last, last + 2 * CADENCE), "until the next is due and a grace past it"
    assert not graphs_of(store, PERCEPT, at=last + 2 * CADENCE, now=last), "and none past that"
    assert not graphs_of(store, STATE), "a percept is no state"


def test_a_message_carrying_several_readings_chains_them_in_order(monkeypatch, snapshots):
    """A sentinel's alarm carries its watcher's last quiet sample and the reading that broke the window:
    two percepts, the earlier made 25 seconds before and holding only until the reading's instant, and
    the reading naming it as its previous; the percept before the message names nothing new, and ends
    where the earlier begins. A heartbeat's one element follows the reading, at the same instant."""
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    store = snapshots.stand_in(CASES_DIR / "a_first_reading_becomes_an_observation.trig")
    before = snapshots.NOW - CADENCE
    [quiet] = received(store, snapshots.ME, PROBE, b'{"value": 640}', before)
    alarm = b'{"value": [{"value": 656, "age_s": 25}, {"value": 361, "age_s": 0}]}'
    earlier, reading = received(store, snapshots.ME, PROBE, alarm, snapshots.NOW)
    assert (earlier, reading) == (OBSERVED + "probe_20260101T115935Z", OBSERVED + "probe_20260101T120000Z")
    assert [(o.rsplit("#", 1)[-1], n, p and p.rsplit("#", 1)[-1]) for o, n, p in _chain(store)] == [
        ("obs_probe_20260101T114500Z", 640.0, None),
        ("obs_probe_20260101T115935Z", 656.0, "obs_probe_20260101T114500Z"),
        ("obs_probe_20260101T120000Z", 361.0, "obs_probe_20260101T115935Z")]
    assert _period(store, quiet)[1] == snapshots.NOW - timedelta(seconds=25), "ended where the earlier began"
    assert _period(store, earlier) == (snapshots.NOW - timedelta(seconds=25), snapshots.NOW)
    assert graphs_of(store, PERCEPT, at=snapshots.NOW, now=snapshots.NOW) == [reading]
    heartbeat = b'{"value": [{"value": 370, "age_s": 0}]}'
    [beat] = received(store, snapshots.ME, PROBE, heartbeat, snapshots.NOW)
    assert beat == OBSERVED + "probe_20260101T120000Z_2", "a second reading at one instant is named apart"
    assert [p for o, _, p in _chain(store) if o.endswith("_2")] == [TEST.replace("test#", "orexis#") + "obs_probe_20260101T120000Z"]
    assert graphs_of(store, PERCEPT, at=snapshots.NOW, now=snapshots.NOW) == [beat]
