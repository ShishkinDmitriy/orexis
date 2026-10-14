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
retained. Which sensors are the agent's is its observer role's to say: the ones a role it
`orexis:plays` reads (`sensing.cadence.sensors`), held by onboarding to where they are mounted, and `open`
subscribes to their topics' patterns.

**A MESSAGE BECOMES OBSERVATIONS THROUGH SENSING, AND THE TRANSPORT KNOWS NO CODEC.** `handle`
takes a message's topic, bytes and instant and calls sensing's `received` once per sensor of the
agent's whose pattern matches the topic — a board carrying two peripherals publishes one
document, and each sensor takes its own value out of it — and `received` reads the codec, the
pointer and the scaling off the sensor's own binding in the world. What `handle` answers is the
sensor and the graph written, for whoever runs the rest of a pass over them.

**IT STARTS ITSELF.** `start` subscribes, attaches, and asks after its sensors' missing readings
every `NUDGE_S` of the timeline — a board told to sense now while its reading is missing, which the
runtime once did on its behalf. Which are missing it asks sensing (`cadence.lapsed`), since what an
observation is and how they are kept are sensing's, and a transport beneath it may not name them.

**THE MEMBER BRINGS ITSELF UP, AND THE THREAD IS THE CONTAINER'S.** `connect` makes a client per
broker the environment names, in this transport's own variables — `MQTT_BROKERS`, each broker's IRI
and the url the agent reaches it at, the agent's `MQTT_USERNAME` and `MQTT_PASSWORD`, and `MQTT_CA`,
`MQTT_CERT` and `MQTT_KEY` for a url that is `mqtts` — and paho is imported there and nowhere else in
the agent. It refuses without a broker or a credential rather than guess one, for the reason no
command has a default world: a guess puts a misconfigured agent on the real topics. A message
arrives on a client's network thread, and a write belongs on the one executing thread, so
`connect` hands every message to the container's `deliver(topic, payload, at)`, which enqueues,
and the container's thread calls `handle`. A test hands a client of its own with paho's shape —
`subscribe`, `publish`, `connect`, `loop_start` and the two setters. Nothing here reads a host
or a port off the world, and nothing could: a world names its brokers in its society graph, as
what clients connect to, and where each listens is in a deployment graph — the world's own, or the
installation's allocation — a kind the agent's vocabulary does not declare and its boot passes
over (a-documents-kind-says-who-reads-it).

**A TOPIC GOES OVER A BROKER THE AGENT SHARES WITH THE CLIENT IT IS ABOUT.** A world may have any
number of brokers, and MQTT4SSN says which a client `isConnectedToBroker`: a sensor's or an
actuator's topic is carried by the brokers of the client hosting it, and a peer's by the peer's. So
the member subscribes to a sensor's topic on every broker it shares with the sensor's client, and
listens on its own topic on every broker it is connected to; a command or a document goes out on
the first broker, by IRI, that it shares with whoever it is for, and where it shares none it is
said once and not sent, as a topic with no name to publish to is. A member of one client sends
everything over it, whatever the world says, as a test's does.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime

from agent import clock
from agent.ontology import BELIEF, local_of
from agent.store import Raw, answer, graphs_of, rows
from agent.transport.transport import Transport

log = logging.getLogger("mqtt")

#  HOW OFTEN THE MEMBER ASKS AFTER ITS SENSORS' MISSING READINGS, in seconds of the one timeline.
NUDGE_S = 60.0

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

#  EVERY PATTERN NAMING A TOPIC A SENSOR PUBLISHES ON, for the sensors the agent reads — which sensing
#  says (`cadence.sensors`), since a sensor is the agent's by a role it plays, and no word of a transport's.
_TOPICS_Q = """
SELECT ?sensor ?pattern WHERE {
  VALUES ?sensor { $sensors } ?sensor mqtt4ssn:observesTopic ?topic .
  ?filter mqtt4ssn:matchesTopic ?topic ; mqtt4ssn:hasFilterPattern ?pattern }
ORDER BY ?sensor ?pattern"""


#  WHAT THIS MEMBER REACHES: a device that publishes on a topic, or listens on one, or whose board does.
_REACHES_Q = """
ASK { { $device mqtt4ssn:observesTopic ?topic } UNION { $device mqtt4ssn:listensToTopic ?topic }
      UNION { ?board ssn:hasSubSystem $device ; mqtt4ssn:listensToTopic ?topic } }"""

