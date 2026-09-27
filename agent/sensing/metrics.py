"""Everything sensing reports of how it is doing — its gauge and its event — and nowhere else.

Instrumentation, not model (`agent/metrics.py`). Adding a figure is editing this module, and it is
imported only where sensing is loaded, so an agent that senses nothing reports no silence.

THE GAUGE IS OVER THE BELIEF BASE, where sensing writes — never the imaginaria, which copy its
readings and would count one silent sensor once per scope.
"""

from __future__ import annotations

from datetime import datetime

import pyoxigraph as ox

from agent.metrics import Event, Gauge, sample
from agent.ontology import PUBLIC, local_of
from agent.store import graphs_of, rows

#  THE SENSORS SAID SILENT NOW: `sensing:silentSince` in a state graph of the agent's, which
#  `missed` writes once a sensor is past its limit of cadences and `received` takes back when a
#  reading ends it.
SILENCE = Gauge("silence", """
SELECT (COUNT(DISTINCT ?sensor) AS ?silent)
WHERE { GRAPH $cat { ?g a orexis:StateGraph } GRAPH ?g { ?sensor sensing:silentSince ?since } }""")

#  EACH READING AS IT IS WRITTEN, by `received`: how long after the reading it replaces it came, in
#  the agent's seconds, beside the cadence the world states, tagged by the sensor.
RECEIVED = Event("received", values=("interval_s", "cadence_s"), tags=("sensor",))


def gauges(beliefs: ox.Store) -> list:
    """Sensing's gauge, sampled over the belief base."""
    return sample(__name__, [beliefs])


#  WHEN THE READING BEFORE WAS MADE, off the graph of the key, which `received` names; and the
#  sensor's `orexis:localId`, the tag history already carries.
_BEFORE_Q = """SELECT ?t WHERE { GRAPH $graph { ?o sosa:resultTime ?t } } LIMIT 1"""
_ID_Q = """SELECT ?id WHERE { $sensor orexis:localId ?id } LIMIT 1"""


def made_before(store: ox.Store, graph: str) -> datetime | None:
    """When the reading `graph` holds was made, read before a new one replaces it — or None."""
    found = rows(store, _BEFORE_Q, (), graph=graph)
    return datetime.fromisoformat(found[0]["t"]) if found else None


def report_received(store: ox.Store, sensor: str, *, at: datetime, before: datetime,
                    cadence: float | None) -> None:
    """Say a reading of `sensor` made at `at`, replacing one made `before`: the interval between,
    beside the cadence the world states where it states one."""
    found = rows(store, _ID_Q, graphs_of(store, PUBLIC), sensor=sensor)
    RECEIVED({"interval_s": round((at - before).total_seconds(), 3),
              **({"cadence_s": float(cadence)} if cadence is not None else {})},
             sensor=found[0]["id"] if found else local_of(sensor))
