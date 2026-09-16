"""Tower of Hanoi through the ordinary search (#257): the domain-is-a-plug-in claim, tested
on a classical planning task. The domain is an ontology and ONE move action with no
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


def _solved(agent, budget=None):
    """Plan with the budget the WORLD states (`world/hanoi/beliefs`), or with one pinned on this
    instance — the way tests used to raise a depth, and the only place a budget is set by hand."""
    from orexis_agent_deliberation.planner import Planner

    p = Planner(agent, agent.me)
    if budget is not None:
        p.budget = budget
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
    """The classical 2-disk optimum, found by the ordinary search: the budget allows a
    four-move solution to be found too, the cheapest achiever costs three, so three it is —
    optimality from orexis:costs, not from any Hanoi code. At the ENGINE'S default budget,
    pinned here so the default is known to solve the small puzzle: the world's 64 is for three."""
    agent = _mover(monkeypatch, ["disk_1", "disk_2"])
    from orexis_agent_deliberation.planner import Planner
    plan = _solved(agent, budget=Planner.BUDGET)
    assert plan.outcome == "satisfied", plan.outcome
    assert len(plan.steps) == 3, [s.action.rsplit("#", 1)[-1] for s in plan.steps]


def test_three_disks_solve_in_exactly_seven_moves(monkeypatch):
    """The money assertion: 2^n − 1. The world's budget of 64 worlds allows eight-move
    solutions to be reached — and the seven-move one must win, because achievers are ranked by
    cost alone and every move costs one. The optimal Tower of Hanoi solution is the cheapest
    achiever, by no algorithm anybody wrote."""
    agent = _mover(monkeypatch, ["disk_1", "disk_2", "disk_3"])
    plan = _solved(agent)
    assert plan.outcome == "satisfied", plan.outcome
    moves = [(s.via.rsplit("_", 1)[-1], s.about.rsplit("#", 1)[-1])
             for s in plan.steps]
    assert len(plan.steps) == 7, moves
    #  ONE schema, ground per ROW: every step is the same action, and the (disk, peg) pair
    #  rides on via/about — which is what the kernel's $via channel exists for.
    assert {s.action for s in plan.steps} == {H + "Move"}
    assert moves[0] == ("1", "PegC"), moves


def test_the_want_counts_the_disks_astray_and_the_count_prunes(monkeypatch):
    """Hanoi's estimate — disks not yet home — was admissible and measured before #492 and
    NOT shipped, because breadth-first it guided nothing. Best-first it does a little: 56
    forks to 50 on three disks, still exactly seven moves. A little is the honest reading,
    since the optimal path moves disks AWAY from C to free the ones beneath and a count cannot
    see that; the pin is on the seven, and the fork count is held below where it stood."""
    from orexis_agent_deliberation import imaginarium
    from orexis_agent_deliberation.planner import Planner

    agent = _mover(monkeypatch, ["disk_1", "disk_2", "disk_3"])
    p = Planner(agent, agent.me)
    assert p._estimate_in(p._begin(_goal(agent)), _goal(agent)) == 3.0, \
        "three disks on A: every one at least a move from home"

    forks = []
    reached = imaginarium.Imaginarium.reached
    monkeypatch.setattr(imaginarium.Imaginarium, "reached",
                        lambda self, *a, **k: (forks.append(1), reached(self, *a, **k))[1])
    plan = _solved(agent)
    assert len(plan.steps) == 7, plan.outcome
    assert len(forks) < 56, f"{len(forks)} forks: measured 50 with the estimate, 56 without"


KNOB = '''@prefix orexis: <http://example.org/orexis#> .
@prefix knob: <urn:knob#> .
@prefix sh: <http://www.w3.org/ns/shacl#> .

#  A FREE FOREIGN ACTION that genuinely changes state: a knob flipping between two positions,
#  no cost, nothing a solved puzzle reads. The runbook measured it at 2.8x the forks of a
#  three-disk solve before anything could see it.
knob:Flip a orexis:Action ;
    orexis:available """SELECT ?via ?about WHERE {
        ?via <urn:knob#at> ?here .
        ?about a <urn:knob#Position> . FILTER(?about != ?here) }""" ;
    orexis:retracts """CONSTRUCT { $via <urn:knob#at> ?old } WHERE { $via <urn:knob#at> ?old }""" ;
    sh:construct """CONSTRUCT { $via <urn:knob#at> $about } WHERE { }""" .
knob:left a knob:Position . knob:right a knob:Position .
'''


def _with_knob(monkeypatch, tmp_path, agent_factory):
    from assembly import loader

    knob = tmp_path / "knob.ttl"
    knob.write_text(KNOB)
    real = loader.action_files()
    monkeypatch.setattr(loader, "action_files", lambda: real + (knob,))
    agent = agent_factory()
    agent.beliefs.update(f"""INSERT DATA {{ GRAPH <{STATE_GRAPH}> {{
        <urn:knob#dial> <urn:knob#at> <urn:knob#left> }} }}""")
    agent.desires.rebuild()
    return agent


