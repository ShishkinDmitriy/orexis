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

from orexis.agent import clock
from orexis.agent.execution.ontology import EXECUTION
from orexis.agent.planning.extract_plan import extract_plan
from orexis.agent.planning.ontology import BY, OF, PLAN_GRAPH, PLANNING, SATISFIED
from orexis.agent.planning.planner import Planner
from orexis.agent.store import (Raw, bind, catalogue_of, close_catalogue, graphs_of,
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
    return planner.imaginaria[0]


def _steps(store, graph: str) -> list[dict]:
    """The plan's steps in chain order, each with what it fills and what it came from."""
    return rows(store, bind(f"""
        SELECT ?step ?fills ?of (COUNT(?before) AS ?n) WHERE {{
          GRAPH $plan {{ ?step a <{EXECUTION}Step> ; <{EXECUTION}fills> ?fills ; <{OF}> ?of .
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
    forked in, read back out of `prov:wasDerivedFrom`, by a caller holding no search node."""
    (graph,) = graphs_of(walked, PLAN_GRAPH)
    by_chain = [s["of"] for s in _steps(walked, graph)]

    #  the same walk, done by hand from the world the plan was found in
    #  the world the plan was found in: the deepest fork, whose name carries the longest path
    deepest = max((g for g in graph_names_of(walked) if "/possible/" in g), key=len)
    ancestry, world = [], deepest
    while True:
        found = rows(walked, bind(f"""
            SELECT ?parent ?by WHERE {{ GRAPH $cat {{ $w prov:wasDerivedFrom ?parent .
                                        OPTIONAL {{ $w <{BY}> ?by }} }} }}""",
            cat=Raw(f"<{catalogue_of(walked)}>"), w=Raw(f"<{world}>")))
        if not found or not found[0].get("by"):
            break
        ancestry.append(found[0]["by"])
        world = found[0]["parent"]
    assert list(reversed(ancestry)) == by_chain, "root first, and the same candidates"


def test_an_answer_is_written_with_no_steps(walked):
    """A plan with no steps is an ANSWER. Extracting one from the ground the pass started in
    walks no ancestry — a ground says no `planning:by` — so the graph holds the outcome and
    nothing else."""
    (ground,) = [g for g in graph_names_of(walked) if "/ground/" in g][:1]
    graph = extract_plan(walked, ground, "urn:test:nothing", SATISFIED, None)

    assert _steps(walked, graph) == []
    assert rows(walked, bind(f"SELECT ?o WHERE {{ GRAPH $g {{ $g <{PLANNING}outcome> ?o }} }}",
                             g=Raw(f"<{graph}>")))[0]["o"] == SATISFIED


def graph_names_of(store) -> list[str]:
    return sorted({q.graph_name.value for q in store.quads_for_pattern(None, None, None, None)
                   if isinstance(q.graph_name, ox.NamedNode)})
