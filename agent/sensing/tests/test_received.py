"""`received`, one case per file, held to a PATCH of the store it leaves.

A case in `received/` is a belief base as bytes find it — the world with the pot's ranges and
the probe's frequency, whatever observation by the sensor already stands — and the diff is what
the bytes leave: the sensor's graph holding one sosa:Observation with the number it gave, who made
it and when, and the catalogue's account of it, holding until the next reading is due — or, for a
sensor reading a series, a forecast graph per stretch ahead. What the observation is OF, its
quantity and its sides are the rules' to conclude (test_rules.py).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from datetime import datetime, timedelta

from agent import clock
from agent.ontology import STATE
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
    "a_first_reading_becomes_an_observation": (b'{"value": 0.22}', [OBSERVED + "probe"]),
    "a_second_reading_replaces_the_first": (b'{"value": 0.08}', [OBSERVED + "probe"]),
    "a_reading_carries_the_side_the_one_it_replaces_was_judged_on": (b'{"value": 0.101}', [OBSERVED + "probe"]),
    "a_number_unchanged_past_the_limit_says_the_sensor_stuck": (b'{"value": 0.25}', [OBSERVED + "probe"]),
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
    assert received(store, snapshots.ME, TEST + "loose", b'{"value": 0.2}', snapshots.NOW) == [OBSERVED + "loose"]
    assert not rows(store, "SELECT ?f WHERE { GRAPH ?g { ?o sosa:hasFeatureOfInterest ?f } }", ())


def test_one_message_for_two_sensors_is_two_observations(monkeypatch, snapshots):
    """A board carrying two peripherals publishes one message; a transport hands it to sensing
    once per sensor that owns the channel, and each keeps the number its pointer finds."""
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    store = snapshots.stand_in(BOARD)
    message = b'{"temperature": 21.5, "soil": {"moisture": 0.22}}'
    written = [g for sensor in (PROBE, TEST + "thermo") for g in received(store, snapshots.ME, sensor, message, snapshots.NOW)]
    assert written == [OBSERVED + "probe", OBSERVED + "thermo"]
    found = rows(store, "SELECT ?s ?v WHERE { GRAPH ?g { ?o a sosa:Observation ; sosa:madeBySensor ?s ; sensing:rawResult ?v } } ORDER BY ?s", ())
    assert [(r["s"].rsplit("#", 1)[-1], float(r["v"])) for r in found] == [("probe", 0.22), ("thermo", 21.5)]


def test_a_sensor_stating_no_frequency_stands_until_replaced(monkeypatch, snapshots):
    """The board's probe states no frequency: the world made no promise about the next
    reading, so the observation has no end."""
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    store = snapshots.stand_in(BOARD)
    [graph] = received(store, snapshots.ME, PROBE, b'{"soil": {"moisture": 0.2}}', snapshots.NOW)
    period = rows(store, "SELECT ?start ?end WHERE { GRAPH ?cat { ?cat a orexis:CatalogueGraph . $g dcterms:temporal ?p . "
                         "?p orexis:start ?start . OPTIONAL { ?p orexis:end ?end } } }", (), g=graph)
    assert len(period) == 1 and period[0].get("end") is None, period


def test_every_case_is_read_and_no_diff_is_orphaned(snapshots):
    assert set(BYTES) == {c.stem for c in CASES}, [c.name for c in CASES]
    assert not snapshots.orphans_in(CASES_DIR)



def test_an_array_of_readings_is_an_observation_each_the_earlier_ending_at_the_next(monkeypatch, snapshots):
    """A sentinel's alarm carries its watcher's last quiet sample and the reading that broke the window:
    the earlier is an observation of its own, made 25 seconds before and holding only until the
    reading's instant, so at that instant the reading alone holds; a heartbeat's one element takes it
    away again."""
    from datetime import datetime, timedelta

    from agent.ontology import STATE
    from agent.store import graphs_of

    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    store = snapshots.stand_in(CASES_DIR / "a_first_reading_becomes_an_observation.trig")
    alarm = b'{"value": [{"value": 656, "age_s": 25}, {"value": 361, "age_s": 0}]}'
    assert received(store, snapshots.ME, PROBE, alarm, snapshots.NOW) == [OBSERVED + "probe_earlier_0", OBSERVED + "probe"]
    said = {r["g"].rsplit("/", 1)[-1]: (float(r["n"]), datetime.fromisoformat(r["t"])) for r in rows(
        store, "SELECT ?g ?n ?t WHERE { GRAPH ?g { ?o sensing:rawResult ?n ; sosa:resultTime ?t } }", ())}
    assert said == {"probe_earlier_0": (656.0, snapshots.NOW - timedelta(seconds=25)), "probe": (361.0, snapshots.NOW)}
    assert OBSERVED + "probe_earlier_0" not in graphs_of(store, STATE, at=snapshots.NOW), "ended at the reading's instant"
    heartbeat = b'{"value": [{"value": 370, "age_s": 0}]}'
    assert received(store, snapshots.ME, PROBE, heartbeat, snapshots.NOW) == [OBSERVED + "probe"]
    assert OBSERVED + "probe_earlier_0" not in snapshots.graph_names(store), "the alarm's earlier reading is gone"


#  THE SENSORS SAID STUCK: the row, the instant it says, and the graph's own start.
_STUCK_Q = """
SELECT ?sensor ?since ?start WHERE {
  GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?g a orexis:StateGraph ; orexis:arrivedBy orexis:Derived ;
               dcterms:temporal/orexis:start ?start }
  GRAPH ?g { ?sensor sensing:stuckSince ?since } }"""

_RUN_Q = "SELECT ?since WHERE { ?o sosa:madeBySensor $sensor ; sensing:unchangedSince ?since }"


def _stuck(store):
    return [(r["sensor"], datetime.fromisoformat(r["since"]), datetime.fromisoformat(r["start"]))
            for r in rows(store, _STUCK_Q, ())]


def _run_of(store, sensor, at):
    found = rows(store, _RUN_Q, graphs_of(store, STATE, at=at, now=at), sensor=sensor)
    return datetime.fromisoformat(found[0]["since"]) if found else None


def _every_cadence(store, snapshots, number: float, readings: int, start: datetime | None = None) -> datetime:
    """`readings` readings of `number` by the probe, one per cadence from `start`; the last one's instant."""
    at = start or snapshots.NOW
    for _ in range(readings):
        received(store, snapshots.ME, PROBE, f'{{"value": {number}}}'.encode(), at)
        at += CADENCE
    return at - CADENCE


