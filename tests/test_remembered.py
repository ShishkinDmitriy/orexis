"""A remembered plan is a method on the want, lifted from a plan that worked (#469). The
courier's delivery: searched once, walked to its end, remembered for its want in the world it
was decided in; the same pose again adopts it with no search and the trace says so; another
pose searches; a remembered plan that fails a step is forgotten."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from orexis_agent_deliberation import planner, pursuit, remembered
from orexis_agent_deliberation.ontology import remembered_graph
from orexis_agent_progression.store import bindings
from test_courier import C, STATE_GRAPH, W, WANT, _driver, _goal


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
    monkeypatch.setattr(planner.Planner, "plan", lambda self, d: (searches.append(d.uri), real(self, d))[1])
    first = pursuit.pursue(agent, _goal(agent))
    assert first is not None and len(searches) == 1
    walked = agent.keeper.walked(first)
    _walk(agent, first)
    assert agent.keeper.standing() == [], "walked to its end"
    kept = bindings(agent.beliefs.query(f"SELECT ?r WHERE {{ GRAPH <{remembered_graph(agent.id)}> {{ ?r a deliberation:RememberedPlan ; deliberation:forWant <{WANT}> }} }}"))
    assert len(kept) == 1, "lifted into the agent's own graph, for the want"
    assert _goal(agent).state == "met"
    # the same world again
    _repose(agent, "c0_0", "c1_2")
    again = pursuit.pursue(agent, _goal(agent))
    assert again is not None and len(searches) == 1, "the same world: the plan is remembered, nothing is searched"
    assert [s.action for s in agent.keeper.walked(again)] == [s.action for s in walked]
    from orexis_agent_progression.ontology import DELIBERATION_GRAPH
    verdicts = bindings(agent.beliefs.query(f"""
SELECT ?v WHERE {{ GRAPH <{DELIBERATION_GRAPH}> {{ ?d a deliberation:Deliberation ; deliberation:verdict ?v }} }}"""))
    assert planner.REMEMBERED in {r["v"] for r in verdicts}, "and the trace says it was remembered"
    _walk(agent, again)
    assert len(bindings(agent.beliefs.query(f"SELECT ?r WHERE {{ GRAPH <{remembered_graph(agent.id)}> {{ ?r a deliberation:RememberedPlan }} }}"))) == 1, \
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
    assert bindings(agent.beliefs.query(f"SELECT ?r WHERE {{ GRAPH <{remembered_graph(agent.id)}> {{ ?r a deliberation:RememberedPlan }} }}"))
    agent.keeper.expect(again, "show me", not_after=datetime.now(timezone.utc) + timedelta(hours=1))
    agent.keeper.lapse(again)                                   # the world did not answer
    assert not bindings(agent.beliefs.query(f"SELECT ?r WHERE {{ GRAPH <{remembered_graph(agent.id)}> {{ ?r a deliberation:RememberedPlan }} }}")), \
        "forgotten: a plan that failed a step is not remembered"


# --- the second form (#469): weighed as one candidate where the world differs ----------------

def _remembered_uri(agent):
    rows = bindings(agent.beliefs.query(f"SELECT ?r WHERE {{ GRAPH <{remembered_graph(agent.id)}> {{ ?r a deliberation:RememberedPlan ; deliberation:forWant <{WANT}> }} }}"))
    assert len(rows) == 1
    return rows[0]["r"]


def _candidates(agent):
    from orexis_agent_progression.ontology import DELIBERATION_GRAPH
    return bindings(agent.beliefs.query(f"""
