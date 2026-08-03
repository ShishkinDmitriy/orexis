"""Perception — two capabilities over one shared ingest path.

Which one an agent gets is decided by its **hardware**, and derived at genesis from the
device's own nature:

- **ag:Polling** (pull-mode device) — the agent drives it. It owns the cadence and may ask
  for a reading now.
- **ag:Listening** (push-mode device) — the device announces on its own clock and takes no
  orders. The agent records what arrives, and that is all it can do.

What survives the difference is the **judgment**: either way the agent decides how stale a
reading may be before it stops trusting it, because that is about belief rather than control.
What does not survive is the cadence — a listening agent is never asked for one, since it
could not apply it. That asymmetry is enforced by shapes/perception.ttl, not by convention.

What deliberately does NOT appear here is a protocol. How a device is spoken to is a
`Driver`'s business (see drivers.py), chosen per sensor from what the world says about it —
so an agent may hold one sensor on a bus and another on a wire under a single attention
policy. A capability distinguishes what an agent must decide; a binding distinguishes how a
device is reached, and only the second varies by transport.

Everything touched here is discovered: which sensors (`ag:polls`), what property they read
(`sosa:observes`), and where to announce a perception (`ag:eventTopic`).

Vocabulary: ontology/perception.ttl. Rules: shapes/perception.ttl.
Derivation: rules/perception.ru. See knowledge/domain/sensing.md.
"""

from __future__ import annotations

from .. import config
from ..influx_writer import InfluxWriter
from ..ontology import LISTENING, POLLING, band_for
from ..sensed_writer import SensedWriter
from ..store import bindings
from .base import Module
from .drivers import driver_for

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

    def __init__(self, agent):
        super().__init__(agent)
        self.max_age_s = self._max_age_s()
        # one driver per sensor, chosen from its binding — not from anything the agent believes
        self.drivers = {s.uri: driver_for(s, self.publish) for s in self.me.sensors}
        for sensor in self.me.sensors:
            if self.drivers[sensor.uri] is None:
                self.log.warning("%s states no binding I can speak — it will never be read",
                                 sensor.local_id)
        # An agent judges itself against its own band, which is part of what it WANTS — so an
        # agent with no stake in the subject has no verdict to reach, and says so.
        self.band = None
        try:
            b = agent.beliefs.bidding()
            self.band = (b.low, b.high)
        except Exception:
            pass

        self.influx = InfluxWriter(
            config.env("INFLUX_URL", "http://localhost:8086"),
            config.env("INFLUX_TOKEN", "dev-token-change-me"),
            config.env("INFLUX_ORG", "agora"),
            config.env("INFLUX_BUCKET", "sensors"),
        )
        self.sensed = SensedWriter(agent.store)

    def _max_age_s(self) -> int:
        raise NotImplementedError

    def subscriptions(self) -> list[str]:
        # exactly my own sensors, and only where their binding listens at all — never a
        # wildcard, so the access grant stays visible in the subscription itself
        return [t for s in self.me.sensors if self.drivers[s.uri]
                for t in self.drivers[s.uri].subscriptions(s)]

    def stop(self) -> None:
        self.influx.close()

    def handle(self, topic: str, payload: bytes) -> bool:
        for sensor in self.me.sensors:
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
        """Record the reading as my own assertion, and announce what I make of it."""
        try:
            self.influx.write_reading(sensor.subject_id, sensor.local_id, value)
        except Exception as exc:  # history is best-effort; never drop the reading over it
            self.log.error("influx write failed: %s", exc)
        try:
            self.sensed.write(
                subject_uri=sensor.subject, subject_id=sensor.subject_id,
                value=round(value, 3), sensor_uri=sensor.uri,
                observed_property=sensor.observes, author_uri=self.me.uri,
                world_version=self.agent.world.version,
            )
        except Exception as exc:
            self.log.error("sensed write failed: %s", exc)

        if self.me.event_topic:
            # voluntary disclosure: I announce my own verdict, not my raw state. A host
            # listens for this to know scarcity has appeared, and never reads my moisture.
            self.publish(self.me.event_topic, {
                "agent": self.me.agent_id, "subject": sensor.subject,
                "value": round(value, 3), "band": self.judge(value),
            })
        self.on_reading(sensor, value)
        self.agent.reading_recorded(sensor.subject, value)

    def on_reading(self, sensor, value: float) -> None:
        """What this capability does after recording. Polling re-aims; listening does not."""

    def judge(self, value: float) -> str | None:
        """My own verdict, against my own limits. Computed, never stored."""
        return None if self.band is None else band_for(value, *self.band)

    def sense_now(self) -> None:
        """Ask for a reading now, if my hardware allows it. Listening cannot."""

    def fresh_reading(self, subject_uri: str):
        """The latest reading, or None if it is older than I am willing to trust."""
        reading = self.agent.beliefs.current_reading(subject_uri)
        return reading if reading and reading.is_fresh(self.max_age_s) else None


class PollingModule(PerceptionModule):
    """ag:Polling — derived from being wired to a pull-mode sensor."""

    CAPABILITY = POLLING
    name = "polling"

    def __init__(self, agent):
        self.beliefs = agent.beliefs.polling()
        super().__init__(agent)
        self.min_sleep_s, self.max_sleep_s = self._bounds()
        self.sent_cadence: dict[str, int] = {}

    def _max_age_s(self) -> int:
        return self.beliefs.max_age_s

    def _bounds(self) -> tuple[int, int]:
        rows = bindings(self.agent.store.query(_BOUNDS_Q))
        if not rows:
            raise RuntimeError("the ontology states no cadence bounds — re-run agora-seed")
        return int(rows[0]["min"]), int(rows[0]["max"])

    def start(self) -> None:
        self.sense_now()

    def on_reading(self, sensor, value: float) -> None:
        self.set_cadence(sensor, self.cadence_for(value))

    def cadence_for(self, value: float) -> int:
        """How long the board may sleep: the closer to my own trouble, the closer I watch."""
        b = self.beliefs
        if self.band is None:
            return min(self.max_sleep_s, max(self.min_sleep_s, b.slow_sleep_s))
        low, high = self.band
        span = high - low
        urgency = 1.0 if span <= 0 else min(1.0, max(0.0, (high - value) / span))
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
        for sensor in self.me.sensors:
            if self.drivers[sensor.uri]:
                self.drivers[sensor.uri].sense_now(sensor)


class ListeningModule(PerceptionModule):
    """ag:Listening — derived from being wired to a push-mode sensor.

    No cadence, because there is nothing to send it to. The agent keeps its freshness rule,
    which now works as a *detector* rather than a control: if the board goes quiet, readings
    go stale and the agent stops acting on them instead of quietly using old numbers.
    """

    CAPABILITY = LISTENING
    name = "listening"

    def __init__(self, agent):
        self.beliefs = agent.beliefs.listening()
        super().__init__(agent)

    def _max_age_s(self) -> int:
        return self.beliefs.max_age_s
