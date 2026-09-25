"""Tower of Hanoi in the 0.2.0 runtime: the world boots from the files beside this test, the
mover plans and takes its own moves, and the runtime stops when every disk is home."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from agent import clock
from agent.ontology import DESIRE, STATE
from agent.runtime import MET, Runtime, boot
from agent.store import graphs_of, rows

WORLD = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)

_HOME_Q = """PREFIX hanoi: <http://example.org/orexis/hanoi#>
SELECT (COUNT(DISTINCT ?d) AS ?n) WHERE { GRAPH ?g { ?d (hanoi:on)+ hanoi:PegC } }"""
_ACTS_Q = "SELECT (COUNT(?a) AS ?n) WHERE { GRAPH ?g { ?a a execution:Act } }"


def _home(store) -> int:
    return int(rows(store, _HOME_Q, ())[0]["n"])


def _acts(runtime) -> int:
    return int(rows(runtime.executor.intentions, _ACTS_Q, ())[0]["n"])


def test_the_boot_says_what_each_graph_is():
    beliefs = boot(WORLD, "hanoi")
    assert len(graphs_of(beliefs, DESIRE)) == 1 and len(graphs_of(beliefs, STATE)) == 1
    assert _home(beliefs) == 0, "three disks on peg A"
    (scopes,) = rows(beliefs, "SELECT (COUNT(?s) AS ?n) WHERE { GRAPH ?g { ?s a planning:Scope } }", ())
    assert int(scopes["n"]) >= 1, "scope_actions ran at boot"


def test_the_tower_is_solved_in_seven_moves_and_the_runtime_stops(monkeypatch):
    monkeypatch.setattr(clock, "now", lambda: NOW)
    runtime = Runtime(boot(WORLD, "hanoi"), "hanoi", budget=64)
    assert runtime.run() == MET
    assert _acts(runtime) == 7 and _home(runtime.beliefs) == 3
    assert runtime.run() == MET and _acts(runtime) == 7, "met stays met, and nothing moves again"


def test_a_budget_that_cuts_the_search_short_is_finished_by_the_passes_after(monkeypatch):
    """Twenty candidates a pass: two passes hand nothing down, the third hands the plan, and
    the passes together are the one-shot search. The clock TICKS here, as a running agent's
    does — a pass at the same instant as the last re-lays the present under the last one's
    name and the search would start over."""
    ticks = iter(range(1, 10_000))
    monkeypatch.setattr(clock, "now", lambda: NOW + timedelta(seconds=next(ticks)))
    runtime = Runtime(boot(WORLD, "hanoi"), "hanoi", budget=20)
    assert runtime.run(passes=12) == MET
    assert _acts(runtime) == 7


def test_a_lived_in_volume_keeps_the_agents_state_and_reloads_the_worlds(monkeypatch):
    monkeypatch.setattr(clock, "now", lambda: NOW)
    beliefs = boot(WORLD, "hanoi")
    Runtime(beliefs, "hanoi", budget=64).run()
    boot(WORLD, "hanoi", beliefs)                     # a restart on the same volume
    assert _home(beliefs) == 3, "the solved tower is the agent's belief, not the file's"
    assert len(graphs_of(beliefs, STATE)) == 1 and len(graphs_of(beliefs, DESIRE)) == 1
