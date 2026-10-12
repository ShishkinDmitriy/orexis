"""`missed`: which sensors' readings are missing at an instant, and which of them have gone
silent — asked every minute of the timeline by sensing's own `start`, which the runtime waits for.

**A READING IS MISSING WHEN THE LATEST PERCEPT'S PERIOD HAS ENDED.** The percept `received` writes
holds from its instant until the next is due by the sensor's `ssn-system:Frequency` and a grace past
it (`received.GRACE`), or until the next arrives, so the period of the LATEST — the percept no percept
names as its previous — ending IS the reading going missing — later than due, since a reading a little
late is not missing (#870): a reader asking at a later instant is handed no percept of the sensor,
which is what unmeasured is. An older percept's period ended when its successor arrived, and says
nothing missed (#944).
Which sensors are in that state is `cadence.lapsed`, the one read of it, which the MQTT member asks
too. This act answers them, earliest lapse first, for the container to nudge
through the driver (`sense_now`); it writes nothing for a reading merely missed, since the
period's end already says it, and a mark would say it twice.

**A SENSOR SILENT PAST THE LIMIT IS SAID SO.** One whose reading has been missing for
`sensing:silentAfter` cadences and more — the limit the observer role reading it states, the observer
shape's default where it states none (`cadence.limit_of`) — gets `sensing:silentSince` the instant its
last reading fell due — named for the state, not for the tick that noticed — in a graph of the
agent's own classified `sensing:SilenceGraph`, arrived `orexis:Derived`, since a silence is the
agent's own conclusion about its sensor: sensing's kind and no belief, as a stuck sensor is said in a
percept's revision, since nothing in the mind reads it and a belief the agent derived is the state a
transition may delete from. It holds from that instant and is present while the silence lasts; the sensor's next
reading drops it at the writer (`received`). Said once: a sensor already said silent is not
re-said on every tick. SOSA and SSN say how often a sensor reports and nothing about one that
has stopped, so this is one of sensing's own words.

**A SENSOR THAT HAS NEVER REPORTED IS NOT HERE.** Its absence is, in the store, the same as
a sensor not yet due; that fault is the container's to count from boot, and is the seam this
leaves open — as is the sweep: this reads the ended percept's row off the catalogue, so an upkeep
that dropped ended graphs would have to leave a sensor's latest percept standing. None does: a
percept is forgotten by `received` alone, past the depth sensing keeps, and never the latest.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from agent.hash_named_graph import hash_named_graph
from agent.ontology import DERIVED, local_of
from agent.store import Raw, catalogue_of, entry, remember, rows, update

from .cadence import cadence_of, lapsed, limit_of
from .ontology import SILENCE_GRAPH, SILENT_AFTER_TERM, silent_graph

log = logging.getLogger("missed")

#  EVERY SENSOR SAID SILENT ALREADY: the row in a silence graph of the agent's.
_SILENT_Q = """
SELECT DISTINCT ?sensor WHERE { GRAPH $cat { ?sg a sensing:SilenceGraph } GRAPH ?sg { ?sensor sensing:silentSince ?since } }"""


def missed(store, me: str, now: datetime, *, memo=None) -> list[str]:
    """The sensors whose reading is missing at `now` — observed once, and the observation
    fallen due before now with nothing arrived since (`cadence.lapsed`) — earliest lapse first; and
    any of them silent for the limit of cadences its observer role allows is said so, once, by
    `sensing:silentSince` in a silence graph of `me`'s own.
    """
    found = lapsed(store, now, memo)
    if not found:
        return []
    cat = Raw(f"<{remember(memo, ('catalogue',), lambda: catalogue_of(store))}>")
    silent = {r["sensor"] for r in rows(store, _SILENT_Q, (), cat=cat)}
    out: list[str] = []
    for sensor, fell_due in found:
        if sensor in out:
            continue
        out.append(sensor)
        if sensor in silent:
            continue                                    # said already, and once is enough
        cadence = cadence_of(store, sensor, memo)
        limit = limit_of(store, sensor, SILENT_AFTER_TERM, memo)
        if cadence is None or now < fell_due + timedelta(seconds=limit * cadence):
            continue
        graph = silent_graph(local_of(me), sensor)
        update(store, f"""
INSERT DATA {{
  GRAPH <{graph}> {{ <{sensor}> sensing:silentSince "{fell_due.isoformat()}"^^xsd:dateTime . }}
  {entry(store, graph, SILENCE_GRAPH, DERIVED, me, start=fell_due)} }}""")
        hash_named_graph(store, graph)
        log.warning("%s: %s silent since %s, %d cadences past", local_of(me), local_of(sensor),
                    fell_due.isoformat(timespec="seconds"), limit)
    return out
