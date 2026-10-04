"""`create`: sensing's part, and what it does of its own accord once started (a-package-starts-itself) —
it asks, every `EVERY_S` of the one timeline, which readings have fallen due and says which
sensors have gone silent (`missed`), whether or not anything arrived (#843). What a transport hands
it, `received` writes; nothing else here is called.

WHAT SENSING SAYS HAPPENED, by the part's own signals, each carrying an event of `events.py` and made
only where heard: `observed`, an observation graph written — heard as it is written, whoever wrote
it, and said with what the rules concluded of it, which is written by then, since belief's part
starts before any package beyond the mind and so hears the graph first; and with how long after the
reading it replaced it came, which the part remembers per sensor since the reading replaced is gone
by then — and `silence`, how many sensors are said silent after each ask.
"""

from __future__ import annotations

from datetime import datetime

from agent.lifecycle import Signal
from agent.store import Raw, catalogue_of, revisions_of, rows

from .cadence import cadence_of
from .events import Observed, Silence, tag_of
from .missed import missed
from .ontology import OBSERVATION_GRAPH

#  HOW OFTEN SENSING ASKS WHAT HAS FALLEN DUE, in seconds of the one timeline.
EVERY_S = 60.0

#  WHAT AN OBSERVATION IS — what the sensor gave, in the graph written, and what the rules concluded
#  of it, in its revisions. Its sensor and its subject go by the local names of their IRIs
#  (`events.tag_of`), never by a stated id a world may leave out (#885).
_OBSERVED_Q = """
SELECT ?sensor ?feature ?property ?value ?t WHERE {
  ?o sosa:madeBySensor ?sensor ; sosa:resultTime ?t ; sosa:hasFeatureOfInterest ?feature ;
     sosa:observedProperty ?property ; sosa:hasSimpleResult ?value } LIMIT 1"""

#  THE SENSORS SAID SILENT NOW: `sensing:silentSince` in a state graph of the agent's.
_SILENT_Q = """
SELECT (COUNT(DISTINCT ?sensor) AS ?silent)
WHERE { GRAPH $cat { ?g a orexis:StateGraph } GRAPH ?g { ?sensor sensing:silentSince ?since } }"""


class _Sensing:
    def __init__(self, runtime):
        self.runtime = runtime
        self.observed = Signal("observed")
        self.silence = Signal("silence")
        self._last: dict[str, datetime] = {}          # sensor -> when its last reading was made

    def start(self, runtime) -> None:
        def ask():
            missed(runtime.beliefs, runtime.me, runtime.now)
            return self.silence.emit(self._silence()) if self.silence.connected else []
        runtime.every(EVERY_S, ask)
        if self.observed.connected:
            runtime.on(OBSERVATION_GRAPH, self._observation)

    def _observation(self, graph: str) -> list[str]:
        """Say the observation `graph` holds, with how long after the last of its sensor it came."""
        beliefs = self.runtime.beliefs
        found = rows(beliefs, _OBSERVED_Q, [graph, *revisions_of(beliefs, graph)])
        if not found:
            return []
        o = found[0]
        at = datetime.fromisoformat(o["t"])
        before = self._last.get(o["sensor"])
        self._last[o["sensor"]] = at
        cadence = cadence_of(beliefs, o["sensor"])
        return self.observed.emit(Observed(
            observed_property=o["property"], value=round(float(o["value"]), 6), at=at,
            sensor=tag_of(o["sensor"]), sensor_id=tag_of(o["sensor"]), feature_id=tag_of(o["feature"]),
            interval_s=round((at - before).total_seconds(), 3) if before is not None else None,
            cadence_s=float(cadence) if cadence is not None else None))

    def _silence(self) -> Silence:
        found = rows(self.runtime.beliefs, _SILENT_Q, (), cat=Raw(f"<{catalogue_of(self.runtime.beliefs)}>"))
        return Silence(silent=int(found[0].get("silent") or 0) if found else 0)


def create(runtime) -> _Sensing:
    """Sensing's part: once started, it asks after what has fallen due every `EVERY_S`, and says an
    observation written and the silence, where heard."""
    return _Sensing(runtime)
