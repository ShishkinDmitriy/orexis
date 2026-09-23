"""Continuing a search — the claim that its state is the store's and not a Python heap.

The planner suite shows what a whole pass leaves. These hold `Planner.search` to the one thing
the weighings exist for: called again on the same imaginarium, it takes up where it stopped.
A search the budget cut short is finished by a second call, on the worlds the first one made
and not on copies of them; and a search that has finished, asked again, makes nothing new.
"""

from __future__ import annotations

import pytest

from agent import clock
from agent.store import dump_nt, graph_names, graphs_of, rows
from agent.planning.derive_wants import derive_wants
from agent.planning.ontology import EXHAUSTED, PLAN_GRAPH, SATISFIED
from agent.planning.find_wants import find_wants
from agent.planning.lay_ground import lay_ground
from agent.planning.planner import Planner
from agent.planning.prepare_ground import prepare_ground
from agent.planning.unweighed import unweighed
from agent.planning.weigh import weigh

#  What a pass left, counted: the worlds it forked and the weighings it wrote for the want.
_MADE_Q = """
SELECT (COUNT(DISTINCT ?w) AS ?worlds) (COUNT(DISTINCT ?x) AS ?weighings) WHERE {
  GRAPH ?cat { ?cat a orexis:CatalogueGraph .
    { ?w a planning:PossibleGraph } UNION { ?x a planning:Weighing ; planning:for $want } } }"""

_PLAN_Q = """
SELECT ?outcome (COUNT(?step) AS ?steps) WHERE {
  GRAPH ?g { ?g a planning:Plan ; planning:for $want ; planning:outcome ?outcome .
             OPTIONAL { ?step a execution:Step ; execution:partOf ?g } } }
GROUP BY ?outcome"""


@pytest.fixture
def imagined(monkeypatch, snapshots):
    """The low tank's imaginarium with its want derived — the store `search` is handed."""
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    beliefs = snapshots.stand_in(snapshots.cases_in(snapshots.Path(__file__).parent / "plans")[0])
    import pyoxigraph as ox
    store = prepare_ground(beliefs, ox.Store())
    lay_ground(store, snapshots.NOW)
    for pair in unweighed(store):
        weigh(store, pair["for"], pair["about"])
    derive_wants(store, snapshots.NOW)
    (want,) = find_wants(store, snapshots.NOW)
    return Planner(beliefs, snapshots.AGENT), store, want


def _made(store, want) -> tuple[int, int]:
    (row,) = rows(store, _MADE_Q, (), want=want)
    return int(row["worlds"]), int(row["weighings"])


def _plan(store, want) -> tuple[str, int]:
    (row,) = rows(store, _PLAN_Q, (), want=want)
    return row["outcome"], int(row["steps"])


def test_a_search_the_budget_cut_short_is_finished_by_the_next_call(imagined, snapshots):
    """One fork's worth of budget reaches a world the want is not met in and says EXHAUSTED;
    the next call, with room, finishes from that world rather than from nothing — the same
    plan the plans case shows, and no world made twice."""
    planner, store, want = imagined
    planner.search(store, want, budget=1)
    assert _plan(store, want) == (EXHAUSTED, 0)
    assert _made(store, want) == (1, 2), "the ground weighed, and one world forked and weighed"

    planner.search(store, want, budget=32)
    assert _plan(store, want) == (SATISFIED, 2)
    assert _made(store, want) == (2, 3), "one more world, on top of the first — not beside it"


def test_a_finished_search_asked_again_makes_nothing_new(imagined, snapshots):
    """Every weighing closed, the frontier is empty and the next call reads its way straight
    to the plan it already found. Held to the whole store: not one quad differs."""
    planner, store, want = imagined
    planner.search(store, want)
    before = dump_nt(store, *sorted(graph_names(store)))

    planner.search(store, want)
    assert dump_nt(store, *sorted(graph_names(store))) == before
    assert _plan(store, want) == (SATISFIED, 2)
    assert graphs_of(store, PLAN_GRAPH), "and the plan graph is the one thing asked by class"
