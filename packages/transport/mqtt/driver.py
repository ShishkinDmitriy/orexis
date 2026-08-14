"""Devices reachable on a message bus.

A transport, not a capability: it changes how a device is spoken to and nothing an agent has
to decide. So this package has an `ontology.ttl` (the binding terms) and a `shapes.ttl` (when
a binding is complete), and deliberately no `rules.ru` — there is no capability to derive.

Vocabulary: transports/mqtt/ontology.ttl. Rules: transports/mqtt/shapes.ttl.
See knowledge/domain/sensing.md.
"""

from __future__ import annotations

from agent.codec import CodecError, codec_for
from agent.driver import Driver
from agent.pointer import DEFAULT_POINTER, PointerError, resolve


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
        """A channel of this transport's is the declaration — `mqtt:onBus` or `mqtt:readingTopic`.

        It used to be `mqtt:onBus` alone, which contradicted that term's own vocabulary: *"which
        bus this resource is reachable on. **Optional while a society has one.**"* A sensor may
        legitimately state where it publishes and leave the bus to be the only one there is.

        That gap is not academic. `mqtt:onBus` is also what mints a broker CREDENTIAL — it is the
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

        **This transport no longer decodes.** It used to call `json.loads` itself, which made
        JSON a property of speaking MQTT rather than of what the device sends — two independent
        facts fused in one line. Bytes go to whichever codec the sensor's binding selects; what
        comes back is a document, and the pointer is indifferent to which codec made it.

        None rather than a default is the whole discipline here: a pointer that misses is a
        world stating something the device does not send, and answering 0.0 would record that
        as a measurement. The caller warns; nothing is written. A binding naming a codec this
        build does not carry lands here the same way, for the same reason.
        """
        codec = codec_for(sensor)
        if codec is None:
            return None
        try:
            doc = codec.decode(payload)
        except CodecError:
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

        The verdict is opaque here. Sensing collects it from whichever module holds a stake
        and passes it through; this driver never learns what a band is.
        """
        if sensor.command_topic:
            self.publish(sensor.command_topic,
                         {"sleep_s": int(sleep_s), **(verdict or {})}, True)

    def sense_now(self, sensor) -> None:
        if sensor.command_topic:
            self.publish(sensor.command_topic, {"sense": True}, False)