#  THE BROKERS A THING IS REACHED OVER: the ones it is connected to where it is a client — an agent
#  told something — and otherwise the ones of the client hosting it or the system it is part of.
_BROKERS_Q = """
SELECT DISTINCT ?broker WHERE {
  { $thing mqtt4ssn:isConnectedToBroker ?broker }
  UNION { ?client mqtt4ssn:hosts ?system ; mqtt4ssn:isConnectedToBroker ?broker . ?system ssn:hasSubSystem* $thing } }
ORDER BY ?broker"""

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

    def __init__(self, me: str, clients, deliver=None):
        """`clients` by the IRI of the broker each is connected to, or one client standing for them all."""
        self.me, self.clients = me, clients if isinstance(clients, dict) else {None: clients}
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
        """The agent's side of the bus, up: a client per broker `MQTT_BROKERS` names — its IRI, then
        the url the agent reaches it at — under the agent's credential, with its certificate where
        the url is `mqtts`, each loop running and every message handed to `deliver(topic, payload,
        at)`. `client` makes a client for a broker's IRI, where a test hands its own."""
        from urllib.parse import urlparse
        env = os.environ if environ is None else environ
        said, username = env.get("MQTT_BROKERS", "").split(), env.get("MQTT_USERNAME")
        if not said or len(said) % 2:
            raise RuntimeError("no MQTT_BROKERS in the environment, each a broker's IRI and its url — this agent is "
                               "told where its bus is, never guesses")
        if not username:
            raise RuntimeError("no MQTT_USERNAME in the environment — this agent has no credential for the bus. "
                               "Run `orexis-mqtt <world>` and regenerate the compose file.")
        if client is None:
            import paho.mqtt.client as paho                 # the one import of the library in the agent
            client = lambda _broker: paho.Client(paho.CallbackAPIVersion.VERSION2, client_id=local_of(me))
        ca, cert, key = env.get("MQTT_CA"), env.get("MQTT_CERT"), env.get("MQTT_KEY")
        clients = {}
        for broker, text in zip(said[::2], said[1::2]):
            url = urlparse(text)
            if url.scheme not in ("mqtt", "mqtts") or not url.hostname:
                raise RuntimeError(f"MQTT_BROKERS says {local_of(broker)} is at {text!r}, which is no mqtt:// or mqtts:// url")
            session = client(broker)
            if url.scheme == "mqtts":
                if not (ca and cert and key):
                    raise RuntimeError(f"{local_of(broker)} is at {text}, and the environment holds no MQTT_CA, "
                                       "MQTT_CERT and MQTT_KEY to reach it with")
                session.tls_set(ca_certs=ca, certfile=cert, keyfile=key)
            session.username_pw_set(username, env.get("MQTT_PASSWORD"))
            clients[broker] = session
        member = cls(me, clients, deliver)
        for broker, session in clients.items():
            url = urlparse(said[said.index(broker) + 1])
            session.on_message = lambda _client, _userdata, message: member.deliver(message.topic, message.payload, clock.now())
            session.connect(url.hostname, url.port or {"mqtt": 1883, "mqtts": 8883}[url.scheme])
            session.loop_start()
            log.info("%s on %s at %s:%s%s", local_of(me), local_of(broker), url.hostname, url.port,
                     " with a certificate" if url.scheme == "mqtts" else "")
        return member

    def start(self, runtime) -> None:
        """Begin as every member does, and ask after the missing readings of this member's sensors
        every `NUDGE_S`: a board is told to sense now once a minute while its reading is missing."""
        super().start(runtime)
        runtime.every(NUDGE_S, lambda: self.nudge(runtime.beliefs, runtime.now))

    def stop(self) -> None:
        for client in self.clients.values():
            loop_stop, disconnect = getattr(client, "loop_stop", None), getattr(client, "disconnect", None)
            if loop_stop and disconnect:
                loop_stop()
                disconnect()

    def _over(self, store, thing: str) -> list:
        """The clients `thing` is reached over: each broker this member is connected to that the world
        says carries it, by IRI; the one client, where the member has one."""
        if None in self.clients:
            return [self.clients[None]]
        carried = [r["broker"] for r in rows(store, _BROKERS_Q, graphs_of(store, BELIEF, common=True), thing=thing)]
        return [self.clients[b] for b in carried if b in self.clients]

    def _topics(self, store) -> list[dict]:
        """Every sensor the agent reads that publishes on a topic, with each pattern naming it. Which
        sensors are the agent's is sensing's to say (`cadence.sensors`), imported here as `lapsed` is
        where a message is handed on: sensing is loaded where the agent reads a sensor at all."""
        from agent.sensing.cadence import sensors
        mine = sensors(store)
        if not mine:
            return []
        return rows(store, _TOPICS_Q, graphs_of(store, BELIEF, common=True), sensors=Raw(" ".join(f"<{s}>" for s in mine)))

    def nudge(self, store, now: datetime) -> list[str]:
        """Tell the board of every sensor of this member's whose reading has fallen due to sense now;
        the sensors asked. Writes nothing. Which readings have fallen due is SENSING'S to say
        (`cadence.lapsed`): an observation is its kind and no word of a transport's, so the member
        asks, as it hands `received` the bytes (#944) — imported here, as `received` is, so a member
        that only listens never loads sensing."""
        from agent.sensing.cadence import lapsed
        mine = {r["sensor"] for r in self._topics(store)}
        asked = list(dict.fromkeys(sensor for sensor, _ in lapsed(store, now) if sensor in mine))
        for sensor in asked:
            self.sense_now(store, sensor)
        return []

    def reaches(self, store, device: str) -> bool:
        return bool(answer(store, _REACHES_Q, graphs_of(store, BELIEF, common=True), device=device)["boolean"])

    def set_cadence(self, store, sensor: str, sleep_s: int) -> bool:
        topic = self._command_topic(store, sensor)
        if topic is None:
            return False
        return self.publish(store, sensor, topic, {"sleep_s": int(sleep_s)}, True)

    def actuate(self, store, actuator: str, payload: dict) -> bool:
        """Publish a step's command on the topic the actuator listens to, or its board's; not
        retained, since a command is an act and a retained one would be taken again by a device
        that reconnects."""
        names = [p for p in (r["pattern"] for r in rows(store, _ACTUATES_Q, graphs_of(store, BELIEF, common=True), actuator=actuator))
                 if "+" not in p and "#" not in p]
        if not names:
            return self._unreached(actuator, "the command is not sent")
        if not self.publish(store, actuator, names[0], payload, False):
            return False
        self._unreachable.discard(actuator)
        log.info("%s: %s on %s", local_of(actuator), payload, names[0])
        return True

    def sense_now(self, store, sensor: str) -> None:
        topic = self._command_topic(store, sensor)
        if topic is not None:
            self.publish(store, sensor, topic, {"sense": True}, False)

    def tell(self, store, to: str, document: bytes) -> bool:
        """Publish a document on the topic the agent `to` listens to, by a pattern with no
        wildcard; not retained, since what was said is said once."""
        names = [p for p in (r["pattern"] for r in rows(store, _LISTENS_Q, graphs_of(store, BELIEF, common=True), agent=to))
                 if "+" not in p and "#" not in p]
        if not names:
            return self._unreached(to, "nothing said to it is sent")
        over = self._over(store, to)
        if not over:
            return self._unshared(to, "nothing said to it is sent")
        self._unreachable.discard(to)
        over[0].publish(names[0], document, retain=False)
        log.info("told %s on %s", local_of(to), names[0])
        return True

    def open(self, store) -> list[str]:
        """Subscribe to every pattern the world implies for the agent's sensors, and to the topic
        it listens to itself; the patterns."""
        own = {r["pattern"] for r in rows(store, _LISTENS_Q, graphs_of(store, BELIEF, common=True), agent=self.me)}
        on = {id(c): (c, set(own)) for c in self.clients.values()}
        for r in self._topics(store):
            for client in self._over(store, r["sensor"]):
                on[id(client)][1].add(r["pattern"])
        for client, patterns in on.values():
            for pattern in sorted(patterns):
                client.subscribe(pattern)
        patterns = sorted(set().union(*(p for _, p in on.values())))
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
        refuses a topic listened to by no speaker and a sensor reporting to no observer role — so an
        agent that only senses never loads speech (#824, #927). Sensing it does load, to ask which
        sensors are its (`cadence.sensors`), since which are is a role's word and no transport's."""
        if any(matches(r["pattern"], topic) for r in rows(store, _LISTENS_Q, graphs_of(store, BELIEF, common=True), agent=self.me)):
            from agent.speech.heard import heard
            return [(None, graph) for graph in heard(store, self.me, payload)]
        mine = list(dict.fromkeys(r["sensor"] for r in self._topics(store) if matches(r["pattern"], topic)))
        if not mine:
            log.debug("%s: a message on %s is nobody's of mine", local_of(self.me), topic)
            return []
        from agent.sensing.received import received
        written = []
        for sensor in mine:
            written += [(sensor, graph) for graph in received(store, self.me, sensor, payload, at, memo=memo)]
        return written

    def publish(self, store, device: str, topic: str, payload: dict, retain: bool) -> bool:
        """A command to `device` out, as the JSON document the firmware reads, over the first broker
        this member shares with it; False, said once, where it shares none."""
        over = self._over(store, device)
        if not over:
            return self._unshared(device, "no command is sent")
        over[0].publish(topic, json.dumps(payload).encode(), retain=retain)
        return True

    def _unshared(self, who: str, what: str) -> bool:
        """Say once that `who` is on no broker this member is connected to, and False."""
        if who not in self._unreachable:
            self._unreachable.add(who)
            log.warning("%s is on no broker this agent is connected to, so %s", local_of(who), what)
        return False

    def _command_topic(self, store, sensor: str) -> str | None:
        """The topic name the sensor's board takes commands on: a pattern of a filter matching
        it with no wildcard, since a publish takes a name. None, said in the log, where the
        board listens nowhere or every pattern is a wildcard."""
        patterns = [r["pattern"] for r in rows(store, _COMMANDS_Q, graphs_of(store, BELIEF, common=True), sensor=sensor)]
        names = [p for p in patterns if "+" not in p and "#" not in p]
        if not names:
            log.warning("%s: its board listens on %s, and none is a topic name to publish to",
                        local_of(sensor), patterns or "no topic")
            return None
        return names[0]
