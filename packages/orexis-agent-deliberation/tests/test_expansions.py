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
from orexis_agent_progression.ontology import PUBLIC
from orexis_agent_progression.store import bindings

from orexis_agent_deliberation.affordances import Affordances
from orexis_agent_deliberation.imaginarium import Imaginarium
from orexis_agent_deliberation.planner import PASS_GRAPH, Planner

HANOI = "http://example.org/orexis/hanoi#"     # what hanoi:Move declares it takes

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
    #  A CASE EITHER FINDS SOMETHING OR SAYS WHY NOT. `exhausted` is a legitimate answer and
    #  one case is about it; anything else that returns no steps has gone quiet, which is what
    #  this guards — a case whose world stopped affording would otherwise pass by doing nothing.
    assert plan.steps or plan.outcome == "exhausted", f"{case.name}: {plan.outcome}"
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
        f"SELECT ?w WHERE {{ ?w a deliberation:PossibleWorld ; deliberation:atDepth ?d ; "
        f"deliberation:weighed ?x . ?x deliberation:forWant <{want.uri}> ; "
        f"deliberation:remaining 0.0 }} ORDER BY ?d LIMIT 1", PASS_GRAPH))
    assert solved, "no world in the store reaches the goal"
    walked, here = [], solved[0]["w"]
    while True:
        row = bindings(im.query_over(
            f"SELECT ?from ?fills ?onto WHERE {{ <{here}> deliberation:from ?from ; "
            f"progression:by ?s . ?s <http://example.org/orexis/progression#fills> ?fills . "
            f"OPTIONAL {{ ?s <{HANOI}onto> ?onto }} }}", PASS_GRAPH))
        if not row:
            break
        walked.append((row[0]["fills"], row[0].get("onto")))
        here = row[0]["from"]
    walked.reverse()
    assert [a for a, _ in walked] == [s.action for s in plan.steps], walked
    assert [b for _, b in walked] == [s.value_of(HANOI + "onto") for s in plan.steps], walked

    #  AND WHAT THE SEARCH CONCLUDED, not only what it did: the world the plan ends in is the
    #  one the want is MET in, and the society accepts it. Both are about the WORLD rather than
    #  about the pass, which is why they survive a re-root where a verdict does not.
    achievers = {r["w"] for r in bindings(im.query_over(
        f"SELECT ?w WHERE {{ ?w a deliberation:PossibleWorld ; deliberation:meets <{want.uri}> }}",
        PASS_GRAPH))}
    assert solved[0]["w"] in achievers, "the world with nothing remaining meets THIS want"
    #  AND THE OTHER HALF: a world judged and found wanting says so, naming the same want, so
    #  a later pass — resumed, or for another want sharing the imaginarium — need not re-judge.
    failed = {r["w"] for r in bindings(im.query_over(
        f"SELECT ?w WHERE {{ ?w a deliberation:PossibleWorld ; deliberation:fails <{want.uri}> }}",
        PASS_GRAPH))}
    assert failed and not (failed & achievers), "judged both ways, and never both at once"
    assert bindings(im.query_over(
        f"SELECT ?l WHERE {{ <{solved[0]['w']}> deliberation:lawful ?l }}", PASS_GRAPH)), \
        "and the pass asked whether the society would accept it"

    #  AND THE OPEN LIST, ordered as `_priority` orders it, asked of the store.
    frontier = bindings(im.query_over(
        f"SELECT ?w ?spent ?left WHERE {{ ?w a deliberation:PossibleWorld ; "
        f"deliberation:spent ?spent ; deliberation:weighed ?x . "
        f"?x deliberation:forWant <{want.uri}> ; deliberation:open true ; "
        f"deliberation:remaining ?left ; deliberation:wouldReach ?u }} "
        f"ORDER BY (?spent + ?left) ?u ?spent", PASS_GRAPH))
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
    quick, slow = rows["Pouring-level-pump"], rows["Trickling-level-dripper"]

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


