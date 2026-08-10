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

# What a sensor's value is called when nothing says otherwise. Every single-property device
# here already publishes `{"value": ...}`, so the default is what the fleet does — and a world
# that never states a pointer reads exactly as it did before this existed.
DEFAULT_POINTER = "/value"


class PointerError(ValueError):
    """A pointer that does not resolve to a number in this payload."""


def resolve(pointer: str, doc):
    """The one RAW VALUE a JSON Pointer identifies — RFC 6901, April 2013, Standards Track.

    A pointer, not a query: RFC 6901 identifies exactly ONE value, which is exactly what a
    device reports per property. RFC 9535's JSONPath returns a nodelist, and taking "the first"
    of one would be a collapse rule we invented and then had to defend.

    What comes out is **raw** — what the device put on the wire. Interpreting it is a third
    stage that does not exist yet (issue #26), and this function is indifferent to it exactly
    as it is indifferent to whichever codec produced `doc`.

    The empty pointer is legal in the RFC and means the whole document. It is refused here
    rather than supported, because a whole document is not a number and letting it through
    would turn a mis-stated world into a parse failure much further away.
    """
    if not pointer.startswith("/"):
        raise PointerError(f"{pointer!r} is not a JSON Pointer — it must start with '/'")

    node = doc
    for token in pointer.split("/")[1:]:
        # Order matters and is the classic bug: `~1` becomes `/` FIRST, then `~0` becomes `~`.
        # Reversed, a literal `~1` written as `~01` would decode to `/` instead of `~1`.
        key = token.replace("~1", "/").replace("~0", "~")
        if isinstance(node, list):
            if not key.isdigit():
                raise PointerError(f"{pointer!r}: {key!r} is not an array index")
            index = int(key)
            if index >= len(node):
                raise PointerError(f"{pointer!r}: index {index} is past the end")
            node = node[index]
        elif isinstance(node, dict):
            if key not in node:
                raise PointerError(f"{pointer!r}: no {key!r} here")
            node = node[key]
        else:
            raise PointerError(f"{pointer!r}: {key!r} has nothing to select from")
    return node


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
        """A channel of this transport's is the declaration — `ag:onBus` or `ag:readingTopic`.

        It used to be `ag:onBus` alone, which contradicted that term's own vocabulary: *"which
        bus this resource is reachable on. **Optional while a society has one.**"* A sensor may
        legitimately state where it publishes and leave the bus to be the only one there is.

        That gap is not academic. `ag:onBus` is also what mints a broker CREDENTIAL — it is the
        test `onboarding/mqtt.py` applies to decide a principal exists — so a peripheral sharing
        its board's connection must not carry one, or onboarding writes a password for a client
        that never connects. Two sensors on one board are reached over MQTT and are not two
        principals, and only a claim test that reads the channel can say both at once.

        Still answered from what the world DECLARES rather than from what happens to be
        present: a reading topic is one of this package's terms, so stating one is the sensor
        saying it speaks MQTT.
        """
        return bool(sensor.bus or sensor.reading_topic)

    def subscriptions(self, sensor) -> list[str]:
        return [sensor.reading_topic] if sensor.reading_topic else []

    def owns(self, sensor, topic: str) -> bool:
        return sensor.reading_topic == topic

    def parse(self, sensor, payload: bytes) -> float | None:
        """The RAW VALUE this sensor's pointer identifies, or None if it does not resolve.

        Takes the sensor because one payload may carry several sensors' values — the board is
        one MQTT client with one credential, so a device with two peripherals publishes one
        message and each sensor points at its own field.

        None rather than a default is the whole discipline here: a pointer that misses is a
        world stating something the device does not send, and answering 0.0 would record that
        as a measurement. The caller warns; nothing is written.
        """
        try:
            doc = json.loads(payload)
        except ValueError:
            return None
        try:
            return float(resolve(sensor.reading_pointer or DEFAULT_POINTER, doc))
        except (PointerError, TypeError, ValueError):
            return None

    def set_cadence(self, sensor, sleep_s: int, verdict: dict | None = None) -> None:
        """The standing instruction, and whatever the agent wants its device to show.

        One retained message rather than two, and the same one that was already being sent —
        the device is told how often to look and what its agent made of the last look in the
        same breath. Retained is what makes the second half work at all: a board that deep-sleeps
        gets the current verdict the instant it subscribes, instead of showing nothing until the
        next reading it takes has been judged.

        The verdict is opaque here. Perception collects it from whichever module holds a stake
        and passes it through; this driver never learns what a band is.
        """
        if sensor.command_topic:
            self.publish(sensor.command_topic,
                         {"sleep_s": int(sleep_s), **(verdict or {})}, True)

    def sense_now(self, sensor) -> None:
        if sensor.command_topic:
            self.publish(sensor.command_topic, {"sense": True}, False)
