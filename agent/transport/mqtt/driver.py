"""The MQTT driver: the agent's side of the bus, answering the transport family's `Transport`
contract from MQTT4SSN's words, with the topic filter matching MQTT itself specifies.

**WHAT THE WORLD SAYS AND WHAT FOLLOWS.** A sensor speaks MQTT when it `mqtt4ssn:observesTopic`
a topic. What the agent subscribes to is the pattern of every `mqtt4ssn:TopicFilter` that
`mqtt4ssn:matchesTopic` a topic one of its sensors publishes on, and a message on a channel is a
sensor's when a pattern of its topic matches the channel by MQTT's own rules — `+` one level,
`#` the rest. A command goes
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

**THE MEMBER BRINGS ITSELF UP, AND THE THREAD IS THE CONTAINER'S.** `connect` makes the client
from the environment, in this transport's own variables — `MQTT_HOST` and `MQTT_PORT`, the
agent's `MQTT_USERNAME` and `MQTT_PASSWORD`, and `MQTT_CA`, `MQTT_CERT` and `MQTT_KEY` with
`MQTT_TLS_PORT` where it holds a certificate — and paho is imported there and nowhere else in
the agent. It refuses without a host or a credential rather than guess one, for the reason no
command has a default world: a guess puts a misconfigured agent on the real topics. A message
arrives on the client's network thread, and a write belongs on the one executing thread, so
`connect` hands every message to the container's `deliver(topic, payload, at)`, which enqueues,
and the container's thread calls `handle`. A test hands a client of its own with paho's shape —
`subscribe`, `publish`, `connect`, `loop_start` and the two setters. Nothing here reads a host
or a port off the world; 0.1.0 read the bus's off the world as the one piece of infrastructure
everyone must agree on, and MQTT4SSN has `hasHostAddress` on a Broker, so that is a choice the
sovereign may reverse.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime

from agent import clock
from agent.ontology import PUBLIC, local_of
from agent.sensing.received import received
from agent.store import graphs_of, rows
from agent.transport.transport import Transport

log = logging.getLogger("mqtt")

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


class Mqtt(Transport):
    """One agent's side of the bus: what the container needs of this transport, answered from
    the world in MQTT4SSN's words, over a client the container connected."""

    def __init__(self, me: str, client):
        self.me, self.client = me, client

    @classmethod
    def connect(cls, me: str, deliver, *, environ=None, client=None) -> "Mqtt":
        """The agent's side of the bus, up: a client under the agent's credential, with a
        certificate where the environment holds one, connected to the broker the environment
        names, its loop running, and every message handed to `deliver(topic, payload, at)`."""
        env = os.environ if environ is None else environ
        host, username = env.get("MQTT_HOST"), env.get("MQTT_USERNAME")
        if not host:
            raise RuntimeError("no MQTT_HOST in the environment — this agent is told where its bus is, never guesses")
        if not username:
            raise RuntimeError("no MQTT_USERNAME in the environment — this agent has no credential for the bus. "
                               "Run `orexis-mqtt <world>` and regenerate the compose file.")
        if client is None:
            import paho.mqtt.client as paho                 # the one import of the library in the agent
            client = paho.Client(paho.CallbackAPIVersion.VERSION2, client_id=local_of(me))
        ca, cert, key = env.get("MQTT_CA"), env.get("MQTT_CERT"), env.get("MQTT_KEY")
        if ca and cert and key:
            client.tls_set(ca_certs=ca, certfile=cert, keyfile=key)
            port = int(env.get("MQTT_TLS_PORT", 8883))
        else:
            port = int(env.get("MQTT_PORT", 1883))
        client.username_pw_set(username, env.get("MQTT_PASSWORD"))
        client.on_message = lambda _client, _userdata, message: deliver(message.topic, message.payload, clock.now())
        client.connect(host, port)
        client.loop_start()
        log.info("%s on %s:%s%s", local_of(me), host, port, " with a certificate" if ca and cert and key else "")
        return cls(me, client)

    @classmethod
    def claims(cls, store, sensor: str) -> bool:
        """A sensor that publishes on a topic speaks MQTT, whether or not a filter names it yet."""
        return bool(rows(store, "SELECT ?topic WHERE { $sensor mqtt4ssn:observesTopic ?topic }",
                         graphs_of(store, PUBLIC), sensor=sensor))

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
