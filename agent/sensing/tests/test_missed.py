"""`missed`: which readings have fallen due with nothing arrived, and which sensors are silent.

One case per file in `missed/`, held to a PATCH of the store it leaves: the world with an
observation whose period has ended, and the diff is the silence said of its sensor. The rest
is told over the world: nothing is missing while the reading stands, nor while it is late inside
its grace (#870), a lapsed reading is
missing and nothing is written for it, a sensor silent past the limit is said so once, a
reading ends the silence, and a sensor stating no frequency is never missing.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import pytest

from agent import clock
from agent.sensing.missed import SILENT_AFTER, missed
from agent.sensing.received import GRACE, received
from agent.sensing.ontology import OBSERVATION_GRAPH, SILENT_AFTER_TERM
from agent.store import graphs_of, rows, update

CASES_DIR = Path(__file__).parent / "missed"
CASES = sorted(p for p in CASES_DIR.glob("*.trig") if "." not in p.stem)
WORLD = Path(__file__).parent / "worlds" / "a_pot_and_its_probe.trig"
BOARD = Path(__file__).parent / "worlds" / "a_board_and_its_peripherals.trig"
PROBE = "http://example.org/test#probe"
CADENCE = timedelta(seconds=900)
LAPSE = CADENCE * (1 + GRACE)            # when the reading goes missing: due, and a grace past it

_SILENCES_Q = """
SELECT ?g ?sensor ?since ?start WHERE {
  GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?g a orexis:StateGraph ; orexis:arrivedBy orexis:Derived ;
               dcterms:temporal/orexis:start ?start }
  GRAPH ?g { ?sensor sensing:silentSince ?since } }"""


def _silences(store):
    return [(r["sensor"], datetime.fromisoformat(r["since"]), datetime.fromisoformat(r["start"]))
            for r in rows(store, _SILENCES_Q, ())]


@pytest.fixture
def pot(monkeypatch, snapshots):
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    store = snapshots.stand_in(WORLD)
    received(store, snapshots.ME, PROBE, b'{"value": 0.2}', snapshots.NOW)
    return store


@pytest.mark.parametrize("case", CASES, ids=[c.stem for c in CASES])
def test_missed_says_the_silence_the_patch_says(case, monkeypatch, request, snapshots):
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    store = snapshots.stand_in(case)
    assert missed(store, snapshots.ME, snapshots.NOW + CADENCE * (1 + SILENT_AFTER)) == [PROBE]
    snapshots.held_to_diff(case, request, "missed", snapshots.snapshot_of(store))


def test_nothing_is_missing_while_the_reading_stands(pot, snapshots):
    assert missed(pot, snapshots.ME, snapshots.NOW + timedelta(minutes=10)) == []
    assert _silences(pot) == []


def test_a_reading_late_inside_its_grace_is_still_the_present(pot, snapshots):
    """#870: the next reading was due a minute ago and has not arrived. The one in hand is late, not
    missing — still the present to a reader asking now, so a step sized from it has a number."""
    late = snapshots.NOW + CADENCE + timedelta(minutes=1)
    assert missed(pot, snapshots.ME, late) == []
    assert rows(pot, "SELECT ?v WHERE { ?o sensing:rawResult ?v }",
                graphs_of(pot, OBSERVATION_GRAPH, at=late, now=late)) == [{"v": "0.2"}]


def test_a_percept_followed_by_the_next_is_not_missing(pot, snapshots):
    """#944: a sensor's percepts are kept, and each but the latest ended where the next began — an
    ended period that says nothing missed, since the latest, the one no percept follows, still holds."""
    received(pot, snapshots.ME, PROBE, b'{"value": 0.21}', snapshots.NOW + CADENCE)
    assert missed(pot, snapshots.ME, snapshots.NOW + CADENCE + timedelta(minutes=10)) == []


def test_a_lapsed_reading_is_missing_and_nothing_is_written_for_it(pot, snapshots):
    assert missed(pot, snapshots.ME, snapshots.NOW + LAPSE + timedelta(minutes=1)) == [PROBE]
    assert _silences(pot) == []


def test_a_sensor_silent_past_the_limit_is_said_so_once(pot, snapshots):
    fell_due = snapshots.NOW + LAPSE
    late = fell_due + CADENCE * SILENT_AFTER
    assert missed(pot, snapshots.ME, late - timedelta(seconds=1)) == [PROBE] and _silences(pot) == []
    assert missed(pot, snapshots.ME, late) == [PROBE]
    said = _silences(pot)
    assert said == [(PROBE, fell_due, fell_due)]
    assert missed(pot, snapshots.ME, late + timedelta(hours=1)) == [PROBE]
    assert _silences(pot) == said, "said once"


def test_a_reading_ends_the_silence(pot, snapshots):
    late = snapshots.NOW + LAPSE + CADENCE * SILENT_AFTER
    missed(pot, snapshots.ME, late)
    assert _silences(pot)
    received(pot, snapshots.ME, PROBE, b'{"value": 0.2}', late)
    assert _silences(pot) == []
    assert missed(pot, snapshots.ME, late + timedelta(minutes=1)) == []


def test_a_sensor_stating_no_frequency_is_never_missing(monkeypatch, snapshots):
    """The board's probe states no frequency, so its reading never falls due."""
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    store = snapshots.stand_in(BOARD)
    assert received(store, snapshots.ME, PROBE, b'{"soil": {"moisture": 0.2}}', snapshots.NOW)
    assert missed(store, snapshots.ME, snapshots.NOW + timedelta(days=30)) == []


def test_every_case_is_read_and_no_diff_is_orphaned(snapshots):
    assert CASES, "no case in missed/"
    assert not snapshots.orphans_in(CASES_DIR)


def test_the_silence_limit_is_the_agents_where_its_self_graph_states_one(pot, snapshots):
    """The keeper's world says `sensing:silentAfter 1` of it in the public world graph, which is the
    world's word and not the keeper's: three cadences hold. Its self graph says the same, a stance:
    one cadence past the reading's grace, the probe is silent, where the figure in code would have
    waited three."""
    update(pot, f"INSERT DATA {{ GRAPH <http://example.org/test#world> {{ <{snapshots.ME}> <{SILENT_AFTER_TERM}> 1 }} }}")
    fell_due = snapshots.NOW + LAPSE
    assert missed(pot, snapshots.ME, fell_due + CADENCE) == [PROBE] and _silences(pot) == [], \
        "stated in a public graph, the limit is not the keeper's stance"
    snapshots.stating(pot, {SILENT_AFTER_TERM: 1})
    assert missed(pot, snapshots.ME, fell_due + CADENCE - timedelta(seconds=1)) == [PROBE] and _silences(pot) == []
    assert missed(pot, snapshots.ME, fell_due + CADENCE) == [PROBE]
    assert _silences(pot) == [(PROBE, fell_due, fell_due)]
