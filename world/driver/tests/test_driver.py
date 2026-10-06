"""The driver world (#903): the dispatcher's two vans and two parcels on two DISJOINT grids, and one
driver the agent controls, who sits in a van and must board the other before it can move. "One van
at a time" is world state here and not a mechanism: a drive's precondition needs the driver aboard
the van (`domains/courier/actions.ttl`), a boarding moves the driver between vans
(`domains/courier/driver.ttl`), and every plan respects the limit by construction. What this world
is held to is what was MEASURED on it:

- it boots and is possible: one scope, the driver aboard van A, and no constraint the present
  violates, so `orexis-onboard` refuses nothing (`tests/test_layout.py` onboards it whole);
- THE TWO PARCELS ARE ONE WANT, and only because the world says the driver is one body: the
  derivation couples two instances where a CONSTRAINT's rows over the reach join them
  (`agent/planning/couplings.py`), and on disjoint grids the two-vans constraint yields no row. So
  the world states the driver's own — a driver is aboard one van at a time — whose rows over the
  delete-free reach put the driver aboard both vans and join them. Without it the parcels are two
  wants, planned apart at five and six steps, and the two plans walked side by side drive van A with
  the driver aboard van B, measured and pinned below;
- coupled, the search finds ONE plan of eleven steps — van A's delivery, the boarding, van B's —
  optimal for both by construction, at the figures measure-the-search tabulates; the estimate reads
  ten, admissible and loose by the boarding no parcel owes;
- WALKED, the plan is one act at a time: every step is taken only once the step before it has been
  answered, every drive moves the van the driver is aboard at that act, and both parcels are
  delivered by one intention.
"""

from __future__ import annotations

import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from agent import clock
from agent.planning.planner import Planner
from agent.runtime import UNFINISHED, Runtime, boot
from agent.store import rows
from onboarding import reading

WORLD = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
D = "http://example.org/orexis/world/driver#"
JOINT = "every_parcel_delivered.pursued.parcel_a.parcel_b"
A = "every_parcel_delivered.pursued.parcel_a"
B = "every_parcel_delivered.pursued.parcel_b"
#  THE TWO CONSTRAINTS this world states (`constraints.ttl`).
TWO_VANS, ONE_VAN = "no_cell_holds_two_vans", "a_driver_is_aboard_one_van"
#  WHAT THE COUPLED SEARCH NEEDS: 191 candidates, measured, so the default budget of 128 cuts it
#  short and the passes after would finish it; the tests state 256, as the dispatcher's do.
BUDGET = 256
#  THE BANDS, as the courier declares them: a drive lands half a minute to a minute after it is taken,
#  a boarding one minute to two, a pick and a drop at once.
DRIVE_LEAST_S = 30

#  THE WORLD WITHOUT THE DRIVER'S CONSTRAINT: the holding taken out, the constraint left described.
UNHELD = {"constraints.ttl": [(":dispatcher planning:holds :a_driver_is_aboard_one_van .", "")]}

_MEMBERS_Q = "SELECT ?m ?s WHERE { GRAPH ?g { ?m planning:inScope ?s } }"
_WANTS_Q = "SELECT ?w WHERE { GRAPH ?g { ?w a planning:Want ; prov:wasDerivedFrom ?d } }"
_PLANS_Q = """
SELECT ?want ?outcome (COUNT(?step) AS ?steps) WHERE {
  GRAPH ?p { ?p a planning:Plan ; planning:outcome ?outcome ; planning:for ?want .
             OPTIONAL { ?step a execution:Step ; execution:partOf ?p } } }
GROUP BY ?want ?outcome"""
#  THE PLAN'S STEPS IN THE ORDER IT PLACES THEM, with what each fills and what it is filled with.
_ORDERED_Q = """PREFIX courier: <http://example.org/orexis/courier#>
SELECT ?a ?van ?parcel ?to ?driver WHERE {
  GRAPH ?p { ?p a planning:Plan ; planning:for $want . ?step a execution:Step ; execution:partOf ?p ; planning:fills ?a ;
             execution:notBefore ?nb ; execution:landsAt ?la .
             OPTIONAL { ?step courier:van ?van } OPTIONAL { ?step courier:parcel ?parcel }
             OPTIONAL { ?step courier:to ?to } OPTIONAL { ?step courier:driver ?driver } } }
ORDER BY ?nb ?la"""
#  WHAT A WANT'S SEARCH SPENT — every weighing but a ground's: the budget's unit, the runbook's candidates.
_SPENT_Q = """
SELECT ?for (COUNT(?x) AS ?n) WHERE {
  GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?x a planning:Weighing ; planning:for ?for ; planning:weighs ?u .
    FILTER NOT EXISTS { ?u a planning:GroundGraph } } }
GROUP BY ?for"""
#  THE POSSIBLE WORLDS WEIGHED PER WANT, and per constraint.
_WEIGHED_Q = """
SELECT ?for (COUNT(?x) AS ?n) WHERE {
  GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?x a planning:Weighing ; planning:for ?for ; planning:weighs ?w .
    ?w a planning:PossibleGraph } }
GROUP BY ?for"""
_IMPOSSIBLE_Q = """
SELECT ?w WHERE { GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?w a planning:PossibleGraph ; planning:impossible ?by } }"""
_REMAINING_Q = """
SELECT ?for ?left WHERE {
  GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?x a planning:Weighing ; planning:for ?for ; planning:weighs ?g ;
    planning:remaining ?left . ?g a planning:GroundGraph } }"""
