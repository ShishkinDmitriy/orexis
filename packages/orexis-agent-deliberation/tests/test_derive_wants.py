"""`derive_wants`, one case per file, held to a snapshot of the whole store it leaves.

A case in `derive_wants/` is the store as `judge_desires` leaves it and nothing of the world
that was judged: the judgments — one per desire per instant, met or unmet, the results where
unmet — the desires they judge, the levers whose effects say which properties move together
(what a scope is made of), and whatever want already stands. No readings, no predictions,
no topology: the function reads the judgments and nothing in hand, which is its contract,
and a case that gave it more would not be testing that. `<case>.snapshot.trig` beside the
case is the whole store afterwards, in the case's own order, so `diff` of case against
snapshot is exactly what deriving did. The machinery is the conftest's. See
knowledge/decisions/judge-desires-then-derive-wants.md.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from orexis_agent_progression import clock

from orexis_agent_deliberation import pursuit

CASES_DIR = Path(__file__).parent / "derive_wants"
CASES = sorted(p for p in CASES_DIR.glob("*.trig") if "." not in p.stem)


@pytest.mark.parametrize("case", CASES, ids=[c.stem for c in CASES])
def test_derive_wants_leaves_the_store_as_the_snapshot_says(case, monkeypatch, request, snapshots):
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    agent = snapshots.stand_in(case)
    before = snapshots.snapshot_of(agent.beliefs)
    pursuit.derive_wants(agent)
    snapshots.held_to(case, request, "derive_wants", before, snapshots.snapshot_of(agent.beliefs))


def test_every_case_is_read_and_no_snapshot_is_orphaned(snapshots):
    """A glob that stopped matching would pass every case by running none."""
    assert len(CASES) >= 11, [c.name for c in CASES]
    assert not snapshots.orphans_in(CASES_DIR)
