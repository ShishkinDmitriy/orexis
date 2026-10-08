"""Planning's part: its Planner, whose own signals say what a pass published, reached and blocked;
linked, they reach the executor, and the executor's `intention_resolved` asks for the next pass; once
started it plans every pass and holds the agent while something is wanted."""

from __future__ import annotations

from pathlib import Path

from agent import clock
from agent.execution.events import Taking
from agent.lifecycle import MET, PLANNED, Signal
from agent.planning.ontology import BUDGET_TERM
from agent.planning.planner import Planner
from agent.planning.create import create
from agent.store import rows

BENCH = Path(__file__).parent / "bench"
#  THE FIRST STEP OF A PUBLISHED PLAN: the one nothing follows.
_HEAD_Q = """SELECT ?s WHERE { GRAPH $plan { ?s a execution:Step . FILTER NOT EXISTS { ?o execution:then ?s } } }"""


class _Executor:
    """What planning links to, as the executor answers it: its signal, and a record of what it heard."""

    def __init__(self):
        self.intention_resolved, self.taking, self.heard = Signal("intention_resolved"), Signal("taking"), []

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
    #  A HEAD ABOUT TO BE TAKEN IS PLANNING'S TO CHECK (#916): heard, and — the present admitting the
    #  plan's first move, as it did when the plan was found — nothing ended.
    assert execution.executor.taking.connected
    (head,) = [r["s"] for r in rows(runtime.beliefs, _HEAD_Q, (), plan=published)]
    execution.executor.taking.emit(Taking(head, snapshots.NOW))
    assert execution.executor.heard == [(kind, published, want)], "a head the present admits is not ended"
    execution.executor.intention_resolved.emit(type("Resolved", (), {"want": want, "outcome": "failed"})())
    assert runtime.pressed, "an intention that ended asks for the next pass at once"
    assert runtime.outcome not in (MET, PLANNED)


def test_linked_to_no_executor_it_holds_an_agent_holding_a_desire_once_every_want_has_a_plan(monkeypatch, snapshots, stand_in_runtime):
    """Nothing to link to, so nothing walks what it publishes (#928): the pass publishes the plan and
    the want is walked by it as `walking` counts, which is as far as this agent takes it — but the
    case's keeper holds the desire the want was minted under, and a desire holds any agent, so
    planning neither lets go `planned` nor says the want unreachable. An agent holding wants alone
    lets go `planned` (world/hanoi/tests/, agent/tests/test_runtime.py)."""
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    runtime = stand_in_runtime(snapshots.stand_in(BENCH / "two_disk_hanoi.trig"), None, snapshots.NOW,
                               agent_id=snapshots.AGENT, budget=64)
    part = create(runtime)
    part.link({"planning": part})
    part.start(runtime)
    [(_, plan)] = runtime.timers
    plan()
    assert part.planner.walking() and part.planner.standing(snapshots.NOW), "a plan published, its want standing"
    assert part.planner.holds_a_desire() and part.planner in runtime.held and runtime.outcome is None
    assert not runtime.pressed, "nothing is cut short, so nothing asks for the next pass at once"


def test_its_planner_spends_the_agents_stance_unless_the_runtime_was_handed_a_budget(snapshots, stand_in_runtime):
    """The process's runtime is handed no budget, so the Planner reads `planning:budget` off the self
    graph; a runtime a test sized hands its own down (knowledge/domain/kernel/stance.md)."""
    store = snapshots.stating(snapshots.stand_in(BENCH / "two_disk_hanoi.trig"), {BUDGET_TERM: 12})
    assert create(stand_in_runtime(store, None, snapshots.NOW, agent_id=snapshots.AGENT)).planner.budget == 12
    assert create(stand_in_runtime(store, None, snapshots.NOW, agent_id=snapshots.AGENT, budget=64)).planner.budget == 64
