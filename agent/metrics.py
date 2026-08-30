"""What an agent knows about itself, reported on its own clock.

Everything here is a fact the agent is uniquely placed to state. Nothing else can say how many
triples its private belief base holds, because nothing else can reach it; nothing else knows how
long it has been since a reading arrived, because the gap is only visible from the end that was
waiting. Both were computed by hand during bring-up — the freshness one by pulling every stored
reading and differencing timestamps — which is the tell that the agent should have been saying it
all along.

**Counting is in the kernel; REPORTING is a capability.** Every agent counts the same figures,
and `Observations` counts into them before any module exists — so the account itself is the
kernel's, on the same argument that put `observation.py` here. Where the account GOES is
`capabilities/reporting/`, because that part could differ: a series bucket today, the bus
tomorrow, and the two fail independently.

That capability is MANDATORY — its rule's premise is being an agent, and a shape refuses an agent
without it. Mandatory is not the same as uniform, and treating them as one question is what kept
the whole of this in the kernel: rule 2 asks whether the HOW could differ, not whether every
agent has it. See knowledge/decisions/telemetry-is-a-mandatory-capability.md.

**Counters live here; the events live where they happen.** `Observations` already caught the two
write failures and only logged them — silent data loss that nothing surfaced. It now also tells
this object, which is why the counters hang off the agent rather than off `Observations`: an agent
can hold more than one of those (sensing and simulated-sensing each build their own), and two
sets of counters would report half the truth each.

**Reporting is separate from counting**, and it is now separate in the file layout too. Counting
costs nothing and always happens. Reporting needs a writer, a timer and a credential, so it lives
in a module that starts with the others — which means a test that builds an agent without running
it makes no network calls at all.

See knowledge/domain/agent-metrics.md.
"""

from __future__ import annotations

import logging
import time
from collections import deque
from datetime import datetime, timezone


log = logging.getLogger("metrics")

#  `tree_bytes` WAS HERE, and is upkeep's now (`orexis_progression_patience.upkeep`): the one
#  thing that measures the belief base on disk is the clock that compacts it, and a layer may
#  not import the container for a helper. Reporting reads it from there.


class Metrics:
    """One agent's account of itself. Always present, and it only ever counts.

    Where the account goes is `capabilities/reporting/`, which reads `agent_fields()` off this
    object on its own clock. The split is the one rule 2 draws: counting could not be done
    differently, and a sink could.
    """

    def __init__(self, agent):
        self.agent = agent
        self.started_at = time.monotonic()
        #  What a sensor delivered, how often, how stale, what the store refused — sensing's
        #  counters now, reported through its `reports()`/`series()` (metrics-are-an-aspect).
        # The STORY, beside the figures (#125): point-in-time transitions with their prose —
        # an intention adopted, a commitment resolved, an end judged. Bounded, so a deployment
        # with no working reporter cannot grow a leak: the series is a projection for the
        # operator's eyes, and the record it projects is the graph, which loses nothing here.
        self._events: deque = deque(maxlen=256)

    # --- what the rest of the agent tells it ---

    def event(self, kind: str, text: str, **tags: str) -> None:
        """A transition worth a marker over the series, stamped with the instant it happened.

        Told by whoever the transition happens to, exactly as the counters are — the kernel
        keeps the account, the reporting capability decides where it goes. The text is prose
        for a human reading a dashboard and must never be parsed; the same contract as
        `ag:becauseOf`, whose projection the first caller is.
        """
        self._events.append((datetime.now(timezone.utc), kind, text, tags))

    def take_events(self) -> list[tuple]:
        """Drain the buffer, oldest first. The caller owns what it takes: a reporter whose
        write fails hands them back through `requeue_events`, so a flaky sink delays the
        story rather than losing it."""
        out = []
        while self._events:
            out.append(self._events.popleft())
        return out

    def requeue_events(self, events: list[tuple]) -> None:
        """Put back what could not be written, in order, ahead of anything newer. The bound
        still holds — under a long outage the oldest markers fall off, which is the right
        casualty: the graph keeps the record, this only decorates it."""
        self._events.extendleft(reversed(events))

    # --- what it says about itself ---

    def uptime_s(self) -> float:
        return time.monotonic() - self.started_at

    def agent_fields(self) -> dict:
        return {
            "uptime_s": round(self.uptime_s(), 1),
            # Flat is the expectation, not growth. `sensed_writer` deletes before it inserts, so
            # an agent's belief base holds one current observation per subject however long it
            # runs — a rising line here means something started appending instead, and that is
            # exactly the failure this number exists to make visible.
            "belief_triples": len(self.agent.beliefs),
            # Both were being swallowed by `Observations` and only logged. A dashboard that is
            # flat at zero here is the evidence that nothing is being lost quietly.
            # Which world an agent is actually running, as opposed to which one is on disk. A
            # world can be re-ratified while agents keep running the version they booted with,
            # and nothing else at runtime would show the difference.
            "world_version": int(self.agent.world.version),
            **self._upkeep_fields(),
        }

    def _upkeep_fields(self) -> dict:
        """What the agent has had to do to keep its own house. `belief_bytes` and
        `belief_triples` are reported separately and the interesting thing was always their
        QUOTIENT — flat triples under rising bytes is the signature of write amplification —
        so the compaction count is what tells a reader why the bytes line has teeth in it.
        Every other figure is a MODULE's, answered to the choir's `reports()` and merged by
        reporting (metrics-are-an-aspect); the kernel reports only what is the mind's own."""
        upkeep = getattr(self.agent, "upkeep", None)
        out = {} if upkeep is None else {"belief_compactions": upkeep.compactions}
        return out
