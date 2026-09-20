"""A remembered plan is a method on the want, lifted from a plan that worked (#469), keyed by
its regressed precondition (#551). The courier's delivery: searched once, walked to its end,
remembered for its want; the same pose again adopts it with no search and the trace says so,
and so does the same pose with a stray fact beside it, since the plan never read that fact; a
pose where a fact the plan read is absent refuses it, and the trace names the fact; a
remembered plan that fails a step is forgotten."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from orexis_agent_deliberation import planner, pursuit, remembered
from orexis_agent_deliberation.ontology import remembered_graph
from orexis_agent_deliberation.plan import REMEMBERED
from orexis_agent_progression.store import bindings
from test_courier import C, STATE_GRAPH, W, WANT, _driver, _goal
from orexis_agent_progression.ontology import PUBLIC


def _answer(agent, predicts):
    adds, retracts = predicts
    for f in retracts:
        agent.beliefs.update(f"DELETE DATA {{ GRAPH <{STATE_GRAPH}> {{ <{f[0]}> <{f[1]}> <{f[2]}> . }} }}")
    for f in adds:
        agent.beliefs.update(f"INSERT DATA {{ GRAPH <{STATE_GRAPH}> {{ <{f[0]}> <{f[1]}> <{f[2]}> . }} }}")


def _walk(agent, uri):
    keeper = agent.keeper
    for _ in range(40):
        standing = [s for s in keeper.standing() if s.uri == uri]
        if not standing:
            return
        step = standing[0].step
        assert keeper.expect(uri, "show me", not_after=datetime.now(timezone.utc) + timedelta(hours=1))
        _answer(agent, step.predicts)
    raise AssertionError("a plan that never ends")


def _repose(agent, van, parcel):
    agent.beliefs.update(f"DELETE WHERE {{ GRAPH <{STATE_GRAPH}> {{ <{W}van> <{C}at> ?c }} }}")
    agent.beliefs.update(f"DELETE WHERE {{ GRAPH <{STATE_GRAPH}> {{ <{W}parcel> ?p ?o }} }}")
    agent.beliefs.update(f"""INSERT DATA {{ GRAPH <{STATE_GRAPH}> {{
        <{W}van> <{C}at> <{W}{van}> . <{W}parcel> <{C}at> <{W}{parcel}> . }} }}""")


def test_a_plan_that_worked_is_remembered_and_adopted_again_without_a_search(monkeypatch):
    agent = _driver(monkeypatch, "c0_0", "c1_2")
    searches = []
    real = planner.Planner.plan
    monkeypatch.setattr(planner.Planner, "plan", lambda self, d, **kw: (searches.append(d.uri), real(self, d, **kw))[1])
    first = pursuit.pursue(agent, _goal(agent))
    assert first is not None and len(searches) == 1
    walked = agent.keeper.walked(first)
    _walk(agent, first)
    assert agent.keeper.standing() == [], "walked to its end"
    kept = bindings(agent.beliefs.query(f"SELECT ?r WHERE {{ GRAPH <{remembered_graph(agent.id)}> {{ ?r a deliberation:RememberedPlan ; deliberation:forWant <{WANT}> }} }}", agent.beliefs.graphs_of(PUBLIC)))
    assert len(kept) == 1, "lifted into the agent's own graph, for the want"
    assert _goal(agent).state == "met"
    # the same world again
    _repose(agent, "c0_0", "c1_2")
    again = pursuit.pursue(agent, _goal(agent))
    assert again is not None and len(searches) == 1, "the same world: the plan is remembered, nothing is searched"
    assert [s.action for s in agent.keeper.walked(again)] == [s.action for s in walked]
    from orexis_agent_progression.ontology import DELIBERATION_GRAPH
    verdicts = bindings(agent.beliefs.query(f"""
