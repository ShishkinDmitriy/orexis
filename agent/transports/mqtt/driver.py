"""Devices reachable on a message bus.

A transport, not a capability: it changes how a device is spoken to and nothing an agent has
to decide. So this package has an `ontology.ttl` (the binding terms) and a `shapes.ttl` (when
a binding is complete), and deliberately no `rules.ru` — there is no capability to derive.

Vocabulary: transports/mqtt/ontology.ttl. Rules: transports/mqtt/shapes.ttl.
See knowledge/domain/sensing.md.
"""

from __future__ import annotations

import json

from agent.driver import Driver


class MqttDriver(Driver):
    """A reading channel, and maybe a command channel.

    Two levers, deliberately unequal. **Cadence** is standing policy and is published
    *retained*, so a board that is deep asleep still receives it the moment it wakes and
    subscribes — the reliable lever. **Sense** is a best-effort nudge that lands only if the
    device is awake, and is never retained: a retained `sense` would re-fire on every wake,
    forever.
    """

    def __init__(self, publish):
        self.publish = publish

    @classmethod
    def claims(cls, sensor) -> bool:
        """`ag:onBus` is the declaration — the device says it is reachable on a bus."""
        return bool(sensor.bus)

    def subscriptions(self, sensor) -> list[str]:
        return [sensor.reading_topic] if sensor.reading_topic else []

    def owns(self, sensor, topic: str) -> bool:
        return sensor.reading_topic == topic

    def parse(self, payload: bytes) -> float | None:
        try:
            doc = json.loads(payload)
            return float(doc["value"])
        except (ValueError, TypeError, KeyError):
            return None

    def set_cadence(self, sensor, sleep_s: int) -> None:
        if sensor.command_topic:
            self.publish(sensor.command_topic, {"sleep_s": int(sleep_s)}, True)

    def sense_now(self, sensor) -> None:
        if sensor.command_topic:
            self.publish(sensor.command_topic, {"sense": True}, False)
