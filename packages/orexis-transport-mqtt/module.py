"""Linking: the agent's connection to its society, as a capability module the bus grants.

**The kernel has no mailbox.** It used to: a paho client in the runtime, a dispatch loop that
handed every message to every module, `subscriptions` and `handle` on `Module`, a watchdog on
the session, `mqtt_connected` in the health series. None of that is BDI — an agent perceives
and acts through capabilities, and how bytes move is a capability like any other, with
interchangeable implementations. So this module holds all of it, granted to every agent by
the fact of a bus in the world (`rules.ru`), found like any capability through `PROVIDES`,
and speaking to the rest of the agent through the choir alone:

- `subscriptions` — asked of every module once the session is up: which channels do you need;
- `handle(channel, payload)` — every arriving message, offered to every module; nobody taking
  it is logged, because a topic disagreement looks exactly like a device that never speaks;
- `send(channel, payload, retain)` — what `Module.publish` tells, and this module carries.

The credential and the certificate arrive in the environment under this transport's names,
minted by `orexis-mqtt`; the bus is found in the world in this transport's words. See
knowledge/decisions/the-kernel-has-no-mailbox.md and knowledge/domain/transport.md.
"""

from __future__ import annotations

import json
import logging
import time

import paho.mqtt.client as mqtt

from agent import config
from agent.module import Module, contributes
from modality.ontology import HANDLE, SEND, SUBSCRIPTIONS
from modality.store import bindings

from .watchdog import BusWatchdog

log = logging.getLogger("mqtt")

LINKING = "http://example.org/orexis/mqtt#Linking"

#  Where the society meets: the one piece of infrastructure that is a belief, not an
#  environment variable — because everyone must agree on it. Two buses would be a routing
#  question (`mqtt:onBus`) nothing here decides.
_BUS_Q = """
SELECT ?bus ?host ?port ?tlsPort WHERE {
  ?bus a mqtt:MessageBus ; mqtt:brokerHost ?host ; mqtt:brokerPort ?port .
  OPTIONAL { ?bus mqtt:brokerTlsPort ?tlsPort }  }"""


