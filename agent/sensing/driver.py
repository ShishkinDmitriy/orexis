"""What sensing needs of a transport, and nothing more — the contract a transport's driver
implements.

A driver knows how one kind of device is reached: whether the world's binding of a sensor is
one it recognises, which channels carry that sensor's readings, whether a message on a channel
is that sensor's, how to nudge the device and how to set its cadence. It reads that binding
from the store by the sensor's IRI in its own words; sensing hands it a `Sensor` and never a
topic. What a driver no longer does is `parse`: bytes to number is the pipeline's, so the
transport hands sensing the bytes and the sensor they are for, and sensing's `received` is
the callback it calls.
"""

from __future__ import annotations


class Driver:
    """What sensing needs of any binding. A transport subclasses it."""

    @classmethod
    def claims(cls, store, sensor) -> bool:
        """Whether this transport recognises how the world says to reach this device —
        answered from what the device declares, in the transport's own words."""
        return False

    def subscriptions(self, store, sensor) -> list[str]:
        """The channels to listen on for this sensor's readings, if the binding has any."""
        return []

    def owns(self, store, sensor, channel: str) -> bool:
        """Whether an inbound message on this channel is this sensor's reading."""
        return False

    def set_cadence(self, store, sensor, sleep_s: int) -> bool:
        """Standing policy, where the device accepts instruction. Whether anything was SENT."""
        return False

    def sense_now(self, store, sensor) -> None:
        """Ask for a reading now, best-effort."""
