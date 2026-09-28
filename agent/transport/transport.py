"""What the container needs of any transport — the contract every member of the family answers,
kept at the family's level so that sensing knows no transport at all.

A transport is how an agent's sensors reach it and how its commands reach them: over a broker,
a serial line, a socket. What is the same of every one is what the container asks — how a
member is brought up from the environment (`connect`, which imports the member's own library
and nothing else does), the
channels to listen on for the agent's sensors (`open`), what a message on a channel becomes
(`handle`: one call of sensing's `received` per sensor of the agent's the message is for,
answered as the sensor and the graph written), and the two commands a device may take
(`set_cadence`, `sense_now`), and the command a step sends an actuator (`actuate`). What differs is the member's: how a channel is named in the
world, in the vocabulary it adopts, what a device publishes on, and what its library is.

WHETHER A MEMBER IS LOADED AT ALL is not asked of the member, since asking would import it: it is
the member's premise, which the runtime reads off the world before anything of the member is
imported (`agent.runtime.PREMISES`, #824). It was `claims`, a question the member answered of a
sensor, and its one caller imported the member to ask it.

THE ARROW POINTS ONE WAY. A member imports this contract, sensing's `received` and speech's
`heard`, the callbacks it calls, each where a message is for it, so a member loads no package
its agent was not given; sensing imports nothing of any transport and speaks no word of one, so a transport's
whole vocabulary stays the member's and the observation sensing writes never says how its bytes
arrived. The thread a message arrives on is the member's client's, and a write belongs on the
one executing thread, so `connect` is handed the container's `deliver` and a message goes there
— to a queue — and never to `handle` directly.

SEVERAL MEMBERS ARE ONE TRANSPORT TO THE CONTAINER. A world may reach its board over MQTT and a
forecast service over HTTP, so the container connects every member whose premise holds and holds
them behind `Transports`: each member is handed a `deliver` that tags its messages, so a message
goes back to the member that queued it, and a nudge, a cadence or a command goes to the member
that `reaches` the device — a question only a loaded member is asked, so it imports nothing.

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

    def open(self, store) -> list[str]:
        """Listen on every channel the world implies for the agent's sensors, and on the one
        its peers tell it things on; the channels."""
        return []

    def handle(self, store, channel: str, payload: bytes, at: datetime, *, memo=None) -> list[tuple[str | None, str]]:
        """A message on a channel at an instant: on the agent's own channel a peer's document,
        handed to speech's `heard` and answered with no sensor; otherwise handed to sensing once
        per sensor of the agent's it is for, the sensor and the graph written. None where it is
        nobody's."""
        return []

    def tell(self, store, to: str, document: bytes) -> bool:
        """Send a peer a document this agent said — TriG, as an `execution:Saying` made it — on the
        channel the peer listens to. Whether anything was SENT."""
        return False

    def set_cadence(self, store, sensor: str, sleep_s: int) -> bool:
        """Standing policy, where the device accepts instruction. Whether anything was SENT."""
        return False

    def sense_now(self, store, sensor: str) -> None:
        """Ask for a reading now, best-effort."""

    def reaches(self, store, device: str) -> bool:
        """Whether this member reaches `device` — a sensor it is read over, an actuator or a board
        it commands — which is where the container sends a nudge, a cadence or a command."""
        return False

    def actuate(self, store, actuator: str, payload: dict) -> bool:
        """Send a device the command a step was sized to — the payload an `execution:Command`
        answered when the step was taken. Whether anything was SENT: a member that does not
        reach the actuator sends nothing, and the executor's patience says what that costs."""
        return False


class Transports(Transport):
    """Several members as the one transport the container holds: a message handed back to the
    member that queued it, and a device's nudge, cadence or command to the member reaching it."""

    def __init__(self, members: list[Transport]):
        self.members = list(members)

    @classmethod
    def connect(cls, me: str, deliver, *, members=(), environ=None, client=None) -> Transport:
        """Every member of `members` brought up, each handed a `deliver` that tags its messages with
        the member; one member is itself, and no member is nothing to hold."""
        members = list(members)
        if len(members) == 1:
            return members[0].connect(me, deliver, environ=environ)
        return cls([member.connect(me, lambda channel, payload, at, n=n: deliver((n, channel), payload, at),
                                   environ=environ) for n, member in enumerate(members)])

    def open(self, store) -> list[str]:
        return [channel for member in self.members for channel in member.open(store)]

    def handle(self, store, channel, payload: bytes, at: datetime, *, memo=None) -> list[tuple[str | None, str]]:
        n, own = channel
        return self.members[n].handle(store, own, payload, at, memo=memo)

    def reaches(self, store, device: str) -> bool:
        return self._reaching(store, device) is not None

    def tell(self, store, to: str, document: bytes) -> bool:
        return any(member.tell(store, to, document) for member in self.members)

    def set_cadence(self, store, sensor: str, sleep_s: int) -> bool:
        member = self._reaching(store, sensor)
        return member is not None and member.set_cadence(store, sensor, sleep_s)

    def sense_now(self, store, sensor: str) -> None:
        if (member := self._reaching(store, sensor)) is not None:
            member.sense_now(store, sensor)

    def actuate(self, store, actuator: str, payload: dict) -> bool:
        member = self._reaching(store, actuator)
        return member is not None and member.actuate(store, actuator, payload)

    def _reaching(self, store, device: str) -> Transport | None:
        return next((member for member in self.members if member.reaches(store, device)), None)
