"""`scope_actions`, one case per file, held to a PATCH of the store it leaves.

A case in `scope_actions/` is the actions an agent holds — each with the effect it
declares, or none — loaded into a bare store. The function clusters them into the scopes their
effects join and writes the scopes.

HELD TO A PATCH RATHER THAN A SNAPSHOT, which is this directory alone and is an experiment.
`<case>.patch` is the unified diff from the case to the store the function leaves, comments
left out of both sides, and what the function must leave is what applying one to the other
gives — compared over every quad, exactly as a snapshot is. The argument for it is that a
reader checking a case reads the DIFF and nothing else, so storing the diff puts the artifact
and the claim in one file; the argument against is that a snapshot can be opened and read as a
store, which a patch cannot. Five cases here, and the other directories keep their snapshots,
so the two can be compared before either is made the rule. See knowledge/domain/scope.md.

THE DERIVATIONS ARE THE CASE'S. In a running agent the partition also joins what every loaded
package's derivation rules read and write, and genesis puts those edges in the store beside the
actions; a case that states no derivation graph states no derivations, so a case says what its
levers alone make, and nothing on disk reaches it.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from orexis_agent_execution import clock

from orexis_agent_planning.scope_actions import scope_actions

CASES_DIR = Path(__file__).parent / "scope_actions"
CASES = sorted(p for p in CASES_DIR.glob("*.trig") if "." not in p.stem)


@pytest.mark.parametrize("case", CASES, ids=[c.stem for c in CASES])
def test_scope_actions_leaves_the_store_the_patch_says(case, monkeypatch, request, snapshots):
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    store = snapshots.stand_in(case)
    scope_actions(store)
    snapshots.held_to_patch(case, request, "scope_actions", snapshots.snapshot_of(store))


def test_every_case_is_read_and_no_patch_is_orphaned(snapshots):
    """A glob that stopped matching would pass every case by running none."""
    assert len(CASES) >= 5, [c.name for c in CASES]
    assert not [p.name for p in CASES_DIR.glob("*.patch")
                if not (CASES_DIR / (p.stem + ".trig")).exists()]
