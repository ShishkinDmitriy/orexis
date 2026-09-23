"""`take`, one case per file, held to a PATCH of the store it leaves.

A case in `take/` is an imaginarium whose ground has been admitted: the candidates stand as
edges from it and no world has been forked. The test takes every candidate that has reached no
world, in name order, and `<case>.diff` is what that made: one world per candidate, forked with
the action's effect applied, and its row — what it spent, when it is, its mint number, its
hash, and the candidate that made it.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from agent import clock
from agent.store import rows
from agent.planning.take import take

CASES_DIR = Path(__file__).parent / "take"
CASES = sorted(p for p in CASES_DIR.glob("*.trig") if "." not in p.stem)

_UNTAKEN_Q = """
SELECT ?cand WHERE {
  GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?cand a planning:Candidate .
               FILTER NOT EXISTS { ?w planning:by ?cand } } }
ORDER BY ?cand"""


@pytest.mark.parametrize("case", CASES, ids=[c.stem for c in CASES])
def test_take_forks_the_worlds_the_patch_says(case, monkeypatch, request, snapshots):
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    store = snapshots.stand_in(case)
    taken = [take(store, r["cand"], snapshots.ME) for r in rows(store, _UNTAKEN_Q, ())]
    assert taken, f"{case.name} admits no candidate to take"
    snapshots.held_to_diff(case, request, "take", snapshots.snapshot_of(store))


def test_every_case_is_read_and_no_diff_is_orphaned(snapshots):
    assert len(CASES) >= 2, [c.name for c in CASES]
    assert not snapshots.orphans_in(CASES_DIR)
