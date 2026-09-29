"""Planning's part: its Planner, whose own signals say what a pass published, reached and blocked;
linked, they reach the executor, and the executor's `intention_resolved` asks for the next pass; once
started it plans every pass and holds the agent while something is wanted."""

from __future__ import annotations

from pathlib import Path

from agent import clock
from agent.lifecycle import MET, Signal
from agent.planning.planner import Planner
from agent.planning.create import create

BENCH = Path(__file__).parent / "bench"


class _Executor:
    """What planning links to, as the executor answers it: its signal, and a record of what it heard."""

    def __init__(self):
        self.intention_resolved, self.heard = Signal("intention_resolved"), []

    def adopt(self, plan, want, desire=None):
        self.heard.append(("adopt", plan, want))

    def end_for(self, want, outcome):
        self.heard.append((outcome, want))

    def end_at(self, step, outcome):
        self.heard.append((outcome, step))


class _Execution:
    def __init__(self):
        self.executor = _Executor()


def test_its_part_plans_every_pass_links_its_signals_down_and_holds_the_agent(monkeypatch, snapshots, stand_in_runtime):
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    runtime = stand_in_runtime(snapshots.stand_in(BENCH / "two_disk_hanoi.trig"), None, snapshots.NOW,
                               agent_id=snapshots.AGENT, budget=64)
    part, execution = create(runtime), _Execution()
    assert isinstance(part.planner, Planner)
    part.link({"planning": part, "execution": execution})
    part.start(runtime)
    [(seconds, plan)] = runtime.timers
    assert seconds == 0, "every pass"
    written = plan()
    [(kind, published, want)] = execution.executor.heard
    assert kind == "adopt" and published in written and want in part.planner.walking()
    assert part.planner in runtime.held, "a want is walked, so the agent is held"
    execution.executor.intention_resolved.emit(type("Resolved", (), {"want": want, "outcome": "failed"})())
    assert runtime.pressed, "an intention that ended asks for the next pass at once"
    assert runtime.outcome != MET