SELECT ?v WHERE {{ GRAPH <{DELIBERATION_GRAPH}> {{ ?d a deliberation:Deliberation ; deliberation:verdict ?v }} }}""", agent.beliefs.graphs_of(PUBLIC)))
    assert REMEMBERED in {r["v"] for r in verdicts}, "and the trace says it was remembered"
    _walk(agent, again)
    assert len(bindings(agent.beliefs.query(f"SELECT ?r WHERE {{ GRAPH <{remembered_graph(agent.id)}> {{ ?r a deliberation:RememberedPlan }} }}", agent.beliefs.graphs_of(PUBLIC)))) == 1, \
        "a remembered plan finishing again is not remembered twice"
    # another world
    _repose(agent, "c3_3", "c1_2")
    third = pursuit.pursue(agent, _goal(agent))
    assert third is not None and len(searches) == 2, "a different world searches"


def test_a_remembered_plan_that_fails_a_step_is_forgotten(monkeypatch):
    agent = _driver(monkeypatch, "c0_0", "c1_2")
    first = pursuit.pursue(agent, _goal(agent))
    _walk(agent, first)
    _repose(agent, "c0_0", "c1_2")
    again = pursuit.pursue(agent, _goal(agent))
    assert bindings(agent.beliefs.query(f"SELECT ?r WHERE {{ GRAPH <{remembered_graph(agent.id)}> {{ ?r a deliberation:RememberedPlan }} }}", agent.beliefs.graphs_of(PUBLIC)))
    agent.keeper.expect(again, "show me", not_after=datetime.now(timezone.utc) + timedelta(hours=1))
    agent.keeper.lapse(again)                                   # the world did not answer
    assert not bindings(agent.beliefs.query(f"SELECT ?r WHERE {{ GRAPH <{remembered_graph(agent.id)}> {{ ?r a deliberation:RememberedPlan }} }}", agent.beliefs.graphs_of(PUBLIC))), \
        "forgotten: a plan that failed a step is not remembered"


# --- keyed by the regressed precondition (#551) ----------------------------------------------


def _remembered_uri(agent):
    rows = bindings(agent.beliefs.query(f"SELECT ?r WHERE {{ GRAPH <{remembered_graph(agent.id)}> {{ ?r a deliberation:RememberedPlan ; deliberation:forWant <{WANT}> }} }}", agent.beliefs.graphs_of(PUBLIC)))
    assert len(rows) == 1
    return rows[0]["r"]


def _candidates(agent):
    from orexis_agent_progression.ontology import DELIBERATION_GRAPH
    return bindings(agent.beliefs.query(f"""
SELECT ?take ?verdict ?chosen ?missing WHERE {{ GRAPH <{DELIBERATION_GRAPH}> {{
  ?d a deliberation:Deliberation ; deliberation:considered ?c .
  ?c deliberation:wouldTake ?take ; deliberation:verdict ?verdict .
  OPTIONAL {{ ?c deliberation:missing ?missing }}
  OPTIONAL {{ ?d deliberation:chose ?chosen }} }} }}""", agent.beliefs.graphs_of(PUBLIC)))


def test_a_stray_fact_no_longer_forces_a_search(monkeypatch):
    """The world differs in a fact no rule of the plan read. The whole-world hash keyed the
    plan to that fact and searched again; the regressed precondition does not read it, so
    the plan is adopted with no search — the measure #551 asked for."""
    agent = _driver(monkeypatch, "c0_0", "c1_2")
    first = pursuit.pursue(agent, _goal(agent))
    walked = agent.keeper.walked(first)
    _walk(agent, first)
    _repose(agent, "c0_0", "c1_2")
    agent.beliefs.update(f"INSERT DATA {{ GRAPH <{STATE_GRAPH}> {{ <urn:stray> <urn:p> <urn:o> . }} }}")
    searches = []
    real = planner.Planner.plan
    monkeypatch.setattr(planner.Planner, "plan", lambda self, d, **kw: (searches.append(d.uri), real(self, d, **kw))[1])
    again = pursuit.pursue(agent, _goal(agent))
    assert again is not None and searches == [], "a stray fact is not a fact the plan read"
    assert [s.action for s in agent.keeper.walked(again)] == [s.action for s in walked]


def test_a_missing_premise_refuses_the_plan_and_the_trace_names_the_fact(monkeypatch):
    """The van stands somewhere the remembered plan did not start from. The plan's first
    drive read `van at c0_0`; that fact is absent, so the plan does not apply, the pass
    searches, and its trace says which fact was missing rather than only that one was."""
    from orexis_agent_deliberation import trace
    agent = _driver(monkeypatch, "c0_0", "c1_2")
    first = pursuit.pursue(agent, _goal(agent))
    _walk(agent, first)
    uri = _remembered_uri(agent)
    _repose(agent, "c3_3", "c1_2")
    searches = []
    real = planner.Planner.plan
    monkeypatch.setattr(planner.Planner, "plan", lambda self, d, **kw: (searches.append(d.uri), real(self, d, **kw))[1])
    again = pursuit.pursue(agent, _goal(agent))
    assert again is not None and len(searches) == 1, "a fact the plan read is absent: the pass searches"
    rows = {r["take"]: r for r in _candidates(agent)}
    assert rows[uri]["verdict"] == trace.INAPPLICABLE
    assert f"{W}van" in rows[uri]["missing"] and f"{C}at" in rows[uri]["missing"] and "c0_0" in rows[uri]["missing"], \
        rows[uri]["missing"]
    assert agent.keeper.walked(again), "and the search still found a delivery"
    assert _remembered_uri(agent) == uri, "inapplicable here is not forgotten — it applies elsewhere"


