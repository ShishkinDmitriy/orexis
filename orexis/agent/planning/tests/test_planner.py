"""`Planner.plan`, the pass end to end, one case per file, held to a PATCH of the imaginarium it
leaves.

The suites beside this one hold each stage of the pipeline to a snapshot of the store it
leaves. This one asks the question those cannot: does a search over the worlds those stages
build actually reach the state a want names, by chaining a step the case declares once?

A case in `plans/` is a whole small world — an agent, a lever, a desire and a reading — and
what it is held to is the IMAGINARIUM the pass leaves: the grounds it laid, the wants it
derived, every world it forked with the candidate that made it, the weighing of each for the
want, and the plan. The search's whole state is in that store, which is what makes the diff
the claim: a reader sees which worlds were opened, which met the want, which fork repeated
a world already seen, and what the plan came to — and could continue the search from it.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from orexis.agent import clock
from orexis.agent.planning.planner import Planner

CASES_DIR = Path(__file__).parent / "plans"
CASES = sorted(p for p in CASES_DIR.glob("*.trig") if "." not in p.stem)


@pytest.mark.parametrize("case", CASES, ids=[c.stem for c in CASES])
def test_the_pass_leaves_the_imaginarium_the_patch_says(case, monkeypatch, request, snapshots):
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    store = snapshots.stand_in(case)
    planner = Planner(store, snapshots.AGENT)
    planner.plan(snapshots.NOW)
    #  ONE SCOPE PER CASE, so one imaginarium: a case with two would need a diff each, and
    #  none here declares two.
    (imagined,) = planner.imaginaria
    snapshots.held_to_diff(case, request, "planner", snapshots.snapshot_of(imagined))


def test_every_case_is_read_and_no_diff_is_orphaned(snapshots):
    """A glob that stopped matching would pass every case by running none."""
    assert len(CASES) >= 2, [c.name for c in CASES]
    assert not snapshots.orphans_in(CASES_DIR)
