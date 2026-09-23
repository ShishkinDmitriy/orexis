"""The bench: the Planner on a problem big enough that the pass is the search, and the ledger
its results are tracked in.

Two hanoi puzzles, held to their answers — three moves for two disks, seven for three — and
TIMED as the median of several passes, with the count of engine statements beside the time,
printed so `pytest -s` shows them. No time is asserted: this Pi drifts about twofold between
invocations, so a threshold would be red on a slow morning and say nothing on a fast one.
What is asserted is the plan; what is reported is what it cost.

**THE LEDGER.** `pytest orexis/agent/planning/tests/test_bench.py -s -n0 --bench-record`
appends one row per case to `bench/results.tsv`: the date, the commit (`-dirty` where the
tree has uncommitted changes), the machine, the case, the budget, how many runs, the median
and the minimum in milliseconds, the queries and updates of one pass, and the steps of the
plan. A number without its commit and its machine is an impression, and the ledger refuses
to be written under xdist, where two workers would append at once. The runbook
`knowledge/runbooks/measure-the-search.md` says how to read the series and how to compare two
trees, which is alternated in one session or it is not a measurement.

THE THREE-DISK PUZZLE NEEDS MORE THAN THE DEFAULT BUDGET: a uniform-cost search with no
heuristic weighs around eighty candidates before it has proved nothing shorter than seven
moves exists, so the Planner is sized here — which is what the budget is for, a ceiling on
compute a container states.
"""

from __future__ import annotations

import collections
import os
import platform
import statistics
import subprocess
import time
from datetime import date
from pathlib import Path

import pyoxigraph as ox
import pytest

from orexis.agent import clock
from orexis.agent.planning.ontology import PLAN_GRAPH
from orexis.agent.planning.planner import Planner
from orexis.agent.store import Raw, bind, graphs_of, rows

BENCH = Path(__file__).parent / "bench"
LEDGER = BENCH / "results.tsv"
COLUMNS = ("date", "commit", "machine", "case", "budget", "runs", "median_ms", "min_ms",
           "queries", "updates", "steps")
RUNS = 5

_PLAN_Q = """
SELECT ?outcome ?costs (COUNT(?step) AS ?steps) WHERE {
  GRAPH $plan { $plan planning:outcome ?outcome . OPTIONAL { $plan planning:costs ?costs }
                OPTIONAL { ?step a execution:Step ; execution:partOf $plan } } }
GROUP BY ?outcome ?costs"""


def _pass(case: Path, budget: int, snapshots, counts: collections.Counter | None = None):
    """One pass over the case from a fresh store: the milliseconds it took and its plan."""
    store = snapshots.stand_in(case)
    planner = Planner(store, snapshots.AGENT, budget=budget)
    if counts is not None:
        counts.clear()
    started = time.perf_counter()
    planner.plan(snapshots.NOW)
    took = (time.perf_counter() - started) * 1000
    (imagined,) = planner.imaginaria
    (graph,) = graphs_of(imagined, PLAN_GRAPH)
    (plan,) = rows(imagined, bind(_PLAN_Q, plan=Raw(f"<{graph}>")))
    return took, plan


def _counting(monkeypatch) -> collections.Counter:
    """Every engine statement, counted by kind, for as long as the patch stands."""
    counts = collections.Counter()
    q, u = ox.Store.query, ox.Store.update
    monkeypatch.setattr(ox.Store, "query", lambda self, *a, **k: (counts.update(["query"]), q(self, *a, **k))[1])
    monkeypatch.setattr(ox.Store, "update", lambda self, *a, **k: (counts.update(["update"]), u(self, *a, **k))[1])
    return counts


def _commit() -> str:
    """The commit the numbers are about, `-dirty` where the tree is not that commit."""
    try:
        short = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True,
                               check=True, cwd=BENCH).stdout.strip()
        dirty = subprocess.run(["git", "status", "--porcelain", "--untracked-files=no"],
                               capture_output=True, text=True, check=True, cwd=BENCH).stdout.strip()
        return short + ("-dirty" if dirty else "")
    except Exception:                                               # noqa: BLE001
        return "unknown"


def _record(row: dict) -> None:
    """Append one row to the ledger, writing the header where the file is new."""
    assert not os.environ.get("PYTEST_XDIST_WORKER"), \
        "--bench-record needs -n0: two workers would append to the ledger at once"
    new = not LEDGER.exists()
    with LEDGER.open("a") as out:
        if new:
            out.write("\t".join(COLUMNS) + "\n")
        out.write("\t".join(str(row[c]) for c in COLUMNS) + "\n")


@pytest.mark.parametrize("case, moves, budget", [("two_disk_hanoi", 3, 32), ("three_disk_hanoi", 7, 128)])
def test_the_planner_solves_hanoi_and_says_what_it_cost(case, moves, budget, monkeypatch, request, snapshots):
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    path = BENCH / f"{case}.trig"
    #  THE STATEMENTS OF ONE PASS, counted on a run of its own, since the count does not drift
    #  and the timed runs must not pay for it.
    counts = _counting(monkeypatch)
    _, plan = _pass(path, budget, snapshots, counts)
    queries, updates = counts["query"], counts["update"]
    monkeypatch.undo()
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    times = [_pass(path, budget, snapshots)[0] for _ in range(RUNS)]
    row = {"date": date.today().isoformat(), "commit": _commit(), "machine": platform.node(),
           "case": case, "budget": budget, "runs": RUNS, "median_ms": round(statistics.median(times)),
           "min_ms": round(min(times)), "queries": queries, "updates": updates, "steps": int(plan["steps"])}
    print(f"\n{case}: median {row['median_ms']} ms of {RUNS} (min {row['min_ms']}), {queries} queries, "
          f"{updates} updates, {plan['outcome'].rsplit('#', 1)[-1]} in {plan['steps']} steps")
    if request.config.getoption("--bench-record"):
        _record(row)
    assert plan["outcome"].endswith("#Satisfied"), plan
    assert int(plan["steps"]) == moves and float(plan["costs"]) == float(moves)


def test_the_ledger_has_the_columns_the_bench_writes():
    """A ledger somebody edited by hand, or one an older bench wrote, is read by nobody until
    its header is the bench's."""
    if not LEDGER.exists():
        pytest.skip("no ledger yet — `--bench-record` writes the first row")
    assert LEDGER.read_text().splitlines()[0].split("\t") == list(COLUMNS)
