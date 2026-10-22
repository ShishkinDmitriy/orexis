"""`create`: coordination's part (a-package-starts-itself). Linked, it holds speech's part, through which it says
what it asks and answers, as a step's saying does. Started, it mints the agent's secret where it holds none;
answers every question heard as it arrives; concludes its conflicts and lays what it yields to as each question
or answer arrives, so the next pass plans and takes its steps against the peer's latest word and not the one
before it; and every pass asks the peers in range, concludes and lays again — after planning and execution, so
what it says of its future is what the pass left walking.
"""

from __future__ import annotations

import logging

from agent.ontology import local_of

from .answer import answer
from .ask import ask
from .conclude import conclude
from .lay import lay
from .mint import mint
from .ontology import ANSWER_GRAPH, QUESTION_GRAPH

log = logging.getLogger("coordination")


class _Coordination:
    def __init__(self, runtime):
        self.runtime = runtime
        self.speech = None

    def link(self, parts) -> None:
        self.speech = parts.get("speech")

    def start(self, runtime) -> None:
        runtime.wrote(mint(runtime.beliefs, runtime.me))
        runtime.on(QUESTION_GRAPH, self._heard)
        runtime.on(ANSWER_GRAPH, lambda graph: self._yield())
        runtime.every(0, self._pass)

    def _say(self, peer: str, document) -> list[str]:
        if self.speech is None:
            return []
        log.info("%s: says %s to %s", local_of(self.runtime.me),
                 ", ".join(g.value.split("/coordination/")[-1] for g in document.named_graphs()), local_of(peer))
        return self.speech.say(document, [peer])

    def _heard(self, graph: str) -> list[str]:
        said = answer(self.runtime.beliefs, self.runtime.me, graph, self.runtime.now)
        return (self._say(*said) if said else []) + self._yield()

    def _yield(self) -> list[str]:
        runtime = self.runtime
        return conclude(runtime.beliefs, runtime.me, runtime.now) + lay(runtime.beliefs, runtime.me, runtime.now)

    def _pass(self) -> list[str]:
        runtime = self.runtime
        written = []
        for peer, document in ask(runtime.beliefs, runtime.me, runtime.now):
            written += self._say(peer, document)
        return written + self._yield()


def create(runtime) -> _Coordination:
    """Coordination's part: what asks, answers and yields."""
    return _Coordination(runtime)
