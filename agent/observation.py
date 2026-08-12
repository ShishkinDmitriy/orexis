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

from . import config
from .influx_writer import InfluxWriter
from .sensed_writer import SensedWriter


def _short(uri: str) -> str:
    """A term's local name, for a human reading a log line. Never used as an identifier."""
    return uri.rstrip("#/").split("#")[-1].split("/")[-1]


class Observations:
    """One agent's record of what it has observed. Held by whichever module does the observing."""

    def __init__(self, agent):
        self.agent = agent
        self.me = agent.me
        self.log = agent.log if hasattr(agent, "log") else None
        # The bucket and the token have NO defaults, and that is the point. They are this
        # agent's alone, minted by `agora-influx` and mounted into its container only; falling
        # back to a shared bucket would quietly undo the isolation at exactly the moment the
        # credential failed to arrive. The URL and org may default — they say where the store
        # is, which is not a privilege. See knowledge/decisions/series-and-bus-isolation.md.
        bucket, token = config.env("INFLUX_BUCKET"), config.env("INFLUX_TOKEN")
        if not bucket or not token:
            raise RuntimeError(
                "no INFLUX_BUCKET/INFLUX_TOKEN in the environment — this agent has no series "
                "store of its own. Run `agora-influx <world>` and regenerate the compose file.")
        self.influx = InfluxWriter(
            config.env("INFLUX_URL", "http://localhost:8086"),
            token,
            config.env("INFLUX_ORG", "agora"),
            bucket,
        )
        self.sensed = SensedWriter(agent.store)

    def close(self) -> None:
        self.influx.close()

    def record(self, log, sensor, value: float) -> None:
        """Keep it, assert it, announce it, and notice it.

        `log` belongs to the calling module so a failure is attributed to the capability that
        was observing, not to this helper.
        """
        # A reading is the agent's whole reason to be running, and until now taking one logged
        # NOTHING on the happy path — only a cadence CHANGE said anything, and only when it
        # changed. So an agent receiving a reading every ten seconds and an agent whose board
        # had been silent for two days produced identical logs: none. Diagnosing the second
        # meant reading Grafana, which is a poor place to learn that nothing is arriving.
        #
        # One line, at INFO, naming the instrument and the property. Both matter now that a
        # subject can be watched by more than one sensor: "0.183" alone does not say whether
        # that is soil or air.
        verdict = self.agent.annotations(sensor.subject, sensor.observes, value)
        log.info("%s: %s %.3f%s", sensor.local_id, _short(sensor.observes), value,
                 "".join(f"  {k}={v}" for k, v in sorted(verdict.items())))

        try:
            self.influx.write_reading(sensor.subject_id, sensor.local_id, value,
                                      _short(sensor.observes))
        except Exception as exc:  # history is best-effort; never drop the reading over it
            # Logged AND counted. Logging alone made this invisible: nothing reads a container's
            # log until something is already known to be wrong, so a store that had quietly
            # stopped accepting writes looked exactly like one that was working.
            log.error("influx write failed: %s", exc)
            self.agent.metrics.influx_failed()
        try:
            self.sensed.write(
                subject_uri=sensor.subject, subject_id=sensor.subject_id,
                value=round(value, 3), sensor_uri=sensor.uri,
                observed_property=sensor.observes, author_uri=self.me.uri,
                # How it was made, in the sensor's own words. A shape requires it, so a sensor
                # with no sense mode never reaches here — the world is refused first.
                used_procedure=sensor.sense_mode,
                world_version=self.agent.world.version,
            )
        except Exception as exc:
            log.error("sensed write failed: %s", exc)
            self.agent.metrics.sensed_failed()
        if self.me.event_topic:
            # Voluntary disclosure: the agent announces its own verdict, not its raw state. A
            # host listens for this to learn that scarcity has appeared, and never reads a
            # moisture. The number comes from whoever observed; the judgment comes from
            # whichever capability holds a stake — see runtime.annotations.
            self.agent.publish(self.me.event_topic, {
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
        self.agent.metrics.reading_recorded(sensor)
        self.agent.reading_recorded(sensor.subject, sensor.observes, value)
