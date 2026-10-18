"""`create`: the prediction package's part, and what it does once started (a-package-starts-itself) —
it answers every percept and every belief a job writes by one walk over the keys, in the order their
drifts read each other (`order`, #996). A percept holding a node some sensor made — a reading, of
sensing's `sensing:ObservationGraph` kind, a word this package may speak from above sensing (#944) —
rewrites that sensor's key and every key whose drifts read it, transitively; a belief holding no
sensor's node — a step the executor committed to, a document a peer said — rewrites every key's, since
what a drift reads at an instant may have changed and the package cannot tell for which key. Each key
is rewritten ONCE an arrival, and a key read by another is written before the other is asked, so the
soil's drying reads the air as this agent foresees it. It hears of the graph through the runtime, by
kind, and knows no package that wrote it; a graph closed early is a belief written too, since its
period changed, and is heard the same way.

WHAT THIS PART WROTE IS ITS OWN, AND IT ANSWERS NOTHING OF IT. The runtime says every graph a handler
wrote, and a prediction is a forecast of this agent's — a kind the runtime may one day hand to whoever
hears beliefs (#992). Heard as an arrival, each key's prediction would rewrite every key, without end;
so the part keeps the names of what it wrote and passes those over.
"""

from __future__ import annotations

from agent.ontology import BELIEF
from agent.store import graphs_of, rows

from .ontology import OBSERVATION_GRAPH
from .order import order
from .predict import predict

#  WHICH SENSORS MADE WHAT A GRAPH HOLDS — none for a silence, a peer's word or a committed step.
_MADE_BY_Q = "SELECT DISTINCT ?sensor WHERE { GRAPH $g { ?o sosa:madeBySensor ?sensor } } ORDER BY ?sensor"

#  EVERY SENSOR WITH A PERCEPT IN HAND AND THE PROPERTY IT OBSERVES: the keys a prediction stands for,
#  read over the percepts and what the rules concluded of them, where the property is.
_OBSERVED_BY_Q = "SELECT DISTINCT ?sensor ?property WHERE { ?o sosa:madeBySensor ?sensor ; sosa:observedProperty ?property } ORDER BY ?sensor"


class _Prediction:
    def __init__(self):
        self.own: set[str] = set()

    def start(self, runtime) -> None:
        def predicted(graph: str) -> list[str]:
            if graph in self.own:
                return []
            store = runtime.beliefs
            arrived = {r["sensor"] for r in rows(store, _MADE_BY_Q, (), g=graph)}
            keys: dict[str, str] = {}
            for r in rows(store, _OBSERVED_BY_Q, graphs_of(store, OBSERVATION_GRAPH)):
                keys.setdefault(r["sensor"], r["property"])
            after = {keys[s] for s in arrived if s in keys} if arrived else None
            written = []
            for prop in order(store, set(keys.values()), after=after):
                for sensor in sorted(s for s, p in keys.items() if p == prop):
                    written += predict(store, runtime.me, sensor, now=runtime.now)
            self.own.update(written)
            return written
        runtime.on(OBSERVATION_GRAPH, predicted)
        runtime.on(BELIEF, predicted)


def create(runtime) -> _Prediction:
    """The prediction package's part: once started, it walks the keys in the order their drifts read
    each other — a sensor's key and what depends on it whenever a percept it made is written, every
    key's whenever any belief is — and answers nothing of what it wrote itself."""
    return _Prediction()
