"""`conclude`, held to snapshot cases: each a store before, and the diff of what `conclude` leaves
(`.claude/skills/snapshot-tests`). What each case claims is said at the head of its `.trig`."""

from __future__ import annotations

from pathlib import Path

import pytest

from agent.coordination.conclude import conclude

CASES = Path(__file__).parent / "conclude"


@pytest.mark.parametrize("case", sorted(p for p in CASES.glob("*.trig") if ".actual" not in p.name), ids=lambda p: p.stem)
def test_conclude_leaves_what_the_case_says(case, request, snapshots):
    store = snapshots.stand_in(case)
    conclude(store, snapshots.ME, snapshots.NOW)
    snapshots.held_to_diff(case, request, "conclude", snapshots.snapshot_of(store))


def test_no_diff_outlives_its_case(snapshots):
    assert snapshots.orphans_in(CASES) == []
