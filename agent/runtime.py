"""One agent, one process. It is given its own id and discovers everything else.

  AGORA_AGENT_ID=fern agora-agent

Startup builds its own belief base and then reads it:

  0. the ratified **world files** are loaded into a store that belongs to this process alone,
     and the derivation rules are re-run over them — so what this agent can do is computed
     from the world, not told to it, and no shared service has to be up for that to happen;
  1. the **world** says what I am — what I act for, what I may poll, which market I belong
     to, what I can do, where each of those lives on the wire, and which bus to meet on;
  2. my **own beliefs** supply the parameters for each capability I composed. They are written
     once, at birth, and are mine thereafter — a restart does not touch them;
  3. the **packages** implementing those capabilities are loaded, and nothing else runs;
  4. those beliefs are **validated against the shapes of the capabilities I derived**, and I
     refuse to run if they do not hold — the check belongs where the data is.

The environment tells it which agent it is and where to keep its store. Everything else —
including the broker — is discovered, because a channel name is meaningless without the bus it
is on and every member must agree on it.

Nothing in this process can reach another agent's beliefs, and no module knows the name of
any instance. Adding a capability to an agent is a genesis edit: compose the capability in
the world, add its block of beliefs, and the module starts running at next boot.

See knowledge/decisions/capability-packages.md.
"""

from __future__ import annotations

import logging
import signal

import paho.mqtt.client as mqtt

from . import config, genesis, loader
from .beliefs import Beliefs
from .metrics import Metrics
from .upkeep import BeliefBaseUpkeep
from .store import bindings
from .watchdog import BusWatchdog
from .validate import validate_agent
from .world import MessageBus, Self, World, load_bus, load_self, load_world

log = logging.getLogger("agent")


def _family_q(family: str) -> str:
    """Which capability terms belong to a family. Asked of the T-Box, so a module can look
    for "whoever perceives" without knowing that polling and listening are the two ways.

    Two branches, and the second is not the tidy-up it looks like. A caller may name a family
    (`sensing:SensingCapability`, whose members are `sensing:Subscribing` and `sensing:Listening`) or it may
    name a capability that is its own family of one — `agent.provider(ACTUATION)` does exactly
    that, and there is no term anywhere declared `a actuation:Actuation`. That used to work by accident:
    the branch said `rdfs:subClassOf*`, and a zero-length path matches reflexively, so the family
    returned itself. Stating it is the same answer without depending on a property path's
    reflexivity to carry a case nobody had written down.

    The subclass walk itself is gone. `agora/inference.py` asserts what the vocabulary entails
    before anything reads it, so a capability under a sub-family already carries the parent's
    type here.
    """
    return f"""
SELECT ?capability WHERE {{
  {{ GRAPH ?g {{ ?capability a <{family}> }} }}
  UNION
  {{ BIND(<{family}> AS ?capability) }}
}}"""


