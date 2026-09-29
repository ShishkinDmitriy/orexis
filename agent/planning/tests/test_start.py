"""Planning's `start`: once started it plans every pass, says every plan it published, and holds the
agent while something is wanted; an intention that ends asks for the next pass at once."""

from __future__ import annotations

from pathlib import Path

from agent import clock
from agent.events import INTENTION_RESOLVED, MET, PLAN_PUBLISHED
from agent.planning.planner import Planner
from agent.planning.start import start

BENCH = Path(__file__).parent / "bench"


def test_started_it_plans_every_pass_says_what_it_published_and_holds_the_agent(monkeypatch, snapshots, stand_in_runtime):
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    runtime = stand_in_runtime(snapshots.stand_in(BENCH / "two_disk_hanoi.trig"), None, snapshots.NOW,
                               agent_id=snapshots.AGENT, budget=64)
    planner = start(runtime)
    assert isinstance(planner, Planner) and len(runtime.gauges) == 1
    [(seconds, plan)] = runtime.timers
    assert seconds == 0, "every pass"
    written = plan()
    [(event, what)] = [(e, w) for e, w in runtime.emitted if e == PLAN_PUBLISHED]
    assert what["plan"] in written and what["want"] in planner.walking()
    assert planner in runtime.held, "a want is walked, so the agent is held"
    [heard] = runtime.listeners[INTENTION_RESOLVED]
    heard(intention="urn:i", want=what["want"], outcome="failed")
    assert runtime.pressed, "an intention that ended asks for the next pass at once"
    assert runtime.outcome != MET