_COSTS_Q = """
SELECT ?want ?spent WHERE { GRAPH ?p { ?p a planning:Plan ; planning:for ?want ; planning:spent ?spent } }"""
#  WHERE THINGS STAND AND WHOM THE DRIVER IS IN, asked of what the agent BELIEVES by kind — a published
#  plan's steps state what they predict in graphs of their own, which are no belief.
_WHERE_Q = """PREFIX courier: <http://example.org/orexis/courier#>
SELECT ?x ?p ?o WHERE { GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?g a orexis:BeliefGraph }
  GRAPH ?g { ?x ?p ?o FILTER(?p IN (courier:at, courier:aboard, courier:carriedBy)) } }"""
#  WHAT A STEP FILLS, read off the plan it was published in.
_STEP_Q = """PREFIX courier: <http://example.org/orexis/courier#>
SELECT ?a ?van ?driver WHERE { GRAPH ?p { $step planning:fills ?a .
  OPTIONAL { $step courier:van ?van } OPTIONAL { $step courier:driver ?driver } } }"""
_INTENTIONS_Q = "SELECT (COUNT(?i) AS ?n) WHERE { GRAPH ?g { ?i a execution:Intention } }"


def _local(iri: str | None) -> str | None:
    return iri.rsplit("#", 1)[-1].rsplit("/", 1)[-1] if iri else None


def variant(tmp_path: Path, name: str, edits: dict) -> Path:
    """The driver world with its documents rewritten — a copy, since a world imports its domains by the tree's shape."""
    world = tmp_path / name / "world" / "driver"
    shutil.copytree(WORLD, world, ignore=shutil.ignore_patterns("tests", "secrets", "__pycache__"))
    (tmp_path / name / "domains").symlink_to(WORLD.parents[1] / "domains")
    for file, pairs in edits.items():
        text = (world / file).read_text()
        for old, new in pairs:
            assert old in text, f"{file} no longer says {old!r}"
            text = text.replace(old, new)
        (world / file).write_text(text)
    return world


class _Clock:
    """One timeline: every read moves it on by a second, as a running agent's clock does."""

    def __init__(self, at):
        self.at = at

    def __call__(self):
        self.at += timedelta(seconds=1)
        return self.at


@pytest.fixture
def ticking(monkeypatch):
    monkeypatch.setattr(clock, "now", lambda: NOW)


def _pass(world: Path, budget: int = BUDGET):
    """One pass of the Planner over the booted world, from the present. The one imaginarium."""
    planner = Planner(boot(world, "dispatcher"), "dispatcher", budget=budget)
    planner.plan(NOW)
    (im,) = planner.imaginaria.values()
    return im


def _wants(im) -> set[str]:
    return {_local(r["w"]) for r in rows(im, _WANTS_Q, ())}


def _plans(im) -> dict[str, tuple[str, int]]:
    return {_local(r["want"]): (_local(r["outcome"]), int(r["steps"])) for r in rows(im, _PLANS_Q, ())}


def _ordered(im, want: str) -> list[tuple]:
    return [(_local(r["a"]), _local(r.get("van")), _local(r.get("parcel")), _local(r.get("to")), _local(r.get("driver")))
            for r in rows(im, _ORDERED_Q, (), want=D + want)]


def _counted(im, query: str) -> dict[str, int]:
    return {_local(r["for"]): int(r["n"]) for r in rows(im, query, ())}


