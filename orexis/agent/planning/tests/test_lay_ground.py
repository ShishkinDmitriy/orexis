"""`lay_ground`, one case per file, held to a PATCH of the store it lays the grounds INTO.

The same belief bases `prepare_ground/` fills a second store from, laid in place: the present
as a ground of its own, and one more per boundary a prediction makes, each forked from the one
before with the prediction's retraction run and its facts added, classified with the stretch
it holds over and hashed — and a boundary whose ground hashes like the one before it laid as
no ground at all.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from orexis.agent import clock
from orexis.agent.planning.lay_ground import lay_ground

CASES_DIR = Path(__file__).parent / "lay_ground"
CASES = sorted(p for p in CASES_DIR.glob("*.trig") if "." not in p.stem)


@pytest.mark.parametrize("case", CASES, ids=[c.stem for c in CASES])
def test_lay_ground_lays_the_grounds_the_patch_says(case, monkeypatch, request, snapshots):
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    store = snapshots.stand_in(case)
    lay_ground(store, snapshots.NOW)
    snapshots.held_to_diff(case, request, "lay_ground", snapshots.snapshot_of(store))


def test_every_case_is_read_and_no_diff_is_orphaned(snapshots):
    assert len(CASES) >= 3, [c.name for c in CASES]
    assert not snapshots.orphans_in(CASES_DIR)
