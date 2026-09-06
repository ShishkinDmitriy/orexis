"""The cone outlives the pass (#553): a search's worlds are kept as diffs, and the next pass
looks for the present among them. Where the present is a kept world, the pass re-roots there
and resumes the frontier, spending nothing on what was already imagined; where it is not, or
where the invariant half moved, the cone is dead and the pass starts from nothing. Graphs are
dropped when a pass ends and re-made from the nearest kept graph when a rule next runs against
a node; a retract of a keyed fact matches by key, so a re-made world holds one reading per node.
"""
from __future__ import annotations

import pyoxigraph as ox
import pytest

from conftest import build_agent, genesis_store
from orexis_agent_deliberation import planner as search, pursuit
from orexis_agent_deliberation.imaginarium import Imaginarium
from orexis_agent_deliberation.planner import Planner
from orexis_agent_progression.ontology import DELIBERATION_GRAPH, STATE_GRAPH
from orexis_agent_progression.store import bindings
from test_courier import C, W, WANT, _driver, _goal


def _take(agent, step):
    """The world does what the step predicted, exactly — the puzzle worlds' surprise-free road."""
    adds, retracts = step.predicts
    for s, p, o in retracts:
        agent.beliefs.update(f"DELETE DATA {{ GRAPH <{STATE_GRAPH}> {{ <{s}> <{p}> <{o}> . }} }}")
    for s, p, o in adds:
        agent.beliefs.update(f"INSERT DATA {{ GRAPH <{STATE_GRAPH}> {{ <{s}> <{p}> <{o}> . }} }}")


def _kept_worlds(agent) -> int:
    rows = bindings(agent.beliefs.query_union(f"""
SELECT ?k WHERE {{ GRAPH <{DELIBERATION_GRAPH}> {{ ?d a deliberation:Deliberation ; deliberation:keptWorlds ?k }} }}"""))
    assert len(rows) == 1
    return int(rows[0]["k"])


def test_a_pass_after_a_step_taken_as_predicted_resumes_the_cone_and_finds_the_tail(monkeypatch):
    """The van drives the first leg exactly as planned. The next pass finds the present among
    the kept worlds, re-roots there, builds nothing from scratch, and its plan is the tail of
    the first — the same steps, one fewer."""
    agent = _driver(monkeypatch, "c0_0", "c1_2")
    planner = Planner(agent, agent.me)
    first = planner.plan(_goal(agent))
    assert len(first.steps) == 8 and _kept_worlds(agent) == 0
    begins = []
    real = search.Planner._begin
    monkeypatch.setattr(search.Planner, "_begin", lambda self, d: (begins.append(1), real(self, d))[1])
    _take(agent, first.steps[0])
    again = planner.plan(_goal(agent))
    assert begins == [], "nothing was built from scratch: the present was a kept world"
    assert _kept_worlds(agent) > 0, "and the trace says how many worlds the pass began with"
    assert [s.action for s in again.steps] == [s.action for s in first.steps[1:]]
    assert [(s.via, s.about) for s in again.steps] == [(s.via, s.about) for s in first.steps[1:]]
    assert planner._root.taken == () and planner._root.diff == search.signature.EMPTY, \
        "the new root stands nowhere but the present"


def test_a_present_that_matches_no_kept_world_starts_from_nothing(monkeypatch):
    """The parcel is moved while the van drives: no imagined world holds that, so the cone is
    dead and the pass is built afresh — the road every pass took before #553."""
    agent = _driver(monkeypatch, "c0_0", "c1_2")
    planner = Planner(agent, agent.me)
    first = planner.plan(_goal(agent))
    _take(agent, first.steps[0])
    agent.beliefs.update(f"DELETE DATA {{ GRAPH <{STATE_GRAPH}> {{ <{W}parcel> <{C}at> <{W}c1_2> . }} }}")
    agent.beliefs.update(f"INSERT DATA {{ GRAPH <{STATE_GRAPH}> {{ <{W}parcel> <{C}at> <{W}c2_2> . }} }}")
    begins = []
    real = search.Planner._begin
    monkeypatch.setattr(search.Planner, "_begin", lambda self, d: (begins.append(1), real(self, d))[1])
    again = planner.plan(_goal(agent))
    assert begins == [1] and _kept_worlds(agent) == 0
    assert again.steps, "and a delivery is still found from the new world"


