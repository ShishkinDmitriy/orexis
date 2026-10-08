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
what it `orexis:actsFor`, a sample of it, or a place that contains it (`schema:containedInPlace`),
and `open` subscribes to their topics' patterns.

**A MESSAGE BECOMES OBSERVATIONS THROUGH SENSING, AND THE TRANSPORT KNOWS NO CODEC.** `handle`
takes a message's topic, bytes and instant and calls sensing's `received` once per sensor of the
agent's whose pattern matches the topic — a board carrying two peripherals publishes one
document, and each sensor takes its own value out of it — and `received` reads the codec, the
pointer and the scaling off the sensor's own binding in the world. What `handle` answers is the
sensor and the graph written, for whoever runs the rest of a pass over them.

**IT STARTS ITSELF.** `start` subscribes, attaches, and asks after its sensors' missing readings
every `NUDGE_S` of the timeline — a board told to sense now while its reading is missing, which the
runtime once did on its behalf.

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
or a port off the world, and nothing could: a world names its broker in its society graph, as
what clients connect to, and where it listens is in a deployment graph — the world's own, or the
installation's allocation — a kind the agent's vocabulary does not declare and its boot passes
over (a-documents-kind-says-who-reads-it).
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime

from agent import clock
from agent.ontology import PUBLIC, SELF_GRAPH, local_of
from agent.store import Raw, answer, catalogue_of, graphs_of, instant, rows
from agent.transport.transport import Transport

log = logging.getLogger("mqtt")

#  HOW OFTEN THE MEMBER ASKS AFTER ITS SENSORS' MISSING READINGS, in seconds of the one timeline.
NUDGE_S = 60.0

#  EVERY OBSERVATION WHOSE STANDING HAS ENDED, by the kernel's kind and SOSA's words: a sensor whose
#  reading has fallen due with nothing arrived since, since the next replaces its graph whole.
_LAPSED_Q = """
SELECT DISTINCT ?sensor WHERE {
  GRAPH $cat { ?g a orexis:StateGraph ; dcterms:temporal/orexis:end ?end . FILTER(?end < $now) }
  GRAPH ?g { ?o sosa:madeBySensor ?sensor } }"""

#  THE PATTERNS OF THE FILTERS THAT MATCH THE TOPIC A SENSOR'S BOARD LISTENS ON.
_COMMANDS_Q = """
SELECT ?pattern WHERE {
  ?board ssn:hasSubSystem $sensor ; mqtt4ssn:listensToTopic ?topic .
  ?filter mqtt4ssn:matchesTopic ?topic ; mqtt4ssn:hasFilterPattern ?pattern }
ORDER BY ?pattern"""

#  WHERE AN ACTUATOR TAKES COMMANDS: a topic it listens to itself, as MQTT4SSN's
#  `listensToTopic` says of an actuator, or its board's.
_ACTUATES_Q = """
SELECT ?pattern WHERE {
  { $actuator mqtt4ssn:listensToTopic ?topic } UNION { ?board ssn:hasSubSystem $actuator ; mqtt4ssn:listensToTopic ?topic }
  ?filter mqtt4ssn:matchesTopic ?topic ; mqtt4ssn:hasFilterPattern ?pattern }
ORDER BY ?pattern"""

#  EVERY SENSOR OF THE SELF'S THAT PUBLISHES ON A TOPIC, with each pattern that names it.
_MINE_Q = """
SELECT ?sensor ?pattern WHERE {
  ?me a orexis:Self ; orexis:actsFor ?subject . ?subject schema:containedInPlace* ?host .
  ?sensor sosa:isHostedBy/(sosa:isSampleOf)? ?host ; mqtt4ssn:observesTopic ?topic .
  ?filter mqtt4ssn:matchesTopic ?topic ; mqtt4ssn:hasFilterPattern ?pattern }
ORDER BY ?sensor ?pattern"""


#  WHAT THIS MEMBER REACHES: a device that publishes on a topic, or listens on one, or whose board does.
_REACHES_Q = """
ASK { { $device mqtt4ssn:observesTopic ?topic } UNION { $device mqtt4ssn:listensToTopic ?topic }
      UNION { ?board ssn:hasSubSystem $device ; mqtt4ssn:listensToTopic ?topic } }"""

