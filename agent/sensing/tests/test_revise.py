"""`revise`, one case per file, held to a PATCH of the store it leaves.

A case in `revise/` is a belief base as a reading finds it — the world with the ranges it
states, whatever reading of the key already stands — and the diff is what the reading leaves:
the graph of readings with the node's key and one revision per region, the result graph
beside it with the number and the instant, and the catalogue's account of both.
"""

from __future__ import annotations

from datetime import timezone
from pathlib import Path

import pytest

from agent import clock
from agent.sensing.revise import revise

CASES_DIR = Path(__file__).parent / "revise"
CASES = sorted(p for p in CASES_DIR.glob("*.trig") if "." not in p.stem)

TEST = "http://example.org/test#"
HORIZON_S = 900.0

#  WHAT EACH CASE'S READING IS: the value, and the property where it is not the moisture.
READ = {
    "a_first_reading_becomes_its_revisions_and_its_result": (0.22, "moisture"),
    "a_second_reading_replaces_the_first": (0.08, "moisture"),
    "a_reading_no_region_is_stated_for_is_revised_against_nothing": (22, "warmth"),
}


@pytest.mark.parametrize("case", CASES, ids=[c.stem for c in CASES])
def test_revise_leaves_the_reading_the_patch_says(case, monkeypatch, request, snapshots):
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    store = snapshots.stand_in(case)
    value, prop = READ[case.stem]
    reading = revise(store, snapshots.ME, TEST + "zz", TEST + prop, value, snapshots.NOW, HORIZON_S,
                     sensor=TEST + "probe")
    assert reading.endswith(f"/sensed/keeper/zz_{prop}")
    snapshots.held_to_diff(case, request, "revise", snapshots.snapshot_of(store))


def test_every_case_is_read_and_no_diff_is_orphaned(snapshots):
    assert set(READ) == {c.stem for c in CASES}, [c.name for c in CASES]
    assert not snapshots.orphans_in(CASES_DIR)
