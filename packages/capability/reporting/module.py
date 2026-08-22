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

import json

from agent import config, sovereign
from agent.metrics import tree_bytes
from agent.module import Module, Timer
from agent.store import bindings

from .beliefs import REPORTING_PICKS
from .terms import STORING


class StoringModule(Module):
    """`reporting:Storing` — the account goes into this agent's own bucket."""

    CAPABILITY = STORING
    name = "reporting"

    def __init__(self, agent):
        super().__init__(agent)
        self.beliefs = agent.desires.read(REPORTING_PICKS)
        self._timer: Timer | None = None
        self._writer = None

    # How many rows an answer may carry. A cap rather than a stream: the sovereign's
    # questions are a person's, and a person who truly wants a million rows has the volume.
    ANSWER_ROWS = 1000

    def subscriptions(self) -> list[str]:
        # The sovereign's question channel (agent/sovereign.py) — the one topic an agent
        # listens on that the world does not state, because it is not the society's business:
        # the ACL grants it to exactly one principal, and this module is where the agent
        # answers for itself. In reporting, deliberately: saying how you are and answering
        # what you believe are one capability's two voices.
        return [sovereign.query_topic(self.agent.id)]

    def handle(self, topic: str, payload: bytes) -> bool:
        if topic != sovereign.query_topic(self.agent.id):
            return False
        answer = self._answer_for(payload)
        return self._reply(answer)

    def _modalities(self) -> dict:
        """The mind's askable surfaces, by the modality's own name — the agent's attributes,
        not a registry: a store that lands on the agent (#299) lands here by one line."""
        return {"beliefs": self.agent.beliefs.query_union,
                "desires": self.agent.desires.query_union}

    def _answer_for(self, payload: bytes) -> dict:
        """One question against ONE modality — named, required, never defaulted.

        The sovereign asks a modality, not a shard and not a union: a-store-is-a-modality's
        third ruling, which is "there is no default world" applied to a mind. A payload that
        names none is refused with the road spelled out, because a fallback would answer a
        question the asker did not ask.
        """
        try:
            asked = json.loads(payload.decode("utf-8"))
            modality, sparql = asked["modality"], asked["sparql"]
        except Exception:
            return {"error": "the payload is JSON with 'modality' and 'sparql', and there is "
                             "no default modality — as there is no default world"}
        surface = self._modalities().get(modality)
        if surface is None:
            return {"error": f"no modality called {modality!r} in this mind — there is "
                             f"{', '.join(sorted(self._modalities()))}"}
        try:
            # The union view within the modality: its private graphs are exactly what cannot
            # be seen elsewhere, and asking is still read-only by construction — the query
            # API structurally cannot execute an update, whichever store answers.
            rows = bindings(surface(sparql))
            answer: dict = {"rows": rows[: self.ANSWER_ROWS]}
            if len(rows) > self.ANSWER_ROWS:
                answer["truncated"] = len(rows)
            return answer
        except Exception as exc:
            # An UPDATE lands here too: the refusal is the engine's, not a filter that could
            # rot. The error goes back — a silent drop would leave the sovereign staring at
            # a timeout.
            return {"error": str(exc)}

    def _reply(self, answer: dict) -> bool:
        # The dict itself: Agent.publish serialises, and pre-dumping here double-encoded
        # the answer into a JSON string OF a JSON string — found by the first live ask.
        self.agent.publish(sovereign.result_topic(self.agent.id), answer)
        self.log.info("answered the sovereign: %s", "error" if "error" in answer
                      else f"{len(answer['rows'])} row(s)")
        return True

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
        # The story rides the same tick, writer, token and bucket as the figures (#125) — so
        # nothing new is granted, and an agent whose modules tell no events writes none. Each
        # event carries its own instant, so landing on the tick costs nothing but latency.
        events = metrics.take_events()
        try:
            self._writer.write_agent_health(
                self.agent.id, metrics.agent_fields(),
                {local_id: (metrics.readings.get(local_id, 0),
                            metrics.reading_age_s(local_id),
                            metrics.cadence_acked_s(local_id))
                 for local_id in sorted(metrics.sensors_seen())},
                belief_bytes=tree_bytes(getattr(self.agent.beliefs, "path", None)),
                tagged=[row for m in self.agent.modules for m_row in [m.series()]
                        for row in m_row],
            )
            if events:
                self._writer.write_events(self.agent.id, events)
        except Exception as exc:
            # Counted nowhere, deliberately: a failure to report the failure count is not worth
            # the counter it would need, and the gap in the series says it plainly enough. The
            # EVENTS go back, though — a figure missed is superseded by the next tick's, where
            # a transition missed is gone, and its whole worth is being rare.
            metrics.requeue_events(events)
            self.log.error("could not report: %s", exc)
