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

WHETHER A MEMBER IS LOADED AT ALL is not asked of the member, since asking would import it: a
transport is no role, and the runtime loads a member where a role the agent is declared in needs
bytes and the society wires a bus, read off the world before anything of the member is imported
(`agent.runtime.TRANSPORTS`, #824, #927). It was `claims`, a question the member answered of a
sensor, and its one caller imported the member to ask it.

THE ARROW POINTS ONE WAY. A member imports this contract, sensing's `received` and speech's
`heard`, the callbacks it calls, each where a message is for it, so a member loads no package
its agent was not given; sensing imports nothing of any transport and speaks no word of one, so a transport's
whole vocabulary stays the member's and the observation sensing writes never says how its bytes
arrived. The thread a message arrives on is the member's client's, and a write belongs on the
one executing thread, so `connect` is handed the container's `deliver` and a message goes there
— to a queue — and never to `handle` directly.

A MEMBER IS A PART (a-package-starts-itself). The executor's `commanded` and speech's `told` are
connected to its `command` and `tell_to` when the parts are linked; `start` is handed the runtime:
every message the member's thread receives is submitted to it as a job that `handle`s it, the member
opens what it listens on and schedules what it does of its own accord — MQTT asks after a board's
missing reading, HTTP polls — and holds the agent running. `stop` ends it.

A CHANNEL IS THE TRANSPORT'S, AND WHICH ROW READS IT IS WHAT POINTS AT IT. A member carries bytes on a channel
— a topic, a Telegram chat, a mailbox, a url — and knows nothing of what they mean: a channel a sensor observes is
sensing's, one an agent listens on is speech's, and the channel of a `speech:Chat` the agent is in is translation's,
a person's prose. For the last a member says `prose`, a signal carrying `Prose` — the channel, who said it where
the channel tells, the words — which translation hears when the parts are linked, and it sends prose back by
`say_to`, so no member imports translation and translation imports no member.

SEVERAL MEMBERS ARE ONE TRANSPORT TO THE CONTAINER. A world may reach its board over MQTT and a
forecast service over HTTP; the runtime holds every member it attached behind `Transports`, which
sends a nudge, a cadence or a command to the member that `reaches` the device — a question only a
loaded member is asked, so it imports nothing.

It was sensing's `Driver`, from 0.1.0, where the sensing module drove the transport; in 0.2.0
sensing is called and never calling, and a contract nothing in sensing reads is not sensing's.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Prose:
    """A person's words on a channel at `at`: the channel's node in the world, the person who said them where the
    channel tells — a Telegram user, a mailbox's sender — or None where it does not, and the text. Where the carrier
    tells whom the words were for, `addressed` says so — True where they tagged or replied to this agent's own
    account, False where they tagged or replied to someone else and not it, None where the carrier tells nothing —
    and `message` is the carrier's id of the words, which an answer may reply to."""
    channel: str
    sender: str | None
    text: str
    at: datetime | None = None
    addressed: bool | None = None
    message: str | None = None


class Transport:
    """What the container needs of any member. A member subclasses it and holds its client."""

    @classmethod
    def connect(cls, me: str, deliver, *, environ=None, client=None) -> "Transport":
        """Bring the agent's side up from the environment — address, credential, transport
        security in the member's own variables — with every message handed to `deliver(channel,
        payload, at)`, the container's. A test hands a `client` of its own; nothing else does."""
        raise NotImplementedError("a member brings itself up; the contract cannot")

    def start(self, runtime) -> None:
        """Begin: every message this member's thread receives submitted to the runtime as a job
        that handles it, the agent's channels opened, the member attached, and the agent held running."""
        self.store = runtime.beliefs
        self.deliver = lambda channel, payload, at: runtime.submit(
            lambda: [graph for _, graph in self.handle(runtime.beliefs, channel, payload, at)])
        self.open(runtime.beliefs)
        runtime.attach(self)
        #  A MEMBER KEEPS THE AGENT RUNNING: what it senses goes on arriving whatever is wanted.
        runtime.hold(self)

    def command(self, actuator: str, payload: dict) -> list[str]:
        """A step's command, connected to the executor's `commanded` when the part is linked: sent
        where this member reaches the actuator, and nothing written either way."""
        if self.reaches(self.store, actuator):
            self.actuate(self.store, actuator, payload)
        return []

    def tell_to(self, to: str, document: bytes) -> list[str]:
        """A document for a peer, connected to speech's `told` when the part is linked: sent where this
        member reaches the peer, and nothing written."""
        self.tell(self.store, to, document)
        return []

    def stop(self) -> None:
        """End: whatever the member holds open, closed."""

    def say_to(self, store, channel: str, text: str, *, reply: str | None = None) -> bool:
        """Prose out on `channel`, a chat's channel this member carries — a Telegram chat, a mailbox, a topic — as a
        reply to the message `reply` names where the carrier threads one. Whether anything was SENT: a member that
        does not carry the channel sends nothing."""
        return False

    def writing_in(self, store, channel: str) -> bool:
        """Show on `channel`, a chat's channel this member carries, that the agent is writing, where the channel can
        show it. Whether it was SHOWN: a member that does not carry the channel, or cannot show it, shows nothing."""
        return False

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
    """Several members as the one transport the container holds: a device's nudge, cadence or
    command to the member reaching it, and a message named `(n, channel)` to the n-th member."""

    def __init__(self, members: list[Transport]):
        self.members = list(members)

    def open(self, store) -> list[str]:
        return [channel for member in self.members for channel in member.open(store)]

    def start(self, runtime) -> None:
        for member in self.members:
            member.start(runtime)

    def stop(self) -> None:
        for member in self.members:
            member.stop()

    def command(self, actuator: str, payload: dict) -> list[str]:
        for member in self.members:
            member.command(actuator, payload)
        return []

    def tell_to(self, to: str, document: bytes) -> list[str]:
        for member in self.members:
            member.tell_to(to, document)
        return []

    def handle(self, store, channel, payload: bytes, at: datetime, *, memo=None) -> list[tuple[str | None, str]]:
        n, own = channel
        return self.members[n].handle(store, own, payload, at, memo=memo)

    def reaches(self, store, device: str) -> bool:
        return self._reaching(store, device) is not None

    def tell(self, store, to: str, document: bytes) -> bool:
        return any(member.tell(store, to, document) for member in self.members)

    def say_to(self, store, channel: str, text: str, *, reply: str | None = None) -> bool:
        return any(member.say_to(store, channel, text, reply=reply) for member in self.members)

    def writing_in(self, store, channel: str) -> bool:
        return any(member.writing_in(store, channel) for member in self.members)

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