def test_a_moved_invariant_half_forgets_the_cone(monkeypatch):
    """A fact no reading carries — public knowledge — changes between passes. Every kept diff
    was computed against a world that is gone, so the cone is forgotten whole."""
    agent = _driver(monkeypatch, "c0_0", "c1_2")
    planner = Planner(agent, agent.me)
    planner.plan(_goal(agent))
    graph = agent.beliefs.public_graphs()[0]
    agent.beliefs.update(f"INSERT DATA {{ GRAPH <{graph}> {{ <urn:test:new> <urn:test:fact> <urn:test:o> . }} }}")
    begins = []
    real = search.Planner._begin
    monkeypatch.setattr(search.Planner, "_begin", lambda self, d: (begins.append(1), real(self, d))[1])
    planner.plan(_goal(agent))
    assert begins == [1] and _kept_worlds(agent) == 0


def test_graphs_are_dropped_when_the_pass_ends_and_remade_when_asked(monkeypatch):
    agent = _driver(monkeypatch, "c0_0", "c1_2")
    planner = Planner(agent, agent.me)
    planner.plan(_goal(agent))
    im = planner.imaginarium
    assert im is not None and len(planner._nodes) > 1
    others = [n for n in planner._nodes if n is not planner._root]
    assert all(not n.materialised and not im.holds(n.graph) for n in others), \
        "every imagined graph but the root's is gone when the pass ends"
    deepest = max(others, key=lambda n: len(n.taken))
    name = planner._graph(deepest)
    assert im.holds(name) and deepest.materialised
    chain, m = [], deepest
    while m is not None:
        chain.append(m)
        m = m.parent
    assert all(n.materialised for n in chain), "re-made from the root down, each from its parent"
    assert planner._root.graph == STATE_GRAPH and im.holds(STATE_GRAPH)


def test_a_retract_of_a_keyed_fact_matches_by_key():
    """A kept step's delete list names the reading its rule read; re-made on a present whose
    reading differs, an exact retract would miss and leave two readings on one node. The
    imaginarium retracts what the node CARRIES under that predicate, whatever its value."""
    from conftest import genesis_store as gs
    st = gs({"fern": 0.30})
    im = Imaginarium(st, STATE_GRAPH)
    obs = next(q.subject for q in st.quads(STATE_GRAPH)
               if q.predicate.value == "http://www.w3.org/ns/sosa/hasSimpleResult")
    pred = ox.NamedNode("http://www.w3.org/ns/sosa/hasSimpleResult")
    dec = ox.NamedNode("http://www.w3.org/2001/XMLSchema#decimal")
    row = type("R", (), {"action": "urn:x:dose", "via": "urn:x:pump", "about": None})()
    stale = [ox.Triple(obs, pred, ox.Literal("0.29", datatype=dec))]     # not what the node holds
    fresh = [ox.Triple(obs, pred, ox.Literal("0.55", datatype=dec))]
    child = im.reached(STATE_GRAPH, (row,), fresh, stale)
    values = [q.object.value for q in im.quads(child) if q.subject == obs and q.predicate == pred]
    assert values == ["0.55"], values


def test_the_deliberator_keeps_one_planner_per_want(monkeypatch):
    agent = _driver(monkeypatch, "c0_0", "c1_2")
    uri = pursuit.pursue(agent, _goal(agent))
    assert uri is not None
    planners = agent.deliberator._planners
    assert WANT in planners and planners[WANT].imaginarium is not None, "the cone is held on the want"
