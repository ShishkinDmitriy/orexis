"""How often a sensor reports, in SSN-System's words — read by `received` to say until when an
observation stands, and by `missed` to say when a silence has lasted long enough to be one.

A sensor's `ssn-system:hasSystemCapability` carries an `ssn-system:hasSystemProperty` typed
`ssn-system:Frequency`, whose `schema:value` is the time between one observation and the
next in the `schema:unitCode` it states — QUDT's `unit:SEC`, `unit:MIN`, `unit:HR`, `unit:DAY`,
or the UN/CEFACT code spelled the same — seconds where it states none. A sensor stating no
frequency has no cadence: its percept stands until the next arrives and its silence is never
said, since the world made no promise the absence could break.

How many of those cadences a reading may be missing before the sensor is said silent,
`sensing:silentAfter`, and how many of its readings may give one number before it is said stuck,
`sensing:stuckAfter`, are the observer role's that reads the sensor (`limit_of`): stated on the role
in the self graph where it is played, and the observer shape's default in this layer's ontology
where the role states none (`ontology.default_of`).

**WHICH SENSORS ARE THE AGENT'S** (`sensors`): the ones an observer role it plays reads, declared in
its self graph. A transport asks, to know what to subscribe to and fetch, since a sensor is the
agent's by a role and no transport's word says so.

**WHEN A CADENCE HAS LAPSED** (`lapsed`): the sensors whose latest percept's period has ended — the
next reading due and a grace past it, with nothing arrived. One read and one owner: `missed` asks it
to say a sensor silent, and a transport beneath asks it to nudge a board, since what an observation
is and how they are kept are sensing's, and a member that restated the question in its own text
would be a second reader of a kind it may not name (#944).
"""

from __future__ import annotations

import logging
from datetime import datetime

from agent.ontology import BELIEF, SELF_GRAPH, local_of
from agent.store import Raw, catalogue_of, graphs_of, instant, remember, rows

from .ontology import default_of

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
        found = rows(store, _CADENCE_Q, graphs_of(store, BELIEF, common=True), sensor=sensor)
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


#  EVERY SENSOR THE AGENT READS: each an observer role it plays declares, in the self graph.
_SENSORS_Q = "SELECT DISTINCT ?sensor WHERE { ?me a orexis:Self ; orexis:plays/sensing:sensor ?sensor } ORDER BY ?sensor"


def sensors(store) -> list[str]:
    """Every sensor the agent reads: each an observer role the self plays declares (`sensing:sensor`), in
    its self graph, sorted — whose bytes a transport hands `received`. Which of them a member reaches, a
    topic or a form, is the member's to say in its own words; which are the agent's is the role's, and
    so sensing's, and no transport names it."""
    return [r["sensor"] for r in rows(store, _SENSORS_Q, graphs_of(store, SELF_GRAPH))]


#  WHAT AN OBSERVER ROLE READING THIS SENSOR STATES OF A LIMIT, in the self graph where it is played.
_LIMIT_Q = """
SELECT DISTINCT ?n WHERE { ?me a orexis:Self ; orexis:plays ?role . ?role sensing:sensor $sensor ; $limit ?n }"""


def limit_of(store, sensor: str, limit: str, memo=None) -> int:
    """How many cadences or readings `limit` — `sensing:silentAfter`, `sensing:stuckAfter` — allows
    `sensor`: the figure the observer role reading it states in the self graph, or the observer
    shape's default where it states none, several, or one that is no number, said in the log, since
    two answers are never picked between. Remembered per pass where a memo is given."""
    def read():
        found = rows(store, _LIMIT_Q, graphs_of(store, SELF_GRAPH), sensor=sensor, limit=limit)
        if len(found) == 1:
            try:
                return int(float(found[0]["n"]))
            except ValueError:
                pass
        if found:
            log.warning("the roles reading %s state %s for %s: the default, %d, holds", local_of(sensor),
                        ", ".join(sorted(r["n"] for r in found)), local_of(limit), default_of(limit))
        return default_of(limit)
    return remember(memo, ("limit", sensor, limit), read)

