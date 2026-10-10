"""`create`: sensing's part, and what it does of its own accord once started (a-package-starts-itself) —
it asks, every `EVERY_S` of the one timeline, which readings have fallen due and says which
sensors have gone silent (`missed`), whether or not anything arrived (#843). What a transport hands
it, `received` writes. What the agent comes to hold true of a subject from a percept is no
part of sensing's: a domain's transition, triggered by the percept arriving, makes it, and the
belief package applies it (a-transition-changes-the-state-and-an-inference-only-concludes).

WHAT SENSING SAYS HAPPENED, by the part's own signals, each carrying an event of `events.py` and made
only where heard: `observed`, an observation graph written — heard as it is written, whoever wrote
it, and said with what the rules concluded of it, which is written by then, since an observer is a
deliberator too and belief's part starts first in a pass (`agent.runtime.PASS`), so it hears the
graph first; and with how long after the percept before it it came, read off that percept, which
is kept (`sensing:previous`, #944) — `silence`, how many sensors are said silent after each ask — and
`doubted`, which sensors are said silent or stuck after each ask, one event per sensor doubted, and
one saying neither for a sensor doubted at the last ask and no longer, so the series' last word on it
in a window is that it is fine (#894). Silent is a state graph `missed` writes; stuck is what
sensing's rule concluded of the latest percept, read where that percept holds now.
"""

from __future__ import annotations

from datetime import datetime

from agent.lifecycle import Signal
from agent.ontology import PERCEPT
from agent.store import Raw, catalogue_of, graphs_of, revisions_of, rows

from .cadence import cadence_of
from .events import Doubted, Observed, Silence, tag_of
from .missed import missed
from .ontology import OBSERVATION_GRAPH

#  HOW OFTEN SENSING ASKS WHAT HAS FALLEN DUE, in seconds of the one timeline.
EVERY_S = 60.0

#  WHAT AN OBSERVATION IS — what the sensor gave, in the graph written, and what the rules concluded
#  of it, in its revisions — with the percept before it. Its sensor and its subject go by the local
#  names of their IRIs (`events.tag_of`), never by a stated id a world may leave out (#885). The raw
#  number rides on the point beside the reading, where the observation has one.
_OBSERVED_Q = """
SELECT ?sensor ?feature ?property ?value ?t ?raw ?previous WHERE {
  ?o sosa:madeBySensor ?sensor ; sosa:resultTime ?t ; sosa:hasFeatureOfInterest ?feature ;
     sosa:observedProperty ?property ; sosa:hasSimpleResult ?value
  OPTIONAL { ?o sensing:rawResult ?raw } OPTIONAL { ?o sensing:previous ?previous } } LIMIT 1"""

#  WHEN THE PERCEPT BEFORE IT WAS MADE, read where sensing keeps it.
_MADE_Q = "SELECT ?t WHERE { $percept sosa:resultTime ?t } LIMIT 1"

#  THE SENSORS SAID SILENT NOW: `sensing:silentSince` in a state graph of the agent's.
_SILENT_Q = """
SELECT (COUNT(DISTINCT ?sensor) AS ?silent)
WHERE { GRAPH $cat { ?g a orexis:StateGraph } GRAPH ?g { ?sensor sensing:silentSince ?since } }"""

#  THE SENSORS SAID SILENT NOW, each: the row in a state graph of the agent's.
_SILENT_EACH_Q = """
SELECT DISTINCT ?sensor WHERE { GRAPH $cat { ?g a orexis:StateGraph } GRAPH ?g { ?sensor sensing:silentSince ?since } }"""

#  THE SENSORS STUCK NOW: what sensing's rule concluded of the percept holding now.
_STUCK_Q = "SELECT DISTINCT ?sensor WHERE { ?sensor sensing:stuckOn ?number }"


class _Sensing:
    def __init__(self, runtime):
        self.runtime = runtime
        self.observed = Signal("observed")
        self.silence = Signal("silence")
        self.doubted = Signal("doubted")
        self._doubts: set[str] = set()                # the sensors doubted at the last ask

    def start(self, runtime) -> None:
        def ask():
            missed(runtime.beliefs, runtime.me, runtime.now)
            written = self.silence.emit(self._silence()) if self.silence.connected else []
            if self.doubted.connected:
                for event in self._doubted(runtime.now):
                    written += self.doubted.emit(event)
            return written
        runtime.every(EVERY_S, ask)
        if self.observed.connected:
            runtime.on(OBSERVATION_GRAPH, self._observation)

    def _observation(self, graph: str) -> list[str]:
        """Say the observation `graph` holds, with how long after the percept before it it came."""
        beliefs = self.runtime.beliefs
        found = rows(beliefs, _OBSERVED_Q, [graph, *revisions_of(beliefs, graph)])
        if not found:
            return []
        o = found[0]
        at = datetime.fromisoformat(o["t"])
        made = rows(beliefs, _MADE_Q, graphs_of(beliefs, OBSERVATION_GRAPH), percept=o["previous"]) if o.get("previous") else []
        before = datetime.fromisoformat(made[0]["t"]) if made else None
        cadence = cadence_of(beliefs, o["sensor"])
        return self.observed.emit(Observed(
            observed_property=o["property"], value=round(float(o["value"]), 6), at=at,
            sensor=tag_of(o["sensor"]), sensor_id=tag_of(o["sensor"]), feature_id=tag_of(o["feature"]),
            interval_s=round((at - before).total_seconds(), 3) if before is not None else None,
            cadence_s=float(cadence) if cadence is not None else None,
            raw=round(float(o["raw"]), 6) if o.get("raw") is not None else None))

    def _silence(self) -> Silence:
        found = rows(self.runtime.beliefs, _SILENT_Q, (), cat=Raw(f"<{catalogue_of(self.runtime.beliefs)}>"))
        return Silence(silent=int(found[0].get("silent") or 0) if found else 0)

    def _doubted(self, now: datetime) -> list[Doubted]:
        """Which sensors are doubted at `now`, and how; and, saying neither, each doubted at the last
        ask and no longer — so the last word in a window on a sensor that recovered is nought."""
        beliefs = self.runtime.beliefs
        silent = {r["sensor"] for r in rows(beliefs, _SILENT_EACH_Q, (), cat=Raw(f"<{catalogue_of(beliefs)}>"))}
        stuck = {r["sensor"] for r in rows(beliefs, _STUCK_Q, graphs_of(beliefs, PERCEPT, at=now, now=now))}
        said = [Doubted(sensor=tag_of(sensor), silent=int(sensor in silent), stuck=int(sensor in stuck))
                for sensor in sorted(silent | stuck)]
        said += [Doubted(sensor=tag_of(sensor)) for sensor in sorted(self._doubts - (silent | stuck))]
        self._doubts = silent | stuck
        return said


def create(runtime) -> _Sensing:
    """Sensing's part: once started, it asks after what has fallen due every `EVERY_S`, and says an
    observation written and the silence, where heard."""
    return _Sensing(runtime)
