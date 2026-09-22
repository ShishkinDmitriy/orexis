"""The search reads predictions and computes none (#643,
the-drift-is-sensings-and-its-result-is-predictions).

A drift is a package's rule over `$elapsed`, sensing's word since #643: sensing runs it after
every reading at the horizons the package lists and writes predictions, graphs holding during
their windows. The search reads the prediction holding at a node's instant — the predicted
reading in place of the one the world holds, EXCEPT a key the path itself changed — and runs
no rule that knows a rate. The crossing a desire foresees is the start of the earliest prediction
at which the desire reads unmet.
"""
from __future__ import annotations

from datetime import timedelta

import pytest

from agent import genesis, runtime
from conftest import genesis_store
from orexis_agent_deliberation import derive_wants as judging, pursuit
from orexis_agent_deliberation.derive_wants import derive_wants
from orexis_agent_deliberation.planner import Planner
from orexis_agent_progression import clock
from orexis_agent_progression.ontology import ACTIONS_GRAPH, STATE_GRAPH
from orexis_agent_progression.store import bindings
from orexis_agent_progression.ontology import PUBLIC
from orexis_agent_progression.ontology import PREDICTION

MOISTURE = "http://example.org/orexis/water#SoilMoisture"
OBSERVING = "http://example.org/orexis/sensing#Observing"
LANDS = "http://example.org/orexis#landsAfter"
RATE = 0.03                                   # the loner's pot, per day


def _gardener(monkeypatch, moisture=0.30):
    monkeypatch.setenv("OREXIS_WORLD", "loner")
    st = genesis_store({("zz", MOISTURE): moisture}, world="loner")
    genesis.classify_kernel_graphs(st, "gardener")
    agent = runtime.Agent("gardener", st=st)
    for module in agent.modules:          # predict what it holds, as a booted agent does
        if hasattr(module, "repredict"):
            module.repredict()
    return agent


def _region_want(agent):
    return next(g for g in agent.considering()
                if getattr(g, "observed_property", None) == MOISTURE and not g.is_epistemic)


def _look_takes(agent, seconds: int) -> None:
    agent.beliefs.update(f"""DELETE {{ GRAPH <{ACTIONS_GRAPH}> {{ <{OBSERVING}> <{LANDS}> ?t }} }}
        INSERT {{ GRAPH <{ACTIONS_GRAPH}> {{ <{OBSERVING}> <{LANDS}>
            "SELECT ({seconds} AS ?seconds) WHERE {{ }}" }} }}
        WHERE {{ GRAPH <{ACTIONS_GRAPH}> {{ <{OBSERVING}> <{LANDS}> ?t }} }}""")


def test_a_fact_the_plan_changed_is_not_overridden_by_a_prediction(monkeypatch):
    """The plan's branch beats the do-nothing branch: a reading a step wrote stays the step's at
    every later instant — a look's reading included, since nothing dries after a step inside a
    pass, the record's seam — while a reading the plan never touched is the prediction's."""
    import pyoxigraph as ox

    agent = _gardener(monkeypatch, moisture=0.04)
    planner = Planner(agent, agent.me)
    desire = planner._begin(_region_want(agent))
    node = bindings(agent.beliefs.query(f"SELECT ?o WHERE {{ GRAPH <{STATE_GRAPH}> {{ ?o sosa:observedProperty <{MOISTURE}> }} }}", agent.beliefs.graphs_of(PUBLIC)))[0]["o"]
    later = clock.now() + timedelta(hours=3)
    #  A step's diff is the whole node, as every effect's retraction writes it (#619): the
    #  present's reading out, the same key back with the value the dose reaches.
    result = ox.NamedNode("http://www.w3.org/ns/sosa/hasSimpleResult")
    present = [ox.Triple(q.subject, q.predicate, q.object)
               for q in planner.imaginarium.quads(STATE_GRAPH) if q.subject.value == node]
    dosed = [t if t.predicate != result else
             ox.Triple(t.subject, result, ox.Literal("0.25", datatype=ox.NamedNode("http://www.w3.org/2001/XMLSchema#decimal")))
             for t in present]
    added, retracted = planner._predicted(STATE_GRAPH, desire, later, added=dosed, retracted=present)
    assert added == dosed and retracted == present, "the moisture the step wrote is not overridden"
    added, retracted = planner._predicted(STATE_GRAPH, desire, later)
    assert any(t.subject.value == node for t in added), "left alone, the prediction stands in for it"
    assert any(t.subject.value == node for t in retracted), "and takes the present's reading out, type and all"


def test_the_at_want_is_derived_at_the_first_prediction_that_reads_unmet(monkeypatch):
    """0.12 at three hundredths a day above a floor of 0.10: an hour and five hours out the
    pot is still in its region, a day out it is below — so the crossing is the START of the
    window that reaches the day, the first instant the region MAY be left, and nothing in the
    kernel knew the rate."""
    agent = _gardener(monkeypatch, moisture=0.12)
    desire = _region_want(agent)
    derive_wants(agent.beliefs.engine)   # a crossing is what the last judging found
    crossing = judging.crossing_of(agent.beliefs.engine, desire.uri)
    assert crossing is not None
    windows = agent.beliefs.windows_of(PREDICTION)
    starts = [s for _, s, _ in windows]
    assert crossing in starts, "the crossing is a window's start"
    assert abs((crossing - clock.now()).total_seconds() - 18000) < 120, "five hours: the window that reaches a day"
    content = _gardener(monkeypatch, 0.20)
    derive_wants(content.beliefs.engine)
    assert judging.crossing_of(content.beliefs.engine, _region_want(content).uri) is None, \
        "a pot the ladder never predicts below has no crossing"