def test_a_free_foreign_action_no_longer_multiplies_the_solve(monkeypatch, tmp_path):
    """The runbook's knob (#488): one free action from another domain, flipping a dial the
    puzzle never reads. Before relevance it took a three-disk solve from 56 forks to 157 —
    the bound is blind to a free action and cycle detection cannot fold a world that really
    changed. Relevance reads the knob's effect off its own construct, finds it touches
    nothing the solved want reads, records it as such and never simulates it: the same 50
    forks as without the knob, and the same seven moves."""
    from orexis_agent_deliberation import imaginarium, trace
    from orexis_agent_deliberation.planner import Planner
    from orexis_agent_progression.store import bindings

    agent = _with_knob(monkeypatch, tmp_path,
                       lambda: _mover(monkeypatch, ["disk_1", "disk_2", "disk_3"]))
    forks = []
    reached = imaginarium.Imaginarium.reached
    monkeypatch.setattr(imaginarium.Imaginarium, "reached",
                        lambda self, *a, **k: (forks.append(1), reached(self, *a, **k))[1])
    p = Planner(agent, agent.me)
    plan = p.plan(_goal(agent))
    assert len(plan.steps) == 7, plan.outcome
    assert len(forks) == 50, f"{len(forks)} forks: 50 without the knob, 157 with it unseen"
    assert "urn:knob#Flip" not in p._compiled.relevant, "the knob touches nothing the want reads"
    rows = bindings(agent.beliefs.query_union(f"""SELECT (COUNT(?c) AS ?n) WHERE {{
        ?c <http://example.org/orexis/deliberation#wouldTake> <urn:knob#Flip> ;
           <http://example.org/orexis/deliberation#verdict> "{trace.IRRELEVANT}" }}"""))
    assert int(rows[0]["n"]) > 0, "and the trace says so, rather than the row vanishing"


def test_the_budget_is_the_worlds_pick_and_the_kernel_bounds_it(monkeypatch):
    """A pass is budgeted in WORLDS, and the sovereign states it in the agent's beliefs like a
    patience (#494). `world/hanoi` states 64 and the planner reads exactly that; an agent whose
    beliefs say nothing gets the engine's own ceiling; and a statement outside the
    constitutional bounds is refused at the gate, which is the piece a beliefs file can get
    wrong — a budget of zero is an agent that never thinks and looks calm."""
    from agent.validate import validate_agent
    from orexis_agent_deliberation.planner import Planner

    agent = _mover(monkeypatch, ["disk_1"])
    assert Planner(agent, agent.me).budget == 64, "the world's own statement"

    def restate(n):
        agent.beliefs.update(f"""DELETE {{ GRAPH <{agent.beliefs.graph}> {{
            <{agent.me.uri}> deliberation:budgetWorlds ?b }} }}
          INSERT {{ GRAPH <{agent.beliefs.graph}> {{
            <{agent.me.uri}> deliberation:budgetWorlds {n} }} }}
          WHERE  {{ GRAPH <{agent.beliefs.graph}> {{
            <{agent.me.uri}> deliberation:budgetWorlds ?b }} }}""")
        agent.desires.rebuild()

    restate(0)
    with pytest.raises(Exception):
        validate_agent(agent.beliefs, "hanoi", agent.me.uri, agent.me.capabilities,
                       desires=agent.desires)

    agent.beliefs.update(f"""DELETE WHERE {{ GRAPH <{agent.beliefs.graph}> {{
        <{agent.me.uri}> deliberation:budgetWorlds ?b }} }}""")
    agent.desires.rebuild()
    assert Planner(agent, agent.me).budget == Planner.BUDGET, \
        "nothing stated: the engine's ceiling, and validation does not miss it"
    validate_agent(agent.beliefs, "hanoi", agent.me.uri, agent.me.capabilities,
                   desires=agent.desires)


# --- the plan is handed down whole, and the world steps it (#510) -------------

def _answer(agent, predicts):
    """The world answering exactly as a step predicted: its retractions gone from the sensed
    graph, its additions in it — what a device would report, written by hand in a world
    that has no device."""
    def term(x):
        return repr(float(x)) if isinstance(x, (int, float)) else f"<{x}>"
    adds, retracts = predicts
    gone = " . ".join(" ".join(map(term, f)) for f in retracts if len(f) == 3)
    come = " . ".join(" ".join(map(term, f)) for f in adds if len(f) == 3)
    if gone:
        agent.beliefs.update(f"DELETE DATA {{ GRAPH <{STATE_GRAPH}> {{ {gone} . }} }}")
    if come:
        agent.beliefs.update(f"INSERT DATA {{ GRAPH <{STATE_GRAPH}> {{ {come} . }} }}")


def test_three_disks_are_solved_with_one_search_and_seven_answered_steps(monkeypatch):
    """#510: the search runs ONCE and hands the keeper the whole plan; every move after the
    first is taken because the world confirmed the move before it — the step's own
    prediction, plain facts present and gone — and never because a search said so again.
    There is no mover in this world, so the world answers by hand and the watch is opened
    where an actor would open it; what is tested is the keeper's stepping, not the device."""
    from datetime import datetime, timedelta, timezone
    from orexis_agent_deliberation import planner, pursuit

    agent = _mover(monkeypatch, ["disk_1", "disk_2", "disk_3"])
    searches = []
    real = planner.Planner.plan
    monkeypatch.setattr(planner.Planner, "plan", lambda self, d, **kw: (searches.append(1), real(self, d, **kw))[1])
    keeper = agent.keeper
    uri = pursuit.pursue(agent, _goal(agent))
    assert uri is not None and len(searches) == 1
    assert len(keeper.standing(want=WANT)) == 1 and keeper.in_progress(WANT) is not None
    taken = []
    for _ in range(7):
        step = keeper.standing(want=WANT)[0].step
        taken.append(step)
        assert step.predicts is not None, "a step from the ledger carries what it predicted"
        assert keeper.expect(uri, "moved — show me",
                             not_after=datetime.now(timezone.utc) + timedelta(hours=1))
        _answer(agent, step.predicts)                       # the world answers as predicted
    assert len(taken) == 7 and len({s.about for s in taken} | {s.via for s in taken}) >= 1
    assert keeper.standing(want=WANT) == [], "the plan finished with its last step answered"
    assert keeper.in_progress(WANT) is None
    assert len(searches) == 1, "seven moves, one search"
    assert _goal(agent).state == "met", "and the stack stands on the home peg"
    assert keeper.reports()["expectations_met"] == 7
