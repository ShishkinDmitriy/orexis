"""One search per case file, held to a PATCH of the store it leaves.

A case in `plan_wants/` is a world with a want standing in it and the levers that could serve
it — loaded into a bare store, searched, and the plan written down. `<case>.patch`
beside it is the whole store afterwards, so `diff` of case against snapshot is exactly what
one pass decided: the trace it left, and the plan it found.

THE OBJECTIVE IS IN THE STORE, which is what makes a search snapshot-shaped at all. A case's
want states its met-test as a SHAPE, and a want nobody measures is judged binary from that
shape — unmet 1, met 0 (`planner._urgency_in`). So no capability need be loaded, the choir is
asked and answers nothing, and the whole of what the search steers by is in the file.

ONE COLUMN IS NORMALISED AND ONLY ONE. `deliberation:tookSeconds` is how long the pass took on
the machine that ran it, so it differs every run and cannot be in a snapshot; it is dropped
before the comparison. Everything else the pass writes — which candidates it weighed, what it
would reach, what it chose, the plan and its steps — is a function of the case.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from orexis_agent_progression import clock
from orexis_agent_progression.ontology import DELIBERATION_GRAPH

from orexis_agent_deliberation.planner import Planner, write_plan

CASES_DIR = Path(__file__).parent / "plan_wants"
CASES = sorted(p for p in CASES_DIR.glob("*.trig") if "." not in p.stem)

TOOK = "http://example.org/orexis/deliberation#tookSeconds"


@pytest.mark.parametrize("case", CASES, ids=[c.stem for c in CASES])
def test_a_pass_leaves_the_store_as_the_snapshot_says(case, monkeypatch, request, snapshots):
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    agent = snapshots.stand_in(case)
    for want in agent.wants.find_all_pursued():
        write_plan(agent.beliefs.engine, want.uri, Planner(agent, agent.me).plan(want))
    agent.beliefs.update(
        f"DELETE {{ GRAPH <{DELIBERATION_GRAPH}> {{ ?s <{TOOK}> ?v }} }} "
        f"WHERE  {{ GRAPH <{DELIBERATION_GRAPH}> {{ ?s <{TOOK}> ?v }} }}")
    snapshots.held_to_patch(case, request, "a pass", snapshots.snapshot_of(agent.beliefs))


def test_every_case_is_read_and_no_snapshot_is_orphaned(snapshots):
    """A glob that stopped matching would pass every case by running none."""
    assert len(CASES) >= 1, [c.name for c in CASES]
    assert not snapshots.orphans_in(CASES_DIR)
