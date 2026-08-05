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
        try:
            self.influx.write_reading(sensor.subject_id, sensor.local_id, value)
        except Exception as exc:  # history is best-effort; never drop the reading over it
            log.error("influx write failed: %s", exc)
        try:
            self.sensed.write(
                subject_uri=sensor.subject, subject_id=sensor.subject_id,
                value=round(value, 3), sensor_uri=sensor.uri,
                observed_property=sensor.observes, author_uri=self.me.uri,
                world_version=self.agent.world.version,
            )
        except Exception as exc:
            log.error("sensed write failed: %s", exc)

        if self.me.event_topic:
            # Voluntary disclosure: the agent announces its own verdict, not its raw state. A
            # host listens for this to learn that scarcity has appeared, and never reads a
            # moisture. The number comes from whoever observed; the judgment comes from
            # whichever capability holds a stake — see runtime.annotations.
            self.agent.publish(self.me.event_topic, {
                "agent": self.me.agent_id, "subject": sensor.subject,
                "value": round(value, 3),
                **self.agent.annotations(sensor.subject, value),
            })
        self.agent.reading_recorded(sensor.subject, value)
