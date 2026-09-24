"""`Link`: the agent's MQTT client, wrapped — what to subscribe to, where a message goes, how a
command leaves. The socket is the container's: it makes the client with the broker's address and
the agent's credentials from the environment, connects it and runs its loop, and hands it here.

The client is anything with paho's shape — `subscribe(pattern)`, `publish(topic, payload,
retain=)`, and an `on_message` the link sets — so a test hands a stand-in and a container hands
paho. What is subscribed is derived: the patterns naming the topics of every sensor of the
agent's, the same read `handle` routes by.
"""

from __future__ import annotations

import json
import logging

from agent import clock
from agent.ontology import PUBLIC
from agent.store import graphs_of, rows

from .driver import Mqtt
from .handle import MINE_Q, handle

log = logging.getLogger("mqtt")


class Link:
    """One agent's side of the bus."""

    def __init__(self, store, me: str, client, *, now=None):
        self.store, self.me, self.client = store, me, client
        self.now = now or clock.now
        self.driver = Mqtt(self.publish)
        client.on_message = self._on_message

    def open(self) -> list[str]:
        """Subscribe to every pattern the world implies for the agent's sensors; the patterns."""
        patterns = sorted({r["pattern"] for r in rows(self.store, MINE_Q, graphs_of(self.store, PUBLIC), me=self.me)})
        for pattern in patterns:
            self.client.subscribe(pattern)
        log.info("listening on %s", patterns or "nothing")
        return patterns

    def publish(self, topic: str, payload: dict, retain: bool) -> None:
        """A command out, as the JSON document the firmware reads."""
        self.client.publish(topic, json.dumps(payload).encode(), retain=retain)

    def _on_message(self, client, userdata, message) -> None:
        handle(self.store, self.me, message.topic, message.payload, self.now())
