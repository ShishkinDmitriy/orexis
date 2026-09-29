"""Execution's `start`: once started it adopts what planning publishes, walks what is due every pass,
and ends an intention whose want planning says is reached before any step was taken."""

from __future__ import annotations

from pathlib import Path

from agent import clock
from agent.events import INTENTION_RESOLVED, PLAN_PUBLISHED, STEP_BLOCKED, WANT_REACHED
from agent.execution.executor import Executor
from agent.execution.start import start
from agent.store import entry, update

BENCH = Path(__file__).resolve().parents[2] / "planning" / "tests" / "bench"
PLAN, WANT = "urn:test:plan", "urn:test:want"


def _hand_down(store) -> None:
    """A plan of one step handed down, as planning would write it — by hand, since execution imports
    nothing of planning, its tests included."""
    update(store, f"""INSERT DATA {{
  GRAPH <{PLAN}> {{ <{PLAN}> <http://example.org/orexis/execution#pursues> <{WANT}> .
                   <{PLAN}.s1> a <http://example.org/orexis/execution#Step> ;
                               <http://example.org/orexis/execution#partOf> <{PLAN}> . }}
  {entry(store, PLAN, "http://example.org/orexis#PlanGraph", "http://example.org/orexis#Recorded")} }}""")


def test_started_it_adopts_what_is_published_and_ends_what_was_reached_untaken(monkeypatch, snapshots, stand_in_runtime):
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    store = snapshots.stand_in(BENCH / "two_disk_hanoi.trig")
    runtime = stand_in_runtime(store, None, snapshots.NOW, agent_id=snapshots.AGENT)
    executor = start(runtime)
    assert isinstance(executor, Executor)
    assert set(runtime.listeners) >= {PLAN_PUBLISHED, WANT_REACHED, STEP_BLOCKED}
    assert [seconds for seconds, _ in runtime.timers] == [0], "a walk every pass"
    _hand_down(store)
    plan, want = PLAN, WANT
    [adopt] = runtime.listeners[PLAN_PUBLISHED]
    assert adopt(plan=plan, want=want) == [executor.graph]
    assert executor.walking() == [want]
    [reached] = runtime.listeners[WANT_REACHED]
    reached(want=want)
    assert executor.walking() == [], "reached before any step was taken: ended"
    assert [what["outcome"] for event, what in runtime.emitted if event == INTENTION_RESOLVED] == ["reached"]


def test_started_it_ends_an_intention_whose_next_step_is_blocked(monkeypatch, snapshots, stand_in_runtime):
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    store = snapshots.stand_in(BENCH / "two_disk_hanoi.trig")
    runtime = stand_in_runtime(store, None, snapshots.NOW, agent_id=snapshots.AGENT)
    executor = start(runtime)
    _hand_down(store)
    [adopt] = runtime.listeners[PLAN_PUBLISHED]
    adopt(plan=PLAN, want=WANT)
    (standing,) = executor.standing()
    [blocked] = runtime.listeners[STEP_BLOCKED]
    blocked(step=standing.at)
    assert executor.walking() == []
    assert [what["outcome"] for event, what in runtime.emitted if event == INTENTION_RESOLVED] == ["failed"]
