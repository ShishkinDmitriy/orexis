"""The MQTT driver: the agent's side of the bus, answering sensing's `Driver` contract from
MQTT4SSN's words, with the topic filter matching MQTT itself specifies.

**WHAT THE WORLD SAYS AND WHAT FOLLOWS.** A sensor speaks MQTT when it `mqtt4ssn:observesTopic`
a topic. What the agent subscribes to for it is the pattern of every `mqtt4ssn:TopicFilter` that
`mqtt4ssn:matchesTopic` that topic, and a message on a channel is the sensor's when a pattern of
its topic matches the channel by MQTT's own rules — `+` one level, `#` the rest. A command goes
to the topic the sensor's board `mqtt4ssn:listensToTopic`, by a pattern with no wildcard in it,
since a publish takes a topic name; the payloads are the ones the firmware has always read,
`{"sleep_s": n}` retained so a board deep asleep finds it on waking, and `{"sense": true}` not
retained. Which sensors are the agent's is never authored: they are the ones `sosa:isHostedBy`
what it `orexis:actsFor`, or a sample of it, and `open` subscribes to their topics' patterns.

**A MESSAGE BECOMES OBSERVATIONS THROUGH SENSING, AND THE TRANSPORT KNOWS NO CODEC.** `handle`
takes a message's topic, bytes and instant and calls sensing's `received` once per sensor of the
agent's whose pattern matches the topic — a board carrying two peripherals publishes one
document, and each sensor takes its own value out of it — and `received` reads the codec, the
pointer and the scaling off the sensor's own binding in the world. What `handle` answers is the
sensor and the graph written, for whoever runs the rest of a pass over them.

**THE CLIENT IS THE CONTAINER'S, AND SO IS THE THREAD.** The driver is handed a client with
paho's shape — `subscribe(pattern)`, `publish(topic, payload, retain=)` — that the container
made with the broker's address and the agent's credentials from the environment and connected;
it sets no callback, since a message arrives on the client's network thread and a write belongs
on the one executing thread, so the container's `on_message` enqueues and its thread calls
`handle`. Nothing here reads a host or a port off the world.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime

from agent.ontology import PUBLIC, local_of
from agent.sensing.driver import Driver
from agent.sensing.received import received
from agent.store import graphs_of, rows

log = logging.getLogger("mqtt")

#  THE PATTERNS OF THE FILTERS THAT MATCH THE TOPIC A SENSOR PUBLISHES ON.
_READINGS_Q = """
SELECT ?pattern WHERE {
  $sensor mqtt4ssn:observesTopic ?topic .
  ?filter mqtt4ssn:matchesTopic ?topic ; mqtt4ssn:hasFilterPattern ?pattern }
ORDER BY ?pattern"""

#  THE PATTERNS OF THE FILTERS THAT MATCH THE TOPIC A SENSOR'S BOARD LISTENS ON.
_COMMANDS_Q = """
SELECT ?pattern WHERE {
  ?board ssn:hasSubSystem $sensor ; mqtt4ssn:listensToTopic ?topic .
  ?filter mqtt4ssn:matchesTopic ?topic ; mqtt4ssn:hasFilterPattern ?pattern }
ORDER BY ?pattern"""

#  EVERY SENSOR OF THE AGENT'S THAT PUBLISHES ON A TOPIC, with each pattern that names it.
_MINE_Q = """
SELECT ?sensor ?pattern WHERE {
  $me orexis:actsFor ?subject .
  ?sensor sosa:isHostedBy/(sosa:isSampleOf)? ?subject ; mqtt4ssn:observesTopic ?topic .
  ?filter mqtt4ssn:matchesTopic ?topic ; mqtt4ssn:hasFilterPattern ?pattern }
