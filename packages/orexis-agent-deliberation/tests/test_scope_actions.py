"""`scope_actions`, one case per file, held to a snapshot of the whole store it leaves.

A case in `scope_actions/` is the actions an agent holds — each with the effect it
declares, or none — loaded into a bare store. The function clusters them into the scopes their
effects join and writes the scopes; `<case>.snapshot.trig` beside the case is the whole store
afterwards, in the case's own order, so `diff` of case against snapshot is exactly what
clustering did. The machinery is the conftest's. See knowledge/domain/scope.md.

THE DERIVATIONS ARE NONE HERE. In a running agent the partition also joins what every loaded
package's derivation rules read and write; a bare store loads no package, so the rules on disk
— every package's, the runtime's reading and not a case's — are patched out, and a case says
what its levers alone make.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from orexis_agent_progression import clock

from orexis_agent_deliberation import relevance
from orexis_agent_deliberation.scope_actions import scope_actions

CASES_DIR = Path(__file__).parent / "scope_actions"
CASES = sorted(p for p in CASES_DIR.glob("*.trig") if "." not in p.stem)


@pytest.mark.parametrize("case", CASES, ids=[c.stem for c in CASES])
def test_scope_actions_leaves_the_store_as_the_snapshot_says(case, monkeypatch, request, snapshots):
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    monkeypatch.setattr(relevance, "rule_edges", lambda: ())
    agent = snapshots.stand_in(case)
    before = snapshots.snapshot_of(agent.beliefs)
    scope_actions(agent)
    snapshots.held_to(case, request, "scope_actions", before, snapshots.snapshot_of(agent.beliefs))


def test_every_case_is_read_and_no_snapshot_is_orphaned(snapshots):
    """A glob that stopped matching would pass every case by running none."""
    assert len(CASES) >= 4, [c.name for c in CASES]
    assert not snapshots.orphans_in(CASES_DIR)
