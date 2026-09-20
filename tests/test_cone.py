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
from orexis_agent_progression.ontology import PUBLIC


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


RESULT = "http://www.w3.org/ns/sosa/hasSimpleResult"
TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"


def predicted_band(step) -> str:
    """The member band a step predicts its reading to be — not the family beside it."""
    adds, _ = step.predicts
    return next(f[4] for f in adds if f[0] == "keyed" and f[3] == TYPE
                and str(f[4]).startswith("http://example.org/orexis#band."))


def band_bounds(agent, cls: str) -> tuple:
    """The facets of a minted band's OWL definition (#576): its low and high bound, either
    None where the band is open on that side."""
    rows = bindings(agent.beliefs.query(f"""
SELECT ?minI ?minE ?maxI ?maxE WHERE {{
  <{cls}> owl:equivalentClass/owl:intersectionOf/rdf:rest*/rdf:first ?r .
  ?r owl:onProperty sosa:hasSimpleResult ; owl:someValuesFrom/owl:withRestrictions ?facets .
  OPTIONAL {{ ?facets rdf:rest*/rdf:first/xsd:minInclusive ?minI }}
  OPTIONAL {{ ?facets rdf:rest*/rdf:first/xsd:minExclusive ?minE }}
  OPTIONAL {{ ?facets rdf:rest*/rdf:first/xsd:maxInclusive ?maxI }}
  OPTIONAL {{ ?facets rdf:rest*/rdf:first/xsd:maxExclusive ?maxE }} }}""", agent.beliefs.graphs_of(PUBLIC)))
    r = rows[0]
    lo = r.get("minI") or r.get("minE")
    hi = r.get("maxI") or r.get("maxE")
    return (float(lo) if lo is not None else None, float(hi) if hi is not None else None)


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


def test_a_re_rooted_cone_says_the_whole_pass_again(monkeypatch):
    """THE ROWS ARE THE NODES, so a re-root rewrites them whole.

    A re-root keeps the subtree under the world the present landed in, DROPS the rest, and
    re-bases everything it kept: new depths, new costs, a new clock, and a new root standing
    nowhere. A `deliberation:PossibleWorld` row amended rather than rewritten would leave two
    kinds of lie in the store — a world that is gone, offered to a reader asking what is still
    open, and a kept world carrying the depth and cost it had under the old root.

    So this asserts what the store says AFTER the second pass: exactly the worlds the planner
    kept, no more; the root among them with no `deliberation:from` and depth 0; and the clock
    moved to the new root's.
    """
    from orexis_agent_deliberation.planner import PASS_GRAPH
    from orexis_agent_progression.store import bindings

    agent = _driver(monkeypatch, "c0_0", "c1_2")
    planner = Planner(agent, agent.me)
    first = planner.plan(_goal(agent))
    assert len(first.steps) == 8
    before = {r["w"] for r in bindings(planner.imaginarium.query_over(
        "SELECT ?w WHERE { ?w a deliberation:PossibleWorld }", PASS_GRAPH))}

    _take(agent, first.steps[0])
    planner.plan(_goal(agent))

    rows = {r["w"]: r for r in bindings(planner.imaginarium.query_over(
        "SELECT ?w ?d WHERE { ?w a deliberation:PossibleWorld ; deliberation:atDepth ?d }",
        PASS_GRAPH))}
    kept = {n.graph for n in planner._nodes}
    assert set(rows) == kept, "the store describes exactly the worlds the pass kept"
    assert before - set(rows), "and the dropped ones are gone, not merely re-stated"

    #  A WORLD PUT BACK ON THE FRONTIER CARRIES NO VERDICT. `meets` and `lawful` are about the
    #  world and survive; a verdict is about a PASS, and the resumed one has not reached them.
    reopened = bindings(planner.imaginarium.query_over(
        "SELECT ?w WHERE { ?w a deliberation:Weighing ; deliberation:open true ; "
        "deliberation:verdict ?v }", PASS_GRAPH))
    assert not reopened, [r["w"] for r in reopened]

    roots = bindings(planner.imaginarium.query_over(
        "SELECT ?w ?d WHERE { ?w a deliberation:PossibleWorld ; deliberation:atDepth ?d . "
        "FILTER NOT EXISTS { ?w deliberation:from ?p } }", PASS_GRAPH))
    assert len(roots) == 1 and roots[0]["d"] == "0", roots
    assert roots[0]["w"] == planner._root.graph, "and it is the root the planner re-rooted on"


