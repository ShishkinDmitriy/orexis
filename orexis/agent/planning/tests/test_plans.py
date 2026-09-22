"""The pass end to end: desires in, a plan in the store.

The three suites beside this one hold each stage of the pipeline to a snapshot of the store it
leaves. This one asks the question those cannot: does a search over the worlds those stages
build actually reach the state a want names, by chaining a step the case declares once?

A case here is a whole small world — an agent, a lever, a desire and a reading. The claim is
about the PLAN, which the pass WRITES: a graph per want in the imaginarium it was searched in,
found by its class and never by its name, exactly as every other read here asks by kind.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pyoxigraph as ox
import pytest

from orexis.agent import clock
from orexis.agent.store import put_graph, close_catalogue, bind, rows, Raw, graphs_of
from orexis.agent.planning.ontology import NO_CANDIDATE, PLAN_GRAPH, SATISFIED
from orexis.agent.planning.planner import Planner
from orexis.agent.planning.scope_actions import scope_actions

CASES = Path(__file__).parent / "plans"
NOW = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
WORLD = "http://example.org/test#world"

#  WHAT A PLAN SAYS, read back out of the graph the pass wrote it into.
_PLAN_Q = """
SELECT ?outcome ?costs ?want WHERE {
  GRAPH $plan { $plan planning:outcome ?outcome ; planning:forWant ?want .
                OPTIONAL { $plan planning:costs ?costs } } }"""

#  ORDERED BY THE CHAIN and not by the step's name, which is a convention the writer happens
#  to assign in order: a step is at the position of how many steps reach it through
#  `execution:then`, so this reads the claim a plan actually makes rather than a spelling.
_STEPS_Q = """
SELECT ?step ?fills (COUNT(?before) AS ?n) WHERE {
  GRAPH $plan { ?step a execution:Step ; execution:fills ?fills .
                OPTIONAL { ?before execution:then+ ?step } } }
GROUP BY ?step ?fills ORDER BY ?n"""


def plans_of(planner: Planner) -> list[dict]:
    """Every plan the pass left, over every imaginarium it made — asked by class."""
    out = []
    for imaginarium in planner.imaginaria:
        for graph in graphs_of(imaginarium.store, PLAN_GRAPH):
            named = Raw(f"<{graph}>")
            (found,) = rows(imaginarium.store, bind(_PLAN_Q, plan=named))
            found["steps"] = [r["fills"] for r
                              in rows(imaginarium.store, bind(_STEPS_Q, plan=named))]
            out.append(found)
    return out


@pytest.fixture
def store(monkeypatch):
    monkeypatch.setattr(clock, "now", lambda: NOW)
    st = ox.Store()
    put_graph(st, WORLD, (CASES / "a_low_tank_is_filled.trig").read_text(), dataset=True)
    close_catalogue(st)
    return st


def test_the_search_chains_a_step_until_the_want_is_met(store):
    """Three doses of five from zero reaches the floor of ten — and the third is what proves
    the chaining, since the want is still unmet after the second."""
    planner = Planner(store, "keeper")
    planner.plan(NOW)
    found = plans_of(planner)
    assert found, "the derivation minted no want for a tank below its floor"
    (plan,) = found
    assert plan["outcome"] == SATISFIED, plan
    assert plan["steps"] == ["http://example.org/test#fill"] * 2, plan["steps"]
    assert float(plan["costs"]) == 2.0


def test_a_want_with_no_lever_is_told_apart_from_one_the_budget_could_not_reach(store):
    """NO CANDIDATE and EXHAUSTED are different findings — one says equip me, the other says
    my doses are too coarse — and a planner that reported them alike would send somebody to
    buy a pump when the problem is the dose."""
    store.update("DELETE WHERE { GRAPH <http://example.org/test#actions> { ?s ?p ?o } }")
    scope_actions(store)
    planner = Planner(store, "keeper")
    planner.plan(NOW)
    (plan,) = plans_of(planner)
    assert plan["outcome"] == NO_CANDIDATE, plan
    assert plan["steps"] == []
    assert "costs" not in plan, "a plan that found nothing was scored a cost"