def test_a_number_unchanged_past_the_limit_says_the_sensor_stuck_once(monkeypatch, snapshots):
    """#462: the probe gives 0.25 at every reading, on time. Through `STUCK_AFTER` cadences nothing
    is said, since still soil and a frozen probe look alike for a while; at the limit the probe is
    said stuck since the run's first reading — named for the state, not for the reading that tipped
    it — and a reading later it is not said again."""
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    store = snapshots.stand_in(WORLD)
    last = _every_cadence(store, snapshots, 0.25, STUCK_AFTER)
    assert _run_of(store, PROBE, last) == snapshots.NOW, "the run began with the first reading"
    assert _stuck(store) == [], f"{STUCK_AFTER} readings are {STUCK_AFTER - 1} cadences unchanged, short of the limit"
    tipped = _every_cadence(store, snapshots, 0.25, 1, last + CADENCE)
    said = _stuck(store)
    assert said == [(PROBE, snapshots.NOW, snapshots.NOW)]
    _every_cadence(store, snapshots, 0.25, 1, tipped + CADENCE)
    assert _stuck(store) == said, "said once"


def test_a_reading_whose_number_differs_ends_the_run_and_the_stuck(monkeypatch, snapshots):
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    store = snapshots.stand_in(WORLD)
    last = _every_cadence(store, snapshots, 0.25, STUCK_AFTER + 1)
    assert _stuck(store)
    moved = last + CADENCE
    received(store, snapshots.ME, PROBE, b'{"value": 0.26}', moved)
    assert _stuck(store) == []
    assert _run_of(store, PROBE, moved) == moved, "a new number is a new run, from this reading"
    last = _every_cadence(store, snapshots, 0.26, STUCK_AFTER - 1, moved + CADENCE)
    assert _stuck(store) == [], "the new run is counted from its own start, and is a cadence short"
    _every_cadence(store, snapshots, 0.26, 1, last + CADENCE)
    assert _stuck(store) == [(PROBE, moved, moved)]


def test_a_number_a_count_apart_is_two_numbers(monkeypatch, snapshots):
    """Identical means the raw number: a probe creeping by a count is alive to this detector, and the
    page says whose that case is."""
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    store = snapshots.stand_in(WORLD)
    at = snapshots.NOW
    for n in range(STUCK_AFTER + 2):
        received(store, snapshots.ME, PROBE, f'{{"value": {1330 + (n % 2)}}}'.encode(), at)
        at += CADENCE
    assert _stuck(store) == [] and _run_of(store, PROBE, at - CADENCE) == at - CADENCE