def test_a_present_that_matches_no_kept_world_starts_from_nothing(monkeypatch):
    """The parcel is moved while the van drives: no imagined world holds that, so the cone is
    dead and the pass is built afresh — the path every pass took before #553."""
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
    graph = agent.beliefs.graphs_of(PUBLIC)[0]
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
    """A dry gardener plans a dose. The dose lands NEAR what was predicted, and the water
    butt's level moves meanwhile. A butt reading carries the same predicates a moisture
    reading does, so the view tells them apart by the property the want is about; and a
    moisture reading off the prediction within the same BAND is the kept world (#576) —
    the domain says what a reading is, and two readings it calls the same are one fact. The
    cone resumes and the pass finds the want where the dose left it. A reading in another
    band is another world, and that is asserted too."""
    from conftest import write_reading
    from test_planning import MOISTURE, STORED
    monkeypatch.setenv("OREXIS_WORLD", "loner")
    st = genesis_store({("zz", MOISTURE): 0.05, ("water_butt", STORED): 3.0}, world="loner")
    agent = build_agent("gardener", st, monkeypatch)
    desire = next(g for g in agent.pursuing() if getattr(g, "observed_property", None) == MOISTURE and not g.is_epistemic)
    planner = Planner(agent, agent.me)
    plan = planner.plan(desire)
    assert plan.steps, "a dry gardener doses"
    band = predicted_band(plan.steps[0])
    assert band.startswith("http://example.org/orexis#band."), "the prediction says what the reading will be"
    lo, hi = band_bounds(agent, band)
    assert lo is not None and hi is not None, "the band the dose reaches has both bounds"
    write_reading(agent, (lo + hi) / 2, MOISTURE)     # lands inside the band the dose predicted
    write_reading(agent, 2.5, STORED)                 # the butt's level moves meanwhile
    desire = next(g for g in agent.pursuing() if getattr(g, "observed_property", None) == MOISTURE and not g.is_epistemic)
    again = planner.plan(desire)
    assert _kept_worlds(agent) > 0, "the butt drifted and the pot landed a hundredth off: the moisture cone stands"
    assert [s.action for s in again.steps] == [s.action for s in plan.steps[1:]], "the tail is what is left"
    write_reading(agent, hi + 0.01, MOISTURE)         # into another band: another world
    desire = next(g for g in agent.pursuing() if getattr(g, "observed_property", None) == MOISTURE and not g.is_epistemic)
    planner.plan(desire)
    assert _kept_worlds(agent) == 0, "a reading in another band is not the kept world"


# --- a surprise is classified (#570) --------------------------------------------------------

def _surprise(agent) -> str | None:
    rows = bindings(agent.beliefs.query_union(f"""
SELECT ?s WHERE {{ GRAPH <{DELIBERATION_GRAPH}> {{ ?d a deliberation:Deliberation . OPTIONAL {{ ?d deliberation:surprise ?s }} }} }}"""))
    assert len(rows) == 1
    return rows[0].get("s")


def test_a_move_the_budget_withheld_is_completed_and_the_surprise_is_read_as_withheld(monkeypatch):
    """A budget of eight worlds stops the search with children un-expanded: worlds it
    reached and never took a row from. The van drives to one of them and then takes a drive
    that child never forked. The next pass finds no kept world, completes what the last pass
    left — the withheld rows, and every row of an un-expanded node — finds the present among
    the new worlds, and says the surprise was a world it chose not to imagine."""
    agent = _driver(monkeypatch, "c0_0", "c1_2")
    planner = Planner(agent, agent.me)
    planner.budget = 8
    first = planner.plan(_goal(agent))
    assert first.steps and _surprise(agent) is None
    imagined = {f[2] for n in planner._nodes for f in n.diff[0] if f[1] == C + "at"} | {W + "c0_0"}
    node, row = None, None
    for n in planner._nodes:
        if not n.taken or n.expanded or n.verdict is not None:
            continue
        #  A drive from this un-expanded world to a cell NO kept world holds the van at —
        #  a cell another path reached is a kept world, and the present would simply be it.
        row = next((r for r in planner._candidates(n, _goal(agent))
                    if r.action == C + "Drive" and r.about not in imagined), None)
        if row is not None:
            node = n
            break
    assert node is not None, "a budget of eight leaves a reached world un-expanded, with a drive nobody imagined"
    for step in node.taken:
        _take(agent, step)                            # the van drives to that child's world
    here = node.taken[-1].about
    agent.beliefs.update(f"DELETE DATA {{ GRAPH <{STATE_GRAPH}> {{ <{W}van> <{C}at> <{here}> . }} }}")
    agent.beliefs.update(f"INSERT DATA {{ GRAPH <{STATE_GRAPH}> {{ <{W}van> <{C}at> <{row.about}> . }} }}")
    again = planner.plan(_goal(agent))
    said = _surprise(agent)
    assert said is not None and said.startswith("withheld:"), said
    assert _kept_worlds(agent) >= 1, "found among the completed worlds and resumed there"
    assert again.steps, "and the delivery goes on from there"


