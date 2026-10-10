"""`create`: sensing's part, and what it does of its own accord once started (a-package-starts-itself) —
it asks, every `EVERY_S` of the one timeline, which readings have fallen due and says which
sensors have gone silent (`missed`), whether or not anything arrived (#843). What a transport hands
it, `received` writes. What the agent comes to hold true of a subject from an observation is no
part of sensing's: a domain's transition, fired by the observation arriving, makes it, and the
belief package applies it (a-transition-changes-the-state-and-an-inference-only-concludes).

WHAT SENSING SAYS HAPPENED, by the part's own signals, each carrying an event of `events.py` and made
only where heard: `observed`, an observation graph written — heard as it is written, whoever wrote
it, and said with what the rules concluded of it, which is written by then, since an observer is a
deliberator too and belief's part starts first in a pass (`agent.runtime.PASS`), so it hears the
graph first; and with how long after the
reading it replaced it came, which the part remembers per sensor since the reading replaced is gone
by then — `silence`, how many sensors are said silent after each ask — and `doubted`, which sensors
are said silent or stuck after each ask, one event per sensor doubted, and one saying neither for a
sensor doubted at the last ask and no longer, so the series' last word on it in a window is that it
is fine (#894).
"""

from __future__ import annotations

from datetime import datetime

from agent.lifecycle import Signal
from agent.store import Raw, catalogue_of, revisions_of, rows

from .cadence import cadence_of
from .events import Doubted, Observed, Silence, tag_of
from .missed import missed
from .ontology import OBSERVATION_GRAPH, SILENT_SINCE, STUCK_SINCE

#  HOW OFTEN SENSING ASKS WHAT HAS FALLEN DUE, in seconds of the one timeline.
EVERY_S = 60.0

#  WHAT AN OBSERVATION IS — what the sensor gave, in the graph written, and what the rules concluded
#  of it, in its revisions. Its sensor and its subject go by the local names of their IRIs
#  (`events.tag_of`), never by a stated id a world may leave out (#885). The raw number rides on the
#  point beside the reading, where the observation has one.
_OBSERVED_Q = """
SELECT ?sensor ?feature ?property ?value ?t ?raw WHERE {
  ?o sosa:madeBySensor ?sensor ; sosa:resultTime ?t ; sosa:hasFeatureOfInterest ?feature ;
     sosa:observedProperty ?property ; sosa:hasSimpleResult ?value
  OPTIONAL { ?o sensing:rawResult ?raw } } LIMIT 1"""

#  THE SENSORS SAID SILENT NOW: `sensing:silentSince` in a state graph of the agent's.
_SILENT_Q = """
SELECT (COUNT(DISTINCT ?sensor) AS ?silent)
WHERE { GRAPH $cat { ?g a orexis:StateGraph } GRAPH ?g { ?sensor sensing:silentSince ?since } }"""

#  THE SENSORS DOUBTED NOW, and how: each `sensing:silentSince` or `sensing:stuckSince` row in a state
#  graph of the agent's.
_DOUBTED_Q = """
SELECT DISTINCT ?sensor ?how WHERE {
  VALUES ?how { sensing:silentSince sensing:stuckSince }
  GRAPH $cat { ?g a orexis:StateGraph } GRAPH ?g { ?sensor ?how ?since } }"""


class _Sensing:
    def __init__(self, runtime):
        self.runtime = runtime
        self.observed = Signal("observed")
        self.silence = Signal("silence")
        self.doubted = Signal("doubted")
        self._last: dict[str, datetime] = {}          # sensor -> when its last reading was made
        self._doubts: set[str] = set()                # the sensors doubted at the last ask

    def start(self, runtime) -> None:
        def ask():
            missed(runtime.beliefs, runtime.me, runtime.now)
            written = self.silence.emit(self._silence()) if self.silence.connected else []
            if self.doubted.connected:
                for event in self._doubted():
                    written += self.doubted.emit(event)
            return written
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
            cadence_s=float(cadence) if cadence is not None else None,
            raw=round(float(o["raw"]), 6) if o.get("raw") is not None else None))

    def _silence(self) -> Silence:
        found = rows(self.runtime.beliefs, _SILENT_Q, (), cat=Raw(f"<{catalogue_of(self.runtime.beliefs)}>"))
        return Silence(silent=int(found[0].get("silent") or 0) if found else 0)

    def _doubted(self) -> list[Doubted]:
        """Which sensors are doubted now, and how; and, saying neither, each doubted at the last ask
        and no longer — so the last word in a window on a sensor that recovered is nought."""
        now: dict[str, dict] = {}
        for r in rows(self.runtime.beliefs, _DOUBTED_Q, (), cat=Raw(f"<{catalogue_of(self.runtime.beliefs)}>")):
            now.setdefault(r["sensor"], {})[{SILENT_SINCE: "silent", STUCK_SINCE: "stuck"}[r["how"]]] = 1
        said = [Doubted(sensor=tag_of(sensor), silent=how.get("silent", 0), stuck=how.get("stuck", 0))
                for sensor, how in sorted(now.items())]
        said += [Doubted(sensor=tag_of(sensor)) for sensor in sorted(self._doubts - set(now))]
        self._doubts = set(now)
        return said


def create(runtime) -> _Sensing:
    """Sensing's part: once started, it asks after what has fallen due every `EVERY_S`, and says an
    observation written and the silence, where heard."""
    return _Sensing(runtime)
