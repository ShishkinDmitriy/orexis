"""`Planner.expand`, one case per file, held to a PATCH of the imaginarium it leaves — the layer
one iteration adds.

A case in `expand/` is an imaginarium MID-SEARCH: the ground laid and weighed, the wants
derived, whatever worlds earlier iterations forked with their candidates and weighings, and
at least one weighing still open. The test asks one iteration of every want that has one, in
name order, and `<case>.diff` is what that added: the worlds forked with what
each spent and when it is, the candidate that reached each, the weighing of each for the
want — met or not, open or not — the candidates passed over and which world each repeated,
and the opened world's weighing closed.

THE CASES ARE MID-SEARCH STORES WRITTEN DOWN, not authored from nothing: each was made by
running the search this far on a plans case and rendering the store, because a hash is not
a thing to write by hand and a weighing's rows are the search's to spell. What a case then
claims is one iteration, in isolation, on a state a reader can see whole.

AN ITERATION IS: take the cheapest open world, and weigh a world per candidate that world
admits — not all actions, the admitted ones; and not one world, as many as there are ways to
move. The predecessor held this to the worlds a whole pass forked, caught as they were made
because the store did not keep them; the store keeps them now, so one iteration is a diff.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from agent import clock
from agent.store import rows
from agent.planning.planner import Planner

CASES_DIR = Path(__file__).parent / "expand"
CASES = sorted(p for p in CASES_DIR.glob("*.trig") if "." not in p.stem)

#  EVERY WANT WITH A WORLD STILL OPEN — whose search the case is in the middle of.
_OPEN_Q = """
SELECT DISTINCT ?want WHERE {
  GRAPH ?cat { ?cat a orexis:CatalogueGraph .
    ?x a planning:Weighing ; planning:for ?want ; planning:open true } }
ORDER BY ?want"""


@pytest.mark.parametrize("case", CASES, ids=[c.stem for c in CASES])
def test_one_iteration_adds_the_layer_the_patch_says(case, monkeypatch, request, snapshots):
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    store = snapshots.stand_in(case)
    planner = Planner(store, snapshots.AGENT)
    wants = [r["want"] for r in rows(store, _OPEN_Q, ())]
    assert wants, f"{case.name} has no open weighing — nothing to expand"
    for want in wants:
        #  ONE ITERATION, or none: `expand` opens the top of the want's frontier unless the
        #  bound refuses it — a search that has met the want for some cost stops there and
        #  leaves the dearer worlds open, which is the frontier as it stands and not a claim
        #  of the case's. The check is the search's own, and lives in the one place.
        planner.expand(store, want)
    snapshots.held_to_diff(case, request, "expand", snapshots.snapshot_of(store))


def test_every_case_is_read_and_no_diff_is_orphaned(snapshots):
    """A glob that stopped matching would pass every case by running none."""
    assert len(CASES) >= 3, [c.name for c in CASES]
    assert not snapshots.orphans_in(CASES_DIR)
