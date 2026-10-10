"""How often a sensor reports, read off SSN-System's frequency in the unit the world states —
over the pot's probe and over a board whose peripherals each state theirs in a unit of their own.
How many of those cadences the agent allows before a doubt is a stance, held where `missed` and
`received` read it, and the reading of a stance in `agent/tests/test_stance.py`. And when a
sensor's cadence has lapsed — its latest percept ended with nothing arrived — the one read `missed`
and the MQTT member both ask (#944)."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

from agent import clock
from agent.sensing.cadence import cadence_of, lapsed
from agent.sensing.received import GRACE, received

WORLDS = Path(__file__).parent / "worlds"
POT = WORLDS / "a_pot_and_its_probe.trig"
BOARD = WORLDS / "a_board_and_its_peripherals.trig"
TEST = "http://example.org/test#"
PROBE = TEST + "probe"


def test_the_pots_probe_reports_every_quarter_hour(snapshots):
    assert cadence_of(snapshots.stand_in(POT), PROBE) == 900.0


def test_each_peripheral_reports_as_its_frequency_says_in_its_own_unit(snapshots):
    store = snapshots.stand_in(BOARD)
    assert cadence_of(store, TEST + "thermo") == 120.0, "two of QUDT's minutes"
    assert cadence_of(store, TEST + "hygro") == 3600.0, "one hour by its UN/CEFACT code"
    assert cadence_of(store, TEST + "gauge") == 30.0, "no unit is seconds"


def test_no_frequency_or_a_unit_nothing_converts_is_no_cadence(snapshots, caplog):
    store = snapshots.stand_in(BOARD)
    assert cadence_of(store, PROBE) is None, "the board's probe states no frequency"
    assert cadence_of(store, TEST + "nobody") is None
    with caplog.at_level("WARNING", logger="cadence"):
        assert cadence_of(store, TEST + "barometer") is None
    assert "nothing here converts" in caplog.text


def test_a_sensor_has_lapsed_when_its_latest_percept_has_ended(monkeypatch, snapshots):
    """The probe read at noon, every quarter hour: its percept holds until the next is due and a grace
    past it, and only then has it lapsed. A second reading ends the first where it begins — an ended
    percept that says nothing lapsed, since the latest, the one no percept follows, still holds."""
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    store = snapshots.stand_in(POT)
    cadence = timedelta(seconds=900)
    received(store, snapshots.ME, PROBE, b'{"value": 0.2}', snapshots.NOW)
    due = snapshots.NOW + cadence * (1 + GRACE)
    assert lapsed(store, due - timedelta(seconds=1)) == []
    assert lapsed(store, due + timedelta(seconds=1)) == [(PROBE, due)]
    received(store, snapshots.ME, PROBE, b'{"value": 0.21}', snapshots.NOW + cadence)
    assert lapsed(store, due + timedelta(seconds=1)) == [], "the second reading holds"


def test_a_sensor_stating_no_frequency_never_lapses(monkeypatch, snapshots):
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    store = snapshots.stand_in(BOARD)
    assert received(store, snapshots.ME, PROBE, b'{"soil": {"moisture": 0.2}}', snapshots.NOW)
    assert lapsed(store, snapshots.NOW + timedelta(days=30)) == []
