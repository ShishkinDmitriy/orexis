"""`handle`: a message arrived on a topic, and every sensor of the agent's that publishes there
has a reading — the listener's act, one call of sensing's `received` per sensor.

**WHOSE SENSORS.** The agent's sensors are not authored: they are the ones `sosa:isHostedBy` what
it `orexis:actsFor`, or a sample of it, which is the same derivation the link subscribes by. A
message for a neighbour's sensor on the same broker is not this agent's and is not received,
though the broker delivered it.

**ONE MESSAGE, SEVERAL SENSORS.** A board carrying two peripherals publishes one document, and
each sensor takes its own value out of it by its pointer, in sensing's pipeline; so a message
is handed to `received` once per sensor whose topic's filter matches the message's topic, and
the graphs written are answered, first sensor first.
"""

from __future__ import annotations

import logging
from datetime import datetime

from agent.ontology import PUBLIC, local_of
from agent.sensing.received import received
from agent.store import graphs_of, rows

from .driver import matches

log = logging.getLogger("mqtt")

#  EVERY SENSOR OF THE AGENT'S THAT PUBLISHES ON A TOPIC, with each pattern that names it.
MINE_Q = """
SELECT ?sensor ?pattern WHERE {
  $me orexis:actsFor ?subject .
  ?sensor sosa:isHostedBy/(sosa:isSampleOf)? ?subject ; mqtt4ssn:observesTopic ?topic .
  ?filter mqtt4ssn:matchesTopic ?topic ; mqtt4ssn:hasFilterPattern ?pattern }
ORDER BY ?sensor ?pattern"""


def handle(store, me: str, topic: str, payload: bytes, at: datetime, *, memo=None) -> list[str]:
    """Route one message to sensing: for every sensor of `me`'s whose topic's filter matches
    `topic`, the observation `received` writes of `payload` at `at`. The graphs written, and
    none where the topic is nobody's of `me`'s."""
    written, seen = [], set()
    for r in rows(store, MINE_Q, graphs_of(store, PUBLIC), me=me):
        sensor = r["sensor"]
        if sensor in seen or not matches(r["pattern"], topic):
            continue
        seen.add(sensor)
        graph = received(store, me, sensor, payload, at, memo=memo)
        if graph:
            written.append(graph)
    if not seen:
        log.debug("%s: a message on %s is nobody's of mine", local_of(me), topic)
    return written
