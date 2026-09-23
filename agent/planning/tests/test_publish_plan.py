"""The crossing: what a pass leaves behind after its imaginarium is gone.

A plan lives in a store that is memory. An intention is the only thing that outlives the pass,
so what these hold to is that the steps arrive whole, that an ANSWER does not become a
commitment, and that a planner told no intentions store writes to none.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pyoxigraph as ox
import pytest

from agent import clock
from agent.execution.ontology import EXECUTION, intentions_graph
from agent.planning.planner import Planner
from agent.planning.scope_actions import scope_actions
from agent.store import close_catalogue, put_graph, query_over, bindings

CASES = Path(__file__).parent / "plans"
NOW = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
AGENT = "keeper"


@pytest.fixture
def beliefs(monkeypatch):
    monkeypatch.setattr(clock, "now", lambda: NOW)
    st = ox.Store()
    put_graph(st, "http://example.org/test#world",
              (CASES / "a_low_tank_is_filled.trig").read_text(), dataset=True)
    close_catalogue(st)
    return st


def _held(intentions, what: str) -> list[dict]:
    return bindings(query_over(intentions, f"""
        SELECT ?i ?o WHERE {{ ?i a <{EXECUTION}Intention> ; <{EXECUTION}{what}> ?o }}""",
        intentions_graph(AGENT)))


def test_the_pass_leaves_an_intention_standing_at_the_plans_head(beliefs):
    """The whole crossing, end to end: a want is derived, a plan is found, and what survives
    the imaginarium is one intention pursuing that want and standing at the first step."""
    intentions = ox.Store()
    Planner(beliefs, AGENT, intentions).plan(NOW)

    pursues = _held(intentions, "pursues")
    assert len(pursues) == 1, pursues
    assert pursues[0]["o"].endswith("keeper.in_range.pursued.tank1"), pursues

    steps = _held(intentions, "step")
    assert len(steps) == 2, "both steps of the plan crossed"
    by = _held(intentions, "by")
    assert len(by) == 1 and by[0]["o"] in {s["o"] for s in steps}, \
        "and it stands at one of them — the head, which nothing points `then` at"


def test_a_planner_given_no_intentions_store_writes_to_none(beliefs):
    """A search that hands nothing down is still a search: the plan is in the imaginarium and
    the pass simply ends there. It is what every case here does."""
    planner = Planner(beliefs, AGENT)
    planner.plan(NOW)

    from agent.planning.ontology import PLAN_GRAPH
    from agent.store import graphs_of
    assert any(graphs_of(im, PLAN_GRAPH) for im in planner.imaginaria.values()), "a plan was found"


def test_an_answer_is_not_a_commitment(beliefs):
    """A want with no lever comes back `NoCandidate` and its plan graph holds no step. Nothing
    stands among the intentions for a want nobody is doing anything about — an empty plan is an
    ANSWER, and the plan graph keeps it where a reader of outcomes will look."""
    beliefs.update("DELETE WHERE { GRAPH <http://example.org/test#actions> { ?s ?p ?o } }")
    scope_actions(beliefs)
    intentions = ox.Store()
    planner = Planner(beliefs, AGENT, intentions)
    planner.plan(NOW)

    from agent.planning.ontology import PLAN_GRAPH
    from agent.store import graphs_of
    assert any(graphs_of(im, PLAN_GRAPH) for im in planner.imaginaria.values()), \
        "the pass still wrote down what it concluded"
    assert _held(intentions, "pursues") == [], "and committed to nothing"
