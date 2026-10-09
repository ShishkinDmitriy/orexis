"""`create`: the belief package's part (a-package-starts-itself) — its deliberator, which says, by
its own `revised` signal, what a pass revised (`events.py`). Started, it revises what the world authored
as its state, once, so a fact concluded from where things stand is believed from the first pass;
then every belief and every prediction written, as it is written, beside what the world states and
what the agent has itself concluded of the present, and nothing else. Belief links to nothing:
nothing it needs lies beneath it.

WHAT STANDS BESIDE A GRAPH REVISED is the public graphs and every state graph the agent DERIVED —
a conclusion it keeps about the present, such as the subject belief a rule judges the next
observation of its key beside (#944) — whatever their period, since the conclusion before is the
premise the next judgment needs. Never another testimony: handed everything believed, the first of
two readings arriving together took the second's side into its own revision, where the second's next
reading never reached it.
"""

from __future__ import annotations

from agent import clock
from agent.ontology import BELIEF, PREDICTION, PUBLIC, STATE
from agent.store import Raw, catalogue_of, graphs_of, revisions_of, rows

from .deliberator import Deliberator

#  EVERY STATE GRAPH THE AGENT DERIVED, of any period: what it concluded of the present and keeps.
_CONCLUDED_Q = """
SELECT ?g WHERE { GRAPH $cat { ?g a orexis:StateGraph ; orexis:arrivedBy orexis:Derived } } ORDER BY ?g"""


class _Belief:
    def __init__(self, runtime):
        self.deliberator = Deliberator(runtime.beliefs, runtime.id)

    def start(self, runtime) -> None:
        def revise(graphs):
            beside = [*graphs_of(runtime.beliefs, PUBLIC), *_concluded(runtime.beliefs)]
            for graph in graphs:
                self.deliberator.changed(graph, read=beside)
            self.deliberator.deliberate(runtime.now or clock.now())
            return []

        revise([g for g in graphs_of(runtime.beliefs, STATE) if not revisions_of(runtime.beliefs, g)])
        runtime.on(BELIEF, lambda graph: revise([graph]))
        runtime.on(PREDICTION, lambda graph: revise([graph]))


def _concluded(store) -> list[str]:
    """Every state graph `store` holds that the agent derived, whatever its period."""
    cat = catalogue_of(store)
    return [r["g"] for r in rows(store, _CONCLUDED_Q, (), cat=Raw(f"<{cat}>"))] if cat else []


def create(runtime) -> _Belief:
    """The belief package's part: its deliberator, to revise what is written once started."""
    return _Belief(runtime)
