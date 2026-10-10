"""`missed`: which sensors' readings are missing at an instant, and which of them have gone
silent — asked every minute of the timeline by sensing's own `start`, which the runtime waits for.

**A READING IS MISSING WHEN THE LATEST PERCEPT'S PERIOD HAS ENDED.** The percept `received` writes
holds from its instant until the next is due by the sensor's `ssn-system:Frequency` and a grace past
it (`received.GRACE`), or until the next arrives, so the period of the LATEST — the percept no percept
names as its previous — ending IS the reading going missing — later than due, since a reading a little
late is not missing (#870): a reader asking at a later instant is handed no percept of the sensor,
which is what unmeasured is. An older percept's period ended when its successor arrived, and says
nothing missed (#944).
This act answers the sensors in that state, earliest lapse first, for the container to nudge
through the driver (`sense_now`); it writes nothing for a reading merely missed, since the
period's end already says it, and a mark would say it twice.

**A SENSOR SILENT PAST THE LIMIT IS SAID SO.** One whose reading has been missing for
`sensing:silentAfter` cadences and more — the agent's limit, a stance in its self graph, and
`SILENT_AFTER` where it states none — gets `sensing:silentSince` the instant its last reading fell
due — named for the state, not for the tick that noticed — in a graph of the agent's own
classified `orexis:StateGraph`, the kernel's kind, since a silence is a fact a plan may
change, holding from that instant and present while the silence lasts; the sensor's next
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

from agent.ontology import STATE, local_of
from agent.stance import stance
from agent.store import Raw, catalogue_of, entry, instant, remember, rows, update

from .cadence import cadence_of
from .ontology import DERIVED, SILENT_AFTER_TERM, silent_graph

log = logging.getLogger("missed")

#  HOW LONG A READING MAY BE MISSING before its sensor is said silent, in its own cadences, where the
#  agent's self graph states no `sensing:silentAfter` of it.
SILENT_AFTER = 3

#  EVERY SENSOR WHOSE LATEST PERCEPT HAS LAPSED, with the instant it did and whether it is said
#  silent already — asked of the catalogue by kind, and of the graphs by pattern: the latest is the
#  one no percept names as its previous.
_MISSING_Q = """
SELECT ?sensor ?end ?since WHERE {
  GRAPH $cat { ?g a sensing:ObservationGraph ; dcterms:temporal/orexis:end ?end . FILTER(?end < $now) }
  GRAPH ?g { ?obs sosa:madeBySensor ?sensor }
  FILTER NOT EXISTS { GRAPH ?h { ?later sensing:previous ?obs } GRAPH $cat { ?h a sensing:ObservationGraph } }
  OPTIONAL { GRAPH $cat { ?sg a orexis:StateGraph } GRAPH ?sg { ?sensor sensing:silentSince ?since } } }
ORDER BY ?end ?sensor"""


def missed(store, me: str, now: datetime, *, memo=None) -> list[str]:
    """The sensors whose reading is missing at `now` — observed once, and the observation
    fallen due before now with nothing arrived since — earliest lapse first; and any of them
    silent for the agent's limit of cadences is said so, once, by `sensing:silentSince` in a graph
    of `me`'s own.
    """
    cat = Raw(f"<{remember(memo, ('catalogue',), lambda: catalogue_of(store))}>")
    lapsed = rows(store, _MISSING_Q, (), cat=cat, now=instant(now))
    limit = stance(store, SILENT_AFTER_TERM, SILENT_AFTER, memo)
    out: list[str] = []
    for r in lapsed:
        sensor, fell_due = r["sensor"], datetime.fromisoformat(r["end"])
        if sensor in out:
            continue
        out.append(sensor)
        if r.get("since"):
            continue                                    # said already, and once is enough
        cadence = cadence_of(store, sensor, memo)
        if cadence is None or now < fell_due + timedelta(seconds=limit * cadence):
            continue
        graph = silent_graph(local_of(me), sensor)
        update(store, f"""
INSERT DATA {{
  GRAPH <{graph}> {{ <{sensor}> sensing:silentSince "{fell_due.isoformat()}"^^xsd:dateTime . }}
  {entry(store, graph, STATE, DERIVED, me, start=fell_due)} }}""")
        log.warning("%s: %s silent since %s, %d cadences past", local_of(me), local_of(sensor),
                    fell_due.isoformat(timespec="seconds"), limit)
    return out
