"""How a device is actually spoken to — the part that varies per binding.

The perception module decides *when* to look and *what to make of it*; a driver knows only
how to reach one kind of device. That line is deliberate: protocol changes nothing an agent
must decide, so it has no business appearing in a capability, a belief, or a policy.

A driver is chosen **per sensor**, from the binding properties the world states on it. So one
agent with one attention policy can hold a sensor on a bus and another on a wire, which is
exactly the case that would force a duplicate cadence if the transport were named in the
capability instead.

Adding a transport means a driver here, the terms in `ontology/<name>.ttl`, and its
completeness rules in `shapes/<name>.ttl`. Perception itself does not change.
"""

from __future__ import annotations

import json


class Driver:
    """What perception needs of any binding."""

    def subscriptions(self, sensor) -> list[str]:
        """Channels to listen on for this sensor's readings, if the binding has any."""
        return []

    def owns(self, sensor, topic: str) -> bool:
        """Whether an inbound message on this channel is this sensor's reading."""
        return False

    def parse(self, payload: bytes) -> float | None:
        raise NotImplementedError

    def set_cadence(self, sensor, sleep_s: int) -> None:
        """Standing policy. Only meaningful where the device accepts instruction."""

    def sense_now(self, sensor) -> None:
        """Ask for a reading now, best-effort."""


class MqttDriver(Driver):
    """Devices reachable on a message bus: a reading channel, and maybe a command channel.

    Two levers, deliberately unequal. **Cadence** is standing policy and is published
    *retained*, so a board that is deep asleep still receives it the moment it wakes and
    subscribes — the reliable lever. **Sense** is a best-effort nudge that lands only if the
    device is awake, and is never retained: a retained `sense` would re-fire on every wake,
    forever.
    """

    def __init__(self, publish):
        self.publish = publish

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


def driver_for(sensor, publish) -> Driver | None:
    """Pick the driver from the binding the device DECLARES — `ag:onBus` means the bus.

    Selecting on a declaration rather than on "does it happen to have a topic" is the same
    reason the shapes key on it: a device with a half-stated binding should be caught, not
    silently treated as belonging to some other transport. When a second binding arrives this
    becomes a lookup rather than a branch, and it stays *here* either way — never in the
    agent's beliefs, because how a device is reached is not something the agent decides.
    """
    if sensor.bus:
        return MqttDriver(publish)
    return None
