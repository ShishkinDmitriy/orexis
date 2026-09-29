"""`create`: the prediction package's part, and what it does once started (a-package-starts-itself) —
it answers every observation a job writes, a graph of the kernel's `orexis:StateGraph` kind holding
a node some sensor made, by rewriting that sensor's predictions (`predict`). It hears of the
observation through the runtime, by kind, and knows no package that wrote it.
"""

from __future__ import annotations

from agent.ontology import STATE
from agent.store import rows

from .predict import predict

#  WHICH SENSORS MADE WHAT A GRAPH HOLDS — none for a silence or a peer's word.
_MADE_BY_Q = "SELECT DISTINCT ?sensor WHERE { GRAPH $g { ?o sosa:madeBySensor ?sensor } } ORDER BY ?sensor"


class _Prediction:
    def start(self, runtime) -> None:
        def predicted(graph: str) -> list[str]:
            return [written for r in rows(runtime.beliefs, _MADE_BY_Q, (), g=graph)
                    for written in predict(runtime.beliefs, runtime.me, r["sensor"], now=runtime.now)]
        runtime.on(STATE, predicted)


def create(runtime) -> _Prediction:
    """The prediction package's part: once started, it rewrites a sensor's predictions whenever an observation it made is written."""
    return _Prediction()
