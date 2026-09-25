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
TO = "http://example.org/orexis/courier#to"      # what courier:Drive declares it takes
from orexis_agent_deliberation import planner as search, pursuit
from orexis_agent_deliberation.imaginarium import Imaginarium
from orexis_agent_deliberation.planner import Planner
from orexis_agent_progression.ontology import DELIBERATION_GRAPH, STATE_GRAPH
from orexis_agent_progression.store import bindings
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
    row = type("R", (), {"action": "urn:x:dose", "binding": (("urn:x:valve", "urn:x:pump"),)})()
    stale = [ox.Triple(obs, pred, ox.Literal("0.29", datatype=dec))]     # not what the node holds
    fresh = [ox.Triple(obs, pred, ox.Literal("0.55", datatype=dec))]
    child = im.reached(STATE_GRAPH, (row,), fresh, stale)
    values = [q.object.value for q in im.quads(child) if q.subject == obs and q.predicate == pred]
    assert values == ["0.55"], values


# --- identification among the children (#554), within the want's view (#565) ----------------


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
    desire = next(g for g in agent.considering() if getattr(g, "observed_property", None) == MOISTURE and not g.is_epistemic)
    planner = Planner(agent, agent.me)
    plan = planner.plan(desire)
    assert plan.steps, "a dry gardener doses"
    band = predicted_band(plan.steps[0])
    assert band.startswith("http://example.org/orexis#band."), "the prediction says what the reading will be"
    lo, hi = band_bounds(agent, band)
    assert lo is not None and hi is not None, "the band the dose reaches has both bounds"
    write_reading(agent, (lo + hi) / 2, MOISTURE)     # lands inside the band the dose predicted
    write_reading(agent, 2.5, STORED)                 # the butt's level moves meanwhile
    desire = next(g for g in agent.considering() if getattr(g, "observed_property", None) == MOISTURE and not g.is_epistemic)
    again = planner.plan(desire)
    assert _kept_worlds(agent) > 0, "the butt drifted and the pot landed a hundredth off: the moisture cone stands"
    assert [s.action for s in again.steps] == [s.action for s in plan.steps[1:]], "the tail is what is left"
    write_reading(agent, hi + 0.01, MOISTURE)         # into another band: another world
    desire = next(g for g in agent.considering() if getattr(g, "observed_property", None) == MOISTURE and not g.is_epistemic)
    planner.plan(desire)
    assert _kept_worlds(agent) == 0, "a reading in another band is not the kept world"


# --- a surprise is classified (#570) --------------------------------------------------------

def _surprise(agent) -> str | None:
    rows = bindings(agent.beliefs.query_union(f"""
SELECT ?s WHERE {{ GRAPH <{DELIBERATION_GRAPH}> {{ ?d a deliberation:Deliberation . OPTIONAL {{ ?d deliberation:surprise ?s }} }} }}"""))
    assert len(rows) == 1
    return rows[0].get("s")


def test_a_world_the_law_refused_is_kept_and_the_exit_is_planned_from_it(tmp_path, monkeypatch):
    """The tempting lever plants the marker the law forbids; the search forks that world,
    refuses it, and keeps it with its verdict. The world then enters it anyway. The next pass
    identifies the present in the refused world, re-roots there, and plans the exit."""
    from conftest import write_reading
    from test_avoidance import MARKER, _avoidance_row, _lawful_gardener, _toy_pair
    from test_planning import MOISTURE
    exit_toy = '''
toy:Exit a orexis:Action ;
    orexis:takes orexis:about, <urn:toy#lever> ;
    orexis:available """SELECT ?want ?about ?lever WHERE { VALUES (?want ?about) { $wants } BIND($me AS ?lever) }""" ;
    orexis:retracts """CONSTRUCT { <urn:naughty> ?p ?o } WHERE {
            <urn:naughty> ?p ?o }""" ;
    sh:construct "CONSTRUCT {} WHERE {}" .
'''
    #  The toys at no cost (#579): the real dose is free and reaches the region, so a
    #  tempting lever dearer than it is dropped before it is simulated, and a world never
    #  forked is never refused. Free, it is forked, refused and kept.
    agent, st = _lawful_gardener(tmp_path, monkeypatch, _toy_pair(0.0, 0.0) + exit_toy)
    moisture = next(g for g in agent.considering() if getattr(g, "observed_property", None) == MOISTURE and not g.is_epistemic)
    planner = Planner(agent, agent.me)
    first = planner.plan(moisture)
    refused = [n for n in planner._nodes if n.verdict == search.trace.FORBIDDEN]
    assert refused, "the tempting world was forked, refused, and kept"
    tempting = refused[0]
    adds, _ = tempting.taken[0].predicts
    landed = next(f[4] for f in adds if f[0] == "keyed" and f[3] == RESULT)
    write_reading(agent, landed, MOISTURE)
    st.update(f"INSERT DATA {{ GRAPH <{STATE_GRAPH}> {{ {MARKER} }} }}")
    moisture = next(g for g in agent.considering() if getattr(g, "observed_property", None) == MOISTURE and not g.is_epistemic)
    planner.plan(moisture)
    assert _kept_worlds(agent) >= 1 and _surprise(agent) is None, "the present was the refused world, kept"
    plan = Planner(agent, agent.me).plan(_avoidance_row(agent))
    assert plan.steps and plan.steps[0].action == "urn:toy#Exit", "and the exit is plannable from inside it"
