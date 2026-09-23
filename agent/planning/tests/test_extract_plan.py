"""Reading a plan out of the worlds that were walked to find it.

The search leaves a tree in the imaginarium — each possible world saying which it was forked
from and which candidate made the fork. These hold to the claim that makes `extract_plan` a
function over a STORE rather than over a tuple: the chain can be read back, in order, by
somebody who was not there when it was walked.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pyoxigraph as ox
import pytest

from agent import clock
from agent.execution.ontology import EXECUTION
from agent.planning.extract_plan import extract_plan
from agent.planning.ontology import BY, FILLS, FROM, OF, PLAN_GRAPH, PLANNING, SATISFIED
from agent.planning.planner import Planner
from agent.store import (Raw, bind, catalogue_of, close_catalogue, graphs_of,
                                          put_graph, rows)

CASES = Path(__file__).parent / "plans"
NOW = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)


@pytest.fixture
def walked(monkeypatch):
    """One pass over the low tank, and the imaginarium it left behind."""
    monkeypatch.setattr(clock, "now", lambda: NOW)
    st = ox.Store()
    put_graph(st, "http://example.org/test#world",
              (CASES / "a_low_tank_is_filled.trig").read_text(), dataset=True)
    close_catalogue(st)
    planner = Planner(st, "keeper")
    planner.plan(NOW)
    return next(iter(planner.imaginaria.values()))


def _steps(store, graph: str) -> list[dict]:
    """The plan's steps in chain order, each with what it fills and what it came from."""
    return rows(store, bind(f"""
        SELECT ?step ?fills ?of (COUNT(?before) AS ?n) WHERE {{
          GRAPH $plan {{ ?step a <{EXECUTION}Step> ; <{FILLS}> ?fills ; <{OF}> ?of .
                         OPTIONAL {{ ?before <{EXECUTION}then>+ ?step }} }} }}
        GROUP BY ?step ?fills ?of ORDER BY ?n""", plan=Raw(f"<{graph}>")))


def test_every_step_names_the_candidate_it_was_minted_from(walked):
    """The one link between what the search walked and what the plan holds. A candidate says
    which action it fills and what it is filled with; a step says the same in the ledger's
    words and points back, so a reader can ask which of the moves offered at that world it
    was."""
    (graph,) = graphs_of(walked, PLAN_GRAPH)
    steps = _steps(walked, graph)
    assert len(steps) == 2, steps

    for step in steps:
        (candidate,) = rows(walked, bind(f"""
            SELECT ?a WHERE {{ GRAPH $cat {{ $by a <{PLANNING}Candidate> ;
                                             <{PLANNING}fills> ?a }} }}""",
            cat=Raw(f"<{catalogue_of(walked)}>"), by=Raw(f"<{step['of']}>")))
        assert candidate["a"] == step["fills"], \
            "a step fills what its candidate filled — the translation is the WORD, not the move"


def test_the_chain_is_the_worlds_ancestry_and_not_a_tuple(walked):
    """What makes this a function over a store: the plan's order is the order the worlds were
    forked in, read back out of the candidate edges, by a caller holding no search node."""
    (graph,) = graphs_of(walked, PLAN_GRAPH)
    by_chain = [s["of"] for s in _steps(walked, graph)]

    #  the same walk, done by hand from the world the plan was found in — the deepest fork,
    #  whose name carries the longest path — one candidate edge at a time: the world says
    #  which candidate reached it, the candidate says which world it was taken in
    deepest = max((g for g in graph_names_of(walked) if "/possible/" in g), key=len)
    ancestry, world = [], deepest
    while True:
        found = rows(walked, bind(f"""
            SELECT ?parent ?by WHERE {{ GRAPH $cat {{ $w <{BY}> ?by . ?by <{FROM}> ?parent }} }}""",
            cat=Raw(f"<{catalogue_of(walked)}>"), w=Raw(f"<{world}>")))
        if not found:
            break
        ancestry.append(found[0]["by"])
        world = found[0]["parent"]
    assert list(reversed(ancestry)) == by_chain, "root first, and the same candidates"


def test_extracting_again_leaves_the_same_plan(walked):
    """The plan is read off the weighings, so extracting it a second time writes the same
    graph whole — one plan per want, replaced rather than added to. The empty answer, a plan
    with no steps and an outcome that says which silence, is the no-lever plans case."""
    (graph,) = graphs_of(walked, PLAN_GRAPH)
    before = _steps(walked, graph)
    (want,) = rows(walked, bind(f"SELECT ?w WHERE {{ GRAPH $g {{ $g <{PLANNING}for> ?w }} }}",
                                g=Raw(f"<{graph}>")))
    assert extract_plan(walked, want["w"]) == graph
    assert _steps(walked, graph) == before
    assert rows(walked, bind(f"SELECT ?o WHERE {{ GRAPH $g {{ $g <{PLANNING}outcome> ?o }} }}",
                             g=Raw(f"<{graph}>")))[0]["o"] == SATISFIED


def graph_names_of(store) -> list[str]:
    return sorted({q.graph_name.value for q in store.quads_for_pattern(None, None, None, None)
                   if isinstance(q.graph_name, ox.NamedNode)})
