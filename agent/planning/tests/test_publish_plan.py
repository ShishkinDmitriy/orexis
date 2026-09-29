"""The crossing: what a pass leaves behind after its imaginarium is gone.

A plan lives in a store that is memory. It is handed down into the belief base as execution's
plan graph, and the executor takes it up; what these hold to is that the steps arrive whole,
that a plan handed down is walked and not handed down again, and that an ANSWER is not handed
down at all.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pyoxigraph as ox
import pytest

from agent import clock
from agent.execution.executor import Executor
from agent.execution.ontology import EXECUTION, intentions_graph
from agent.planning.planner import Planner
from agent.planning.scope_actions import scope_actions
from agent.store import close_catalogue, graphs_of, put_graph, query_over, bindings

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


HANDED = EXECUTION + "PlanGraph"


def test_the_pass_hands_its_plan_down_and_the_executor_takes_it_up(beliefs):
    """The whole crossing, end to end, through the store: a want is derived, a plan is found and
    handed down into the beliefs as execution's plan graph, pursuing the want; the executor takes it
    up, and what survives is one intention pursuing that want and standing at the first step, the
    plan graph gone. Neither called the other."""
    planner = Planner(beliefs, AGENT)
    written = planner.plan(NOW)
    assert graphs_of(beliefs, HANDED) == written and len(written) == 1, written

    x = Executor(beliefs, AGENT)
    assert x.commit_plans() == [intentions_graph(AGENT)]
    assert graphs_of(beliefs, HANDED) == [], "taken up, and forgotten"
    pursues = _held(beliefs, "pursues")
    assert len(pursues) == 1, pursues
    assert pursues[0]["o"].endswith("keeper.in_range.pursued.tank1"), pursues
    steps = _held(beliefs, "step")
    assert len(steps) == 2, "both steps of the plan crossed"
    by = _held(beliefs, "by")
    assert len(by) == 1 and by[0]["o"] in {s["o"] for s in steps}, \
        "and it stands at one of them — the head, which nothing points `then` at"


def test_a_plan_handed_down_is_walked_and_not_handed_down_again(beliefs):
    """The next pass finds the want walked — by the plan handed down, before the executor has taken
    it up — and hands nothing down a second time."""
    planner = Planner(beliefs, AGENT)
    [plan] = planner.plan(NOW)
    assert planner.walking() == {_held_plan_want(beliefs, plan)}
    assert planner.plan(NOW) == []


def test_an_answer_is_not_handed_down(beliefs):
    """A want with no lever comes back `NoCandidate` and its plan graph holds no step. Nothing is
    handed down for a want nobody is doing anything about — an empty plan is an ANSWER, and the
    plan graph keeps it in the imaginarium where a reader of outcomes will look."""
    beliefs.update("DELETE WHERE { GRAPH <http://example.org/test#actions> { ?s ?p ?o } }")
    scope_actions(beliefs)
    planner = Planner(beliefs, AGENT)
    assert planner.plan(NOW) == []
    from agent.planning.ontology import PLAN_GRAPH
    assert any(graphs_of(im, PLAN_GRAPH) for im in planner.imaginaria.values()), \
        "the pass still wrote down what it concluded"
    assert graphs_of(beliefs, HANDED) == [] and _held(beliefs, "pursues") == [], "and handed down nothing"


def _held_plan_want(beliefs, plan: str) -> str:
    return bindings(query_over(beliefs, f"SELECT ?w WHERE {{ <{plan}> <{EXECUTION}pursues> ?w }}", plan))[0]["w"]
