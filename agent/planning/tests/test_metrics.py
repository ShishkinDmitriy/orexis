"""Planning's metrics: its gauges over the imaginaria and never over the belief base, and what its
events read. Their figures on a whole run are Hanoi's and the greenhouse's to hold."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from agent import clock
from agent.planning.metrics import desire_of, gauges, pursued_by
from agent.runtime import Runtime, boot

HANOI = Path(__file__).resolve().parents[3] / "world" / "hanoi"
NOW = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)


def _one_pass(monkeypatch) -> Runtime:
    ticks = iter(range(1, 10_000))
    monkeypatch.setattr(clock, "now", lambda: NOW + timedelta(seconds=next(ticks)))
    runtime = Runtime(boot(HANOI, "hanoi"), "hanoi", budget=20)
    runtime.run(passes=1, poll_s=0)
    return runtime


def test_the_gauges_count_the_imaginaria_and_nothing_of_the_beliefs(monkeypatch):
    """One pass at twenty candidates: a plan cut short and the cone it left, in the imaginaria; the
    belief base holds no plan and no world, so over it every figure is nought."""
    runtime = _one_pass(monkeypatch)
    imagined = {g.name: f for g, f in gauges(runtime.started["planning"].imaginaria.values())}
    assert imagined["plans"]["exhausted"] == 1 and imagined["cone"]["worlds"] == 20
    believed = {g.name: f for g, f in gauges([runtime.beliefs])}
    assert believed["plans"] == {"satisfied": 0, "exhausted": 0, "noCandidate": 0}
    assert believed["cone"]["worlds"] == 0


def test_an_authored_want_was_derived_under_no_desire_and_no_intention_pursues_it_yet(monkeypatch):
    runtime = _one_pass(monkeypatch)
    (store,) = runtime.started["planning"].imaginaria.values()
    want = "http://example.org/orexis/world/hanoi#every_disk_home"
    assert desire_of(store, want) is None
    assert pursued_by(runtime.started["execution"].intentions, "urn:no:intention") is None