def test_a_change_no_lever_makes_is_read_as_exogenous(monkeypatch):
    agent = _driver(monkeypatch, "c0_0", "c1_2")
    planner = Planner(agent, agent.me)
    first = planner.plan(_goal(agent))
    _take(agent, first.steps[0])
    agent.beliefs.update(f"DELETE DATA {{ GRAPH <{STATE_GRAPH}> {{ <{W}parcel> <{C}at> <{W}c1_2> . }} }}")
    agent.beliefs.update(f"INSERT DATA {{ GRAPH <{STATE_GRAPH}> {{ <{W}parcel> <{C}at> <{W}c2_2> . }} }}")
    planner.plan(_goal(agent))
    said = _surprise(agent)
    assert said is not None and said.startswith("exogenous:") and "parcel" in said, said
    assert _kept_worlds(agent) == 0


def test_a_world_the_law_refused_is_kept_and_the_exit_is_planned_from_it(tmp_path, monkeypatch):
    """The tempting lever plants the marker the law forbids; the search forks that world,
    refuses it, and keeps it with its verdict. The world then enters it anyway. The next pass
    identifies the present in the refused world, re-roots there, and plans the exit."""
    from conftest import write_reading
    from test_avoidance import MARKER, _avoidance_row, _lawful_gardener, _toy_pair
    from test_planning import MOISTURE
    exit_toy = '''
toy:Exit a orexis:Action ;
    orexis:available """SELECT ?want ?via WHERE { VALUES (?want ?about) { $wants } BIND($me AS ?via) }""" ;
    orexis:retracts """CONSTRUCT { <urn:naughty> ?p ?o } WHERE {
            <urn:naughty> ?p ?o }""" ;
    sh:construct "CONSTRUCT {} WHERE {}" .
'''
    #  The toys at no cost (#579): the real dose is free and reaches the region, so a
    #  tempting lever dearer than it is dropped before it is simulated, and a world never
    #  forked is never refused. Free, it is forked, refused and kept.
    agent, st = _lawful_gardener(tmp_path, monkeypatch, _toy_pair(0.0, 0.0) + exit_toy)
    moisture = next(g for g in agent.pursuing() if getattr(g, "observed_property", None) == MOISTURE and not g.is_epistemic)
    planner = Planner(agent, agent.me)
    first = planner.plan(moisture)
    refused = [n for n in planner._nodes if n.verdict == search.trace.FORBIDDEN]
    assert refused, "the tempting world was forked, refused, and kept"
    tempting = refused[0]
    adds, _ = tempting.taken[0].predicts
    landed = next(f[4] for f in adds if f[0] == "keyed" and f[3] == RESULT)
    write_reading(agent, landed, MOISTURE)
    st.update(f"INSERT DATA {{ GRAPH <{STATE_GRAPH}> {{ {MARKER} }} }}")
    moisture = next(g for g in agent.pursuing() if getattr(g, "observed_property", None) == MOISTURE and not g.is_epistemic)
    planner.plan(moisture)
    assert _kept_worlds(agent) >= 1 and _surprise(agent) is None, "the present was the refused world, kept"
    plan = Planner(agent, agent.me).plan(_avoidance_row(agent))
    assert plan.steps and plan.steps[0].action == "urn:toy#Exit", "and the exit is plannable from inside it"
