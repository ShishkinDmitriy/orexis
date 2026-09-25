"""The courier in the 0.2.0 runtime: the world boots from the files beside this test, the driver
plans and takes its own drives, and the runtime stops when the parcel stands at its door."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from agent import clock
from agent.ontology import STATE, WANT
from agent.runtime import MET, Runtime, boot
from agent.store import graphs_of, rows

WORLD = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)

_WHERE_Q = """PREFIX courier: <http://example.org/orexis/courier#>
SELECT ?cell WHERE { ?parcel a courier:Parcel ; courier:at ?cell }"""
_ACTS_Q = "SELECT (COUNT(?a) AS ?n) WHERE { GRAPH ?g { ?a a execution:Act } }"


def _parcel_at(store) -> list[str]:
    return [r["cell"].rsplit("#", 1)[-1] for r in rows(store, _WHERE_Q, graphs_of(store, STATE, "http://example.org/orexis#WorldGraph"))]


def _acts(runtime) -> int:
    return int(rows(runtime.executor.intentions, _ACTS_Q, ())[0]["n"])


def test_the_boot_says_what_each_graph_is():
    beliefs = boot(WORLD, "courier")
    assert len(graphs_of(beliefs, WANT)) == 1 and len(graphs_of(beliefs, STATE)) == 1
    assert _parcel_at(beliefs) == ["c1_2"], "the parcel stands where the delivery was posed"


def test_the_parcel_is_delivered_in_eight_steps_and_the_runtime_stops(monkeypatch):
    """Three drives, the pick, three drives, the drop: the cheapest delivery, found by a search
    the drives-owed estimate guides."""
    monkeypatch.setattr(clock, "now", lambda: NOW)
    runtime = Runtime(boot(WORLD, "courier"), "courier", budget=128)
    assert runtime.run() == MET
    assert _acts(runtime) == 8 and _parcel_at(runtime.beliefs) == ["c3_3"]
    assert runtime.run() == MET and _acts(runtime) == 8, "met stays met, and nothing moves again"


def test_a_budget_that_cuts_the_search_short_is_finished_by_the_passes_after(monkeypatch):
    """Sixteen candidates a pass cannot reach the far corner in one pass; the passes together
    are the one-shot search. The clock ticks, as a running agent's does."""
    ticks = iter(range(1, 10_000))
    monkeypatch.setattr(clock, "now", lambda: NOW + timedelta(seconds=next(ticks)))
    runtime = Runtime(boot(WORLD, "courier"), "courier", budget=16)
    assert runtime.run(passes=20) == MET
    assert _acts(runtime) == 8


def test_a_lived_in_volume_keeps_the_agents_state_and_reloads_the_worlds(monkeypatch):
    monkeypatch.setattr(clock, "now", lambda: NOW)
    beliefs = boot(WORLD, "courier")
    Runtime(beliefs, "courier", budget=128).run()
    boot(WORLD, "courier", beliefs)                   # a restart on the same volume
    assert _parcel_at(beliefs) == ["c3_3"], "the delivered parcel is the agent's belief, not the file's"
    assert len(graphs_of(beliefs, STATE)) == 1
    assert graphs_of(beliefs, WANT) == [], "the want was reached and withdrawn, and a restart does not bring it back"
