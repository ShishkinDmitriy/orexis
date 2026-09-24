"""The MQTT driver: sensing's `Driver` contract, answered from MQTT4SSN's words, and the topic
filter matching MQTT itself specifies.

A sensor speaks MQTT when it `mqtt4ssn:observesTopic` a topic. What the agent subscribes to for
it is the pattern of every `mqtt4ssn:TopicFilter` that `mqtt4ssn:matchesTopic` that topic, and a
message on a channel is the sensor's when a pattern of its topic matches the channel by MQTT's
own rules — `+` one level, `#` the rest. A command goes to the topic the sensor's board
`mqtt4ssn:listensToTopic`, by a pattern with no wildcard in it, since a publish takes a topic
name; the payloads are the ones the firmware has always read, `{"sleep_s": n}` retained so a
board deep asleep finds it on waking, and `{"sense": true}` not retained. Who publishes is the
caller's: the driver is handed a `publish(topic, payload, retain)` and never holds a socket.
"""

from __future__ import annotations

import logging

from agent.ontology import PUBLIC, local_of
from agent.sensing.driver import Driver
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
    """What sensing needs of this transport, answered from the world in MQTT4SSN's words."""

    def __init__(self, publish):
        self.publish = publish

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