#  WHERE AN AGENT IS TOLD THINGS: the topic it listens to itself, as a board listens for
#  commands. Its own is what it subscribes to; a peer's is where a document to it is published.
_LISTENS_Q = """
SELECT ?pattern WHERE {
  $agent mqtt4ssn:listensToTopic ?topic .
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


class Mqtt(Transport):
    """One agent's side of the bus: what the container needs of this transport, answered from
    the world in MQTT4SSN's words, over a client the container connected."""

    def __init__(self, me: str, client, deliver=None):
        self.me, self.client = me, client
        self.deliver = deliver or (lambda *message: None)
        self._unreachable: set[str] = set()     # said to listen on no topic name, so said once

    def _unreached(self, who: str, what: str) -> bool:
        """Say once that `who` listens on no topic name — a step whose actuator does is not taken
        and tried again every pass (#869), and a line per pass is noise, not news — and False."""
        if who not in self._unreachable:
            self._unreachable.add(who)
            log.warning("%s listens on no topic name, so %s", local_of(who), what)
        return False

    @classmethod
    def connect(cls, me: str, deliver=None, *, environ=None, client=None) -> "Mqtt":
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
        member = cls(me, client, deliver)
        client.on_message = lambda _client, _userdata, message: member.deliver(message.topic, message.payload, clock.now())
        client.connect(host, port)
        client.loop_start()
        log.info("%s on %s:%s%s", local_of(me), host, port, " with a certificate" if ca and cert and key else "")
        return member

    def start(self, runtime) -> None:
        """Begin as every member does, and ask after the missing readings of this member's sensors
        every `NUDGE_S`: a board is told to sense now once a minute while its reading is missing."""
        super().start(runtime)
        runtime.every(NUDGE_S, lambda: self.nudge(runtime.beliefs, runtime.now))

    def stop(self) -> None:
        loop_stop, disconnect = getattr(self.client, "loop_stop", None), getattr(self.client, "disconnect", None)
        if loop_stop and disconnect:
            loop_stop()
            disconnect()

    def nudge(self, store, now: datetime) -> list[str]:
        """Tell the board of every sensor of this member's whose reading has fallen due to sense now;
        the sensors asked. Writes nothing."""
        mine = {r["sensor"] for r in rows(store, _MINE_Q, graphs_of(store, PUBLIC, SELF_GRAPH))}
        lapsed = [r["sensor"] for r in rows(store, _LAPSED_Q, (), cat=Raw(f"<{catalogue_of(store)}>"), now=instant(now))]
        asked = [sensor for sensor in lapsed if sensor in mine]
        for sensor in asked:
            self.sense_now(store, sensor)
        return []

    def reaches(self, store, device: str) -> bool:
        return bool(answer(store, _REACHES_Q, graphs_of(store, PUBLIC), device=device)["boolean"])

    def set_cadence(self, store, sensor: str, sleep_s: int) -> bool:
        topic = self._command_topic(store, sensor)
        if topic is None:
            return False
        self.publish(topic, {"sleep_s": int(sleep_s)}, True)
        return True

    def actuate(self, store, actuator: str, payload: dict) -> bool:
        """Publish a step's command on the topic the actuator listens to, or its board's; not
        retained, since a command is an act and a retained one would be taken again by a device
        that reconnects."""
        names = [p for p in (r["pattern"] for r in rows(store, _ACTUATES_Q, graphs_of(store, PUBLIC), actuator=actuator))
                 if "+" not in p and "#" not in p]
        if not names:
            return self._unreached(actuator, "the command is not sent")
        self._unreachable.discard(actuator)
        self.publish(names[0], payload, False)
        log.info("%s: %s on %s", local_of(actuator), payload, names[0])
        return True

    def sense_now(self, store, sensor: str) -> None:
        topic = self._command_topic(store, sensor)
        if topic is not None:
            self.publish(topic, {"sense": True}, False)

    def tell(self, store, to: str, document: bytes) -> bool:
        """Publish a document on the topic the agent `to` listens to, by a pattern with no
        wildcard; not retained, since what was said is said once."""
        names = [p for p in (r["pattern"] for r in rows(store, _LISTENS_Q, graphs_of(store, PUBLIC), agent=to))
                 if "+" not in p and "#" not in p]
        if not names:
            return self._unreached(to, "nothing said to it is sent")
        self._unreachable.discard(to)
        self.client.publish(names[0], document, retain=False)
        log.info("told %s on %s", local_of(to), names[0])
        return True

    def open(self, store) -> list[str]:
        """Subscribe to every pattern the world implies for the agent's sensors, and to the topic
        it listens to itself; the patterns."""
        patterns = sorted({r["pattern"] for r in rows(store, _MINE_Q, graphs_of(store, PUBLIC, SELF_GRAPH))}
                          | {r["pattern"] for r in rows(store, _LISTENS_Q, graphs_of(store, PUBLIC), agent=self.me)})
        for pattern in patterns:
            self.client.subscribe(pattern)
        log.info("%s listening on %s", local_of(self.me), patterns or "nothing")
        return patterns

    def handle(self, store, topic: str, payload: bytes, at: datetime, *, memo=None) -> list[tuple[str | None, str]]:
        """Route one message: on the topic the agent listens to, a peer's document, believed by
        speech's `heard`, each graph answered with no sensor; otherwise to sensing — for every
        sensor of the agent's whose topic's filter matches `topic`, the observation `received`
        writes of `payload` at `at`. The sensor and the graph written, first sensor first, and
        none where the topic is nobody's of the agent's.

        EACH CALLBACK IS IMPORTED WHERE A MESSAGE IS FOR IT. A message on the agent's own topic
        comes only to a speaker, and one for a sensor of its only to an observer — `orexis-onboard`
        refuses a topic listened to by no speaker and a sensor reporting to no observer — so an agent
        that only listens never loads sensing and one that only senses never loads speech (#824, #927)."""
        if any(matches(r["pattern"], topic) for r in rows(store, _LISTENS_Q, graphs_of(store, PUBLIC), agent=self.me)):
            from agent.speech.heard import heard
            return [(None, graph) for graph in heard(store, self.me, payload)]
        mine = list(dict.fromkeys(r["sensor"] for r in rows(store, _MINE_Q, graphs_of(store, PUBLIC, SELF_GRAPH))
                                  if matches(r["pattern"], topic)))
        if not mine:
            log.debug("%s: a message on %s is nobody's of mine", local_of(self.me), topic)
            return []
        from agent.sensing.received import received
        written = []
        for sensor in mine:
            written += [(sensor, graph) for graph in received(store, self.me, sensor, payload, at, memo=memo)]
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
