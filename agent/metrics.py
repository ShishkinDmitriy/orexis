"""What an agent knows about itself, reported on its own clock.

Everything here is a fact the agent is uniquely placed to state. Nothing else can say how many
triples its private belief base holds, because nothing else can reach it; nothing else knows how
long it has been since a reading arrived, because the gap is only visible from the end that was
waiting. Both were computed by hand during bring-up — the freshness one by pulling every stored
reading and differencing timestamps — which is the tell that the agent should have been saying it
all along.

**In the kernel, not a capability.** Every agent has a belief base, a connection and an uptime,
whatever it composed, and the value is in *all* of them reporting rather than whichever opted in.
The same argument that put `observation.py` here: a thing every agent does is not one capability's
business. It is also not derivable from wiring, and capabilities are derived from wiring — so
making it one would have meant inventing a rule that fires for everybody, which is the kernel
wearing a disguise.

**Counters live here; the events live where they happen.** `Observations` already caught the two
write failures and only logged them — silent data loss that nothing surfaced. It now also tells
this object, which is why the counters hang off the agent rather than off `Observations`: an agent
can hold more than one of those (perception and simulated-sensing each build their own), and two
sets of counters would report half the truth each.

**Reporting is separate from counting.** Counting costs nothing and always happens. Reporting
needs a writer, a timer and a credential, so it starts in `run()` and stops with the agent — which
means a test that builds an agent without running it makes no network calls at all.

See knowledge/domain/agent-metrics.md.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from pathlib import Path

from . import config
from .beliefs import Block
from .module import Timer
from .ontology import term

log = logging.getLogger("metrics")

# How often an agent says how it is. A belief rather than a constant, because it is a rate this
# agent keeps and a test world may want it faster than a deployed one — the same argument that
# put the sensing cadence in beliefs.
#
# Its ABSENCE is meaningful: an agent that states no interval reports nothing. That is a decision
# stated by omission, like a beliefs file with no bidding block, and it is why this is read with
# `read_optional`. Refusing to start over instrumentation would be disproportionate — an agent
# that cannot report is still an agent.
METRICS = term("SelfReporting")


@dataclass(frozen=True)
class SelfReportingBeliefs:
    interval_s: int


SELF_REPORTING_BLOCK = Block(
    capability=METRICS,
    cls=SelfReportingBeliefs,
    terms={"interval_s": term("metricsIntervalS")},
)

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
    """One agent's account of itself. Always present; reports only when told to start."""

    def __init__(self, agent):
        self.agent = agent
        self.started_at = time.monotonic()
        # Per sensor, keyed by local id — the same key the ACL and the topics use.
        self.readings: dict[str, int] = {}
        self.last_reading_at: dict[str, float] = {}
        self.influx_failures = 0
        self.sensed_failures = 0
        self.mqtt_reconnects = -1  # the first connect is not a RE-connect; see connected()
        self.mqtt_connected = False
        self._timer: Timer | None = None
        self._writer = None

    # --- what the rest of the agent tells it ---

    def reading_recorded(self, sensor) -> None:
        local_id = sensor.local_id
        self.readings[local_id] = self.readings.get(local_id, 0) + 1
        self.last_reading_at[local_id] = time.monotonic()

    def influx_failed(self) -> None:
        self.influx_failures += 1

    def sensed_failed(self) -> None:
        self.sensed_failures += 1

    def connected(self) -> None:
        self.mqtt_connected = True
        self.mqtt_reconnects += 1

    def disconnected(self) -> None:
        self.mqtt_connected = False

    # --- what it says about itself ---

    def uptime_s(self) -> float:
        return time.monotonic() - self.started_at

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

    # --- reporting ---

    def start(self, interval_s: int) -> None:
        """Begin reporting. Called from run(), after the signal mask is in place."""
        bucket, token = config.env("INFLUX_BUCKET"), config.env("INFLUX_TOKEN")
        if not bucket or not token:
            # Unlike a reading, a missing metric is not lost evidence about the world — so this
            # says so and carries on rather than refusing to run. An agent that cannot report is
            # still an agent; one that cannot record is not.
            log.warning("%s: no series credential, so nothing will be reported about this agent",
                        self.agent.id)
            return
        from .influx_writer import InfluxWriter  # deferred: nothing is built for a test agent

        self._writer = InfluxWriter(
            config.env("INFLUX_URL", "http://localhost:8086"), token,
            config.env("INFLUX_ORG", "agora"), bucket)
        self._timer = Timer(interval_s, self.report)
        self._timer.start()
        log.info("%s: reporting on itself every %ss", self.agent.id, interval_s)

    def stop(self) -> None:
        if self._timer:
            self._timer.stop()
        if self._writer:
            try:
                self._writer.close()
            except Exception:  # shutting down; a failed close must not mask the real exit
                pass

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

    def report(self) -> None:
        """Write one round. Never raises: instrumentation must not take an agent down."""
        if self._writer is None:
            return
        try:
            self._writer.write_agent_health(
                self.agent.id, self.agent_fields(),
                {local_id: (self.readings.get(local_id, 0), self.reading_age_s(local_id))
                 for local_id in sorted(self.sensors_seen())},
                belief_bytes=tree_bytes(getattr(self.agent.store, "path", None)),
            )
        except Exception as exc:
            # Counted nowhere, deliberately: a failure to report the failure count is not worth
            # a second counter, and the gap in the series says it.
            log.warning("%s: could not report metrics: %s", self.agent.id, exc)
