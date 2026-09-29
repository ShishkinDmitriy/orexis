"""`start`: what the execution package does once the runtime starts it (a-package-starts-itself) —
it adopts every plan planning publishes, or absorbs it by its patience; it walks what is due every
pass, after planning; it ends an intention whose want planning says is reached, or whose next step
planning says can no longer be taken; and it tells the runtime of every world it writes and every
intention that ends. A step is taken by its action's implementation: a command emitted for the
transport reaching the device, a saying emitted for speech to believe and tell. What it answers
is its executor.
"""

from __future__ import annotations

import pyoxigraph as ox

from agent.events import COMMANDED, INTENTION_RESOLVED, PLAN_PUBLISHED, SAID, STEP_BLOCKED, WANT_REACHED

from . import metrics
from .command import command
from .executor import Executor
from .implementation import COMMAND, SAYING, operations
from .says import says


def start(runtime) -> Executor:
    """Adopt what is published, walk what is due, end what planning says is over, and take each
    step by what its action's implementation holds."""
    def take(said: dict, intention: str) -> None:
        #  ORDER BY ORDER, so a later order is made from the present the earlier ones left: every
        #  event is answered at once, on this thread, before the next order is asked.
        orders = sorted({op.order for op in operations(runtime.beliefs, said.get("fills") or "")
                         if op.kind in (COMMAND, SAYING)})
        if not orders or not (runtime.listened(COMMANDED) or runtime.listened(SAID)):
            executor.say(said, intention)           # nothing reaches the world: as the executor would alone
            return
        for order in orders:
            for actuator, payload in command(runtime.beliefs, said, runtime.me, order=order):
                runtime.emit(COMMANDED, actuator=actuator, payload=payload)
            for agents, document in says(runtime.beliefs, said, runtime.me, order=order):
                runtime.emit(SAID, document=document, to=agents)

    executor = Executor(runtime.beliefs, runtime.id, runtime.intentions, take=take,
                        on_write=lambda graph: runtime.wrote([graph]),
                        on_resolve=lambda intention, want, outcome: runtime.emit(
                            INTENTION_RESOLVED, intention=intention, want=want, outcome=outcome))

    def walk():
        if executor.walk(runtime.now):
            runtime.again()                         # a step taken may make the next due at once
        runtime.lap("execute")
        return []

    runtime.listen(PLAN_PUBLISHED, lambda plan, want: executor.adopt(plan, want))
    runtime.listen(WANT_REACHED, lambda want: executor.end_for(want, "reached"))
    runtime.listen(STEP_BLOCKED, lambda step: executor.end_at(step, "failed"))
    runtime.every(0, walk)
    runtime.gauge(lambda: metrics.gauges(executor.intentions))
    return executor