SELECT ?take ?verdict ?chosen WHERE {{ GRAPH <{DELIBERATION_GRAPH}> {{
  ?d a deliberation:Deliberation ; deliberation:considered ?c .
  ?c deliberation:wouldTake ?take ; deliberation:verdict ?verdict .
  OPTIONAL {{ ?d deliberation:chose ?chosen }} }} }}"""))


def test_in_another_world_a_remembered_plan_is_walked_as_one_candidate_and_wins_its_ties(monkeypatch):
    """The world differs in a fact no rule reads, so the exact hit misses and the pass
    searches — and the remembered route is on the menu as ONE candidate, walked step by step
    in the imaginarium, found to achieve the want, and chosen: the trace names it as what
    would be taken and as what was chosen, and the plan adopted is its steps."""
    from orexis_agent_deliberation import trace
    agent = _driver(monkeypatch, "c0_0", "c1_2")
    first = pursuit.pursue(agent, _goal(agent))
    walked = agent.keeper.walked(first)
    _walk(agent, first)
    uri = _remembered_uri(agent)
    _repose(agent, "c0_0", "c1_2")
    agent.beliefs.update(f"INSERT DATA {{ GRAPH <{STATE_GRAPH}> {{ <urn:stray> <urn:p> <urn:o> . }} }}")
    searches = []
    real = planner.Planner.plan
    monkeypatch.setattr(planner.Planner, "plan", lambda self, d: (searches.append(d.uri), real(self, d))[1])
    again = pursuit.pursue(agent, _goal(agent))
    assert again is not None and len(searches) == 1, "another signature: the pass searches"
    rows = {r["take"]: r for r in _candidates(agent)}
    assert uri in rows, "the remembered plan was weighed as a candidate of its own"
    assert rows[uri]["verdict"] == trace.MET
    chosen = next(r["chosen"] for r in rows.values() if r.get("chosen"))
    took = bindings(agent.beliefs.query_union(f"SELECT ?t WHERE {{ <{chosen}> deliberation:wouldTake ?t }}"))
    assert took and took[0]["t"] == uri, "an achiever tying on cost falls to the route already walked"
    assert [s.action for s in agent.keeper.walked(again)] == [s.action for s in walked]
    _walk(agent, again)
    assert len(bindings(agent.beliefs.query(f"SELECT ?r WHERE {{ GRAPH <{remembered_graph(agent.id)}> {{ ?r a deliberation:RememberedPlan }} }}"))) == 1, \
        "the same route finishing by the search's road is not remembered twice"


def test_a_remembered_plan_whose_step_is_not_on_the_menu_is_passed_over_and_says_so(monkeypatch):
    """The van stands somewhere the remembered first move cannot be made from. The walk finds
    that step off the menu, the trace says which verdict, and the search finds its own way."""
    from orexis_agent_deliberation import trace
    agent = _driver(monkeypatch, "c0_0", "c1_2")
    first = pursuit.pursue(agent, _goal(agent))
    _walk(agent, first)
    uri = _remembered_uri(agent)
    _repose(agent, "c3_3", "c1_2")
    again = pursuit.pursue(agent, _goal(agent))
    assert again is not None
    rows = {r["take"]: r for r in _candidates(agent)}
    assert rows[uri]["verdict"] == trace.UNAVAILABLE
    assert agent.keeper.walked(again), "and the search still found a delivery"


def test_a_remembered_route_chosen_by_the_search_that_fails_is_forgotten(monkeypatch):
    agent = _driver(monkeypatch, "c0_0", "c1_2")
    first = pursuit.pursue(agent, _goal(agent))
    _walk(agent, first)
    _repose(agent, "c0_0", "c1_2")
    agent.beliefs.update(f"INSERT DATA {{ GRAPH <{STATE_GRAPH}> {{ <urn:stray> <urn:p> <urn:o> . }} }}")
    again = pursuit.pursue(agent, _goal(agent))
    agent.keeper.expect(again, "show me", not_after=datetime.now(timezone.utc) + timedelta(hours=1))
    agent.keeper.lapse(again)
    assert not bindings(agent.beliefs.query(f"SELECT ?r WHERE {{ GRAPH <{remembered_graph(agent.id)}> {{ ?r a deliberation:RememberedPlan }} }}")), \
        "forgotten by its steps, whichever road adopted it"
