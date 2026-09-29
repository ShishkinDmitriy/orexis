"""`start`: what the belief package does once the runtime starts it (a-package-starts-itself) — it
revises what the world authored as its state, once, so a fact concluded from where things stand
is believed from the first pass; then every belief and every prediction written, as it is written,
beside what the world states and nothing else; and it reports its gauges. What it answers is its
deliberator.
"""

from __future__ import annotations

from agent import clock
from agent.ontology import BELIEF, PREDICTION, PUBLIC, STATE
from agent.store import graphs_of, revisions_of

from . import metrics
from .deliberator import Deliberator


def start(runtime) -> Deliberator:
    """Revise the authored state, then every belief and prediction written; report the gauges."""
    deliberator = Deliberator(runtime.beliefs, runtime.id)

    def revise(graphs):
        public = graphs_of(runtime.beliefs, PUBLIC)
        for graph in graphs:
            deliberator.changed(graph, read=public)
        deliberator.deliberate(runtime.now or clock.now())
        return []

    revise([g for g in graphs_of(runtime.beliefs, STATE) if not revisions_of(runtime.beliefs, g)])
    runtime.on(BELIEF, lambda graph: revise([graph]))
    runtime.on(PREDICTION, lambda graph: revise([graph]))
    runtime.gauge(lambda: metrics.gauges(runtime.beliefs))
    return deliberator
