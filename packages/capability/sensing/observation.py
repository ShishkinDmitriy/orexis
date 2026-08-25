"""Recording something an agent observed — whatever it observed it with.

An agent that comes to know a value about its subject does the same four things every time:
keep the history, assert the current state as its own testimony, tell its peers what it makes
of it, and tell the rest of itself something new is known. None of that depends on where the
number came from — a board on a bus, a wire, or a model the agent holds.

So it lives here, in the kernel, and not in whichever capability happened to obtain the
reading. Two capability packages needing the same behaviour is exactly when it stops belonging
to either of them: they must not import each other, and duplicating it would let two agents
disagree about what "recording a reading" means.

See knowledge/decisions/capability-packages.md.
"""

from __future__ import annotations

from datetime import datetime, timezone

from agent import config
import time

from . import choir
from .sensed_writer import SensedWriter
from .wiring import event_topic_of


def _short(uri: str) -> str:
    """A term's local name, for a human reading a log line. Never used as an identifier."""
    return uri.rstrip("#/").split("#")[-1].split("/")[-1]


SENSOR_MEASUREMENT = "agent_sensor_health"   # what the dashboards filter on


class Observations:
    """One agent's record of what it has observed. Held by whichever module does the observing."""

    def __init__(self, agent, sensors=()):
        self.event_topic = event_topic_of(agent.beliefs.query, agent.me.uri)
        self.agent = agent
        self.me = agent.me
        self.log = agent.log if hasattr(agent, "log") else None
        self.sensed = SensedWriter(agent.beliefs)
        #  THE COUNTERS ARE SENSING'S (metrics-are-an-aspect): per sensor, keyed by local id —
        #  the same key the ACL and the topics use — and reported through this module's
        #  `reports()` and `series()`. They were the kernel's `Metrics`, which knew what a
        #  sensor was; the kernel counts nothing about readings now.
        self.wired = tuple(sensors)
        self.readings: dict[str, int] = {}
        self.last_reading_at: dict[str, float] = {}
        self.acked_cadence: dict[str, int] = {}
        self.sensed_failures = 0

    def close(self) -> None:
        pass

    # --- the account of what this module has heard ---------------------------------------

    def reading_recorded(self, sensor) -> None:
        self.readings[sensor.local_id] = self.readings.get(sensor.local_id, 0) + 1
        self.last_reading_at[sensor.local_id] = time.monotonic()

    def reading_age_s(self, local_id: str) -> float | None:
        """Seconds since this sensor last delivered. None until it has delivered once — an
        agent that has never heard from its board has a different problem from one whose
        board went quiet, and a number for both would hide the first."""
        at = self.last_reading_at.get(local_id)
        return None if at is None else time.monotonic() - at

    def cadence_acked(self, local_id: str, acknowledged_s: int) -> None:
        """The board's own statement of its rhythm (#135), kept for the health series."""
        self.acked_cadence[local_id] = int(acknowledged_s)

    def cadence_acked_s(self, local_id: str) -> int | None:
        return self.acked_cadence.get(local_id)

    def sensors_seen(self) -> set[str]:
        """Every sensor worth a line: the ones wired to this module, and the ones that have
        delivered. A wired sensor that never delivered reports zero — the "never heard from"
        signal — and a delivered one that is not in the wired set (a simulated sensor, wired
        with `ag:models`, which SPARQL does not follow without inference) is not omitted."""
        return {s.local_id for s in self.wired} | set(self.readings)

    def health_rows(self) -> list[tuple[str, dict, dict]]:
        """One tagged row per sensor for the series — `readings_total`, `reading_age_s`,
        `cadence_acked_s` — the sensor as a TAG, so one generic panel groups by it."""
        rows = []
        for local_id in sorted(self.sensors_seen()):
            fields: dict = {"readings_total": int(self.readings.get(local_id, 0))}
            if (age := self.reading_age_s(local_id)) is not None:
                fields["reading_age_s"] = round(float(age), 1)
            if (acked := self.cadence_acked_s(local_id)) is not None:
                fields["cadence_acked_s"] = int(acked)
            rows.append((SENSOR_MEASUREMENT, {"sensor": local_id}, fields))
        return rows

    def record_prior(self, log, sensor, value: float, at: datetime) -> None:
        """A sample the device took EARLIER, placed at the instant it was actually taken.

        The series store only, deliberately, and the asymmetry with `record` is the whole point.
        A crossing report carries the last value the device saw while the world was still quiet,
        which exists to fix a lie the store tells on its own: two points half an hour apart are
        interpolated into a gradual ramp, so a jump that took twenty-five seconds is drawn as a
        slow soak, and every query over that window reads the same falsehood.

        It is NOT a belief and does not go to the sensed store. What the agent believes is what
        it last heard; this is evidence about the SHAPE of a change it has already been told
        about, arriving in the same breath. Writing it as a current observation would make an
        older value overwrite a newer one — the store upserts one observation per
        subject-property — and would re-trigger everything downstream of a reading for a value
        the agent already superseded. No verdict, no announcement, no re-aim: just the point
        that makes the picture true.
        """
        try:
            self.agent.tell("record", value, at, plant=sensor.subject_id,
                            sensor=sensor.local_id, property=_short(sensor.observes))
            log.info("%s: %.3f at %s — the last quiet look before the crossing",
                     sensor.local_id, value, at.isoformat(timespec="seconds"))
        except Exception as exc:
            log.error("influx write failed for the prior sample: %s", exc)
            pass

    def record(self, log, sensor, value: float, at: datetime | None = None,
               phenomenon_at: datetime | None = None) -> None:
        """Keep it, assert it, announce it, and notice it.

        `log` belongs to the calling module so a failure is attributed to the capability that
        was observing, not to this helper.

        `at` is when the measurement arrived. It is resolved once here and given to BOTH
        stores, so a value's instant is the same in the belief base and in the series — they
        used to be stamped independently, seconds of code apart, and a query joining them
        compared two clocks that were only accidentally close.
        """
        at = at or datetime.now(timezone.utc)
        # A reading is the agent's whole reason to be running, and until now taking one logged
        # NOTHING on the happy path — only a cadence CHANGE said anything, and only when it
        # changed. So an agent receiving a reading every ten seconds and an agent whose board
        # had been silent for two days produced identical logs: none. Diagnosing the second
        # meant reading Grafana, which is a poor place to learn that nothing is arriving.
        #
        # One line, at INFO, naming the instrument and the property. Both matter now that a
        # subject can be watched by more than one sensor: "0.183" alone does not say whether
        # that is soil or air.
        verdict = choir.annotations(self.agent, sensor.subject, sensor.observes, value)
        log.info("%s: %s %.3f%s", sensor.local_id, _short(sensor.observes), value,
                 "".join(f"  {k}={v}" for k, v in sorted(verdict.items())))

        try:
            #  TOLD, not written: whoever holds the series sink (reporting) records it.
            self.agent.tell("record", value, at, plant=sensor.subject_id,
                            sensor=sensor.local_id, property=_short(sensor.observes))
        except Exception as exc:  # history is best-effort; never drop the reading over it
            # Logged AND counted. Logging alone made this invisible: nothing reads a container's
            # log until something is already known to be wrong, so a store that had quietly
            # stopped accepting writes looked exactly like one that was working.
            log.error("influx write failed: %s", exc)
            pass
        try:
            self.sensed.write(
                subject_uri=sensor.subject, subject_id=sensor.subject_id,
                value=round(value, 3), sensor_uri=sensor.uri,
                observed_property=sensor.observes, author_uri=self.me.uri,
                # How it was made, in the sensor's own words. A shape requires it, so a sensor
                # with no sense mode never reaches here — the world is refused first.
                used_procedure=sensor.sense_mode,
                world_version=self.agent.world.version,
                ts=at.isoformat(),
                sample_uri=sensor.sample,
                phenomenon_ts=phenomenon_at.isoformat() if phenomenon_at else None,
            )
        except Exception as exc:
            log.error("sensed write failed: %s", exc)
            self.sensed_failures += 1
        if self.event_topic:
            # Voluntary disclosure: the agent announces its own verdict, not its raw state. A
            # host listens for this to learn that scarcity has appeared, and never reads a
            # moisture. The number comes from whoever observed; the judgment comes from
            # whichever capability holds a stake — see runtime.annotations.
            self.agent.tell("send", self.event_topic, {
                "agent": self.me.agent_id, "subject": sensor.subject,
                # Named, because a subject with two sensors announces two values on one topic
                # and a listener that cannot tell them apart is worse off than one told nothing.
                "property": sensor.observes,
                "value": round(value, 3),
                **verdict,
            })
        # Counted after the writes, so a reading that failed both still counts as heard: the
        # sensor did deliver, and conflating "the board went quiet" with "the store refused" is
        # what makes an outage hard to place.
        self.reading_recorded(sensor)
        choir.recorded(self.agent, sensor.subject, sensor.observes, value)
