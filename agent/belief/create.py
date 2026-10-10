"""`create`: the belief package's part (a-package-starts-itself) — its deliberator, which says, by
its own `revised` signal, what a pass revised (`events.py`). Started, it revises what the world authored
as its state, and any percept nothing was concluded of, once, so a fact concluded from where things
stand is believed from the first pass; then every belief, every percept and every prediction written,
as it is written, beside what the world states and nothing else, and applies the transitions each
triggers. Belief links to nothing: nothing it needs lies beneath it.

WHAT STANDS BESIDE A GRAPH REVISED is the public graphs alone. Never another testimony: handed
everything believed, the first of two readings arriving together took the second's side into its own
revision, where the second's next reading never reached it. And not the agent's own state: an
inference concludes of its source and the world, and what the state was before an arrival is a
premise of a TRANSITION, which `trigger` hands the state it reads itself
(a-transition-changes-the-state-and-an-inference-only-concludes).

A PERCEPT IS HEARD BY ITS OWN KIND (#944): what a sensor said is no belief, so it is not among the
beliefs written, and is revised as it arrives all the same — what it is of and its quantity are the
rules' to conclude, and its arrival triggers the transitions that make the subject belief.
"""

from __future__ import annotations

from agent import clock
from agent.ontology import BELIEF, PERCEPT, PREDICTION, PUBLIC, STATE
from agent.store import graphs_of, revisions_of

from .deliberator import Deliberator
from .ontology import REVISION_GRAPH


class _Belief:
    def __init__(self, runtime):
        self.deliberator = Deliberator(runtime.beliefs, runtime.id)

    def start(self, runtime) -> None:
        def revise(graphs):
            public = graphs_of(runtime.beliefs, PUBLIC)
            for graph in graphs:
                self.deliberator.changed(graph, read=public)
            self.deliberator.deliberate(runtime.now or clock.now())
            return []

        revisions = set(graphs_of(runtime.beliefs, REVISION_GRAPH))
        revise([g for g in graphs_of(runtime.beliefs, STATE, PERCEPT)
                if g not in revisions and not revisions_of(runtime.beliefs, g)])
        runtime.on(BELIEF, lambda graph: revise([graph]))
        runtime.on(PERCEPT, lambda graph: revise([graph]))
        runtime.on(PREDICTION, lambda graph: revise([graph]))


def create(runtime) -> _Belief:
    """The belief package's part: its deliberator, to revise what is written once started."""
    return _Belief(runtime)
