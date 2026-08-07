"""Perception — capabilities over one shared ingest path, split by WHO HOLDS THE CLOCK.

Which one an agent gets is decided by its **hardware**, and derived at genesis from the
device's own nature:

- **ag:Polling** (`ag:Pull` device) — the agent's own timer; it asks for each reading and the
  device replies. The simplest exchange and the most agent control, but it needs a device that
  is reachable at any moment. **Not implemented**: no rule grants it and no class here
  provides it, because a board that deep-sleeps cannot hear the request. The room is kept
  deliberately — see ontology.ttl.
- **ag:Subscribing** (`ag:Scheduled` device) — the agent states an interval and the device
  keeps to it. The agent still decides how often to look; what it delegates is the
  timekeeping, which is exactly what lets the device sleep in between.
- **ag:Listening** (`ag:Push` device) — the device announces on its own clock and takes no
  orders. The agent records what arrives, and that is all it can do.

What survives the whole range is the **freshness judgment**: however the reading arrived, the
agent decides how stale it may be before it stops trusting it, because that is about belief
rather than control. What does not survive is the interval — a listening agent is never asked
for one, since it could not apply it. That asymmetry is enforced by shapes.ttl, not by
convention.

Two things deliberately do NOT appear here:

- **A protocol.** How a device is spoken to is a driver's business (`transports/`), chosen per
  sensor from what the world says about it — so an agent may hold one sensor on a bus and
  another on a wire under a single attention policy.
- **What counts as trouble.** Perception knows how to look and how fresh a number is; it has
  no band and no target, because those belong to whoever holds a stake in the subject. So it
  *asks* — `agent.urgency` for how closely to watch, `agent.annotations` for what to say
  publicly — and an agent with no stake simply gets no answer and watches at its slow cadence.
  That is why nothing here imports another capability.

Everything touched is discovered: which sensors (`ag:polls`), what property they read
(`sosa:observes`), and where to announce a perception (`ag:eventTopic`).

Vocabulary: capabilities/perception/ontology.ttl. Rules: capabilities/perception/shapes.ttl.
Derivation: capabilities/perception/rules.ru. See knowledge/domain/sensing.md.
"""

from __future__ import annotations

from agent.driver import driver_for
from agent.module import Module
from agent.observation import Observations
from agent.store import bindings

from .beliefs import LISTENING_BLOCK, SUBSCRIBING_BLOCK
from .terms import LISTENING, PUSH, SCHEDULED, SUBSCRIBING

# The constitutional bounds are stated in the ontology, not compiled in here — and they hang
# off the capability FAMILY, so every transport and every future perception inherits them.
_BOUNDS_Q = """
SELECT ?min ?max WHERE {
  GRAPH ?g { ag:PerceptionCapability ag:minSleepS ?min ; ag:maxSleepS ?max }
} LIMIT 1"""


class PerceptionModule(Module):
    """Shared ingest: record what a sensor read, announce it, keep a freshness rule.

    Identical whether the reading was asked for or simply arrived.
    """

    # Which kind of device this module is for. The derivation grants the capability from the
    # sensor's ag:senseMode; this is the same pairing, read from the other side.
    SENSE_MODE: str | None = None

    def __init__(self, agent):
        super().__init__(agent)
        # MINE, not the agent's. An agent may hold sensors of different modes, and it derives a
        # capability for each — but a module that took all of them would aim a cadence at a device
        # that takes no orders, and swallow readings from one it never re-aims. The derivation
        # split the capabilities; this splits the sensors the same way.
        self.sensors = tuple(s for s in self.me.sensors
                             if self.SENSE_MODE is None or s.sense_mode == self.SENSE_MODE)
        unclaimed = [s.local_id for s in self.me.sensors if s not in self.sensors]
        if unclaimed:
            self.log.debug("%s: not mine — %s", self.name, ", ".join(unclaimed))

        # one driver per sensor, chosen from its binding — not from anything the agent believes
        self.drivers = {s.uri: driver_for(s, self.publish) for s in self.sensors}
        for sensor in self.sensors:
            if self.drivers[sensor.uri] is None:
                self.log.warning("%s states no binding I can speak — it will never be read",
                                 sensor.local_id)

        # Recording is not perception's to define — see agent/observation.py.
        self.observations = Observations(agent)

    def stale_after_s(self, subject_uri: str) -> int:
        """How old a reading of this subject may be before I stop trusting it.

        A method rather than a number because the answer depends on who holds the clock. Where
        the agent sets the interval it must be relative to that interval; where the device keeps
        its own, an absolute is the only thing the agent can state.
        """
        raise NotImplementedError

    def subscriptions(self) -> list[str]:
        # exactly my own sensors, and only where their binding listens at all — never a
        # wildcard, so the access grant stays visible in the subscription itself
        return [t for s in self.sensors if self.drivers[s.uri]
                for t in self.drivers[s.uri].subscriptions(s)]

    def stop(self) -> None:
        self.observations.close()

    def handle(self, topic: str, payload: bytes) -> bool:
        for sensor in self.sensors:
            driver = self.drivers[sensor.uri]
            if driver is None or not driver.owns(sensor, topic):
                continue
            value = driver.parse(payload)
            if value is None:
                self.log.warning("unreadable payload on %s", topic)
            else:
                self.ingest(sensor, value)
            return True
        return False

    def ingest(self, sensor, value: float) -> None:
        """Record what the sensor read, then re-aim if this capability can."""
        self.observations.record(self.log, sensor, value)
        self.on_reading(sensor, value)

    def on_reading(self, sensor, value: float) -> None:
        """What this capability does after recording. Subscribing re-aims; listening does not."""

    def sense_now(self) -> None:
        """Ask for a reading now, if my hardware allows it. Listening cannot.

        Best-effort even where it is allowed: a device that sleeps between readings only hears
        this if the nudge happens to land inside its waking window. It is the seed of
        ag:Polling, not a substitute for it — a real polling module would need a device that
        is always listening, and would then drive every reading this way.
        """

    def fresh_reading(self, subject_uri: str):
        """The latest reading, or None if it is older than I am willing to trust."""
        reading = self.agent.beliefs.current_reading(subject_uri)
        return reading if reading and reading.is_fresh(self.stale_after_s(subject_uri)) else None

    def sensor_for(self, subject_uri: str):
        """Which of my sensors watches this subject, if any."""
        return next((s for s in self.sensors if s.subject == subject_uri), None)


