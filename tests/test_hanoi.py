"""Tower of Hanoi through the ordinary search (#257): the domain-is-a-plug-in claim, tested
on a classical planning task. The domain is an ontology and six ground actions with no
Python; the goal is a world-ratified desire met by absence; and the optimal solution is the
cheapest achiever — nobody's algorithm."""

import pytest

from conftest import genesis_store

H = "http://example.org/orexis/hanoi#"
W = "http://example.org/orexis/world/hanoi#"
WANT = W + "every_disk_home"
STATE_GRAPH = "http://example.org/orexis/graph/sensed"


def _pose(st, disks):
    """Seed the puzzle: the given stack on peg A, smallest on top."""
    triples, below = [], H + "PegA"
    for d in reversed(disks):                       # largest first onto the peg
        triples.append(f"<{W}{d}> <{H}on> <{below}>")
        below = W + d
    st.update("INSERT DATA { GRAPH <%s> { %s } }" % (STATE_GRAPH, " . ".join(triples) + " . "))


def _mover(monkeypatch, disks):
    """A plain Agent, not conftest's wired builder: the mover holds no bus, so there is no
    transport module for the builder's wire conveniences to find — and none is needed, since
    these tests speak only to `pursuing` and the Planner. Wire-less on purpose: the world's
    whole point is the search."""
    from agent import genesis, runtime

    monkeypatch.setenv("INFLUX_BUCKET", "test-hanoi")
    monkeypatch.setenv("INFLUX_TOKEN", "test-token-hanoi")
    st = genesis_store(world="hanoi")
    _pose(st, disks)
    genesis.classify_own_graphs(st, "hanoi")
    return runtime.Agent("hanoi", st=st)


def _goal(agent):
    return next(g for g in agent.pursuing() if g.uri == WANT)


def _solved(plan, agent, depth):
    from orexis_agent_deliberation.planner import Planner

    p = Planner(agent, agent.me)
    p.MAX_DEPTH = depth
    return p.plan(_goal(agent))


def test_the_goal_is_pursued_and_binary_with_no_module_in_the_room(monkeypatch):
    """The want is pure ratified data — no capability, no measure package — and the kernel
    lifts and judges it: unmet at 1.0 while the stack sits on A, met at 0.0 once nothing is
    astray. Stage one of the two-stage cut, on a want that is not a number."""
    agent = _mover(monkeypatch, ["disk_1"])
    assert _goal(agent).urgency == 1.0 and _goal(agent).state == "unmet"

    agent.beliefs.update(
        f"DELETE {{ GRAPH <{STATE_GRAPH}> {{ <{W}disk_1> <{H}on> <{H}PegA> }} }} "
        f"INSERT {{ GRAPH <{STATE_GRAPH}> {{ <{W}disk_1> <{H}on> <{H}PegC> }} }} WHERE {{}}")
    assert _goal(agent).urgency == 0.0 and _goal(agent).state == "met"


def test_two_disks_solve_in_exactly_three_moves(monkeypatch):
    """The classical 2-disk optimum, found by the ordinary search: depth allows four, the
    cheapest achiever costs three, so three it is — optimality from orexis:costs, not from
    any Hanoi code."""
    agent = _mover(monkeypatch, ["disk_1", "disk_2"])
    plan = _solved(None, agent, depth=4)
    assert plan.outcome == "satisfied", plan.outcome
    assert len(plan.steps) == 3, [s.act.action.rsplit("#", 1)[-1] for s in plan.steps]


def test_three_disks_solve_in_exactly_seven_moves(monkeypatch):
    """The money assertion: 2^n − 1. Depth allows EIGHT, so an eight-move solution is
    reachable — and the seven-move one must win, because achievers are ranked by cost alone
    and every move costs one. The optimal Tower of Hanoi solution is the cheapest achiever,
    by no algorithm anybody wrote."""
    agent = _mover(monkeypatch, ["disk_1", "disk_2", "disk_3"])
    plan = _solved(None, agent, depth=8)
    assert plan.outcome == "satisfied", plan.outcome
    assert len(plan.steps) == 7, [s.act.action.rsplit("#", 1)[-1] for s in plan.steps]
