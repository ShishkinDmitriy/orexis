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

from agent import clock
from agent.sensing.received import received
from agent.store import rows

CASES_DIR = Path(__file__).parent / "received"
BOARD = Path(__file__).parent / "worlds" / "a_board_and_its_peripherals.trig"
CASES = sorted(p for p in CASES_DIR.glob("*.trig") if "." not in p.stem)
TEST = "http://example.org/test#"
PROBE = TEST + "probe"
OBSERVED = "http://example.org/orexis/graph/observed/keeper/"     # the writer's name, for eyes

FORECAST = "http://example.org/orexis/graph/forecast/keeper/"     # the writer's name, for eyes

#  WHAT EACH CASE'S BYTES SAY, and which graphs they land in.
BYTES = {
    "a_first_reading_becomes_an_observation": (b'{"value": 0.22}', [OBSERVED + "probe"]),
    "a_second_reading_replaces_the_first": (b'{"value": 0.08}', [OBSERVED + "probe"]),
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
