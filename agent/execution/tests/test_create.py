"""Execution's part: its executor, which adopts what planning publishes, ends an intention planning says
is reached before any step or blocked, and says by its own signal every intention that ends; linked, it
walks again when the deliberator says the present changed; once started, it walks every pass."""

from __future__ import annotations

from pathlib import Path

from agent import clock
from agent.lifecycle import Signal
from agent.execution.executor import Executor
from agent.belief.events import Revised
from agent.execution.create import create
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


class _Belief:
    def __init__(self):
        self.deliberator = type("D", (), {"revised": Signal("revised")})()


def _part(monkeypatch, snapshots, stand_in_runtime):
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    store = snapshots.stand_in(BENCH / "two_disk_hanoi.trig")
    runtime = stand_in_runtime(store, None, snapshots.NOW, agent_id=snapshots.AGENT)
    part = create(runtime)
    ended = []
    part.executor.intention_resolved.connect(lambda resolved: ended.append(resolved.outcome))
    return store, runtime, part, ended


def test_its_part_adopts_what_is_published_and_ends_what_was_reached_untaken(monkeypatch, snapshots, stand_in_runtime):
    store, runtime, part, ended = _part(monkeypatch, snapshots, stand_in_runtime)
    belief = _Belief()
    part.link({"execution": part, "belief": belief})
    part.start(runtime)
    assert [seconds for seconds, _ in runtime.timers] == [0], "a walk every pass"
    belief.deliberator.revised.emit(Revised(("urn:g",)))
    assert len(runtime.jobs) == 1, "the present changed, so a walk is queued"
    _hand_down(store)
    assert part.executor.adopt(PLAN, WANT) == [part.executor.graph]
    assert part.executor.walking() == [WANT]
    part.executor.end_for(WANT, "reached")
    assert part.executor.walking() == [] and ended == ["reached"], "reached before any step was taken: ended"


def test_its_part_ends_an_intention_whose_next_step_is_blocked(monkeypatch, snapshots, stand_in_runtime):
    store, runtime, part, ended = _part(monkeypatch, snapshots, stand_in_runtime)
    _hand_down(store)
    part.executor.adopt(PLAN, WANT)
    (standing,) = part.executor.standing()
    part.executor.end_at(standing.at, "failed")
    assert part.executor.walking() == [] and ended == ["failed"]
