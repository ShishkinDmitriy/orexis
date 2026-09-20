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
from orexis_agent_progression.store import bindings

from orexis_agent_deliberation.imaginarium import Imaginarium
from orexis_agent_deliberation.planner import PASS_GRAPH, Planner

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
    planner = Planner(agent, agent.me)
    plan = planner.plan(want)
    assert plan.steps, f"{case.name}: the pass found nothing, so there is nothing to look at"
    assert forks, f"{case.name}: the pass forked no world"
    knows = snapshots.canonical_graphs({PASS_GRAPH: planner.imaginarium.dump_nt(PASS_GRAPH)})
    snapshots.held_worlds_to(case, request, forks, knows)


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


def test_the_store_alone_says_what_the_pass_decided(monkeypatch, snapshots):
    """THE POINT OF THE ROWS: come to the store knowing nothing and read the search off it.

    Every world the pass made has a row saying where it came from, what the path spent, what
    the want read there and how far it still was. So the plan is not something only Python
    holds: walk `deliberation:from` back from the world where nothing remains, and the steps
    come out — the same three the pass returned, in the same order.

    And the FRONTIER is a query, not a heap: the worlds with no `deliberation:expanded`,
    ordered by spent plus remaining, which is the A* key `_priority` computes. Asking for the
    next world to open needs nothing carried over from the last iteration.
    """
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    agent = snapshots.stand_in(CASES_DIR / "two_disk_hanoi.trig")
    (want,) = agent.wants.find_all_pursued()
    planner = Planner(agent, agent.me)
    plan = planner.plan(want)
    im = planner.imaginarium

    #  THE WORLD WHERE NOTHING REMAINS, and the path back to the one forked from nothing.
    solved = bindings(im.query_over(
        "SELECT ?w WHERE { ?w a deliberation:PossibleWorld ; deliberation:remaining 0.0 ; "
        "deliberation:atDepth ?d } ORDER BY ?d LIMIT 1", PASS_GRAPH))
    assert solved, "no world in the store reaches the goal"
    walked, here = [], solved[0]["w"]
    while True:
        row = bindings(im.query_over(
            f"SELECT ?from ?fills ?about WHERE {{ <{here}> deliberation:from ?from ; "
            f"progression:by ?s . ?s <http://example.org/orexis/progression#fills> ?fills . "
            f"OPTIONAL {{ ?s orexis:about ?about }} }}", PASS_GRAPH))
        if not row:
            break
        walked.append((row[0]["fills"], row[0].get("about")))
        here = row[0]["from"]
    walked.reverse()
    assert [a for a, _ in walked] == [s.action for s in plan.steps], walked
    assert [b for _, b in walked] == [s.about for s in plan.steps], walked

    #  AND THE OPEN LIST, ordered as `_priority` orders it, asked of the store.
    frontier = bindings(im.query_over(
        "SELECT ?w ?spent ?left WHERE { ?w a deliberation:PossibleWorld ; deliberation:spent ?spent ; "
        "deliberation:remaining ?left ; deliberation:wouldReach ?u . "
        "FILTER NOT EXISTS { ?w deliberation:expanded true } } "
        "ORDER BY (?spent + ?left) ?u ?spent", PASS_GRAPH))
    assert frontier, "every world expanded and none left open — nothing to resume from"
    keys = [float(r["spent"]) + float(r["left"]) for r in frontier]
    assert keys == sorted(keys), keys


def test_a_world_says_when_it_is_and_a_step_says_how_long_it_took(monkeypatch, snapshots):
    """AN ACTION TAKES TIME, so a possible world is facts AT AN INSTANT.

    Two levers reach the same want, one quick and dear and one slow and cheap. The first
    iteration forks both; they differ in what the tank reads and in WHEN the world is, and
    each step carries its own duration — the action's `orexis:landsAfter` evaluated where it
    is taken, which exists nowhere else once the pass ends.

    THE INSTANT IS WRITTEN AND NOT DERIVED, and that is forced rather than chosen: this engine
    binds nothing for duration arithmetic, so no query can add a path's seconds to the pass's
    clock. A reader handed only `deliberation:takes` could not say when the world is.

    AND TIME IS NOT COST. The search orders by what a path spends, so the slow cheap trickle is
    preferred to the quick dear pour — an assertion that would fail the day the two axes were
    confused for one.
    """
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    agent = snapshots.stand_in(CASES_DIR / "two_levers_that_take_different_time.trig")
    (want,) = agent.wants.find_all_pursued()
    planner = Planner(agent, agent.me)
    plan = planner.plan(want)
    rows = {r["w"].rsplit("/", 1)[-1]: r for r in bindings(planner.imaginarium.query_over(
        "SELECT ?w ?at ?takes ?spent ?fills WHERE { ?w a deliberation:PossibleWorld ; "
        "deliberation:atInstant ?at ; deliberation:takes ?takes ; deliberation:spent ?spent ; "
        "progression:by ?s . ?s <http://example.org/orexis/progression#fills> ?fills }", PASS_GRAPH))}
    quick, slow = rows["Pouring-pump-level"], rows["Trickling-dripper-level"]

    assert quick["at"].startswith("2026-01-01T12:00:30"), quick["at"]
    assert slow["at"].startswith("2026-01-01T12:10:00"), slow["at"]
    assert (float(quick["takes"]), float(slow["takes"])) == (30.0, 600.0)

    #  THE ROOT IS THE PASS'S CLOCK, which is how the clock reaches the store at all.
    (root,) = bindings(planner.imaginarium.query_over(
        "SELECT ?at WHERE { ?w a deliberation:PossibleWorld ; deliberation:atInstant ?at . "
        "FILTER NOT EXISTS { ?w deliberation:from ?p } }", PASS_GRAPH))
    assert root["at"].startswith("2026-01-01T12:00:00"), root["at"]

    assert float(slow["spent"]) < float(quick["spent"]), "the trickle is the cheaper path"
    assert [st.action.rsplit("#", 1)[-1] for st in plan.steps] == ["Trickling"], \
        "cost decides, not duration — the slow cheap lever is the one taken"
