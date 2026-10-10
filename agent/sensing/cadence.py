"""How often a sensor reports, in SSN-System's words — read by `received` to say until when an
observation stands, and by `missed` to say when a silence has lasted long enough to be one.

A sensor's `ssn-system:hasSystemCapability` carries an `ssn-system:hasSystemProperty` typed
`ssn-system:Frequency`, whose `schema:value` is the time between one observation and the
next in the `schema:unitCode` it states — QUDT's `unit:SEC`, `unit:MIN`, `unit:HR`, `unit:DAY`,
or the UN/CEFACT code spelled the same — seconds where it states none. A sensor stating no
frequency has no cadence: its percept stands until the next arrives and its silence is never
said, since the world made no promise the absence could break.

How many of those cadences the agent allows a reading to be missing before it says the sensor
silent, `sensing:silentAfter`, and how many of its readings may give one number before it is said
stuck, `sensing:stuckAfter`, are the agent's own word about itself, stances in its self graph, read by
`missed` and `received` through the kernel's `stance` with the figure in code where it states none.

**WHEN A CADENCE HAS LAPSED** (`lapsed`): the sensors whose latest percept's period has ended — the
next reading due and a grace past it, with nothing arrived. One read and one owner: `missed` asks it
to say a sensor silent, and a transport beneath asks it to nudge a board, since what an observation
is and how they are kept are sensing's, and a member that restated the question in its own text
would be a second reader of a kind it may not name (#944).
"""

from __future__ import annotations

import logging
from datetime import datetime

from agent.ontology import PUBLIC, local_of
from agent.store import Raw, catalogue_of, graphs_of, instant, remember, rows

log = logging.getLogger("cadence")

_CADENCE_Q = """
SELECT ?every ?unit WHERE {
  $sensor ssn-system:hasSystemCapability/ssn-system:hasSystemProperty ?f .
  ?f a ssn-system:Frequency ; schema:value ?every .
  OPTIONAL { ?f schema:unitCode ?unit } }"""

#  A unit of time as its seconds, by the local name QUDT and UN/CEFACT spell it under.
_SECONDS = {"SEC": 1.0, "MIN": 60.0, "HR": 3600.0, "HUR": 3600.0, "DAY": 86400.0}

#  EVERY SENSOR WHOSE LATEST PERCEPT HAS LAPSED, with the instant it did — asked of the catalogue by
#  kind, and of the graphs by pattern: the latest is the one no percept names as its previous, and a
#  revision, of the same kind, holds no `sosa:madeBySensor` and is no match.
_LAPSED_Q = """
SELECT ?sensor ?end WHERE {
  GRAPH $cat { ?g a sensing:ObservationGraph ; dcterms:temporal/orexis:end ?end . FILTER(?end < $now) }
  GRAPH ?g { ?obs sosa:madeBySensor ?sensor }
  FILTER NOT EXISTS { GRAPH ?h { ?later sensing:previous ?obs } GRAPH $cat { ?h a sensing:ObservationGraph } } }
ORDER BY ?end ?sensor"""


def cadence_of(store, sensor: str, memo=None) -> float | None:
    """The seconds between one of `sensor`'s observations and the next, as the world states
    them, or None where it states no frequency, several, or a unit nothing here converts.
    Remembered per pass where a memo is given."""
    def read():
        found = rows(store, _CADENCE_Q, graphs_of(store, PUBLIC), sensor=sensor)
        if len(found) != 1:
            if found:
                log.warning("%s states %d frequencies: none is its cadence", local_of(sensor), len(found))
            return None
        unit = found[0].get("unit")
        seconds = _SECONDS.get(local_of(unit) if unit else "SEC")
        if seconds is None:
            log.warning("%s states its frequency in %s, which nothing here converts", local_of(sensor), unit)
            return None
        return float(found[0]["every"]) * seconds
    return remember(memo, ("cadence", sensor), read)


def lapsed(store, now: datetime, memo=None) -> list[tuple[str, datetime]]:
    """Every sensor whose latest percept had ended by `now` — its next reading due and a grace past it,
    and nothing arrived — with the instant it ended, earliest first. A sensor stating no frequency is
    never here: its percept has no end. Writes nothing."""
    cat = Raw(f"<{remember(memo, ('catalogue',), lambda: catalogue_of(store))}>")
    return [(r["sensor"], datetime.fromisoformat(r["end"]))
            for r in rows(store, _LAPSED_Q, (), cat=cat, now=instant(now))]