def _where(store) -> dict[str, str]:
    return {_local(r["x"]): _local(r["o"]) for r in rows(store, _WHERE_Q, ()) if r["x"].startswith(D)}


def _walk(world: Path, passes: int = 40, budget: int = BUDGET) -> dict:
    """The runtime over the booted world, pass after pass with the clock moved on by a drive's least
    landing between passes, until no intention stands or `passes` are spent. Every executor event in
    the order it happened — a step taken with what it filled and where the driver was the moment it
    was taken, a step answered, an intention resolved."""
    time = _Clock(NOW)
    clock.now = time
    beliefs = boot(world, "dispatcher")
    runtime = Runtime(beliefs, "dispatcher", budget=budget)
    executor = runtime.parts["execution"].executor
    events: list[tuple] = []

    def taken(event):
        #  ONE FILLING, however many graphs state the step — the plan, and the intention that adopted it.
        ((action, van),) = {(_local(r["a"]), _local(r.get("van"))) for r in rows(beliefs, _STEP_Q, (), step=event.step)}
        events.append(("taken", event.step, _local(event.want), action, van, _where(beliefs).get("driver")))
        return []
    executor.step_taken.connect(taken)
    executor.step_answered.connect(lambda e: events.append(("answered", e.step, e.landed)) or [])
    executor.intention_resolved.connect(lambda e: events.append(("resolved", _local(e.want), e.outcome)) or [])
    outcome = runtime.run(passes=1, poll_s=0)
    n = 1
    while n < passes and outcome == UNFINISHED and executor.standing():
        time.at += timedelta(seconds=DRIVE_LEAST_S)
        outcome = runtime.run(passes=1, poll_s=0)
        n += 1
    return {"runtime": runtime, "beliefs": beliefs, "outcome": outcome, "events": events, "passes": n}


def test_the_driver_is_world_state_and_the_world_as_posed_is_possible(ticking):
    """One scope, the driver and its boarding in it with both vans and both parcels; the driver aboard
    van A; and neither constraint violated in the present, so the pass says no contradiction and
    onboarding refuses nothing."""
    beliefs = boot(WORLD, "dispatcher")
    assert _where(beliefs) == {"driver": "van_a", "van_a": "c0_0", "parcel_a": "c0_1", "van_b": "g10_0", "parcel_b": "g10_1"}
    members: dict[str, set] = {}
    for r in rows(beliefs, _MEMBERS_Q, ()):
        members.setdefault(_local(r["m"]), set()).add(r["s"])
    assert len({s for ss in members.values() for s in ss}) == 1, "one scope: the driver joins what the grids keep apart"
    assert {"driver", "van_a", "van_b", "parcel_a", "parcel_b", "Drive", "Pick", "Drop", "Board", "aboard", "at"} <= set(members)
    assert reading.contradicted(WORLD, "dispatcher") == []
    assert Planner(boot(WORLD, "dispatcher"), "dispatcher").contradictions(NOW) == []


def test_one_driver_makes_two_parcels_on_disjoint_grids_one_want_and_one_plan_of_eleven_steps(ticking):
    """ONE want about both parcels, and one plan: van A's five steps, the boarding, van B's five. The
    plan drives one van, moves the driver, and drives the other — every drive of van A placed before
    the one boarding and every drive of van B after it, since a drive needs the driver aboard. THE
    FIGURES, measured: 191 candidates, 133 possible worlds, each constraint weighed in all 133 and
    marking none — the boarding deletes the van left, so no world a plan reaches has the driver in
    two, and no drive crosses between the grids; the default budget of 128 cuts the search short.
    The estimate reads ten, the courier's drives, picks and drops of both parcels, against eleven
    spent: admissible, and loose by the one boarding no parcel owes."""
    cut = _pass(WORLD, budget=128)
    assert _plans(cut) == {JOINT: ("Exhausted", 0)} and _counted(cut, _SPENT_Q)[JOINT] == 128
    im = _pass(WORLD)
    assert _wants(im) == {JOINT}
    assert _plans(im) == {JOINT: ("Satisfied", 11)}
    steps = _ordered(im, JOINT)
    boards = [i for i, s in enumerate(steps) if s[0] == "Board"]
    assert len(boards) == 1 and steps[boards[0]][1:] == ("van_b", None, None, "driver"), steps
    drives = [(i, van) for i, (a, van, _, _, _) in enumerate(steps) if a == "Drive"]
    assert len(drives) == 6 and all((van == "van_a") == (i < boards[0]) for i, van in drives), \
        f"van A driven before the boarding and van B after it: {steps}"
    assert (_counted(im, _SPENT_Q)[JOINT], _counted(im, _WEIGHED_Q)) == (191, {JOINT: 133, TWO_VANS: 133, ONE_VAN: 133}), \
        f"measured: {_counted(im, _SPENT_Q)} {_counted(im, _WEIGHED_Q)}"
    assert rows(im, _IMPOSSIBLE_Q, ()) == [], "no world a plan reaches puts the driver in two vans or two vans on a cell"
    left = {_local(r["for"]): float(r["left"]) for r in rows(im, _REMAINING_Q, ())}
    spent = {_local(r["want"]): float(r["spent"]) for r in rows(im, _COSTS_Q, ())}
    assert (left[JOINT], spent[JOINT]) == (10.0, 11.0), f"admissible, and loose by the boarding: {left} {spent}"


