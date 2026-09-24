"""`received`, one case per file, held to a PATCH of the store it leaves.

A case in `received/` is a belief base as bytes find it — the world with the pot's ranges,
whatever observation of the key already stands — and the diff is what the bytes leave: the
graph of the key holding one sosa:Observation with its number, and the catalogue's account of
it. No side is written: that is the rules' to conclude.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from agent import clock
from agent.sensing.received import received
from agent.sensing.wiring import sensors_of

CASES_DIR = Path(__file__).parent / "received"
CASES = sorted(p for p in CASES_DIR.glob("*.trig") if "." not in p.stem)
HORIZON_S = 900.0

#  WHAT EACH CASE'S BYTES SAY, and which graph they land in.
BYTES = {
    "a_first_reading_becomes_an_observation": (b'{"value": 0.22}', "zz"),
    "a_second_reading_replaces_the_first": (b'{"value": 0.08}', "zz"),
    "a_probes_sample_keys_the_node": (b'{"value": 0.22}', "patch"),
}


@pytest.mark.parametrize("case", CASES, ids=[c.stem for c in CASES])
def test_received_leaves_the_observation_the_patch_says(case, monkeypatch, request, snapshots):
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    store = snapshots.stand_in(case)
    (probe,) = sensors_of(store, snapshots.ME)
    payload, feature = BYTES[case.stem]
    graph = received(store, snapshots.ME, probe, payload, snapshots.NOW, horizon=HORIZON_S)
    assert graph == f"http://example.org/orexis/graph/observed/keeper/{feature}_moisture"
    snapshots.held_to_diff(case, request, "received", snapshots.snapshot_of(store))


def test_bytes_that_hold_no_reading_write_nothing(monkeypatch, snapshots, caplog):
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    store = snapshots.stand_in(CASES_DIR / "a_first_reading_becomes_an_observation.trig")
    (probe,) = sensors_of(store, snapshots.ME)
    before = set(snapshots.graph_names(store))
    with caplog.at_level("WARNING", logger="pipeline"):
        assert received(store, snapshots.ME, probe, b'{"temperature": 21}', snapshots.NOW, horizon=HORIZON_S) is None
    assert set(snapshots.graph_names(store)) == before
    assert "unread" in caplog.text


def test_every_case_is_read_and_no_diff_is_orphaned(snapshots):
    assert set(BYTES) == {c.stem for c in CASES}, [c.name for c in CASES]
    assert not snapshots.orphans_in(CASES_DIR)
