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

from datetime import timedelta

import pyoxigraph as ox

from agent import clock
from agent.execution.plans import pursued
from agent.planning.ontology import PLAN_GRAPH, POSSIBLE_GRAPH
from agent.planning.planner import Planner
from agent.store import graphs_of, rows

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
    (imagined,) = planner.imaginaria.values()
    snapshots.held_to_diff(case, request, "planner", snapshots.snapshot_of(imagined))


def test_every_case_is_read_and_no_diff_is_orphaned(snapshots):
    """A glob that stopped matching would pass every case by running none."""
    assert len(CASES) >= 2, [c.name for c in CASES]
    assert not snapshots.orphans_in(CASES_DIR)


# --- reruns: the imaginarium outlives the pass ------------------------------------------------

BENCH = Path(__file__).parent / "bench"

_STEPS_Q = """SELECT (COUNT(?s) AS ?n) WHERE { GRAPH ?p { ?p a planning:Plan . ?s a execution:Step ; execution:partOf ?p } }"""
_HEAD_Q = """
SELECT ?disk ?onto WHERE {
  GRAPH ?g { ?i a execution:Intention ; execution:by ?step . ?step ?pd ?disk ; ?po ?onto .
             FILTER(STRENDS(STR(?pd), "#disk") && STRENDS(STR(?po), "#onto")) } }"""


def _two_disks(snapshots, held: bool):
    store = snapshots.stand_in(BENCH / "two_disk_hanoi.trig")
    return store, Planner(store, snapshots.AGENT, intentions=ox.Store() if held else None)


def _worlds(planner) -> set[str]:
    """The possible worlds standing. A fork is a world with a name nothing had — a world made
    for a filling a kept world already admits is never forked — so no fork means no new name."""
    (im,) = planner.imaginaria.values()
    return set(graphs_of(im, POSSIBLE_GRAPH))


def _steps(planner) -> int:
    (im,) = planner.imaginaria.values()
    return int(rows(im, _STEPS_Q, ())[0]["n"])


def _move(store, disk: str, onto: str) -> None:
    """The world moves a disk: its `hanoi:on` row replaced in the state graph."""
    (row,) = rows(store, f'SELECT ?d ?p ?o ?g WHERE {{ GRAPH ?g {{ ?d ?p ?o }} FILTER(STRENDS(STR(?d), "{disk}") && STRENDS(STR(?p), "#on")) }}')
    store.update(f'DELETE DATA {{ GRAPH <{row["g"]}> {{ <{row["d"]}> <{row["p"]}> <{row["o"]}> }} }} ; '
                 f'INSERT DATA {{ GRAPH <{row["g"]}> {{ <{row["d"]}> <{row["p"]}> <{onto}> }} }}')


def test_a_pass_a_minute_later_hands_down_no_second_intention(monkeypatch, snapshots):
    """Called every minute with nothing happened, the planner used to mint an intention for the
    same want every pass — three passes, three intentions, measured. A want an intention is
    walking is not searched and its plan does not cross again."""
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    store, planner = _two_disks(snapshots, held=True)
    planner.plan(snapshots.NOW)
    assert len(pursued(planner.intentions)) == 1
    imagined = _worlds(planner)
    later = snapshots.NOW + timedelta(minutes=1)
    monkeypatch.setattr(clock, "now", lambda: later)
    planner.plan(later)
    assert len(pursued(planner.intentions)) == 1, "the same commitment stands, and no second one beside it"
    assert len(rows(planner.intentions, "SELECT ?i WHERE { GRAPH ?g { ?i a execution:Intention } }")) == 1
    assert _worlds(planner) == imagined, "and nothing was forked for a want being walked"


def test_nothing_happened_and_the_next_pass_forks_nothing(monkeypatch, snapshots):
    """The old present's hash is the new one's, so the whole cone is kept under the new ground
    and the search reads its way to the same plan."""
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    store, planner = _two_disks(snapshots, held=False)
    planner.plan(snapshots.NOW)
    imagined, steps = _worlds(planner), _steps(planner)
    assert steps == 3
    later = snapshots.NOW + timedelta(minutes=1)
    monkeypatch.setattr(clock, "now", lambda: later)
    planner.plan(later)
    assert (_worlds(planner), _steps(planner)) == (imagined, 3)


def test_a_step_taken_as_predicted_is_planned_on_from_the_kept_cone(monkeypatch, snapshots):
    """The plan's first move is taken; the next pass finds that world to be the present, and the
    rest of the plan is read off the cone beneath it without a fork."""
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    store, planner = _two_disks(snapshots, held=True)
    planner.plan(snapshots.NOW)
    imagined = _worlds(planner)
    (head,) = rows(planner.intentions, _HEAD_Q, ())
    _move(store, head["disk"].rsplit("#", 1)[-1], head["onto"])
    #  THE EXECUTOR ANSWERED: the step landed, so the commitment is resolved and the want is the
    #  search's again. (The keeper's door; a bare row here says the same thing.)
    planner.intentions.update("""INSERT { GRAPH ?g { ?i <http://example.org/orexis/execution#resolvedAt> "2026-01-01T12:00:30Z" } }
                                 WHERE { GRAPH ?g { ?i a <http://example.org/orexis/execution#Intention> } }""")
    later = timedelta(minutes=1) + snapshots.NOW
    monkeypatch.setattr(clock, "now", lambda: later)
    planner.plan(later)
    assert _steps(planner) == 2, "two moves left"
    assert _worlds(planner) < imagined, "found in the cone kept, and not one world forked: the siblings went"
    assert len(pursued(planner.intentions)) == 1, "a new commitment for the rest"


