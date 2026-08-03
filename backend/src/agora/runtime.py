"""One agent, one process. It is given its own id and discovers everything else.

  AGORA_AGENT_ID=fern agora-agent

Startup is three reads and no configuration:

  1. the **world** says what I am — what I act for, what I may poll, which market I belong
     to, what I can do, where each of those lives on the wire, and which bus to meet on;
  2. my **own beliefs** supply the parameters for each capability I composed;
  3. the **packages** implementing those capabilities are loaded, and nothing else runs.

The environment tells it two things only: which agent it is, and where the belief base is.
Everything else — including the broker — is discovered, because a channel name is meaningless
without the bus it is on and every member must agree on it.

Nothing in this process can reach another agent's beliefs, and no module knows the name of
any instance. Adding a capability to an agent is a genesis edit: compose the capability in
the world, add its block of beliefs, and the module starts running at next boot.

See knowledge/decisions/capability-packages.md.
"""

from __future__ import annotations

import logging
import signal

import paho.mqtt.client as mqtt

from . import config, loader, store
from .beliefs import Beliefs
from .store import bindings
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
        self.store = st or store.from_env(config.env, agent_id)  # as myself, not as admin
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
        self.mqtt.connect(self.bus.host, self.bus.port)
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
