"""How a device is actually spoken to — the part that varies per binding.

A sensing module decides *when* to look and *what to make of it*; a driver knows only how
to reach one kind of device. That line is deliberate: protocol changes nothing an agent must
decide, so it has no business appearing in a capability, a belief, or a policy. It is why
`transports/` is a separate tree from `capabilities/` and grants nothing.

A driver is chosen **per sensor**, and it is the driver that decides: each one is asked
whether it recognises the binding the world states on that device. So one agent with one
attention policy can hold a sensor on a bus and another on a wire, which is exactly the case
that would force a duplicate cadence if the transport were named in the capability instead.

Adding a transport is a directory under `transports/` and nothing else: no capability, no
belief, no edit here — because how a device is reached is not something an agent decides.
"""

from __future__ import annotations

from . import loader


class Driver:
    """What sensing needs of any binding."""

    @classmethod
    def claims(cls, sensor) -> bool:
        """Whether this transport recognises how the world says to reach this device.

        Answered from what the device DECLARES — not from "does it happen to have a topic".
        A half-stated binding should be caught by that transport's shapes, not silently
        treated as belonging to some other transport.
        """
        return False

    def subscriptions(self, sensor) -> list[str]:
        """Channels to listen on for this sensor's readings, if the binding has any."""
        return []

    def owns(self, sensor, topic: str) -> bool:
        """Whether an inbound message on this channel is this sensor's reading."""
        return False

    def parse(self, sensor, payload: bytes) -> float | None:
        """The RAW VALUE this sensor's share of the payload holds, or None if unreadable.

        Per sensor and not per message, because one message may carry several sensors' values:
        a board with two peripherals is one client with one credential, so it publishes once.

        Raw is the operative word. What a transport pulls off the wire is what the device sent;
        turning that into an observed quantity is a third stage nothing here performs yet —
        see issue #26 — and keeping the two nameable is what leaves room for it.
        """
        raise NotImplementedError

    def set_cadence(self, sensor, sleep_s: int) -> None:
        """Standing policy. Only meaningful where the device accepts instruction."""

    def sense_now(self, sensor) -> None:
        """Ask for a reading now, best-effort."""


def driver_for(sensor, publish) -> Driver | None:
    """The transport that claims this device, or None if nothing here can speak to it.

    None is a legitimate answer and is reported, not raised: a device stating a binding this
    build has no transport for is a deployment fact — the same shape of fact as a capability
    the world composes and no package implements.
    """
    for cls in loader.drivers():
        if cls.claims(sensor):
            return cls(publish)
    return None
