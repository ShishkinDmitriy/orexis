"""The pass end to end: desires in, a plan out.

The three suites beside this one hold each stage of the pipeline to a snapshot of the store it
leaves. This one asks the question those cannot: does a search over the worlds those stages
build actually reach the state a want names, by chaining a step the case declares once?

A case here is a whole small world — an agent, a lever, a desire and a reading — and the claim
is about the PLAN, not about the store, so it is asserted rather than snapshotted.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pyoxigraph as ox
import pytest

from orexis.agent import clock
from orexis.agent.store import put_graph, close_catalogue
from orexis.agent.planning.plan import EXHAUSTED, NOTHING, SATISFIED
from orexis.agent.planning.planner import Planner
from orexis.agent.planning.scope_actions import scope_actions

CASES = Path(__file__).parent / "plans"
NOW = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
WORLD = "http://example.org/test#world"


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
    plans = Planner(store, "keeper").plan(NOW)
    assert plans, "the derivation minted no want for a tank below its floor"
    (plan,) = plans.values()
    assert plan.outcome == SATISFIED, plan
    assert len(plan.steps) == 2, [s.action for s in plan.steps]
    assert {s.action for s in plan.steps} == {"http://example.org/test#fill"}
    assert plan.cost == 2.0


def test_a_want_with_no_lever_is_told_apart_from_one_the_budget_could_not_reach(store):
    """NOTHING and EXHAUSTED are different findings — one says equip me, the other says my
    doses are too coarse — and a planner that reported them alike would send somebody to buy
    a pump when the problem is the dose."""
    store.update("DELETE WHERE { GRAPH <http://example.org/test#actions> { ?s ?p ?o } }")
    scope_actions(store)
    (plan,) = Planner(store, "keeper").plan(NOW).values()
    assert plan.outcome == NOTHING, plan
    assert plan.steps == ()
