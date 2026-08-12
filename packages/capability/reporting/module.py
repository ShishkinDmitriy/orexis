"""Putting an agent's account of itself into its own series bucket.

**Counting is not this module's business and never was.** `agent/metrics.py` accumulates the
figures in the kernel, because `Observations` counts into them before any module exists and every
agent counts the same things. What this module owns is the *sink*: a credential, a writer, a
clock, and one write per tick. That is the part a second member would replace, and it is why
reporting is a capability at all — `reporting:Announcing` would take the same `agent_fields()`
and put them on the bus instead.

**Mandatory, which is not the same as uniform.** Every agent is granted this by
`rules.ru`, whose premise is being an agent, and a shape refuses one without it. That is
deliberate and load-bearing: a silent agent must not be indistinguishable from a dead one, and an
agent that could lose the ability to say it is unwell is the one you most need to hear from.

Vocabulary: capabilities/reporting/ontology.ttl. Rules: capabilities/reporting/rules.ru.
"""

from __future__ import annotations

from agent import config
from agent.metrics import tree_bytes
from agent.module import Module, Timer

from .beliefs import REPORTING_BLOCK
from .terms import STORING


class StoringModule(Module):
    """`reporting:Storing` — the account goes into this agent's own bucket."""

    CAPABILITY = STORING
    name = "reporting"

    def __init__(self, agent):
        super().__init__(agent)
        self.beliefs = agent.beliefs.read(REPORTING_BLOCK)
        self._timer: Timer | None = None
        self._writer = None

    def start(self) -> None:
        """Begin reporting. Called once the connection is up, with the signal mask in place."""
        bucket, token = config.env("INFLUX_BUCKET"), config.env("INFLUX_TOKEN")
        if not bucket or not token:
            # Unlike a reading, a missing metric is not lost evidence about the world — so this
            # says so and carries on rather than refusing to run. An agent that cannot report is
            # still an agent; one that cannot record is not.
            #
            # Note what this is NOT: a way to opt out. The capability is granted and the shape
            # insists on it; a credential missing from the environment is a deployment fault, and
            # it is loud here for the same reason it is not a belief — an operator can fix it
            # without re-ratifying a world.
            self.log.warning("no series credential, so nothing will be reported about this agent")
            return
        from agent.influx_writer import InfluxWriter  # deferred: nothing built for a test agent

        self._writer = InfluxWriter(
            config.env("INFLUX_URL", "http://localhost:8086"), token,
            config.env("INFLUX_ORG", "agora"), bucket)
        self._timer = Timer(self.beliefs.interval_s, self.report)
        self._timer.start()
        self.log.info("reporting on itself every %ss", self.beliefs.interval_s)

    def stop(self) -> None:
        if self._timer:
            self._timer.stop()
        if self._writer:
            try:
                self._writer.close()
            except Exception:  # shutting down; a failed close must not mask the real exit
                pass

    def report(self) -> None:
        """Write one round. Never raises: instrumentation must not take an agent down."""
        if self._writer is None:
            return
        metrics = self.agent.metrics
        try:
            self._writer.write_agent_health(
                self.agent.id, metrics.agent_fields(),
                {local_id: (metrics.readings.get(local_id, 0), metrics.reading_age_s(local_id))
                 for local_id in sorted(metrics.sensors_seen())},
                belief_bytes=tree_bytes(getattr(self.agent.store, "path", None)),
            )
        except Exception as exc:
            # Counted nowhere, deliberately: a failure to report the failure count is not worth
            # the counter it would need, and the gap in the series says it plainly enough.
            self.log.error("could not report: %s", exc)
