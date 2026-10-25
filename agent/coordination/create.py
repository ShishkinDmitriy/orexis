"""`create`: coordination's part (a-package-starts-itself). Linked, it holds speech's part, through which it says
what it asks and answers, as a step's saying does. Started, it mints the agent's secret where it holds none;
answers every question heard as it arrives; concludes its conflicts and lays what it yields to as each question
or answer arrives, so the next pass plans and takes its steps against the peer's latest word and not the one
before it; and every pass asks the peers in range, concludes and lays again — after planning and execution, so
what it says of its future is what the pass left walking.

LINKED, it holds planning's part too, where the agent plays a planner — a coordinator always does. A draw the
agent concludes it has WON asks the Planner to reopen the walking wants whose plans change a value on the key of
the constraint the draw was over: each was found while the draw stood undecided, yielding as both agents yield,
and nothing a belief makes impossible reopens a plan that has only been made slower than it need be — so without
it the winner kept its wait and the loser crossed first. Searched again from where its step in flight lands, with
the loser's untaken steps no longer laid, the winner's plan takes the way the draw gave it.

WHAT IT DID IS SAID, where anybody hears (`events`): the holdings each question it says carries, `asked`; and
whenever it concludes or lays, every conflict it holds and what it lays of each peer, said and foreseen —
each set said again only where it changed.
"""

from __future__ import annotations

import logging

import pyoxigraph as ox

from agent.lifecycle import Signal
from agent.ontology import local_of

from .answer import answer
from .ask import ask
from .conclude import _conflicts, _wins, conclude
from .events import ASKED, FORESEEN, SAID, Concluded, Held
from .holdings import _heard, _walking_over
from .lay import _laid, lay
from .mint import mint
from .ontology import ANSWER_GRAPH, COORDINATION, QUESTION_GRAPH

log = logging.getLogger("coordination")


class _Coordination:
    def __init__(self, runtime):
        self.runtime = runtime
        self.speech = None
        self.planning = None
        self.held = Signal("held")                        # holdings asked with, said and foreseen
        self.concluded = Signal("concluded")              # every conflict, as concluded
        self._said: dict = {}                             # what was last said of each, so a set is said where it changed

    def link(self, parts) -> None:
        self.speech = parts.get("speech")
        self.planning = parts.get("planning")

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
        if self.held.connected:
            for g in document.named_graphs():
                over = next(document.quads_for_pattern(None, ox.NamedNode(COORDINATION + "over"), None, g), None)
                if over is not None:
                    self._tell(Held(self.runtime.now, ASKED, peer, over.object.value, tuple(_heard(document, g.value))))
        return self.speech.say(document, [peer])

    def _tell(self, event) -> None:
        """Say `event` where what it says differs from what was last said of the same set."""
        key, said = ((event.origin, event.peer, event.constraint), event.holdings) if isinstance(event, Held) else ("conflicts", event.conflicts)
        if self._said.get(key) != said:
            self._said[key] = said
            (self.held if isinstance(event, Held) else self.concluded).emit(event)

    def _heard(self, graph: str) -> list[str]:
        said = answer(self.runtime.beliefs, self.runtime.me, graph, self.runtime.now)
        return (self._say(*said) if said else []) + self._yield()

    def _yield(self) -> list[str]:
        runtime = self.runtime
        before = _wins(runtime.beliefs, runtime.me)
        written = conclude(runtime.beliefs, runtime.me, runtime.now)
        if self.concluded.connected:
            self._tell(Concluded(runtime.now, tuple(_conflicts(runtime.beliefs, runtime.me))))
        won = {draw: constraint for draw, constraint in _wins(runtime.beliefs, runtime.me).items() if draw not in before}
        written += lay(runtime.beliefs, runtime.me, runtime.now)
        if self.held.connected:
            for (peer, constraint), (said, foreseen) in _laid(runtime.beliefs, runtime.me).items():
                self._tell(Held(runtime.now, SAID, peer, constraint, tuple(said)))
                self._tell(Held(runtime.now, FORESEEN, peer, constraint, tuple(foreseen)))
        wants = set().union(*(_walking_over(runtime.beliefs, constraint) for constraint in won.values()))
        if wants and self.planning is not None:
            log.info("%s: won a draw, so asks that %s be planned again", local_of(runtime.me),
                     ", ".join(local_of(w) for w in sorted(wants)))
            self.planning.planner.reopen(wants)
            runtime.again()
        return written

    def _pass(self) -> list[str]:
        runtime = self.runtime
        written = []
        for peer, document in ask(runtime.beliefs, runtime.me, runtime.now):
            written += self._say(peer, document)
        return written + self._yield()


def create(runtime) -> _Coordination:
    """Coordination's part: what asks, answers and yields."""
    return _Coordination(runtime)
