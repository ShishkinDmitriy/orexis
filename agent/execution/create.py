"""`create`: the execution package's part (a-package-starts-itself) — its executor, which says what
happened by its own signals, each carrying an event of `events.py`: `intention_resolved`,
`commanded`, `said`, and — made only where heard — `step_taken`, `step_answered`, `walked`.

LINKED, it connects `commanded` to every transport — a part that takes a `command` — and `said` to speech — what lies beneath it — and
hears the deliberator's `revised`: where a source revised is a state graph, or the transitions an
arrival triggered changed one, the present changed, so the world may have answered a step, and a walk
is queued; a prediction or a committed step revised is not the present, and answers no step. What
a sensor said is no word of this package's (#944): its arrival changes the present by the
transitions it triggers, which the deliberator says. STARTED, it walks what is due every pass, after planning.
A step is taken by its action's implementation, order by order: each command emitted, each saying
emitted, and what they wrote said before the next order is asked, so a later order is made from the
present the earlier ones left.
"""

from __future__ import annotations

from agent.ontology import STATE, local_of
from agent.store import Raw, catalogue_of, rows

from .command import command
from .events import Commanded, Said
from .executor import Executor
from .implementation import COMMAND, SAYING, operations
from .says import says


#  WHETHER ANY OF SOME GRAPHS IS THE PRESENT: a state graph, by the catalogue.
_PRESENT_Q = "SELECT ?g WHERE { GRAPH $cat { VALUES ?g { $revised } ?g a $state } } LIMIT 1"


class _Execution:
    def __init__(self, runtime):
        self.runtime = runtime
        self._queued, self._walked_at, self._since = False, None, -1
        self.executor = Executor(runtime.beliefs, runtime.id, runtime.intentions, take=self._take,
                                 on_write=lambda graph: runtime.wrote([graph]))

    def link(self, parts) -> None:
        for part in parts.values():
            if callable(getattr(part, "command", None)):         # a transport: what sends a command
                self.executor.commanded.connect(lambda c, send=part.command: send(c.actuator, c.payload))
        speech = parts.get("speech")
        if speech is not None:
            self.executor.said.connect(lambda said: speech.say(said.document, said.to))
        belief = parts.get("belief")
        if belief is not None:
            belief.deliberator.revised.connect(
                lambda revised: self._walk_soon() if revised.changed or self._present(revised.graphs) else None)

    def _present(self, graphs) -> bool:
        """Whether any of `graphs` is a state graph — the present, which alone answers a step. A
        prediction revised, or a committed step the executor itself wrote, is not: a walk on those would
        read the clock for nothing, and a read of the clock is a tick in a test. An arrival whose
        transitions changed the state — what a sensor said, among them (#944) — the deliberator says
        by the state graphs it changed, heard beside this."""
        cat = catalogue_of(self.runtime.beliefs)
        return bool(graphs) and cat is not None and bool(rows(
            self.runtime.beliefs, _PRESENT_Q, (), cat=Raw(f"<{cat}>"), state=STATE,
            revised=Raw(" ".join(f"<{g}>" for g in graphs))))

    def _walk_soon(self) -> None:
        """Queue a walk, once: the present changed, and however many revisions say so before it runs,
        one walk answers them all."""
        if not self._queued:
            self._queued = True
            self.runtime.submit(self._walk)

    def start(self, runtime) -> None:
        runtime.every(0, self._pass)

    def _pass(self):
        """The walk a pass asks for, after planning: skipped where this pass walked already and nothing
        was adopted or ended since, since a walk at the same instant over the same intentions finds
        nothing new. THE PASS'S LAP IS MARKED HERE AND ONLY HERE: a lap is from the last mark, so a
        walk a revision queued, run among the drain's jobs, marked `execute` over the sensing and
        revision before it and the pass's `drain` read nought while two readings were being sensed."""
        if not (self._walked_at == self.runtime.now and self._since == len(self.executor.intentions)):
            self._walk()
        self.runtime.lap("execute")
        return []

    def _walk(self):
        self._queued = False
        if self.executor.walk(self.runtime.now):
            self.runtime.again()                    # a step taken may make the next due at once
        self._walked_at, self._since = self.runtime.now, len(self.executor.intentions)
        return []

    def _take(self, said: dict, intention: str) -> None:
        runtime, executor = self.runtime, self.executor
        orders = sorted({op.order for op in operations(runtime.beliefs, said.get("fills") or "")
                         if op.kind in (COMMAND, SAYING)})
        if not orders or not (executor.commanded.connected or executor.said.connected):
            executor.say(said, intention)           # nothing reaches the world: as the executor would alone
            return
        commanding = {op.order for op in operations(runtime.beliefs, said.get("fills") or "") if op.kind == COMMAND}
        for order in orders:
            sent = command(runtime.beliefs, said, order=order)
            #  A COMMAND THAT ANSWERS NOTHING IS A STEP NOT TAKEN (#869): the present held nothing it
            #  sizes from — a reading past its period, say — so nothing went out, and recording the
            #  step taken would have the intention wait out its patience as though the device had run.
            if order in commanding and not sent:
                raise LookupError(f"{local_of(said['fills'])}'s command answered nothing in the present")
            for actuator, payload in sent:
                runtime.wrote(executor.commanded.emit(Commanded(actuator, payload)))
            for agents, document in says(runtime.beliefs, said, order=order):
                runtime.wrote(executor.said.emit(Said(document, tuple(agents))))


def create(runtime) -> _Execution:
    """The execution package's part: its executor, to adopt and walk once linked and started."""
    return _Execution(runtime)
