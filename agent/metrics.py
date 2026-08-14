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
can hold more than one of those (perception and simulated-sensing each build their own), and two
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
from pathlib import Path


log = logging.getLogger("metrics")

def tree_bytes(path: str | Path | None) -> int | None:
    """Bytes on disk under the belief base, or None if it has none (an in-memory store).

    Walked rather than asked, because the store is a directory of files and no API reports its
    size. Cheap enough at a slow interval: a belief base measured in single megabytes.
    """
    if not path:
        return None
    root = Path(path)
    if not root.exists():
        return None
    total = 0
    for p in root.rglob("*"):
        try:
            if p.is_file():
                total += p.stat().st_size
        except OSError:
            continue  # a compaction can delete a file between the walk and the stat
    return total


class Metrics:
    """One agent's account of itself. Always present, and it only ever counts.

    Where the account goes is `capabilities/reporting/`, which reads `agent_fields()` off this
    object on its own clock. The split is the one rule 2 draws: counting could not be done
    differently, and a sink could.
    """

    def __init__(self, agent):
        self.agent = agent
        self.started_at = time.monotonic()
        self.acked_cadence: dict[str, int] = {}
        # Per sensor, keyed by local id — the same key the ACL and the topics use.
        self.readings: dict[str, int] = {}
        self.last_reading_at: dict[str, float] = {}
        self.influx_failures = 0
        self.sensed_failures = 0
        self.mqtt_reconnects = -1  # the first connect is not a RE-connect; see connected()
        self.mqtt_connected = False
        # The STORY, beside the figures (#125): point-in-time transitions with their prose —
        # an intention adopted, a commitment resolved, an end judged. Bounded, so a deployment
        # with no working reporter cannot grow a leak: the series is a projection for the
        # operator's eyes, and the record it projects is the graph, which loses nothing here.
        self._events: deque = deque(maxlen=256)

    # --- what the rest of the agent tells it ---

    def reading_recorded(self, sensor) -> None:
        local_id = sensor.local_id
        self.readings[local_id] = self.readings.get(local_id, 0) + 1
        self.last_reading_at[local_id] = time.monotonic()

    def influx_failed(self) -> None:
        self.influx_failures += 1

    def sensed_failed(self) -> None:
        self.sensed_failures += 1

    def event(self, kind: str, text: str, **tags: str) -> None:
        """A transition worth a marker over the series, stamped with the instant it happened.

        Told by whoever the transition happens to, exactly as the counters are — the kernel
        keeps the account, the reporting capability decides where it goes. The text is prose
        for a human reading a dashboard and must never be parsed; the same contract as
        `intention:becauseOf`, whose projection the first caller is.
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

    def connected(self) -> None:
        self.mqtt_connected = True
        self.mqtt_reconnects += 1

    def disconnected(self) -> None:
        self.mqtt_connected = False

    # --- what it says about itself ---

    def uptime_s(self) -> float:
        return time.monotonic() - self.started_at

    def cadence_acked(self, local_id: str, acknowledged_s: int) -> None:
        """The board's own statement of its rhythm (#135), kept for the health series."""
        self.acked_cadence[local_id] = int(acknowledged_s)

    def cadence_acked_s(self, local_id: str) -> int | None:
        """None until the board has ever said — old firmware stays legal, and absence is the
        pre-ack world rather than an error."""
        return self.acked_cadence.get(local_id)

    def reading_age_s(self, local_id: str) -> float | None:
        """Seconds since this sensor last delivered. None until it has delivered once.

        None rather than zero, and rather than seconds-since-boot: an agent that has never heard
        from its board has a different problem from one whose board went quiet, and reporting a
        number for both would hide it. `readings_total` at 0 is what says the first case out loud.
        """
        at = self.last_reading_at.get(local_id)
        return None if at is None else time.monotonic() - at

    def agent_fields(self) -> dict:
        return {
            "uptime_s": round(self.uptime_s(), 1),
            # Flat is the expectation, not growth. `sensed_writer` deletes before it inserts, so
            # an agent's belief base holds one current observation per subject however long it
            # runs — a rising line here means something started appending instead, and that is
            # exactly the failure this number exists to make visible.
            "belief_triples": len(self.agent.store),
            "mqtt_connected": 1 if self.mqtt_connected else 0,
            "mqtt_reconnects": max(self.mqtt_reconnects, 0),
            # Both were being swallowed by `Observations` and only logged. A dashboard that is
            # flat at zero here is the evidence that nothing is being lost quietly.
            "influx_write_failures": self.influx_failures,
            "sensed_write_failures": self.sensed_failures,
            # Which world an agent is actually running, as opposed to which one is on disk. A
            # world can be re-ratified while agents keep running the version they booted with,
            # and nothing else at runtime would show the difference.
            "world_version": int(self.agent.world.version),
            **self._upkeep_fields(),
        }

    def _upkeep_fields(self) -> dict:
        """What the agent has had to do to keep its own house, and how many minds it has changed.

        `belief_bytes` and `belief_triples` are reported separately above and the interesting
        thing was always their QUOTIENT — flat triples under rising bytes is the signature of
        write amplification, and neither number alone shows it. Now that the ratio triggers a
        compaction, the compaction count is what tells a reader why the bytes line has teeth in
        it, and `belief_revisions` is what tells them an agent is no longer running exactly the
        beliefs its author wrote. See agora/upkeep.py and capabilities/review/.

        **Two sources, because they are two different things now.** Compaction is every agent's
        and comes off the kernel; the revision counts come off a module an agent may not have.
        An agent given no room to move reports the first and not the others — and the ABSENCE of
        those lines is itself the reading, saying this one was never granted any latitude rather
        than that it has had no second thoughts.
        """
        upkeep = getattr(self.agent, "upkeep", None)
        out = {} if upkeep is None else {"belief_compactions": upkeep.compactions}
        for module in getattr(self.agent, "modules", ()):
            try:
                out.update(module.reports())
            except Exception as exc:
                log.error("%s: %s could not report on itself: %s", self.agent.id, module.name, exc)
        return out

    def sensors_seen(self) -> set[str]:
        """Every sensor worth a line: the ones wired to me, and the ones that have delivered.

        The two sets are not the same and neither contains the other. A wired sensor that has
        never delivered belongs here so it can report zero — that is the whole "the board has
        never been heard from" signal. And a sensor that HAS delivered belongs here even when it
        is not in `me.sensors`, which is not a hypothetical: a simulated sensor is wired with
        `ag:models`, a sub-property of `perception:polls`, and SPARQL does not follow sub-properties
        without inference — so a simulated agent's wired set is empty while it is recording
        readings every few seconds. Reporting only the wired set silently omitted every
        simulated agent, which is exactly the world one tests instrumentation in.
        """
        return {s.local_id for s in self.agent.me.sensors} | set(self.readings)