def test_the_inputs_to_the_next_iteration_are_all_in_the_store(monkeypatch, snapshots):
    """A PASS STOPPED WITH ITS FRONTIER OPEN, and everything the next iteration needs
    read back from the store without a planner holding anything.

    This is what the rows are for. An iteration is: take the best open world, read what it
    affords, fork one world per lever. So the question "can it be resumed" is the question
    "are those three in the store", and the answer is now yes:

    - WHICH WORLD IS NEXT — the open weighings for this want, ordered by spent plus remaining,
      which is the A* key `_priority` computes;
    - WHAT IS TRUE THERE — the world's own graph, which is kept for as long as the node is;
    - WHAT IT AFFORDS — each action's `orexis:available` run against that world, by the same
      collections the search uses, which take stores and no agent;
    - and THE BOUND to refuse against, which is what the cheapest achiever spent.

    What is NOT in the store is the agent's own identity — and that is rule 1's one stated
    exception, the single thing a process is handed at boot.
    """
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    #  THE CASE SAYS ITS OWN BUDGET — `deliberation:budgetWorlds` in its pick record, read the
    #  way every pick is — so what stops this pass is in the file rather than in this test.
    agent = snapshots.stand_in(CASES_DIR / "a_budget_that_stops_the_search.trig")
    (want,) = agent.wants.find_all_pursued()
    planner = Planner(agent, agent.me)
    assert planner.budget == 4, "the case's own budget, not this test's"
    plan = planner.plan(want)
    assert plan.outcome == "exhausted", plan.outcome
    im = planner.imaginarium

    #  FROM HERE, NOTHING OF THE PASS IS CONSULTED — only `im`, the want's IRI and the agent.
    frontier = bindings(im.query_over(f"""
SELECT ?world WHERE {{
  ?world a deliberation:PossibleWorld ; deliberation:spent ?spent ; deliberation:minted ?m ;
         deliberation:weighed ?x .
  ?x deliberation:forWant <{want.uri}> ; deliberation:open true ;
     deliberation:remaining ?left ; deliberation:wouldReach ?u . }}
ORDER BY (?spent + ?left) ?u ?spent ?m""", PASS_GRAPH))
    assert frontier, "a pass out of budget left nothing open to resume from"
    next_world = frontier[0]["world"]

    #  ITS READINGS ARE THERE TO BE READ, and they are ITS — not the root's. An open world was
    #  never dropped even when worlds were, so presence alone would prove little; that they
    #  DIFFER from where the pass started is what says the store holds this world and not just
    #  a world. (That EXPANDED worlds survive too is `test_cone`'s assertion, and is what #740
    #  changed.)
    assert im.holds(next_world), "the world to open next is not in the imaginarium"
    assert im.dump_nt(next_world).strip() != im.dump_nt(planner._root.graph).strip(), \
        "the store holds this world's own readings"

    #  AND WHAT IT AFFORDS, asked of that world by collections that hold stores and no agent.
    rows = agent.afforder.offered(Affordances(im),
                                  graphs=[next_world, *im.graphs_of(PUBLIC)])
    assert rows, f"nothing is afforded in {next_world.rsplit('/', 1)[-1]}"
    assert all(r.action and r.binding for r in rows), "and each names its action and what it is filled with"
    #  AND THEY ARE THIS WORLD'S. Hanoi affords a move per (movable disk, legal peg), and which
    #  those are depends on where the disks stand — so the rows here differ from the rows at
    #  the root, and a reader that had quietly asked the wrong world would show the root's.
    at_root = agent.afforder.offered(Affordances(im),
                                     graphs=[planner._root.graph, *im.graphs_of(PUBLIC)])
    assert {(r.action, r.binding) for r in rows} != {(r.action, r.binding) for r in at_root}, \
        "the affordances are read in the world the store named, not wherever the pass stood"

    #  THE BOUND a resumed pass would refuse against: what the cheapest achiever spent, or
    #  none where nothing has achieved yet.
    bound = bindings(im.query_over(
        f"SELECT (MIN(?s) AS ?bound) WHERE {{ ?a deliberation:meets <{want.uri}> ; "
        f"deliberation:spent ?s }}", PASS_GRAPH))
    assert bound, "the bound is a query over the rows, whatever it answers"