def test_where_it_applies_a_remembered_plan_is_still_walked_as_one_candidate_by_a_bare_search(monkeypatch):
    """The walk path (#469, second form) survives for a search entered without the
    adoption in front of it: the remembered route is weighed as ONE candidate, walked in
    the imaginarium, found to achieve the want and chosen — the trace names it as what
    would be taken and as what was chosen."""
    from orexis_agent_deliberation import trace
    agent = _driver(monkeypatch, "c0_0", "c1_2")
    first = pursuit.pursue(agent, _goal(agent))
    _walk(agent, first)
    uri = _remembered_uri(agent)
    _repose(agent, "c0_0", "c1_2")
    plan = planner.Planner(agent, agent.me).plan(_goal(agent))
    rows = {r["take"]: r for r in _candidates(agent)}
    assert uri in rows and rows[uri]["verdict"] == trace.MET
    chosen = next(r["chosen"] for r in rows.values() if r.get("chosen"))
    took = bindings(agent.beliefs.query_union(f"SELECT ?t WHERE {{ <{chosen}> deliberation:wouldTake ?t }}"))
    assert took and took[0]["t"] == uri, "an achiever tying on cost falls to the route already walked"
    kept = remembered.remembered_for(agent, WANT)[0][1]
    assert [s.action for s in plan.steps] == [s.action for s in kept], "the plan adopted is the route's steps"


def test_a_plan_lifted_without_premises_is_forgotten_since_nothing_says_when_it_applies(monkeypatch):
    from dataclasses import replace
    agent = _driver(monkeypatch, "c0_0", "c1_2")
    first = pursuit.pursue(agent, _goal(agent))
    walked = agent.keeper.walked(first)
    _walk(agent, first)
    remembered.forget(agent, _remembered_uri(agent), "make room for one lifted the old way")
    remembered.lift(agent, WANT, [replace(s, precondition=None) for s in walked], None)
    assert len(remembered.remembered_for(agent, WANT)) == 1
    _repose(agent, "c0_0", "c1_2")
    searches = []
    real = planner.Planner.plan
    monkeypatch.setattr(planner.Planner, "plan", lambda self, d, **kw: (searches.append(d.uri), real(self, d, **kw))[1])
    again = pursuit.pursue(agent, _goal(agent))
    assert again is not None and len(searches) == 1, "nothing says when it applies, so it is not adopted"
    assert remembered.remembered_for(agent, WANT) == [], "and it is forgotten on the spot"
    _walk(agent, again)
    kept = remembered.remembered_for(agent, WANT)
    assert len(kept) == 1 and all(s.precondition is not None for s in kept[0][1]), \
        "the search's plan, lifted with premises, takes its place"


def test_a_remembered_route_adopted_on_its_precondition_that_fails_is_forgotten(monkeypatch):
    agent = _driver(monkeypatch, "c0_0", "c1_2")
    first = pursuit.pursue(agent, _goal(agent))
    _walk(agent, first)
    _repose(agent, "c0_0", "c1_2")
    agent.beliefs.update(f"INSERT DATA {{ GRAPH <{STATE_GRAPH}> {{ <urn:stray> <urn:p> <urn:o> . }} }}")
    again = pursuit.pursue(agent, _goal(agent))
    agent.keeper.expect(again, "show me", not_after=datetime.now(timezone.utc) + timedelta(hours=1))
    agent.keeper.lapse(again)
    assert not bindings(agent.beliefs.query(f"SELECT ?r WHERE {{ GRAPH <{remembered_graph(agent.id)}> {{ ?r a deliberation:RememberedPlan }} }}", agent.beliefs.graphs_of(PUBLIC))), \
        "forgotten, whichever way adopted it"


def test_the_regression_subtracts_what_the_chain_produces():
    """Step two's premises include the reading step one predicts; that fact is the chain's
    own, not the world's, so it is not asked of the present. A keyed fact is asked by class
    and key, never by value."""
    from orexis_agent_progression.act import Step
    cls, key = "urn:Obs", (("urn:k", "urn:v"),)
    first = Step(action="urn:a", binding=(("urn:param", "urn:x"),), precondition=frozenset({("urn:s", "urn:p", "urn:o"), ("keyed", cls, key, "urn:c", 0.1)}),
                 predicts=(frozenset({("keyed", cls, key, "urn:c", 0.5)}), frozenset()))
    second = Step(action="urn:b", binding=(("urn:param", "urn:x"),), precondition=frozenset({("keyed", cls, key, "urn:c", 0.5), ("urn:t", "urn:q", "urn:u")}),
                  predicts=(frozenset(), frozenset()))
    facts = remembered.regressed([first, second])
    assert facts == frozenset({("urn:s", "urn:p", "urn:o"), ("keyed", cls, key, "urn:c", 0.1), ("urn:t", "urn:q", "urn:u")})
    assert remembered.regressed([first, Step(action="urn:b", binding=(("urn:param", "urn:x"),))]) is None
    select = remembered._pattern_select(facts)
    assert "<urn:s> <urn:p> <urn:o>" in select and "a <urn:Obs>" in select and "0.1" not in select, select
    #  A reading by what it IS (#576): the band fact renders as one triple on the node.
    banded = remembered._pattern_select(frozenset({("keyed", cls, key, "http://www.w3.org/1999/02/22-rdf-syntax-ns#type", "urn:band:below")}))
    assert "a <urn:Obs>" in banded and "a <urn:band:below>" in banded, banded