def test_a_surprise_starts_the_search_afresh(monkeypatch, snapshots):
    """A state no move reaches — disk 2 on disk 1, on peg B — is nothing the pass imagined, so
    everything goes and the search forks from the new ground."""
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    store, planner = _two_disks(snapshots, held=False)
    planner.plan(snapshots.NOW)
    (im,) = planner.imaginaria.values()
    before = set(graphs_of(im, POSSIBLE_GRAPH))
    (a_disk,) = rows(store, 'SELECT ?d WHERE { GRAPH ?g { ?d ?p ?o } FILTER(STRENDS(STR(?d), "disk_1") && STRENDS(STR(?p), "#on")) }')
    hanoi = "http://example.org/orexis/hanoi#"
    _move(store, "disk_1", hanoi + "PegB")
    _move(store, "disk_2", a_disk["d"])
    later = snapshots.NOW + timedelta(minutes=1)
    monkeypatch.setattr(clock, "now", lambda: later)
    planner.plan(later)
    after = set(graphs_of(im, POSSIBLE_GRAPH))
    assert not (before & after), "no world of the last pass survived"
    assert after and _steps(planner) == 2, "disk 2 to C, disk 1 to C — found from the new ground"


# --- the estimate ---------------------------------------------------------------------------

_WEIGHED_Q = """
SELECT (COUNT(?x) AS ?n) WHERE {
  GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?x a planning:Weighing ; planning:weighs ?w .
               FILTER NOT EXISTS { ?w a planning:GroundGraph } } }"""


def _weighed(store, budget: int, *, estimate: bool, snapshots) -> tuple[int, int]:
    """Three-disk hanoi planned once: candidates weighed, and the plan's steps."""
    if not estimate:
        store.update("DELETE { GRAPH ?g { ?d <http://example.org/orexis#estimates> ?e } } "
                     "WHERE { GRAPH ?g { ?d <http://example.org/orexis#estimates> ?e } }")
    planner = Planner(store, snapshots.AGENT, budget=budget)
    planner.plan(snapshots.NOW)
    (im,) = planner.imaginaria.values()
    return int(rows(im, _WEIGHED_Q, ())[0]["n"]), _steps(planner)


def test_an_estimate_refuses_forks_a_uniform_cost_search_pays_for(monkeypatch, snapshots):
    """The frontier is ordered by spent plus what the want's estimate says is left, and the
    cheapest achiever bounds the sum: on three disks the same seven-move plan is found
    having weighed fewer candidates than with no estimate at all."""
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    with_it = _weighed(snapshots.stand_in(BENCH / "three_disk_hanoi.trig"), 128, estimate=True, snapshots=snapshots)
    without = _weighed(snapshots.stand_in(BENCH / "three_disk_hanoi.trig"), 128, estimate=False, snapshots=snapshots)
    assert with_it[1] == without[1] == 7, "the same optimal plan either way"
    assert with_it[0] < without[0], f"and fewer candidates weighed: {with_it[0]} against {without[0]}"


# --- a search cut short, finished across passes ------------------------------------------------

_OUTCOME_Q = """SELECT ?o WHERE { GRAPH ?p { ?p a planning:Plan ; planning:outcome ?o } }"""


def _outcome(planner) -> str:
    (im,) = planner.imaginaria.values()
    (found,) = rows(im, _OUTCOME_Q, ())
    return found["o"].rsplit("#", 1)[-1]


def test_a_search_the_budget_cuts_short_is_finished_by_the_passes_after(monkeypatch, snapshots):
    """Twenty candidates a pass on three disks, one pass a minute: two passes answer EXHAUSTED
    and hand nothing down, the third reaches the seven-move plan and hands it down, and the
    three together weighed exactly what one pass with room enough weighs — the kept
    imaginarium continues the search, it does not repeat it, and the budget is each call's."""
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    whole, _ = _weighed(snapshots.stand_in(BENCH / "three_disk_hanoi.trig"), 128, estimate=True, snapshots=snapshots)
    store = snapshots.stand_in(BENCH / "three_disk_hanoi.trig")
    planner = Planner(store, snapshots.AGENT, intentions=ox.Store(), budget=20)
    passes = []
    for i in range(3):
        at = snapshots.NOW + timedelta(minutes=i)
        monkeypatch.setattr(clock, "now", lambda at=at: at)
        planner.plan(at)
        passes.append((_outcome(planner), len(pursued(planner.intentions))))
    assert passes == [("Exhausted", 0), ("Exhausted", 0), ("Satisfied", 1)]
    assert _steps(planner) == 7
    (im,) = planner.imaginaria.values()
    assert int(rows(im, _WEIGHED_Q, ())[0]["n"]) == whole, "no candidate weighed twice, and none skipped"
