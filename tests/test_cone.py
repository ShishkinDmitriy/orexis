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
    """The world does what the step predicted, exactly: a plain fact written or removed, a
    keyed fact — a reading — written through the same door a sensor writes it."""
    from conftest import write_reading
    adds, retracts = step.predicts
    for f in retracts:
        if f[0] != "keyed":
            agent.beliefs.update(f"DELETE DATA {{ GRAPH <{STATE_GRAPH}> {{ <{f[0]}> <{f[1]}> <{f[2]}> . }} }}")
    for f in adds:
        if f[0] == "keyed":
            prop = next(v for k, v in f[2] if k.endswith("observedProperty"))
            write_reading(agent, f[4], prop)
        else:
            agent.beliefs.update(f"INSERT DATA {{ GRAPH <{STATE_GRAPH}> {{ <{f[0]}> <{f[1]}> <{f[2]}> . }} }}")


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


# --- identification among the children (#554), within the want's view (#565) ----------------

def test_a_stray_fact_outside_the_view_does_not_kill_the_cone(monkeypatch):
    """The present drifts in a fact the want never reads. Matching within the view, the kept
    world is still the present, and the cone resumes."""
    agent = _driver(monkeypatch, "c0_0", "c1_2")
    planner = Planner(agent, agent.me)
    first = planner.plan(_goal(agent))
    _take(agent, first.steps[0])
    agent.beliefs.update(f"INSERT DATA {{ GRAPH <{STATE_GRAPH}> {{ <urn:stray> <urn:p> <urn:o> . }} }}")
    begins = []
    real = search.Planner._begin
    monkeypatch.setattr(search.Planner, "_begin", lambda self, d: (begins.append(1), real(self, d))[1])
    again = planner.plan(_goal(agent))
    assert begins == [] and _kept_worlds(agent) > 0
    assert [s.action for s in again.steps] == [s.action for s in first.steps[1:]]


def test_a_world_that_landed_in_an_explored_sibling_continues_from_it(monkeypatch):
    """Three disks. The plan's first move goes one way; the world takes the OTHER legal move
    of the same disk — a sibling the search explored. The next pass finds the present in that
    sibling, re-roots there, and continues from the sibling's own subtree: worlds kept, and
    the plan from there as good as a pass from nothing. Not necessarily FEWER forks:
    worlds under the sibling that the first pass reached cheaper through the winning branch
    were credited there, and their nodes go with that branch, so the resumed pass rediscovers
    them — measured, 62 against 50 on this puzzle."""
    from test_hanoi import H, W as HW, _goal as hgoal, _mover
    agent = _mover(monkeypatch, ["disk_1", "disk_2", "disk_3"])
    planner = Planner(agent, agent.me)
    first = planner.plan(hgoal(agent))
    assert len(first.steps) == 7
    planned = first.steps[0]
    other = next(n for n in planner._nodes
                 if len(n.taken) == 1 and n.taken[0].via == planned.via and n.taken[0].about != planned.about)
    assert other.expanded, "the sibling move was explored, not only forked"
    _take(agent, other.taken[0])
    fresh = Planner(agent, agent.me)
    fresh_plan = fresh.plan(hgoal(agent))
    again = planner.plan(hgoal(agent))
    assert _kept_worlds(agent) > 1, "the present was found among the kept worlds, with a subtree beneath it"
    assert again.steps and len(again.steps) == len(fresh_plan.steps), "and the plan from there is as good as a fresh one"
    for step in again.steps:
        _take(agent, step)
    assert hgoal(agent).state == "met", "walked from the sibling, the tower stands"


def test_a_reading_the_want_is_not_about_may_drift_and_the_moisture_cone_survives(monkeypatch):
    """A dry gardener plans a dose. The dose lands exactly as predicted, and the water butt's
    level moves meanwhile. A butt reading carries the same predicates a moisture reading does,
    so the view tells them apart by the property the want is about: the cone resumes, and the
    pass finds the want where the dose left it. A moisture reading off the prediction, by
    however little, is not the kept world — exact until intervals (#556) — and that is asserted
    too, as the honest boundary."""
    from conftest import write_reading
    from test_planning import MOISTURE, STORED
    monkeypatch.setenv("OREXIS_WORLD", "loner")
    st = genesis_store({("zz", MOISTURE): 0.10, ("water_butt", STORED): 3.0}, world="loner")
    agent = build_agent("gardener", st, monkeypatch)
    desire = next(g for g in agent.pursuing() if getattr(g, "observed_property", None) == MOISTURE and not g.is_epistemic)
    planner = Planner(agent, agent.me)
    plan = planner.plan(desire)
    assert plan.steps, "a dry gardener doses"
    _take(agent, plan.steps[0])                       # the dose lands exactly as predicted
    write_reading(agent, 2.5, STORED)                 # the butt's level moves meanwhile
    desire = next(g for g in agent.pursuing() if getattr(g, "observed_property", None) == MOISTURE and not g.is_epistemic)
    again = planner.plan(desire)
    assert _kept_worlds(agent) > 0, "the butt drifted, the moisture cone stands"
    assert [s.action for s in again.steps] == [s.action for s in plan.steps[1:]], "the tail is what is left"
    adds, _ = plan.steps[0].predicts
    landed = next(f[4] for f in adds if f[0] == "keyed")
    write_reading(agent, landed + 0.01, MOISTURE)
    desire = next(g for g in agent.pursuing() if getattr(g, "observed_property", None) == MOISTURE and not g.is_epistemic)
    planner.plan(desire)
    assert _kept_worlds(agent) == 0, "a moisture reading off the prediction is not the kept world — exact, until intervals"
