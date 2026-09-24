"""`received`, one case per file, held to a PATCH of the store it leaves.

A case in `received/` is a belief base as bytes find it — the world with the pot's ranges and
the probe's frequency, whatever observation of the key already stands — and the diff is what
the bytes leave: the graph of the key holding one sosa:Observation with its number, and the
catalogue's account of it, holding until the next reading is due. No side is written: that is
the rules' to conclude.
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

#  WHAT EACH CASE'S BYTES SAY, and which graph they land in.
BYTES = {
    "a_first_reading_becomes_an_observation": (b'{"value": 0.22}', "zamioculcas"),
    "a_second_reading_replaces_the_first": (b'{"value": 0.08}', "zamioculcas"),
    "a_probes_sample_keys_the_node": (b'{"value": 0.22}', "patch"),
}


@pytest.mark.parametrize("case", CASES, ids=[c.stem for c in CASES])
def test_received_leaves_the_observation_the_patch_says(case, monkeypatch, request, snapshots):
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    store = snapshots.stand_in(case)
    payload, feature = BYTES[case.stem]
    graph = received(store, snapshots.ME, PROBE, payload, snapshots.NOW)
    assert graph == f"{OBSERVED}{feature}_moisture"
    snapshots.held_to_diff(case, request, "received", snapshots.snapshot_of(store))


def test_bytes_that_hold_no_reading_write_nothing(monkeypatch, snapshots, caplog):
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    store = snapshots.stand_in(CASES_DIR / "a_first_reading_becomes_an_observation.trig")
    before = set(snapshots.graph_names(store))
    with caplog.at_level("WARNING", logger="pipeline"):
        assert received(store, snapshots.ME, PROBE, b'{"temperature": 21}', snapshots.NOW) is None
    assert set(snapshots.graph_names(store)) == before
    assert "unread" in caplog.text


def test_a_sensor_with_no_host_has_no_key_and_writes_nothing(monkeypatch, snapshots, caplog):
    """The key is what the sensor observes of what hosts it, in SOSA's words; the board's light
    sensor is mounted nowhere, so it is not keyed and its bytes measure nothing."""
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    store = snapshots.stand_in(BOARD)
    before = set(snapshots.graph_names(store))
    with caplog.at_level("WARNING", logger="received"):
        assert received(store, snapshots.ME, TEST + "loose", b'{"value": 0.2}', snapshots.NOW) is None
    assert set(snapshots.graph_names(store)) == before
    assert "no key" in caplog.text


def test_one_message_for_two_sensors_is_two_observations(monkeypatch, snapshots):
    """A board carrying two peripherals publishes one message; a transport hands it to sensing
    once per sensor that owns the channel, and each writes the observation of its own key."""
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    store = snapshots.stand_in(BOARD)
    message = b'{"temperature": 21.5, "soil": {"moisture": 0.22}}'
    written = [received(store, snapshots.ME, sensor, message, snapshots.NOW) for sensor in (PROBE, TEST + "thermo")]
    assert written == [OBSERVED + "zamioculcas_moisture", OBSERVED + "zamioculcas_warmth"]
    found = rows(store, "SELECT ?p ?v WHERE { GRAPH ?g { ?o a sosa:Observation ; sosa:observedProperty ?p ; sosa:hasSimpleResult ?v } } ORDER BY ?p", ())
    assert [(r["p"].rsplit("#", 1)[-1], float(r["v"])) for r in found] == [("moisture", 0.22), ("warmth", 21.5)]


def test_a_sensor_stating_no_frequency_stands_until_replaced(monkeypatch, snapshots):
    """The board's probe states no frequency: the world made no promise about the next
    reading, so the observation has no end."""
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    store = snapshots.stand_in(BOARD)
    graph = received(store, snapshots.ME, PROBE, b'{"soil": {"moisture": 0.2}}', snapshots.NOW)
    period = rows(store, "SELECT ?start ?end WHERE { GRAPH ?cat { ?cat a orexis:CatalogueGraph . $g dcterms:temporal ?p . "
                         "?p orexis:start ?start . OPTIONAL { ?p orexis:end ?end } } }", (), g=graph)
    assert len(period) == 1 and period[0].get("end") is None, period


def test_every_case_is_read_and_no_diff_is_orphaned(snapshots):
    assert set(BYTES) == {c.stem for c in CASES}, [c.name for c in CASES]
    assert not snapshots.orphans_in(CASES_DIR)
