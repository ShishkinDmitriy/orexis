"""`create`: the belief package's part (a-package-starts-itself) — its deliberator, which says, by
its own `revised` signal, what a pass revised (`events.py`). Started, it revises what the world authored
as its state, once, so a fact concluded from where things stand is believed from the first pass; then
every belief and every prediction written, as it is written, beside what the world states and nothing
else, and applies the transitions each triggers. Belief links to nothing: nothing it needs lies beneath
it.

WHAT STANDS BESIDE A GRAPH REVISED is the public graphs alone. Never another testimony: handed
everything believed, the first of two readings arriving together took the second's side into its own
revision, where the second's next reading never reached it. And not the agent's own state: an
inference concludes of its source and the world, and what the state was before an arrival is a
premise of a TRANSITION, which `trigger` hands the state it reads itself
(a-transition-changes-the-state-and-an-inference-only-concludes).

A PACKAGE ABOVE HANDS ITS OWN GRAPHS IN (`revise`), as a runner that prepares its target: what it
writes that is no belief — sensing's observations (#944) — this part never hears, since it knows no
kind of theirs, and the package that writes them hands each here as it arrives, with the kind its
revisions are to be. The deliberator's one queue takes it among the beliefs and the predictions, so
arrivals are transitioned on in the order they came whoever handed them.
"""

from __future__ import annotations

from agent import clock
from agent.ontology import BELIEF, PREDICTION, PUBLIC, STATE
from agent.store import graphs_of, revisions_of

from .deliberator import Deliberator
from .ontology import REVISION_GRAPH


class _Belief:
    def __init__(self, runtime):
        self.runtime = runtime
        self.deliberator = Deliberator(runtime.beliefs, runtime.id)

    def revise(self, graphs, *, kind: str = BELIEF) -> list[str]:
        """Revise `graphs` beside the public graphs and apply the transitions each triggers, now — their
        revisions classified `kind`: a belief's are beliefs, and a package above hands the kind its
        own graphs' revisions are. Writes nothing a reader hears of, so it answers nothing."""
        runtime = self.runtime
        public = graphs_of(runtime.beliefs, PUBLIC)
        for graph in graphs:
            self.deliberator.changed(graph, read=public, kind=kind)
        self.deliberator.deliberate(runtime.now or clock.now())
        return []

    def start(self, runtime) -> None:
        revisions = set(graphs_of(runtime.beliefs, REVISION_GRAPH))
        self.revise([g for g in graphs_of(runtime.beliefs, STATE)
                     if g not in revisions and not revisions_of(runtime.beliefs, g)])
        runtime.on(BELIEF, lambda graph: self.revise([graph]))
        runtime.on(PREDICTION, lambda graph: self.revise([graph]))


def create(runtime) -> _Belief:
    """The belief package's part: its deliberator, to revise what is written once started, and what a
    package above hands it."""
    return _Belief(runtime)
