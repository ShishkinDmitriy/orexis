"""`start`: what the planning package does once the runtime starts it (a-package-starts-itself) —
a pass every pass, after the jobs a pass drains: the Planner's `plan`, then an event for every plan
it published, every want an intention walks that the present now meets, and every step about to be
taken that the present no longer admits; then whether it keeps the agent alive. An intention that
ends is heard, and the next pass comes at once. What it answers is its Planner.

WHAT KEEPS AN AGENT RUNNING, PLANNING'S PART. A desire asks at every instant, so an agent holding
one is held for good. A want is one-shot: when none stands and none is walked, planning lets go,
`met`; when some stand, nothing walks them and no search was cut short, nothing this agent holds
reaches them — said in the log and as a metric by desire — and an agent holding no desire lets go,
`unreachable`. A search the budget cut short asks for the next pass at once.
"""

from __future__ import annotations

import logging

from agent import metrics
from agent.events import INTENTION_RESOLVED, MET, PLAN_PUBLISHED, STEP_BLOCKED, UNREACHABLE, WANT_REACHED
from agent.ontology import local_of

from .metrics import UNREACHED
from .planner import Planner

log = logging.getLogger("planning")


def start(runtime) -> Planner:
    """Plan every pass, say what was published, reached and blocked, and hold the agent while
    something is wanted; hear an intention end."""
    planner = Planner(runtime.beliefs, runtime.id, **({"budget": runtime.budget} if runtime.budget else {}))

    def plan():
        written = planner.plan(runtime.now)
        for plan_, want in planner.handed:
            runtime.emit(PLAN_PUBLISHED, plan=plan_, want=want)
        for want in planner.reached:
            runtime.emit(WANT_REACHED, want=want)
        for step in planner.blocked:
            runtime.emit(STEP_BLOCKED, step=step)
        _keep(runtime, planner)
        runtime.lap("plan")
        return written

    runtime.every(0, plan)
    runtime.listen(INTENTION_RESOLVED, lambda **ended: runtime.again() or ())
    runtime.gauge(planner.gauges)
    return planner


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
