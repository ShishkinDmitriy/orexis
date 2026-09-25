"""What the container needs of any transport — the contract every member of the family answers,
kept at the family's level so that sensing knows no transport at all.

A transport is how an agent's sensors reach it and how its commands reach them: over a broker,
a serial line, a socket. What is the same of every one is what the container asks — how a
member is brought up from the environment (`connect`, which imports the member's own library
and nothing else does), whether a sensor is reached through this member (`claims`), the
channels to listen on for the agent's sensors (`open`), what a message on a channel becomes
(`handle`: one call of sensing's `received` per sensor of the agent's the message is for,
answered as the sensor and the graph written), and the two commands a device may take
(`set_cadence`, `sense_now`), and the command a step sends an actuator (`actuate`). What differs is the member's: how a channel is named in the
world, in the vocabulary it adopts, what a device publishes on, and what its library is.

THE ARROW POINTS ONE WAY. A member imports this contract and sensing's `received`, the callback
it calls; sensing imports nothing of any transport and speaks no word of one, so a transport's
whole vocabulary stays the member's and the observation sensing writes never says how its bytes
arrived. The thread a message arrives on is the member's client's, and a write belongs on the
one executing thread, so `connect` is handed the container's `deliver` and a message goes there
— to a queue — and never to `handle` directly.

It was sensing's `Driver`, from 0.1.0, where the sensing module drove the transport; in 0.2.0
sensing is called and never calling, and a contract nothing in sensing reads is not sensing's.
"""

from __future__ import annotations

from datetime import datetime


class Transport:
    """What the container needs of any member. A member subclasses it and holds its client."""

    @classmethod
    def connect(cls, me: str, deliver, *, environ=None, client=None) -> "Transport":
        """Bring the agent's side up from the environment — address, credential, transport
        security in the member's own variables — with every message handed to `deliver(channel,
        payload, at)`, the container's. A test hands a `client` of its own; nothing else does."""
        raise NotImplementedError("a member brings itself up; the contract cannot")

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

    def actuate(self, store, actuator: str, payload: dict) -> bool:
        """Send a device the command a step was sized to — the payload `execution:command`
        answered when the step was taken. Whether anything was SENT: a member that does not
        reach the actuator sends nothing, and the executor's patience says what that costs."""
        return False
