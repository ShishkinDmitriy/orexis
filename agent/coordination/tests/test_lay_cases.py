"""`lay`, held to snapshot cases: each a store before, and the diff of the forecasts `lay` leaves
(`.claude/skills/snapshot-tests`). What each case claims is said at the head of its `.trig`."""

from __future__ import annotations

from pathlib import Path

import pytest

from agent.coordination.lay import lay

CASES = Path(__file__).parent / "lay"


@pytest.mark.parametrize("case", sorted(p for p in CASES.glob("*.trig") if ".actual" not in p.name), ids=lambda p: p.stem)
def test_lay_leaves_what_the_case_says(case, request, snapshots):
    store = snapshots.stand_in(case)
    lay(store, snapshots.ME, snapshots.NOW)
    snapshots.held_to_diff(case, request, "lay", snapshots.snapshot_of(store))


def test_no_diff_outlives_its_case(snapshots):
    assert snapshots.orphans_in(CASES) == []
