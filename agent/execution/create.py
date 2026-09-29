"""`create`: the execution package's part (a-package-starts-itself) — its executor, which says what
happened by its own signals: `intention_resolved`, `commanded`, `said`.

LINKED, it connects `commanded` to every transport — a part that takes a `command` — and `said` to speech — what lies beneath it — and
hears the deliberator's `revised`: the present changed, so the world may have answered a step, and
a walk is queued. STARTED, it walks what is due every pass, after planning, and reports its gauges.
A step is taken by its action's implementation, order by order: each command emitted, each saying
emitted, and what they wrote said before the next order is asked, so a later order is made from the
present the earlier ones left.
"""

from __future__ import annotations

from . import metrics
from .command import command
from .executor import Executor
from .implementation import COMMAND, SAYING, operations
from .says import says


class _Execution:
    def __init__(self, runtime):
        self.runtime = runtime
        self._queued, self._walked_at, self._since = False, None, -1
        self.executor = Executor(runtime.beliefs, runtime.id, runtime.intentions, take=self._take,
                                 on_write=lambda graph: runtime.wrote([graph]))

    def link(self, parts) -> None:
        for part in parts.values():
            if callable(getattr(part, "command", None)):         # a transport: what sends a command
                self.executor.commanded.connect(part.command)
        speech = parts.get("speech")
        if speech is not None:
            self.executor.said.connect(speech.say)
        belief = parts.get("belief")
        if belief is not None:
            belief.deliberator.revised.connect(lambda graphs: self._walk_soon())

    def _walk_soon(self) -> None:
        """Queue a walk, once: the present changed, and however many revisions say so before it runs,
        one walk answers them all."""
        if not self._queued:
            self._queued = True
            self.runtime.submit(self._walk)

    def start(self, runtime) -> None:
        runtime.every(0, self._pass)
        runtime.gauge(lambda: metrics.gauges(self.executor.intentions))

    def _pass(self):
        """The walk a pass asks for, after planning: skipped where this pass walked already and nothing
        was adopted or ended since, since a walk at the same instant over the same intentions finds
        nothing new."""
        if self._walked_at == self.runtime.now and self._since == len(self.executor.intentions):
            self.runtime.lap("execute")
            return []
        return self._walk()

    def _walk(self):
        self._queued = False
        if self.executor.walk(self.runtime.now):
            self.runtime.again()                    # a step taken may make the next due at once
        self._walked_at, self._since = self.runtime.now, len(self.executor.intentions)
        self.runtime.lap("execute")
        return []

    def _take(self, said: dict, intention: str) -> None:
        runtime, executor = self.runtime, self.executor
        orders = sorted({op.order for op in operations(runtime.beliefs, said.get("fills") or "")
                         if op.kind in (COMMAND, SAYING)})
        if not orders or not (executor.commanded.connected or executor.said.connected):
            executor.say(said, intention)           # nothing reaches the world: as the executor would alone
            return
        for order in orders:
            for actuator, payload in command(runtime.beliefs, said, runtime.me, order=order):
                runtime.wrote(executor.commanded.emit(actuator=actuator, payload=payload))
            for agents, document in says(runtime.beliefs, said, runtime.me, order=order):
                runtime.wrote(executor.said.emit(document=document, to=agents))


def create(runtime) -> _Execution:
    """The execution package's part: its executor, to adopt and walk once linked and started."""
    return _Execution(runtime)