ORDER BY ?sensor ?pattern"""


def matches(pattern: str, topic: str) -> bool:
    """Whether a topic filter matches a topic name, as MQTT specifies: `+` matches one level,
    `#` matches the rest and may only end a filter, and a topic beginning with `$` is matched
    by no wildcard at its first level."""
    if topic.startswith("$") and pattern[:1] in ("+", "#"):
        return False
    levels, names = pattern.split("/"), topic.split("/")
    for i, level in enumerate(levels):
        if level == "#":
            return i == len(levels) - 1
        if i >= len(names) or (level != "+" and level != names[i]):
            return False
    return len(levels) == len(names)


class Mqtt(Driver):
    """One agent's side of the bus: what sensing needs of this transport, answered from the
    world in MQTT4SSN's words, over a client the container connected."""

    def __init__(self, me: str, client):
        self.me, self.client = me, client

    @classmethod
    def claims(cls, store, sensor: str) -> bool:
        """A sensor that publishes on a topic speaks MQTT, whether or not a filter names it yet."""
        return bool(rows(store, "SELECT ?topic WHERE { $sensor mqtt4ssn:observesTopic ?topic }",
                         graphs_of(store, PUBLIC), sensor=sensor))

    def subscriptions(self, store, sensor: str) -> list[str]:
        return [r["pattern"] for r in rows(store, _READINGS_Q, graphs_of(store, PUBLIC), sensor=sensor)]

    def owns(self, store, sensor: str, channel: str) -> bool:
        return any(matches(pattern, channel) for pattern in self.subscriptions(store, sensor))

    def set_cadence(self, store, sensor: str, sleep_s: int) -> bool:
        topic = self._command_topic(store, sensor)
        if topic is None:
            return False
        self.publish(topic, {"sleep_s": int(sleep_s)}, True)
        return True

    def sense_now(self, store, sensor: str) -> None:
        topic = self._command_topic(store, sensor)
        if topic is not None:
            self.publish(topic, {"sense": True}, False)

    def open(self, store) -> list[str]:
        """Subscribe to every pattern the world implies for the agent's sensors; the patterns."""
        patterns = sorted({r["pattern"] for r in rows(store, _MINE_Q, graphs_of(store, PUBLIC), me=self.me)})
        for pattern in patterns:
            self.client.subscribe(pattern)
        log.info("%s listening on %s", local_of(self.me), patterns or "nothing")
        return patterns

    def handle(self, store, topic: str, payload: bytes, at: datetime, *, memo=None) -> list[tuple[str, str]]:
        """Route one message to sensing: for every sensor of the agent's whose topic's filter
        matches `topic`, the observation `received` writes of `payload` at `at`. The sensor
        and the graph written, first sensor first, and none where the topic is nobody's of
        the agent's."""
        written, seen = [], set()
        for r in rows(store, _MINE_Q, graphs_of(store, PUBLIC), me=self.me):
            sensor = r["sensor"]
            if sensor in seen or not matches(r["pattern"], topic):
                continue
            seen.add(sensor)
            graph = received(store, self.me, sensor, payload, at, memo=memo)
            if graph:
                written.append((sensor, graph))
        if not seen:
            log.debug("%s: a message on %s is nobody's of mine", local_of(self.me), topic)
        return written

    def publish(self, topic: str, payload: dict, retain: bool) -> None:
        """A command out, as the JSON document the firmware reads."""
        self.client.publish(topic, json.dumps(payload).encode(), retain=retain)

    def _command_topic(self, store, sensor: str) -> str | None:
        """The topic name the sensor's board takes commands on: a pattern of a filter matching
        it with no wildcard, since a publish takes a name. None, said in the log, where the
        board listens nowhere or every pattern is a wildcard."""
        patterns = [r["pattern"] for r in rows(store, _COMMANDS_Q, graphs_of(store, PUBLIC), sensor=sensor)]
        names = [p for p in patterns if "+" not in p and "#" not in p]
        if not names:
            log.warning("%s: its board listens on %s, and none is a topic name to publish to",
                        local_of(sensor), patterns or "no topic")
            return None
        return names[0]
