"""`missed`: which sensors are silent at an instant, computed and never written.

Told over the world: nothing is silent while the reading stands, nor while it is late inside its
grace (#870), a lapsed reading is not yet a silence, a sensor past the limit is silent since its
latest percept ended and stays so, a reading ends the silence, a sensor stating no frequency is never
silent, the limit is the observer role's, and no ask writes anything.
"""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import pytest

from agent import clock
from agent.sensing.cadence import lapsed
from agent.sensing.missed import missed
from agent.sensing.received import GRACE, received
from agent.sensing.ontology import OBSERVATION_GRAPH, SILENT_AFTER_TERM, default_of
from agent.store import graphs_of, rows, update

SILENT_AFTER = default_of(SILENT_AFTER_TERM)          # where the observer role states none, the observer shape's default

WORLD = Path(__file__).parent / "worlds" / "a_pot_and_its_probe.trig"
BOARD = Path(__file__).parent / "worlds" / "a_board_and_its_peripherals.trig"
PROBE = "http://example.org/test#probe"
CADENCE = timedelta(seconds=900)
LAPSE = CADENCE * (1 + GRACE)            # when the reading goes missing: due, and a grace past it


@pytest.fixture
def pot(monkeypatch, snapshots):
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    store = snapshots.stand_in(WORLD)
    received(store, snapshots.ME, PROBE, b'{"value": 0.2}', snapshots.NOW)
    return store


def test_nothing_is_silent_while_the_reading_stands(pot, snapshots):
    assert missed(pot, snapshots.NOW + timedelta(minutes=10)) == []


def test_a_reading_late_inside_its_grace_is_still_the_present(pot, snapshots):
    """#870: the next reading was due a minute ago and has not arrived. The one in hand is late, not
    missing — still the present to a reader asking now, so a step sized from it has a number."""
    late = snapshots.NOW + CADENCE + timedelta(minutes=1)
    assert lapsed(pot, late) == [] and missed(pot, late) == []
    assert rows(pot, "SELECT ?v WHERE { ?o sensing:rawResult ?v }",
                graphs_of(pot, OBSERVATION_GRAPH, at=late, now=late)) == [{"v": "0.2"}]


def test_a_percept_followed_by_the_next_is_not_missing(pot, snapshots):
    """#944: a sensor's percepts are kept, and each but the latest ended where the next began — an
    ended period that says nothing missed, since the latest, the one no percept follows, still holds."""
    received(pot, snapshots.ME, PROBE, b'{"value": 0.21}', snapshots.NOW + CADENCE)
    assert lapsed(pot, snapshots.NOW + CADENCE + timedelta(minutes=10)) == []


def test_a_lapsed_reading_is_missing_and_not_yet_silent(pot, snapshots):
    at = snapshots.NOW + LAPSE + timedelta(minutes=1)
    assert lapsed(pot, at) == [(PROBE, snapshots.NOW + LAPSE)]
    assert missed(pot, at) == []


def test_a_sensor_past_the_limit_is_silent_since_its_latest_percept_ended(pot, snapshots):
    fell_due = snapshots.NOW + LAPSE
    late = fell_due + CADENCE * SILENT_AFTER
    assert missed(pot, late - timedelta(seconds=1)) == []
    assert missed(pot, late) == [(PROBE, fell_due)]
    assert missed(pot, late + timedelta(hours=1)) == [(PROBE, fell_due)], "and stays so"


def test_asking_writes_nothing(pot, snapshots):
    """Every premise of a silence is stored — the percept's period, the cadence, the role's limit — so
    it is computed at each ask, and the store an ask leaves is the store it was handed."""
    before = set(pot)
    assert missed(pot, snapshots.NOW + LAPSE + CADENCE * SILENT_AFTER)
    assert set(pot) == before


def test_a_reading_ends_the_silence(pot, snapshots):
    late = snapshots.NOW + LAPSE + CADENCE * SILENT_AFTER
    assert missed(pot, late)
    received(pot, snapshots.ME, PROBE, b'{"value": 0.2}', late)
    assert missed(pot, late + timedelta(minutes=1)) == []


def test_a_sensor_stating_no_frequency_is_never_silent(monkeypatch, snapshots):
    """The board's probe states no frequency, so its reading never falls due."""
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    store = snapshots.stand_in(BOARD)
    assert received(store, snapshots.ME, PROBE, b'{"soil": {"moisture": 0.2}}', snapshots.NOW)
    assert lapsed(store, snapshots.NOW + timedelta(days=30)) == []
    assert missed(store, snapshots.NOW + timedelta(days=30)) == []


def test_the_silence_limit_is_the_observer_roles_where_it_states_one(pot, snapshots):
    """The keeper's world says it plays an observer role reading the probe with `sensing:silentAfter 1`,
    in a common belief, which is the world's word and not the keeper's: three cadences hold. Its self
    graph says the same: one cadence past the reading's grace, the probe is silent, where the observer
    shape's default would have waited three."""
    update(pot, f"""INSERT DATA {{ GRAPH <http://example.org/test#world> {{
  <{snapshots.ME}> orexis:plays [ a sensing:Observer ; sensing:sensor <{PROBE}> ; <{SILENT_AFTER_TERM}> 1 ] }} }}""")
    fell_due = snapshots.NOW + LAPSE
    assert missed(pot, fell_due + CADENCE) == [], "stated in a common belief, the role is not the keeper's"
    snapshots.observing(pot, PROBE, {SILENT_AFTER_TERM: 1})
    assert missed(pot, fell_due + CADENCE - timedelta(seconds=1)) == []
    assert missed(pot, fell_due + CADENCE) == [(PROBE, fell_due)]