class Agent:
    """A single agent: its identity, its beliefs, its modules, and one connection."""

    def __init__(self, agent_id: str, st=None):
        self.id = agent_id
        # My own store, built from the ratified files. Nothing else can reach it — that is the
        # isolation, and it is structural rather than enforced.
        self.store = st or genesis.open_belief_base(
            genesis.current_world(), agent_id, config.env("AGORA_STORE"))
        self.world: World = load_world(self.store.query)
        self.bus: MessageBus = load_bus(self.store.query)  # discovered, not configured
        self.me: Self = load_self(self.store.query, agent_id)
        self.beliefs = Beliefs(self.store.query, agent_id, self.me.uri)

        # Built before the modules, because Observations counts into it and a module builds one
        # of those. Counting only — nothing is reported until run() starts it.
        self.metrics = Metrics(self)

        self.mqtt = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.mqtt.on_connect = self._on_connect
        self.mqtt.on_disconnect = self._on_disconnect
        self.mqtt.on_message = self._on_message

        # exactly the modules this agent composed — no more, no less, and since #216 the
        # IMPORTS follow the grants too: a capability names its owning package by namespace,
        # so nothing this agent was not granted is ever imported into this process.
        registry = loader.registry_for(self.me.capabilities)
        self.modules = [
            registry[c](self) for c in sorted(self.me.capabilities) if c in registry
        ]
        unknown = [c for c in sorted(self.me.capabilities) if c not in registry]
        if unknown:
            log.warning("no package implements %s — the world expects more than this build has",
                        ", ".join(unknown))

        # Check myself before acting. A shape applies only to capabilities I actually derived,
        # so this asks exactly the right questions — and refusing to start is the enforcement.
        # It is not self-report: the consequence is not running, not a claim to be fine.
        validate_agent(self.store, agent_id, self.me.uri, self.me.capabilities)

        # Keeping my own house. Not a capability and never optional: every agent's belief base
        # bloats whatever else it can do, so this holds a clock no capability owns — an agent
        # given no room to review itself must still compact. Nothing here starts a thread.
        self.upkeep = BeliefBaseUpkeep(self)

        # And noticing I am cut off (#53) — kernel for the same reason, on a clock of its own
        # because paho's network thread is one of the things it watches. Nothing starts here.
        self.watchdog = BusWatchdog(self)

    # --- how one capability reaches another, without knowing its name ---

    def provider(self, family: str):
        """Whichever of MY modules provides a capability of this family, or None.

        The family is a T-Box term, so the caller asks for "something that perceives" rather
        than for `SubscribingModule`. That is the whole point: no capability package imports
        another's Python, so any of them can be removed without breaking the rest. None is a
        normal answer — an agent that composed neither is simply an agent that cannot.
        """
        members = {r["capability"] for r in bindings(self.store.query(_family_q(family)))}
        return next((m for m in self.modules if m.CAPABILITY in members), None)

    def annotations(self, subject_uri: str, observed_property: str, value: float) -> dict:
        """Everything my modules want to say about a reading of mine, merged.

        This is what makes my announcement *mine* rather than sensing's: whoever holds an
        opinion contributes it, and a module with no stake contributes nothing.
        """
        out: dict = {}
        for module in self.modules:
            try:
                out.update(module.annotate(subject_uri, observed_property, value))
            except Exception as exc:
                log.error("%s: %s could not annotate a reading: %s", self.id, module.name, exc)
        return out

    def bounds(self, subject_uri: str, observed_property: str) -> tuple[float, float] | None:
        """The tightest band any of my modules wants this property held in, or None.

        Collected like urgency — whoever holds a stake contributes, and the intersection is
        what a crossing-watching board is told to announce on leaving (#151): the highest
        floor and the lowest ceiling, because a board that woke for the loosest opinion would
        sleep through the tightest one's trouble.
        """
        answers = []
        for module in self.modules:
            try:
                answer = module.bounds(subject_uri, observed_property)
            except Exception as exc:
                log.error("%s: %s could not state bounds: %s", self.id, module.name, exc)
                continue
            if answer is not None:
                answers.append(answer)
        if not answers:
            return None
        return max(low for low, _ in answers), min(high for _, high in answers)

    def urgency(self, subject_uri: str, observed_property: str,
                value: float | None) -> float | None:
        """How close this reading puts me to trouble — the sharpest opinion any of me holds.

        `value` None asks a different question of the same choir: how urgent is not knowing.
        """
        opinions = []
        for module in self.modules:
            try:
                opinion = module.urgency(subject_uri, observed_property, value)
            except Exception as exc:
                log.error("%s: %s could not judge a reading: %s", self.id, module.name, exc)
                continue
            if opinion is not None:
                opinions.append(opinion)
        return max(opinions) if opinions else None

    # --- the shared connection; modules route by the topics they asked for ---

    def publish(self, topic: str, payload: dict, retain: bool = False) -> None:
        import json

        self.mqtt.publish(topic, json.dumps(payload), qos=1, retain=retain)

    def _on_connect(self, client, userdata, flags, reason_code, properties) -> None:
        # Wrapped whole, like _on_message's per-module dispatch: an exception escaping any
        # callback kills paho's network thread, and a dead network thread is the one failure
        # that silences every future callback including the disconnect that would report it
        # (#53). The watchdog checks for that corpse anyway — this makes it a check that
        # should never fire, which is what a watchdog's checks should be.
        try:
            self.metrics.connected()
            topics = []
            for module in self.modules:
                for topic in module.subscriptions():
                    client.subscribe(topic)
                    topics.append(topic)
            log.info("%s up — world v%s, running %s", self.id, self.world.version,
                     ", ".join(m.name for m in self.modules) or "nothing")
            # The topics, spelled out. An agent subscribed to the wrong thing looks exactly
            # like a device that never speaks, and this is the one line that tells them apart —
            # it can be read against the ACL and against the board's own config without
            # guessing.
            for topic in topics:
                log.info("%s: listening on %s", self.id, topic)
            if not topics:
                log.warning("%s: subscribed to NOTHING — it will never hear anything", self.id)
        except Exception as exc:
            log.error("%s: failed while taking up a connection: %s", self.id, exc)

    def _on_disconnect(self, client, userdata, flags, reason_code, properties) -> None:
        self.metrics.disconnected()
        # It used to be counted and NOT logged, on the reasoning that a reconnecting agent is
        # normal on a marginal link and the count over time is what matters. That reasoning is
        # right about flapping and wrong about the case it actually produced: this agent lost
        # its session and never came back, and the container went on looking perfectly healthy
        # for two days while nothing was ingested. The metric existed and nobody was watching a
        # metric, because nothing had gone visibly wrong.
        #
        # Logged at WARNING with the reason, and _on_connect already logs the way back. A
        # flapping link therefore shows as paired lines — which is information about the link,
        # not noise to be suppressed. A drop with no matching "up" line after it is the shape of
        # the fault that cost the two days.
        log.warning("%s: disconnected from the bus (%s) — paho will retry", self.id, reason_code)

    def reading_recorded(self, subject_uri: str, observed_property: str, value: float) -> None:
        """Sensing tells the rest of me that something new is known.

        The agent's own modules are the only audience: this is me noticing, not me telling
        anyone. It is what lets a bid wait for the reading it asked for instead of using
        whatever happened to be lying around — and, now that a subject can have two sensors,
        for it to wait for the reading it asked for rather than for the next one to arrive.
        """
        for module in self.modules:
            try:
                module.on_reading_recorded(subject_uri, observed_property, value)
            except Exception as exc:
                log.error("%s: %s failed on a new reading: %s", self.id, module.name, exc)

    def _on_message(self, client, userdata, msg) -> None:
        """Offer the message to EVERY module, and note whether any of them wanted it.

        It used to `return` on the first module whose `handle` came back true, which read as an
        optimisation and was a defect: a second module subscribed to the same topic never saw
        the message, and nothing anywhere said so. Exactly what #51 fixed one level down, where
        `SensingModule.handle` returned after the first SENSOR owning a topic and a board's
        second channel went unread.

        It stayed here because nothing wanted one topic twice. Actuation reading its valves'
        status is the case that wants it — a supplier runs actuation beside hosting — and the
        old loop would have handed the status to whichever module came first in the list.

        `reading_recorded` above has always offered to every module. This is the same shape,
        and the two now agree.
        """
        handled = False
        for module in self.modules:
            try:
                if module.handle(msg.topic, msg.payload):
                    handled = True
            except Exception as exc:  # one bad message must not take the agent down
                log.error("%s: %s failed on %s: %s", self.id, module.name, msg.topic, exc)
        if handled:
            return
        # Nobody claimed it, and until now nobody said so. This is the shape a topic
        # disagreement takes — the world names one channel, the device publishes on another,
        # both ends look healthy, and the message is dropped in silence. It cannot be an error
        # (a wildcard subscription may legitimately catch more than one module wants) but it
        # must not be invisible.
        #
        # `handled` means at least one module TOOK it, not that every module was asked. The
        # difference is the whole value of this line: offering the message to everyone would
        # otherwise silence the warning for ever.
        log.warning("%s: nothing handled a message on %s", self.id, msg.topic)

    def run(self) -> None:
        # Who I am on the bus. The broker refuses anonymous connections, and the ACL it holds
        # grants this principal exactly the topics the world wires me to — so a missing
        # credential is a deployment fault worth naming here rather than a bare "Not
        # authorized" from the broker. Set at run() and not at construction: it is needed to
        # connect, and nothing that merely builds an agent should require it.
        username = config.env("MQTT_USERNAME")
        if not username:
            raise RuntimeError(
                "no MQTT_USERNAME in the environment — this agent has no credential for the "
                "bus. Run `agora-mqtt <world>` and regenerate the compose file.")
        cert, key, ca = (config.env("MQTT_CERT"), config.env("MQTT_KEY"), config.env("MQTT_CA"))
        if self.bus.tls_port and cert and key and ca:
            # Prove who I am with the certificate onboarding issued me. Its CN *is* the username
            # above, and the broker authorises on that — so the same ACL applies whichever door
            # I came through, and there is no second notion of identity to keep in step.
            #
            # username_pw_set stays: the broker takes the identity from the certificate, and a
            # username costs nothing to send and makes the connection legible in its log.
            self.mqtt.tls_set(ca_certs=ca, certfile=cert, keyfile=key)
            port = self.bus.tls_port
            log.info("%s: connecting with a certificate", self.id)
        else:
            port = self.bus.port
            if self.bus.tls_port:
                # The world offers mTLS and this container was not given a certificate. Not
                # fatal — the password door is still open and the ACL is the same — but it is
                # a downgrade nobody asked for, so it is said out loud.
                log.warning("%s: the world states a TLS port but I hold no certificate — "
                            "connecting by password. Re-run `agora-onboard`.", self.id)
        # Block them FIRST, then wait. Two reasons, and the second is the one that bit:
        #
        #   - `sigwait` requires it. Its own contract is that the signals be blocked in every
        #     thread beforehand; otherwise the behaviour is undefined.
        #   - an agent is PID 1 in its container, and the kernel discards a signal whose action
        #     is still the default for a namespace's init. Waiting is not handling, so SIGTERM
        #     was dropped on the floor and `podman stop` sat out its ten seconds before
        #     SIGKILL — which meant no module ever got stop(), the Influx writer never flushed,
        #     and the belief base was never closed. Blocking makes the signal PENDING rather
        #     than defaulted, which is delivered to init like any other.
        #
        # Set before the modules start, so their threads inherit the mask and this thread is the
        # one that receives it.
        signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGINT, signal.SIGTERM})

        self.mqtt.username_pw_set(username, config.env("MQTT_PASSWORD"))
        self.mqtt.connect(self.bus.host, port)
        self.mqtt.loop_start()
        # After the mask, so the timer thread inherits it and this thread stays the one that
        # wakes on a signal. Its thread is a daemon, so it cannot hold the process open either.
        # Upkeep runs for everyone, on its own clock, and is NOT a capability: nothing about
        # reclaiming your own disk could be done differently. Started here rather than at
        # construction so that building an agent starts no threads and a test can hold one
        # without it acting. Reporting used to start here too and is a module now — mandatory,
        # granted to every agent, and started below with the rest.
        self.upkeep.start()
        # The watchdog last, after the connect above has had its chance: its disconnection
        # clock started at construction, so an agent that never gets its CONNACK is already
        # being timed. When it resigns it sends SIGTERM to this process — blocked, pending,
        # and received by the sigwait below exactly as `podman stop`'s would be, so a
        # resignation IS a clean shutdown and the container's restart policy is the recovery.
        self.watchdog.start()
        for module in self.modules:
            module.start()

        try:
            signal.sigwait({signal.SIGINT, signal.SIGTERM})
        except KeyboardInterrupt:
            pass
        finally:
            log.info("%s shutting down", self.id)
            for module in self.modules:
                module.stop()
            self.watchdog.stop()
            self.upkeep.stop()
            self.mqtt.loop_stop()
            self.mqtt.disconnect()


def main() -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)-7s %(name)s: %(message)s"
    )
    agent_id = config.env("AGORA_AGENT_ID")
    if not agent_id:
        raise SystemExit(
            "AGORA_AGENT_ID is required — an agent process is one agent, and its id is the "
            "only thing it is told. Try: AGORA_AGENT_ID=fern agora-agent"
        )
    Agent(agent_id).run()


if __name__ == "__main__":
    main()