class MqttModule(Module):
    """The connection, the delivery loop, and the watchdog on the session."""

    CAPABILITY = LINKING
    name = "mqtt"

    def __init__(self, agent):
        super().__init__(agent)
        rows = bindings(agent.beliefs.query(_BUS_Q))
        if not rows:
            raise RuntimeError("the world declares no mqtt:MessageBus — has it been seeded?")
        if len(rows) > 1:
            raise RuntimeError(f"{len(rows)} buses declared; mqtt:onBus routing is not implemented")
        row = rows[0]
        self.uri, self.host, self.port = row["bus"], row["host"], int(row["port"])
        #  Optional second door on the SAME bus, where a principal proves itself with a
        #  certificate instead of a password. Not a different bus: same topics, same ACL.
        self.tls_port = int(row["tlsPort"]) if row.get("tlsPort") else None
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.client.on_connect = lambda c, u, f, rc, p: self._on_connect()
        self.client.on_disconnect = lambda c, u, f, rc, p: self._on_disconnect(rc)
        self.client.on_message = lambda c, u, msg: self._on_message(msg.topic, msg.payload)
        #  The session's story, for the watchdog and the health series. Born disconnected,
        #  and the clock starts NOW, deliberately: an agent whose first connect never
        #  completes — a broker refusing its CONNACK in a loop — is exactly as cut off as one
        #  whose session died, and must meet the same bound (#53).
        self.connected = False
        self.reconnects = -1     # the first connect is not a RE-connect
        self.disconnected_at: float | None = time.monotonic()
        self.watchdog = BusWatchdog(self)

    # --- the session ---------------------------------------------------------------------

    def start(self) -> None:
        username = config.env("MQTT_USERNAME")
        if not username:
            raise RuntimeError(
                "no MQTT_USERNAME in the environment — this agent has no credential for the "
                "bus. Run `orexis-mqtt <world>` and regenerate the compose file.")
        cert, key, ca = (config.env("MQTT_CERT"), config.env("MQTT_KEY"), config.env("MQTT_CA"))
        if self.tls_port and cert and key and ca:
            self.client.tls_set(ca_certs=ca, certfile=cert, keyfile=key)
            port = self.tls_port
            self.log.info("connecting to %s:%s with a certificate", self.host, port)
        else:
            port = self.port
            if self.tls_port:
                self.log.warning("the world states a TLS port but I hold no certificate — "
                                 "connecting by password. Re-run `orexis-onboard`.")
        self.client.username_pw_set(username, config.env("MQTT_PASSWORD"))
        self.client.connect(self.host, port)
        self.client.loop_start()
        self.watchdog.start()

    def stop(self) -> None:
        self.watchdog.stop()
        self.client.loop_stop()
        self.client.disconnect()

    def _on_connect(self) -> None:
        #  Wrapped whole, like _on_message's per-module dispatch: an exception escaping any
        #  callback kills paho's network thread, and a dead network thread is the one failure
        #  that silences every future callback including the disconnect that would report it
        #  (#53). The watchdog checks for that corpse anyway.
        try:
            self.connected = True
            self.reconnects += 1
            self.disconnected_at = None
            topics = [t for wanted in self.agent.ask(SUBSCRIPTIONS) for t in wanted]
            for topic in topics:
                self.client.subscribe(topic)
            #  The topics, spelled out. An agent subscribed to the wrong thing looks exactly
            #  like a device that never speaks, and this is the line that tells them apart —
            #  readable against the ACL and against the board's own config.
            for topic in topics:
                self.log.info("listening on %s", topic)
            if not topics:
                self.log.warning("subscribed to NOTHING — this agent will never hear anything")
        except Exception as exc:
            self.log.error("failed while taking up a connection: %s", exc)

    def _on_disconnect(self, reason_code) -> None:
        self.connected = False
        #  Only the FIRST notice starts the clock: paho may report one dead session more than
        #  once, and each repeat is the same outage, not a fresh one. Logged at WARNING with
        #  the reason — a drop with no matching "listening on" after it is the shape of the
        #  fault that cost two days (#53).
        if self.disconnected_at is None:
            self.disconnected_at = time.monotonic()
        self.log.warning("disconnected from the bus (%s) — paho will retry", reason_code)

    def _on_message(self, topic: str, payload: bytes) -> None:
        """Offer the message to EVERY module, and note whether any of them wanted it.

        Every module, never the first taker: a second module subscribed to the same topic must
        see it too (actuation reading its valves' status beside hosting). Nobody claiming it is
        a WARNING — the world names one channel, the device publishes on another, both ends
        look healthy, and the message would be dropped in silence.
        """
        if not any(self.agent.ask(HANDLE, topic, payload)):
            self.log.warning("nothing handled a message on %s", topic)

    # --- the choir: what the rest of the agent asks of me ---------------------------------

    @contributes(SEND)
    def send(self, channel: str, payload: dict, retain: bool = False, not_after=None) -> bool:
        """What `Module.publish` asks: carry this to the society, and say whether it left.

        **A message with a deadline is never queued.** With no session, paho holds a QoS 1
        publish and delivers it on reconnect — which is right for a cadence a board should
        have whenever it wakes, and wrong for anything the agent may stop meaning: a bid
        arriving after its round closed is a message nobody wants, and the sender cannot tell
        a lost bid from a losing one. So a message that states when it stops mattering is
        refused while the link is down, and whoever asked treats that as *not now* — the act
        stands, and the trigger that changes the answer takes it again
        (publishing-is-a-goal-and-the-protocol-is-a-primitive).

        Everything else is queued exactly as before, which is what a boot-time cadence relies
        on: modules start before the session is up.
        """
        if not_after is not None and not self.connected:
            self.log.info("%s not sent: no session, and it is worth nothing after %s",
                          channel, not_after)
            return False
        self.client.publish(channel, json.dumps(payload), qos=1, retain=retain)
        return self.connected

    def disconnected_for_s(self) -> float | None:
        """How long the session has been down, or None while it is up. Flapping is a different
        fault, and `reconnects` is its counter."""
        return None if self.disconnected_at is None else time.monotonic() - self.disconnected_at

    def alive(self) -> bool | None:
        """Paho's loop thread, if it has ever existed. `_thread` is paho's private attribute,
        and reaching for it is the deliberate price of watching a thing that offers no public
        pulse: if a future paho renames it, this answers None and the watchdog's disconnect
        bound stands guard behind it."""
        thread = getattr(self.client, "_thread", None)
        return None if thread is None else bool(thread.is_alive())

    def reports(self) -> dict:
        return {"link_connected": 1 if self.connected else 0,
                "link_reconnects": max(self.reconnects, 0)}
