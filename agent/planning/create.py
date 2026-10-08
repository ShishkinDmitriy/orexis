"""`create`: the planning package's part (a-package-starts-itself) — its Planner, which says what
happened by its own signals, each carrying an event of `events.py`: `plan_published`,
`want_reached`, `step_blocked`, `reconsidered`, `want_unreachable`, and — made only where heard —
`searched`, `planned`, `rerooted`, `imagined`.

LINKED, it connects those signals to what lies beneath it — the executor adopts a plan published,
ends an unbegun intention whose want is reached, ends one whose next step is blocked, ends one a
reconsideration replaced after its step in flight — and hears two of the executor's: `taking`, a
head about to be handed to its taker, which the Planner checks against the present and says blocked
where the present no longer admits it (#916), and `intention_resolved`, asking for the next pass at once. STARTED, it plans every pass,
after the jobs a pass drains, and holds the agent while something is wanted.

WHAT KEEPS AN AGENT RUNNING, PLANNING'S PART. A desire asks at every instant, so an agent holding
one is held for good. A want is one-shot: when none stands and none is walked, planning lets go,
`met`; when some stand, nothing walks them and no search was cut short, nothing this agent holds
reaches them — said in the log and by `want_unreachable` — and an agent holding no desire lets go,
`unreachable`. A search the budget cut short asks for the next pass at once.
"""

from __future__ import annotations

import logging

from agent.lifecycle import MET, UNREACHABLE
from agent.ontology import local_of

from .planner import Planner

log = logging.getLogger("planning")


class _Planning:
    def __init__(self, runtime):
        #  THE BUDGET IS THE AGENT'S STANCE, read by the Planner off the self graph, unless whoever
        #  made the runtime handed one — a test sizing a search; the process's `main` hands none.
        self.planner = Planner(runtime.beliefs, runtime.id, budget=runtime.budget)
        self.runtime = runtime

    def link(self, parts) -> None:
        execution = parts.get("execution")
        if execution is None:
            return
        executor = execution.executor
        self.planner.plan_published.connect(lambda published: executor.adopt(published.plan, published.want,
                                                                              desire=published.desire))
        self.planner.want_reached.connect(lambda reached: executor.end_for(reached.want, "reached"))
        self.planner.step_blocked.connect(lambda blocked: executor.end_at(blocked.step, "failed"))
        executor.taking.connect(lambda taking: self.planner.check(taking.step, taking.at))
        self.planner.reconsidered.connect(lambda reconsidered: executor.supersede_after(reconsidered.step))
        executor.intention_resolved.connect(lambda ended: self.runtime.again())

    def start(self, runtime) -> None:
        def plan():
            written = self.planner.plan(runtime.now)
            written += _keep(runtime, self.planner)
            runtime.lap("plan")
            return written
        runtime.every(0, plan)


def create(runtime) -> _Planning:
    """The planning package's part: its Planner, to plan every pass once started."""
    return _Planning(runtime)


def _keep(runtime, planner: Planner) -> list[str]:
    """Hold the agent, or let it go and say how the wanting ended; what was written in saying so."""
    standing, walking = planner.standing(runtime.now), planner.walking()
    desire = planner.holds_a_desire()
    if not standing and not walking:
        if desire:
            runtime.hold(planner)
        else:
            runtime.release(planner, MET)
        return []
    if walking:
        runtime.hold(planner)
        return []
    if planner.exhausted():
        runtime.again()                     # the budget cut a search short; the next pass continues it
        runtime.hold(planner)
        return []
    log.error("%s: %d want(s) stand and nothing this agent holds reaches them: %s",
              runtime.id, len(standing), ", ".join(local_of(w) for w in standing))
    written = planner.unreachable(standing)
    if desire:
        runtime.hold(planner)
    else:
        runtime.release(planner, UNREACHABLE)
    return written
