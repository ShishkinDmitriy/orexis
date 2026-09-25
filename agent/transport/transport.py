"""What the container needs of any transport — the contract every member of the family answers,
kept at the family's level so that sensing knows no transport at all.

A transport is how an agent's sensors reach it and how its commands reach them: over a broker,
a serial line, a socket. What is the same of every one is what the container asks — whether a
sensor is reached through this member (`claims`), the channels to listen on for the agent's
sensors (`open`), what a message on a channel becomes (`handle`: one call of sensing's
`received` per sensor of the agent's the message is for, answered as the sensor and the graph
written), and the two commands a device may take (`set_cadence`, `sense_now`). What differs is
the member's: how a channel is named in the world, in the vocabulary it adopts, and what a
device publishes on.

THE ARROW POINTS ONE WAY. A member imports this contract and sensing's `received`, the callback
it calls; sensing imports nothing of any transport and speaks no word of one, so a transport's
whole vocabulary stays the member's and the observation sensing writes never says how its bytes
arrived. The client, the connection and the thread a message arrives on are the container's: a
member is handed a connected client and sets no callback, since a write belongs on the one
executing thread.

It was sensing's `Driver`, from 0.1.0, where the sensing module drove the transport; in 0.2.0
sensing is called and never calling, and a contract nothing in sensing reads is not sensing's.
"""

from __future__ import annotations

from datetime import datetime


class Transport:
    """What the container needs of any member. A member subclasses it, holding the client the
    container connected."""

    @classmethod
    def claims(cls, store, sensor: str) -> bool:
        """Whether this member is how the world says the sensor is reached — answered from what
        the world declares, in the member's own vocabulary."""
        return False

    def open(self, store) -> list[str]:
        """Listen on every channel the world implies for the agent's sensors; the channels."""
        return []

    def handle(self, store, channel: str, payload: bytes, at: datetime, *, memo=None) -> list[tuple[str, str]]:
        """A message on a channel at an instant, handed to sensing once per sensor of the
        agent's it is for: the sensor and the graph written, and none where it is nobody's."""
        return []

    def set_cadence(self, store, sensor: str, sleep_s: int) -> bool:
        """Standing policy, where the device accepts instruction. Whether anything was SENT."""
        return False

    def sense_now(self, store, sensor: str) -> None:
        """Ask for a reading now, best-effort."""
