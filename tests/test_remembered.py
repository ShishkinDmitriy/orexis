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
