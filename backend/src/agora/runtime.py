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
from .store import bindings
from .validate import validate_agent
from .world import MessageBus, Self, World, load_bus, load_self, load_world

log = logging.getLogger("agent")


def _family_q(family: str) -> str:
    """Which capability terms belong to a family. Asked of the T-Box, so a module can look
    for "whoever perceives" without knowing that polling and listening are the two ways."""
    return f"""
SELECT ?capability WHERE {{ GRAPH ?g {{
  {{ ?capability a <{family}> }} UNION {{ ?capability rdfs:subClassOf* <{family}> }}
}} }}"""


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

        self.mqtt = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.mqtt.on_connect = self._on_connect
        self.mqtt.on_message = self._on_message

        # exactly the modules this agent composed — no more, no less
        registry = loader.registry()
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

    def annotations(self, subject_uri: str, value: float) -> dict:
        """Everything my modules want to say about a reading of mine, merged.

        This is what makes my announcement *mine* rather than perception's: whoever holds an
        opinion contributes it, and a module with no stake contributes nothing.
        """
        out: dict = {}
        for module in self.modules:
            try:
                out.update(module.annotate(subject_uri, value))
            except Exception as exc:
                log.error("%s: %s could not annotate a reading: %s", self.id, module.name, exc)
        return out

    def urgency(self, subject_uri: str, value: float) -> float | None:
        """How close this reading puts me to trouble — the sharpest opinion any of me holds."""
        opinions = []
        for module in self.modules:
            try:
                opinion = module.urgency(subject_uri, value)
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
        for module in self.modules:
            for topic in module.subscriptions():
                client.subscribe(topic)
        log.info("%s up — world v%s, running %s", self.id, self.world.version,
                 ", ".join(m.name for m in self.modules) or "nothing")

    def reading_recorded(self, subject_uri: str, value: float) -> None:
        """Perception tells the rest of me that something new is known.

        The agent's own modules are the only audience: this is me noticing, not me telling
        anyone. It is what lets a bid wait for the reading it asked for instead of using
        whatever happened to be lying around.
        """
        for module in self.modules:
            try:
                module.on_reading_recorded(subject_uri, value)
            except Exception as exc:
                log.error("%s: %s failed on a new reading: %s", self.id, module.name, exc)

    def _on_message(self, client, userdata, msg) -> None:
        for module in self.modules:
            try:
                if module.handle(msg.topic, msg.payload):
                    return
            except Exception as exc:  # one bad message must not take the agent down
                log.error("%s: %s failed on %s: %s", self.id, module.name, msg.topic, exc)

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
        self.mqtt.username_pw_set(username, config.env("MQTT_PASSWORD"))
        self.mqtt.connect(self.bus.host, port)
        self.mqtt.loop_start()
        for module in self.modules:
            module.start()

        stop = signal.sigwait  # block until INT/TERM, letting module timers run in their threads
        try:
            stop({signal.SIGINT, signal.SIGTERM})
        except KeyboardInterrupt:
            pass
        finally:
            log.info("%s shutting down", self.id)
            for module in self.modules:
                module.stop()
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
