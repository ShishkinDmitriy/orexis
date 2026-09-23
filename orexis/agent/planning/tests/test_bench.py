"""The bench: the Planner on a problem big enough that the pass is the search.

Two hanoi puzzles, held to their answers — three moves for two disks, seven for three — and
TIMED, with the count of engine statements beside the time, printed so `pytest -s` shows them.
No time is asserted: this Pi drifts about twofold between invocations, so a threshold would be
red on a slow morning and say nothing on a fast one. What is asserted is the plan, and what is
reported is what it cost, for an alternated A/B against another tree (`knowledge/runbooks/
measure-the-search.md`, and the scratch script that runs both trees turn about).

THE THREE-DISK PUZZLE NEEDS MORE THAN THE DEFAULT BUDGET: a uniform-cost search with no
heuristic weighs around eighty candidates before it has proved nothing shorter than seven
moves exists, so the Planner is sized here — which is what the budget is for, a ceiling on
compute a container states.
"""

from __future__ import annotations

import collections
import time
from pathlib import Path

import pyoxigraph as ox
import pytest

from orexis.agent import clock
from orexis.agent.planning.ontology import PLAN_GRAPH
from orexis.agent.planning.planner import Planner
from orexis.agent.store import Raw, bind, graphs_of, rows

BENCH = Path(__file__).parent / "bench"

_PLAN_Q = """
SELECT ?outcome ?costs (COUNT(?step) AS ?steps) WHERE {
  GRAPH $plan { $plan planning:outcome ?outcome . OPTIONAL { $plan planning:costs ?costs }
                OPTIONAL { ?step a execution:Step ; execution:partOf $plan } } }
GROUP BY ?outcome ?costs"""


def _statements(monkeypatch) -> collections.Counter:
    """Every engine statement of the run, counted by kind."""
    counts = collections.Counter()
    q, u = ox.Store.query, ox.Store.update
    monkeypatch.setattr(ox.Store, "query", lambda self, *a, **k: (counts.update(["query"]), q(self, *a, **k))[1])
    monkeypatch.setattr(ox.Store, "update", lambda self, *a, **k: (counts.update(["update"]), u(self, *a, **k))[1])
    return counts


@pytest.mark.parametrize("case, moves, budget", [("two_disk_hanoi", 3, 32), ("three_disk_hanoi", 7, 128)])
def test_the_planner_solves_hanoi_and_says_what_it_cost(case, moves, budget, monkeypatch, snapshots):
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    store = snapshots.stand_in(BENCH / f"{case}.trig")
    counts = _statements(monkeypatch)
    planner = Planner(store, snapshots.AGENT, budget=budget)
    started = time.perf_counter()
    planner.plan(snapshots.NOW)
    took = (time.perf_counter() - started) * 1000
    (imagined,) = planner.imaginaria
    (graph,) = graphs_of(imagined, PLAN_GRAPH)
    (plan,) = rows(imagined, bind(_PLAN_Q, plan=Raw(f"<{graph}>")))
    print(f"\n{case}: {took:.0f} ms, {counts['query']} queries, {counts['update']} updates, "
          f"{plan['outcome'].rsplit('#', 1)[-1]} in {plan['steps']} steps")
    assert plan["outcome"].endswith("#Satisfied"), plan
    assert int(plan["steps"]) == moves and float(plan["costs"]) == float(moves)