def test_without_the_drivers_constraint_the_parcels_are_two_wants_and_their_plans_drive_a_van_its_driver_has_left(ticking, tmp_path):
    """WHY THE WORLD STATES THE DRIVER'S CONSTRAINT. The derivation couples two instances where some
    constraint's rows over the reach join them, and nothing else: with the two-vans constraint alone,
    which on two grids yields no row, the parcels are two wants, planned apart — van A's five steps,
    and a boarding and van B's five — and both plans published. Walked side by side, the boarding is
    taken in the first pass beside van A's first drive, and van A's later drives are taken with the
    driver aboard van B: the fictive drive writes its own prediction and lands, and nothing between two
    passes asks a head's precondition again. Both parcels arrive, by a walk the world says cannot be.
    That is the state "one van at a time" is, read by no constraint, and so by no coupling."""
    unheld = variant(tmp_path, "unheld", UNHELD)
    im = _pass(unheld)
    assert _wants(im) == {A, B}
    assert _plans(im) == {A: ("Satisfied", 5), B: ("Satisfied", 6)}
    walked = _walk(unheld)
    driven = [(van, driver) for kind, *rest in walked["events"] if kind == "taken"
              for _, _, action, van, driver in [rest] if action == "Drive"]
    assert ("van_a", "van_b") in driven, f"van A driven with the driver aboard van B: {driven}"
    assert sorted(e[2] for e in walked["events"] if e[0] == "resolved") == ["done", "done"]


def test_walked_the_one_plan_moves_one_van_at_a_time(ticking):
    """THE ONE PLAN, WALKED: one intention, eleven acts, and one act at a time — every step after the
    first is taken only once the step before it has been answered, landed, so no two acts are ever in
    flight at once; every drive is of the van the driver is aboard the moment it is taken; the boarding
    is the one act between van A's last and van B's first. Both parcels delivered, the driver left
    aboard van B, and the intention done."""
    walked = _walk(WORLD)
    events, beliefs = walked["events"], walked["beliefs"]
    taken = [e for e in events if e[0] == "taken"]
    assert walked["outcome"] == UNFINISHED and len(taken) == 11, "a desire holds the agent, and the one plan is walked whole"
    assert {e[2] for e in taken} == {JOINT}
    flow = [e for e in events if e[0] in ("taken", "answered")]
    assert [e[0] for e in flow] == ["taken", "answered"] * 11, f"one act at a time: {flow}"
    assert all(t[1] == a[1] and a[2] for t, a in zip(flow[::2], flow[1::2])), "each act answered, landed, before the next is taken"
    drives = [(van, driver) for _, _, _, action, van, driver in taken if action == "Drive"]
    assert len(drives) == 6 and all(van == driver for van, driver in drives), f"every drive is of the van the driver is aboard: {drives}"
    actions = [action for _, _, _, action, _, _ in taken]
    assert actions.index("Board") > max(i for i, (_, _, _, a, van, _) in enumerate(taken) if van == "van_a" and a == "Drive")
    assert actions.index("Board") < min(i for i, (_, _, _, a, van, _) in enumerate(taken) if van == "van_b" and a == "Drive")
    assert _where(beliefs) == {"driver": "van_b", "van_a": "c0_3", "parcel_a": "c0_3", "van_b": "g10_3", "parcel_b": "g10_3"}
    executor = walked["runtime"].parts["execution"].executor
    assert int(rows(executor.intentions, _INTENTIONS_Q, ())[0]["n"]) == 1 and executor.walking() == []
    assert [e for e in events if e[0] == "resolved"] == [("resolved", JOINT, "done")]
