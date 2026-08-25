"""The MQTT link: how an agent reaches its society over a broker.

`agent.link.Link`, implemented. Everything the kernel's runtime used to hold about MQTT is
here — the paho client, the world's `mqtt:MessageBus` and its two doors, the credential and
certificate names in the environment, the private loop thread the watchdog wants a pulse
from — and the kernel asks for it through the contract alone (the-link-is-the-transports).

`orexis-mqtt` mints the credential this reads and generates the ACL the broker enforces; see
knowledge/decisions/series-and-bus-isolation.md.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import paho.mqtt.client as mqtt

from agent import config
from agent.link import Link
from agent.store import bindings

log = logging.getLogger("mqtt")

#  Where the society meets: the one piece of infrastructure that is a belief, not an
#  environment variable — because everyone must agree on it. Two buses would be a routing
#  question (`mqtt:onBus`) nothing here decides, and the kernel refuses two answers.
_BUS_Q = """
SELECT ?bus ?host ?port ?tlsPort WHERE {
  ?bus a mqtt:MessageBus ; mqtt:brokerHost ?host ; mqtt:brokerPort ?port .
  OPTIONAL { ?bus mqtt:brokerTlsPort ?tlsPort }  }"""


@dataclass
class MqttLink(Link):
    """A broker the society meets on, and the client that speaks to it."""

    uri: str
    host: str
    port: int
    #  Optional second door on the SAME bus, where a principal proves itself with a certificate
    #  instead of a password. None means this world has no mTLS listener and everyone uses the
    #  port above. It is not a different bus: same topics, same ACL, same society.
    tls_port: int | None = None

    @classmethod
    def where(cls, query):
        rows = bindings(query(_BUS_Q))
        if not rows:
            return None
        if len(rows) > 1:
            raise RuntimeError(f"{len(rows)} buses declared; mqtt:onBus routing is not implemented")
        row = rows[0]
        return cls(uri=row["bus"], host=row["host"], port=int(row["port"]),
                   tls_port=int(row["tlsPort"]) if row.get("tlsPort") else None)

    def __post_init__(self):
        self._client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

    def connect(self, on_up, on_down, on_message) -> None:
        username = config.env("MQTT_USERNAME")
        if not username:
            raise RuntimeError(
                "no MQTT_USERNAME in the environment — this agent has no credential for the "
                "bus. Run `orexis-mqtt <world>` and regenerate the compose file.")
        cert, key, ca = (config.env("MQTT_CERT"), config.env("MQTT_KEY"), config.env("MQTT_CA"))
        if self.tls_port and cert and key and ca:
            self._client.tls_set(ca_certs=ca, certfile=cert, keyfile=key)
            port = self.tls_port
            log.info("connecting to %s:%s with a certificate", self.host, port)
        else:
            port = self.port
            if self.tls_port:
                log.warning("the world states a TLS port but I hold no certificate — "
                            "connecting by password. Re-run `orexis-onboard`.")
        self._client.on_connect = lambda c, u, f, rc, p: on_up()
        self._client.on_disconnect = lambda c, u, f, rc, p: on_down(rc)
        self._client.on_message = lambda c, u, msg: on_message(msg.topic, msg.payload)
        self._client.username_pw_set(username, config.env("MQTT_PASSWORD"))
        self._client.connect(self.host, port)
        self._client.loop_start()

    def subscribe(self, channel: str) -> None:
        self._client.subscribe(channel)

    def publish(self, channel: str, payload: bytes, retain: bool = False) -> None:
        self._client.publish(channel, payload, qos=1, retain=retain)

    def alive(self) -> bool | None:
        """Paho's loop thread, if it has ever existed. `_thread` is paho's private attribute,
        and reaching for it is the deliberate price of watching a thing that offers no public
        pulse: if a future paho renames it, this answers None and the watchdog's disconnect
        bound stands guard behind it."""
        thread = getattr(self._client, "_thread", None)
        return None if thread is None else bool(thread.is_alive())

    def stop(self) -> None:
        self._client.loop_stop()
        self._client.disconnect()
