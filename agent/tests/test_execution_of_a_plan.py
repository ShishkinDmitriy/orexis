"""A plan found by the planner is carried out by the executor, and the world moves it.

The two layers meet here, above both: the planner hands its plan down to the executor's
store, the executor takes the head step, and only the belief base saying what the step
predicted — the disk on the peg the plan said — moves the intention to the next step. A
world that does what the plan said walks the intention to `done`; a world that does not
fails it. Two disks, three moves, the case the bench runs.
"""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import pyoxigraph as ox

from agent import clock
from agent.execution.executor import DEFAULT_PATIENCE_S, Executor
from agent.planning.planner import Planner
from agent.store import rows

BENCH = Path(__file__).resolve().parents[1] / "planning" / "tests" / "bench"

_HEAD_Q = """
SELECT ?disk ?onto WHERE {
  GRAPH ?g { ?i a execution:Intention ; execution:by ?step . ?step ?pd ?disk ; ?po ?onto .
             FILTER NOT EXISTS { ?i execution:resolvedAt ?done }
             FILTER(STRENDS(STR(?pd), "#disk") && STRENDS(STR(?po), "#onto")) } }"""


def _move(beliefs, disk: str, onto: str) -> None:
    """The world does what the move says: the disk lands on whatever is on top of the peg it
    was moved onto, or on the peg itself — the domain's own effect, not the parameter."""
    (row,) = rows(beliefs, f'SELECT ?d ?p ?o ?g WHERE {{ GRAPH ?g {{ ?d ?p ?o }} FILTER(?d = <{disk}> && STRENDS(STR(?p), "#on")) }}')
    top = rows(beliefs, f'SELECT ?t WHERE {{ GRAPH ?g {{ ?t <{row["p"]}>+ <{onto}> . FILTER NOT EXISTS {{ ?z <{row["p"]}> ?t }} FILTER(?t != <{disk}>) }} }}')
    dest = top[0]["t"] if top else onto
    beliefs.update(f'DELETE DATA {{ GRAPH <{row["g"]}> {{ <{row["d"]}> <{row["p"]}> <{row["o"]}> }} }} ; '
                   f'INSERT DATA {{ GRAPH <{row["g"]}> {{ <{row["d"]}> <{row["p"]}> <{dest}> }} }}')


def _planned(snapshots, monkeypatch, **kw):
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    beliefs = snapshots.stand_in(BENCH / "two_disk_hanoi.trig")
    executor = Executor(beliefs, snapshots.AGENT, **kw)
    Planner(beliefs, snapshots.AGENT, executor=executor).plan(snapshots.NOW)
    assert len(executor.walking()) == 1
    return beliefs, executor


def test_a_world_that_does_what_the_plan_said_walks_the_intention_to_done(monkeypatch, snapshots):
    beliefs, x = _planned(snapshots, monkeypatch)
    for move in range(3):
        assert x.tick(snapshots.NOW), f"move {move + 1} is due"
        assert x.drain() == 1
        (head,) = rows(x.intentions, _HEAD_Q, ())
        assert x.tick(snapshots.NOW) == [], "taken, and waiting for the world"
        _move(beliefs, head["disk"], head["onto"])
        x.tick(snapshots.NOW)
    assert x.walking() == [], "done: nothing stands"
    (outcome,) = rows(x.intentions, "SELECT ?o WHERE { GRAPH ?g { ?i a execution:Intention ; execution:outcome ?o } }", ())
    assert outcome["o"] == "done"


def test_a_fictive_action_is_walked_by_a_plain_executor(monkeypatch, snapshots):
    """The world says the move is fictive — its implementation is one `execution:Fictive`
    operation — and an executor that holds other steps to the world takes these itself."""
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    beliefs = snapshots.stand_in(BENCH / "two_disk_hanoi.trig")
    beliefs.update("INSERT { GRAPH ?g { ?a <http://example.org/orexis/execution#implementation> [ "
                   "<http://example.org/orexis/execution#operation> [ a <http://example.org/orexis/execution#Fictive> ] ] } } "
                   "WHERE { GRAPH ?g { ?a a <http://example.org/orexis#Action> } }")
    x = Executor(beliefs, snapshots.AGENT)
    Planner(beliefs, snapshots.AGENT, executor=x).plan(snapshots.NOW)
    for _ in range(3):
        assert x.tick(snapshots.NOW) and x.drain() == 1
        x.tick(snapshots.NOW)
    assert x.walking() == []


def test_a_fictive_executor_walks_the_plan_with_no_world_at_all(monkeypatch, snapshots):
    """Hanoi has no instrument: a fictive executor writes each step's prediction into the
    readings itself, and three passes of tick and drain solve the tower."""
    beliefs, x = _planned(snapshots, monkeypatch, fictive=True)
    for _ in range(3):
        assert x.tick(snapshots.NOW), "the head is due"
        assert x.drain() == 1
        x.tick(snapshots.NOW)               # the world — the executor — has answered
    assert x.walking() == []
    (outcome,) = rows(x.intentions, "SELECT ?o WHERE { GRAPH ?g { ?i a execution:Intention ; execution:outcome ?o } }", ())
    assert outcome["o"] == "done"


def test_a_world_that_does_not_move_fails_the_intention_after_the_patience(monkeypatch, snapshots):
    beliefs, x = _planned(snapshots, monkeypatch)
    x.tick(snapshots.NOW)
    x.drain()
    x.tick(snapshots.NOW + timedelta(seconds=DEFAULT_PATIENCE_S))
    assert x.walking() == []
    (outcome,) = rows(x.intentions, "SELECT ?o WHERE { GRAPH ?g { ?i a execution:Intention ; execution:outcome ?o } }", ())
    assert outcome["o"] == "failed"
