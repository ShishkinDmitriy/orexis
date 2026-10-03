"""How often a sensor reports, in SSN-System's words — read by `received` to say until when an
observation stands, and by `missed` to say when a silence has lasted long enough to be one — and
how many of those cadences the agent allows before it doubts the sensor, in sensing's own words.

A sensor's `ssn-system:hasSystemCapability` carries an `ssn-system:hasSystemProperty` typed
`ssn-system:Frequency`, whose `schema:value` is the time between one observation and the
next in the `schema:unitCode` it states — QUDT's `unit:SEC`, `unit:MIN`, `unit:HR`, `unit:DAY`,
or the UN/CEFACT code spelled the same — seconds where it states none. A sensor stating no
frequency has no cadence: its observation stands until replaced and its silence is never
said, since the world made no promise the absence could break.

A LIMIT is the agent's: `sensing:silentAfter` and `sensing:stuckAfter`, each a count of the doubted
sensor's cadences, stated of the agent by its world as `orexis:actsFor` is, in a public graph the
agent believes. The figure in code (`missed.SILENT_AFTER`, `received.STUCK_AFTER`) is what holds where
the world states none — a default, never a second place the figure lives.
"""

from __future__ import annotations

import logging

from agent.ontology import PUBLIC, local_of
from agent.store import graphs_of, remember, rows

log = logging.getLogger("cadence")

_CADENCE_Q = """
SELECT ?every ?unit WHERE {
  $sensor ssn-system:hasSystemCapability/ssn-system:hasSystemProperty ?f .
  ?f a ssn-system:Frequency ; schema:value ?every .
  OPTIONAL { ?f schema:unitCode ?unit } }"""

#  A unit of time as its seconds, by the local name QUDT and UN/CEFACT spell it under.
_SECONDS = {"SEC": 1.0, "MIN": 60.0, "HR": 3600.0, "HUR": 3600.0, "DAY": 86400.0}


_LIMIT_Q = "SELECT ?n WHERE { $me $limit ?n }"


def limit_of(store, me: str, limit: str, default: int, memo=None) -> int:
    """How many cadences `me` allows before the doubt `limit` names — `sensing:silentAfter`,
    `sensing:stuckAfter` — as its world states of it, or `default` where it states none or several.
    Remembered per pass where a memo is given."""
    def read():
        found = rows(store, _LIMIT_Q, graphs_of(store, PUBLIC), me=me, limit=limit)
        if len(found) != 1:
            if found:
                log.warning("%s states %d figures for %s: the default, %d, holds", local_of(me), len(found), local_of(limit), default)
            return default
        return int(float(found[0]["n"]))
    return remember(memo, ("limit", me, limit), read)


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
