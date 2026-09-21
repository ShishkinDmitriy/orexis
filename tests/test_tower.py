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
from conftest import DISK, ONTO
from orexis_agent_progression.ontology import PUBLIC

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
    genesis.classify_kernel_graphs(st, "mover")
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
                        lambda self, d, **kw: (searches.append(d.uri), real(self, d, **kw))[1])
    keeper = agent.keeper
    outer = pursuit.pursue(agent, next(g for g in agent.considering() if g.uri == WANT))
    assert outer is not None and searches == [WANT], "one search at hanoi's level"
    outer_steps = bindings(agent.intentions.query_union(
        f"SELECT ?s WHERE {{ <{outer}> progression:step ?s }}"))
    assert len(outer_steps) == 7, "seven Moves, and not one drive among them"

    moves_kept, drives = 0, []
    for _ in range(7):
        promises = [d for d in agent.considering() if d.uri.startswith(PROMISE)]
        assert len(promises) == 1, "the Move that is current raised exactly one promise"
        inner = pursuit.pursue(agent, promises[0])
        assert inner is not None, "the courier's search found the drives"
        inner_steps = []
        _walk(agent, inner, inner_steps)
        assert set(inner_steps) <= {"Drive", "Pick", "Drop"} and "Pick" in inner_steps and "Drop" in inner_steps, inner_steps
        drives.append(inner_steps)
        moves_kept += 1
    assert keeper.standing() == [], "every Move kept its promise and the plan finished"
    #  THE WANT IS ONE-SHOT: its plan finished, so it is DONE and the collector takes it on the
    #  next pass. That is how the agent says the tower stands on peg C — in hanoi's words,
    #  written by the bridge.
    assert bindings(agent.beliefs.query(
        f"SELECT ?s WHERE {{ GRAPH ?g {{ <{WANT}> orexis:state ?s }} }}", ()))[0]["s"].endswith("#Done"), \
        "the plan finished, so the want it served is done"
    assert searches.count(WANT) == 1 and len([s for s in searches if s.startswith(PROMISE)]) == 7, \
        "one search above, one below per Move"
    assert all(2 <= len(d) <= 12 for d in drives), drives


def test_a_move_the_courier_cannot_make_is_refused_below_and_the_outer_level_stops_choosing_it(monkeypatch):
    """#533: cut the grid so peg C's cell is unreachable. The outer search still plans seven
    Moves — it sees no cells — and the first Move's promise finds no drives. When the step
    lapses, the refusal is written on it, and the next outer pass passes every Move to peg C
    over, records why, and answers that nothing helps rather than choosing the same move
    again. Two levels that would have looped now stop, with the reason in the trace."""
    from orexis_agent_deliberation import planner, pursuit, trace
    from orexis_agent_progression.ontology import WORLD_GRAPH

    agent = _mover(monkeypatch, ["disk_1", "disk_2", "disk_3"])
    # peg C sits at c1_2; remove the cells around it so no drive reaches it
    for cell in ("c0_2", "c2_2", "c1_1"):
        agent.beliefs.update(f"DELETE WHERE {{ GRAPH <{WORLD_GRAPH}> {{ <{W}{cell}> ?p ?o }} }}")
    agent.beliefs.update(f"DELETE WHERE {{ GRAPH <{STATE_GRAPH}> {{ <{W}van> <{C}at> ?c }} }}")
    agent.beliefs.update(f"INSERT DATA {{ GRAPH <{STATE_GRAPH}> {{ <{W}van> <{C}at> <{W}c1_0> }} }}")
    keeper = agent.keeper
    outer = pursuit.pursue(agent, next(g for g in agent.considering() if g.uri == WANT))
    assert outer is not None, "the outer level plans without seeing a cell"
    promises = [d for d in agent.considering() if d.uri.startswith(PROMISE)]
    assert len(promises) == 1
    failed = agent.deliberator._plans_failed
    assert pursuit.pursue(agent, promises[0]) is None, "the courier finds no way to peg C"
    assert agent.deliberator._plans_failed == failed + 1, "the refusal lapses the step at once"
    #  THE PEG BY ITS OWN NAME: a step writes one triple per parameter its action declares, so
    #  the refusal names `hanoi:onto` where it used to name the kernel's `orexis:about`.
    refused = bindings(agent.intentions.query_union(
        f"SELECT ?s ?a WHERE {{ ?s progression:refusedBelow ?at ; <{ONTO}> ?a }}"))
    assert len(refused) == 1 and refused[0]["a"] == H + "PegC", "the refusal is on the step, naming the peg"
    again = pursuit.pursue(agent, next(g for g in agent.considering() if g.uri == WANT))
    assert again is not None and again != outer, "the outer level decides again, around the refusal"
    head = keeper.current(again)
    assert not (head.value_of(DISK) == W + "disk_1" and head.value_of(ONTO) == H + "PegC"), \
        "the refused move is not chosen again while the refusal is younger than the patience"
    from orexis_agent_progression.ontology import DELIBERATION_GRAPH
    refusals = bindings(agent.beliefs.query(f"""
SELECT ?c WHERE {{ GRAPH <{DELIBERATION_GRAPH}> {{
  ?c deliberation:verdict "{trace.REFUSED}" ; <{DISK}> <{W}disk_1> }} }}""", agent.beliefs.graphs_of(PUBLIC)))
    assert refusals, "and the trace says why it was passed over"
