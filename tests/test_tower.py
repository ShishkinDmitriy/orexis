"""Planning inside another (#523, a-level-is-a-vocabulary-and-a-bridge): hanoi's disks on the
courier's grid. The mover plans seven Moves at hanoi's level and never sees a cell; each
Move, when reached, is a promise the level beneath keeps — its predicted fact, translated
through the tower's bridge, becomes a want the courier's search plans as drives from
wherever the van then stands. Nobody wrote a method. The world answers by hand, as in the
hanoi and courier tests, since neither domain has a device."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from orexis_agent_progression.store import bindings
from conftest import genesis_store

H = "http://example.org/orexis/hanoi#"
C = "http://example.org/orexis/courier#"
W = "http://example.org/orexis/world/tower#"
WANT = W + "every_disk_home"
STATE_GRAPH = "http://example.org/orexis/graph/sensed"
PROMISE = "http://example.org/orexis#promise_"


def _pose(st, disks):
    """The stack on peg A, smallest on top — and, on the grid, every disk at peg A's cell and
    the van in the middle: the same world in two vocabularies."""
    triples, below = [], H + "PegA"
    for d in reversed(disks):
        triples.append(f"<{W}{d}> <{H}on> <{below}>")
        triples.append(f"<{W}{d}> <{C}at> <{W}c0_0>")
        below = W + d
    triples.append(f"<{W}van> <{C}at> <{W}c1_1>")
    st.update("INSERT DATA { GRAPH <%s> { %s } }" % (STATE_GRAPH, " . ".join(triples) + " . "))


def _mover(monkeypatch, disks):
    from agent import genesis, runtime
    monkeypatch.setenv("INFLUX_BUCKET", "test-tower")
    monkeypatch.setenv("INFLUX_TOKEN", "test-token-tower")
    st = genesis_store(world="tower")
    _pose(st, disks)
    genesis.classify_own_graphs(st, "mover")
    return runtime.Agent("mover", st=st)


def _answer(agent, predicts):
    """The world answering exactly as a step predicted — what a device would report."""
    def term(x):
        return repr(float(x)) if isinstance(x, (int, float)) else f"<{x}>"
    adds, retracts = predicts
    gone = " . ".join(" ".join(map(term, f)) for f in retracts if len(f) == 3)
    come = " . ".join(" ".join(map(term, f)) for f in adds if len(f) == 3)
    if gone:
        agent.beliefs.update(f"DELETE DATA {{ GRAPH <{STATE_GRAPH}> {{ {gone} . }} }}")
    if come:
        agent.beliefs.update(f"INSERT DATA {{ GRAPH <{STATE_GRAPH}> {{ {come} . }} }}")


def _walk(agent, uri, steps_seen):
    """Walk one intention's plan by hand: open each step's watch where an actor would, and
    let the world answer it as predicted."""
    keeper = agent.keeper
    for _ in range(40):
        standing = [s for s in keeper.standing() if s.uri == uri]
        if not standing:
            return
        step = standing[0].step
        steps_seen.append(step.action.rsplit("#", 1)[-1])
        assert keeper.expect(uri, f"{step.action.rsplit('#', 1)[-1]} — show me",
                             not_after=datetime.now(timezone.utc) + timedelta(hours=1))
        _answer(agent, step.predicts)
    raise AssertionError("a plan that never ends")


def test_seven_moves_are_planned_once_above_and_each_is_planned_as_drives_below(monkeypatch):
    from orexis_agent_deliberation import planner, pursuit

    agent = _mover(monkeypatch, ["disk_1", "disk_2", "disk_3"])
    searches = []
    real = planner.Planner.plan
    monkeypatch.setattr(planner.Planner, "plan",
                        lambda self, d: (searches.append(d.uri), real(self, d))[1])
    keeper = agent.keeper
    outer = pursuit.pursue(agent, next(g for g in agent.pursuing() if g.uri == WANT))
    assert outer is not None and searches == [WANT], "one search at hanoi's level"
    outer_steps = bindings(agent.intentions.query_union(
        f"SELECT ?s WHERE {{ <{outer}> orexis:step ?s }}"))
    assert len(outer_steps) == 7, "seven Moves, and not one drive among them"

    moves_kept, drives = 0, []
    for _ in range(7):
        promises = [d for d in agent.pursuing() if d.uri.startswith(PROMISE)]
        assert len(promises) == 1, "the Move that is current raised exactly one promise"
        inner = pursuit.pursue(agent, promises[0])
        assert inner is not None, "the courier's search found the drives"
        inner_steps = []
        _walk(agent, inner, inner_steps)
        assert set(inner_steps) <= {"Drive", "Pick", "Drop"} and "Pick" in inner_steps and "Drop" in inner_steps, inner_steps
        drives.append(inner_steps)
        moves_kept += 1
    assert keeper.standing() == [], "every Move kept its promise and the plan finished"
    goal = next(g for g in agent.pursuing() if g.uri == WANT)
    assert goal.state == "met", "the tower stands on peg C — in hanoi's words, written by the bridge"
    assert searches.count(WANT) == 1 and len([s for s in searches if s.startswith(PROMISE)]) == 7, \
        "one search above, one below per Move"
    assert all(2 <= len(d) <= 12 for d in drives), drives
