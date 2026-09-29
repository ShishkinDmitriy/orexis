"""`create`: the planning package's part (a-package-starts-itself) — its Planner, which says what
happened by its own signals: `plan_published`, `want_reached`, `step_blocked`.

LINKED, it connects those signals to what lies beneath it — the executor adopts a plan published,
ends an unbegun intention whose want is reached, ends one whose next step is blocked — and hears the
executor's `intention_resolved`, asking for the next pass at once. STARTED, it plans every pass,
after the jobs a pass drains, and holds the agent while something is wanted.

WHAT KEEPS AN AGENT RUNNING, PLANNING'S PART. A desire asks at every instant, so an agent holding
one is held for good. A want is one-shot: when none stands and none is walked, planning lets go,
`met`; when some stand, nothing walks them and no search was cut short, nothing this agent holds
reaches them — said in the log and as a metric by desire — and an agent holding no desire lets go,
`unreachable`. A search the budget cut short asks for the next pass at once.
"""

from __future__ import annotations

import logging

from agent import metrics
from agent.lifecycle import MET, UNREACHABLE
from agent.ontology import local_of

from .metrics import UNREACHED
from .planner import Planner

log = logging.getLogger("planning")


class _Planning:
    def __init__(self, runtime):
        self.planner = Planner(runtime.beliefs, runtime.id, **({"budget": runtime.budget} if runtime.budget else {}))
        self.runtime = runtime

    def link(self, parts) -> None:
        execution = parts.get("execution")
        if execution is None:
            return
        executor = execution.executor
        self.planner.plan_published.connect(executor.adopt)
        self.planner.want_reached.connect(lambda want: executor.end_for(want, "reached"))
        self.planner.step_blocked.connect(lambda step: executor.end_at(step, "failed"))
        executor.intention_resolved.connect(lambda **ended: self.runtime.again())

    def start(self, runtime) -> None:
        def plan():
            written = self.planner.plan(runtime.now)
            _keep(runtime, self.planner)
            runtime.lap("plan")
            return written
        runtime.every(0, plan)
        runtime.gauge(self.planner.gauges)


def create(runtime) -> _Planning:
    """The planning package's part: its Planner, to plan every pass once started."""
    return _Planning(runtime)


def _keep(runtime, planner: Planner) -> None:
    """Hold the agent, or let it go and say how the wanting ended."""
    standing, walking = planner.standing(runtime.now), planner.walking()
    desire = planner.holds_a_desire()
    if not standing and not walking:
        if desire:
            runtime.hold(planner)
        else:
            runtime.release(planner, MET)
        return
    if walking:
        runtime.hold(planner)
        return
    if planner.exhausted():
        runtime.again()                     # the budget cut a search short; the next pass continues it
        runtime.hold(planner)
        return
    log.error("%s: %d want(s) stand and nothing this agent holds reaches them: %s",
              runtime.id, len(standing), ", ".join(local_of(w) for w in standing))
    if metrics.recording():
        for want in standing:
            UNREACHED(desire=planner.desire_of(want))
    if desire:
        runtime.hold(planner)
    else:
        runtime.release(planner, UNREACHABLE)
