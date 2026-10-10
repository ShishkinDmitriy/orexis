"""`create`: the prediction package's part, and what it does once started (a-package-starts-itself) —
it answers every percept and every belief a job writes. A percept holding a node some sensor made —
a reading, of the kernel's `orexis:PerceptGraph` kind — by rewriting that sensor's predictions
(`predict`); a belief holding no sensor's node — a step the executor committed to, a document a peer
said — by rewriting every key's, since what a drift reads at an instant may have changed and the
package cannot tell for which key. It hears of the graph through the runtime, by kind, and knows no
package that wrote it; a graph closed early is a belief written too, since its period changed, and
is heard the same way.
"""

from __future__ import annotations

from agent.ontology import BELIEF, PERCEPT
from agent.store import graphs_of, rows

from .predict import predict

#  WHICH SENSORS MADE WHAT A GRAPH HOLDS — none for a silence, a peer's word or a committed step.
_MADE_BY_Q = "SELECT DISTINCT ?sensor WHERE { GRAPH $g { ?o sosa:madeBySensor ?sensor } } ORDER BY ?sensor"

#  EVERY SENSOR WITH A PERCEPT IN HAND: the keys a prediction stands for.
_OBSERVED_BY_Q = "SELECT DISTINCT ?sensor WHERE { ?o sosa:madeBySensor ?sensor } ORDER BY ?sensor"


class _Prediction:
    def start(self, runtime) -> None:
        def predicted(graph: str) -> list[str]:
            sensors = [r["sensor"] for r in rows(runtime.beliefs, _MADE_BY_Q, (), g=graph)]
            if not sensors:
                sensors = [r["sensor"] for r in rows(runtime.beliefs, _OBSERVED_BY_Q, graphs_of(runtime.beliefs, PERCEPT))]
            return [written for sensor in sensors
                    for written in predict(runtime.beliefs, runtime.me, sensor, now=runtime.now)]
        runtime.on(PERCEPT, predicted)
        runtime.on(BELIEF, predicted)


def create(runtime) -> _Prediction:
    """The prediction package's part: once started, it rewrites a sensor's predictions whenever a
    percept it made is written, and every key's whenever any belief is."""
    return _Prediction()