class SubscribingModule(PerceptionModule):
    """ag:Subscribing — derived from being wired to a device that keeps to a given interval.

    The standing request is the whole mechanism: the interval is published *retained*, so a
    device that is asleep now receives it the instant it wakes and subscribes. That is why
    this works against hardware the agent cannot otherwise reach.
    """

    CAPABILITY = SUBSCRIBING
    SENSE_MODE = SCHEDULED
    name = "subscribing"

    def __init__(self, agent):
        self.beliefs = agent.beliefs.read(SUBSCRIBING_BLOCK)
        super().__init__(agent)
        self.min_sleep_s, self.max_sleep_s = self._bounds()
        self.sent_cadence: dict[str, int] = {}

    def stale_after_s(self, subject_uri: str) -> int:
        """The interval I asked for, plus slack. NOT an absolute.

        I chose this cadence, so refusing a reading that arrived exactly when I asked for it
        would be refusing my own instruction — which is what a fixed limit did, silently, every
        time a comfortable plant let the cadence relax past it.
        """
        sensor = self.sensor_for(subject_uri)
        cadence = self.sent_cadence.get(sensor.local_id) if sensor else None
        if cadence is None:
            # Not aimed yet. Assume the slowest I would ask for, so a first reading is not
            # rejected for arriving on a schedule I have not set.
            cadence = self.beliefs.slow_sleep_s
        return int(cadence) + self.beliefs.grace_s

    def _bounds(self) -> tuple[int, int]:
        rows = bindings(self.agent.store.query(_BOUNDS_Q))
        if not rows:
            raise RuntimeError("the ontology states no cadence bounds — re-run agora-seed")
        return int(rows[0]["min"]), int(rows[0]["max"])

    def start(self) -> None:
        self.sense_now()

    def on_reading(self, sensor, value: float) -> None:
        self.set_cadence(sensor, self.cadence_for(sensor.subject, value))

    def cadence_for(self, subject_uri: str, value: float) -> int:
        """How long the board may sleep: the closer to my own trouble, the closer I watch.

        Trouble is not perception's to define, so it is asked for. An agent with no stake in
        the subject gets no answer and watches at its slow cadence — the honest reading of
        "nothing here is urgent to me".
        """
        b = self.beliefs
        urgency = self.agent.urgency(subject_uri, value)
        if urgency is None:
            return min(self.max_sleep_s, max(self.min_sleep_s, b.slow_sleep_s))
        sleep_s = b.slow_sleep_s + (b.fast_sleep_s - b.slow_sleep_s) * urgency
        return int(round(min(self.max_sleep_s, max(self.min_sleep_s, sleep_s))))

    def set_cadence(self, sensor, sleep_s: int) -> None:
        """Standing policy. How it is delivered is the driver's problem, not mine."""
        if self.sent_cadence.get(sensor.local_id) == sleep_s:
            return
        driver = self.drivers[sensor.uri]
        if driver is None:
            return
        driver.set_cadence(sensor, sleep_s)
        self.sent_cadence[sensor.local_id] = sleep_s
        self.log.info("%s: cadence now %ss", sensor.local_id, sleep_s)

    def sense_now(self) -> None:
        """Best-effort nudge — lands only if the device is awake to hear it."""
        for sensor in self.sensors:
            if self.drivers[sensor.uri]:
                self.drivers[sensor.uri].sense_now(sensor)


class ListeningModule(PerceptionModule):
    """ag:Listening — derived from being wired to a push-mode sensor.

    No interval, because the device would not take one. The agent keeps its freshness rule,
    which now works as a *detector* rather than a control: if the board goes quiet, readings
    go stale and the agent stops acting on them instead of quietly using old numbers.
    """

    CAPABILITY = LISTENING
    SENSE_MODE = PUSH
    name = "listening"

    def __init__(self, agent):
        self.beliefs = agent.beliefs.read(LISTENING_BLOCK)
        super().__init__(agent)

    def stale_after_s(self, subject_uri: str) -> int:
        """Absolute: this device keeps its own clock, so there is no interval to be relative to."""
        return self.beliefs.max_age_s
