"""What one pass FORKS, held to the worlds it made — the search's own iterations, visible.

A case in `expansions/` is a small problem with more than one move available, and
`<case>.worlds.trig` beside it is every possible world the pass built, in order, each a named
graph holding that node's own readings.

AN ITERATION IS: take one node off the open list, and fork a world per lever that node's world
affords and the closure says is relevant. Not all actions — the afforded, relevant ones; and
not one world — as many as there are ways to move. The first iteration of the two-disk puzzle
makes TWO, which is the whole reason the case is a puzzle and not a tank.

WHY THIS IS NOT A STORE SNAPSHOT. A node's graph is dropped once the node is expanded and
again when the pass ends, to be re-made from the nearest kept graph when a rule next runs
against it — so the store holds none of this afterwards and `test_plan_wants` sees only what
survived. These are caught at the moment `Imaginarium.reached` makes them.

The naming is the imaginarium's and says the path: `Move-disk_1-PegC.Move-disk_2-PegA` is the
world two moves along. A graph's name is for eyes everywhere else in this repo and it is for
eyes here too — what a rule binds to `$state` is whatever name it was handed.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from orexis_agent_progression import clock

from orexis_agent_deliberation.imaginarium import Imaginarium
from orexis_agent_deliberation.planner import Planner

CASES_DIR = Path(__file__).parent / "expansions"
CASES = sorted(p for p in CASES_DIR.glob("*.trig") if "." not in p.stem)


@pytest.mark.parametrize("case", CASES, ids=[c.stem for c in CASES])
def test_a_pass_forks_the_worlds_the_case_says(case, monkeypatch, request, snapshots):
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    forks: list = []
    reached = Imaginarium.reached

    def spy(self, parent, path, added, retracted):
        made = reached(self, parent, path, added, retracted)
        forks.append((parent, made, self._store.dump_nt(made).strip()))
        return made

    monkeypatch.setattr(Imaginarium, "reached", spy)
    agent = snapshots.stand_in(case)
    (want,) = agent.wants.find_all_pursued()
    plan = Planner(agent, agent.me).plan(want)
    assert plan.steps, f"{case.name}: the pass found nothing, so there is nothing to look at"
    assert forks, f"{case.name}: the pass forked no world"
    snapshots.held_worlds_to(case, request, forks)


def test_the_first_iteration_of_the_two_disk_puzzle_makes_two_worlds(monkeypatch, snapshots):
    """AN ITERATION IS PLURAL, and this is the assertion that says so.

    The small disk is the only movable one and it may go to either free peg, so the first node
    off the open list forks TWO worlds — from the same parent, the root's own readings. A
    search that forked one world per iteration would be a walk, and every case in
    `plan_wants/` would still pass, because each has one lever.
    """
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    forks: list = []
    reached = Imaginarium.reached
    monkeypatch.setattr(Imaginarium, "reached", lambda self, p, path, a, r: (
        forks.append((p, reached(self, p, path, a, r))) or forks[-1][1]))
    agent = snapshots.stand_in(CASES_DIR / "two_disk_hanoi.trig")
    (want,) = agent.wants.find_all_pursued()
    Planner(agent, agent.me).plan(want)
    root = forks[0][0]
    first = [made for parent, made in forks if parent == root]
    assert len(first) == 2, [m.rsplit("/", 1)[-1] for m in first]
    assert {m.rsplit("/", 1)[-1] for m in first} == {"Move-disk_1-PegB", "Move-disk_1-PegC"}


def test_every_case_is_read(snapshots):
    """A glob that stopped matching would pass every case by running none."""
    assert len(CASES) >= 1, [c.name for c in CASES]