def test_a_sensor_stating_no_frequency_is_never_said_stuck(monkeypatch, snapshots):
    """The board's probe states no frequency, so the limit has no cadence to count in — as its
    silence is never said, since the world made no promise about how often its number could move."""
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    store = snapshots.stand_in(BOARD)
    at = snapshots.NOW
    for _ in range(STUCK_AFTER + 2):
        received(store, snapshots.ME, PROBE, b'{"soil": {"moisture": 0.2}}', at)
        at += timedelta(days=1)
    assert _stuck(store) == [] and _run_of(store, PROBE, at) == snapshots.NOW


def test_the_stuck_limit_is_the_agents_where_its_self_graph_states_one(monkeypatch, snapshots):
    """The keeper's self graph says `sensing:stuckAfter 2`, a stance: the probe's number, unchanged
    through two cadences, is stuck where the figure in code would have waited six."""
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    store = snapshots.stating(snapshots.stand_in(WORLD), {STUCK_AFTER_TERM: 2})
    last = _every_cadence(store, snapshots, 0.25, 2)
    assert _stuck(store) == [], "two readings are one cadence unchanged"
    received(store, snapshots.ME, PROBE, b'{"value": 0.25}', last + CADENCE)
    assert _stuck(store) == [(PROBE, snapshots.NOW, snapshots.NOW)]


#  WHAT THE NEW OBSERVATION CARRIES: each side the one before was judged on, and the range.
CARRIES = CASES_DIR / "a_reading_carries_the_side_the_one_it_replaces_was_judged_on.trig"
_CARRIED_Q = "SELECT ?word ?range WHERE { GRAPH ?g { ?o sosa:madeBySensor $sensor ; ?word ?range . VALUES ?word { orexis:wasBelow orexis:wasAbove } } }"


def _carried(store) -> set[tuple[str, str]]:
    return {(r["word"].rsplit("#", 1)[-1], r["range"].rsplit("#", 1)[-1]) for r in rows(store, _CARRIED_Q, (), sensor=PROBE)}


def _carrying(snapshots, text: str):
    """The case `CARRIES` describes, its text edited, and 0.101 received at noon."""
    store = snapshots.stand_in(CARRIES, text)
    received(store, snapshots.ME, PROBE, b'{"value": 0.101}', snapshots.NOW)
    return store


@pytest.mark.parametrize("edit, carried", [
    (("", ""), {("wasBelow", "zamioculcas.operating")}),
    (("orexis:margin 0.002 ; ", ""), set()),
    (("orexis:margin 0.002 ; ", "orexis:margin 0.0 ; "), set()),
    (("  orexis:obs_probe sensing:below :zamioculcas.operating .\n", ""), set()),
    (("sensing:below :zamioculcas.operating", "sensing:above :zamioculcas.operating"), {("wasAbove", "zamioculcas.operating")}),
], ids=["below-a-range-stating-a-margin", "no-margin", "a-margin-of-nought", "no-side-concluded", "above"])
def test_a_reading_carries_the_side_of_a_range_stating_a_margin_and_nothing_else(monkeypatch, snapshots, edit, carried):
    """Only a range stating a margin above nought is carried for, and only where the rules concluded
    the replaced observation below or above it. Where its revisions say no side — the revision cut
    short by its budget — nothing is carried and the reading is judged alone, as a range stating no
    margin judges every reading: the store is handed no side it has no evidence for."""
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    text = CARRIES.read_text()
    assert edit[0] in text
    assert _carried(_carrying(snapshots, text.replace(*edit))) == carried


def test_every_reading_of_one_message_carries_the_side_the_store_last_concluded(monkeypatch, snapshots):
    """No rule runs between two readings one message carries, so the earlier one's side is not
    concluded when the later is written: both carry what the observation they replace was judged."""
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    store = snapshots.stand_in(CARRIES)
    alarm = b'{"value": [{"value": 0.095, "age_s": 25}, {"value": 0.101, "age_s": 0}]}'
    assert received(store, snapshots.ME, PROBE, alarm, snapshots.NOW) == [OBSERVED + "probe_earlier_0", OBSERVED + "probe"]
    found = rows(store, "SELECT ?g ?range WHERE { GRAPH ?g { ?o orexis:wasBelow ?range } }", ())
    assert sorted(r["g"].rsplit("/", 1)[-1] for r in found) == ["probe", "probe_earlier_0"], found
