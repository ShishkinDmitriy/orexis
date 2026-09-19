"""The belief base's own housekeeping — the one thing every agent reviews about itself.

An agent's store grows on disk for ever while its triple count never moves. It is an LSM tree,
and `sensed_writer` does DELETE-then-INSERT on one observation node per subject, so every
reading appends a new version plus a tombstone. Old versions are reclaimed by compaction, which
is **size-triggered** — and a few hundred triples never approach any threshold, so nothing ever
compacts. On `simulation-fern` that was ~170 KB an hour, about 4 MB a day per agent, for a
dataset whose size never changed.

**In the kernel, not a capability**, by exactly the argument `metrics.py` makes: every agent has
a belief base whatever else it can do, and a rule granting a "please maintain yourself"
capability would fire for everybody, which is the kernel wearing a disguise. What is a capability
is the ability to reconsider something an agent *chose* — and the test for one is whether the
*how* could differ. Reviewing can be done by rule or by asking a model; compacting cannot be done
two ways. **Keeping your own house is not a choice, so it is not a capability.**

**And it holds its own clock, for the same reason.** It used to run on the reviewer's, which was
fine while every agent had a reviewer. Self-review is a capability now, granted only to an agent
the world gave room to move — so an agent without a mandate would have stopped compacting
silently, undoing #45 for exactly the agents nobody was watching. A thing every agent does needs
a timer no capability owns.

**The ratio that revealed the problem is the ratio that triggers the remedy.** `metrics.py`
already computes both numbers on its own clock, and neither alone shows anything: the triples are
flat (correct) and the bytes rise (alarming only if you know the triples are flat). Their quotient
is the whole signal, and it is the trigger. See knowledge/decisions/self-review-is-a-capability.md and issue #45.

The threshold lives in the ontology rather than here, for the same reason the cadence bounds do:
it is what this society tolerates, not how this file happens to be written.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path

from .timer import Timer
from orexis_agent_progression.ontology import OUTDATED
from orexis_agent_progression.store import bindings
from orexis_agent_progression.ontology import PUBLIC

log = logging.getLogger("upkeep")


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



# How often the ratio is looked at. Slow on purpose: compaction is a blocking full rewrite, and
# the growth it answers is measured in megabytes per DAY. Checking hourly would be checking
# sixty times more often than the signal can move.
EVERY_S = 3600

# Read from the T-Box, never compiled in. It hangs off `orexis:BeliefBase` — a fact about the store
# every agent keeps, which is where it had to move when the review vocabulary left the kernel:
# the kernel cannot reference a term a capability owns, and a capability that may not be
# installed cannot be what says how large a belief base may get.
_RATIO_Q = """
SELECT ?ratio WHERE {
  GRAPH ?g { orexis:BeliefBase orexis:maxBytesPerTriple ?ratio }
} LIMIT 1"""


class BeliefBaseUpkeep:
    """Compact when the store is mostly write amplification. Runs on its own clock."""

    name = "belief-base"

    def __init__(self, agent):
        self.agent = agent
        rows = bindings(agent.beliefs.query(_RATIO_Q, agent.beliefs.graphs_of(PUBLIC)))
        if not rows:
            raise RuntimeError(
                "the ontology states no orexis:maxBytesPerTriple — this build's vocabulary is older "
                "than its code")
        self.max_bytes_per_triple = int(rows[0]["ratio"])
        self.compactions = 0
        self._timer: Timer | None = None

    def ratio(self) -> float | None:
        """Bytes on disk per triple held, or None for a store that has no disk.

        None rather than zero: an in-memory store — every test, and every tool that builds a
        world to read it and throw it away — has nothing to compact and no ratio to report, and
        reporting a number for it would put a meaningless line on every dashboard.
        """
        path = getattr(self.agent.beliefs, "path", None)
        if not path:
            return None
        held = len(self.agent.beliefs)
        if held <= 0:
            return None
        size = tree_bytes(path)
        return None if size is None else size / held

    def consider(self) -> bool:
        """Compact if the ratio says the file is mostly history. True if it ran.

        Never raises. Upkeep failing is a reason to say so, not a reason to stop being an agent —
        the same rule instrumentation lives by, and for the same reason.
        """
        ratio = self.ratio()
        if ratio is None or ratio <= self.max_bytes_per_triple:
            return False
        started = time.monotonic()
        try:
            self.agent.beliefs.optimize()
        except Exception as exc:
            # Counted nowhere. A compaction that failed leaves the store exactly as it was, and
            # the next tick will see the same ratio and try again — the retry IS the record.
            log.warning("%s: could not compact the belief base: %s", self.agent.id, exc)
            return False
        self.compactions += 1
        after = self.ratio()
        log.info("%s: belief base compacted in %.1fs — %.0f bytes/triple, now %.0f",
                 self.agent.id, time.monotonic() - started, ratio, after if after else 0)
        return True

    # --- its own clock ---------------------------------------------------------------------

    def start(self) -> None:
        """Begin looking. Started from `run()` like every other timer, so building an agent
        starts no threads and a test can hold one without it acting."""
        self._timer = Timer(EVERY_S, self._tick)
        self._timer.start()

    def sweep(self) -> int:
        """Drop every graph of the agent's own whose period has ended, whatever its kind
        (#645, a-root-holds-always-and-an-outdated-graph-is-dropped). Returns how many went.

        HERE because keeping your own house is not a capability and this is the clock that
        proves it: a graph that ends by the clock must not depend on an event some agent may
        stop receiving. The door already hides an outdated graph from every reader, so
        correctness never waits on this; it is hygiene for a volume — one function, on this
        tick and at boot, in place of the sweep each package used to keep. What a graph's
        ending MEANS is still the owner's: every module is told `orexis:outdated` before the
        drop, and writes the verdict it leaves (absence-is-not-retraction).
        """
        gone = 0
        for graph in self.agent.beliefs.outdated():
            self.agent.tell(OUTDATED, graph)
            self.agent.beliefs.drop_graph(graph)
            gone += 1
        if gone:
            log.info("%s: %d graph(s) whose period had ended were dropped", self.agent.id, gone)
        return gone

    def _tick(self) -> None:
        try:
            self.sweep()
            self.consider()
        except Exception as exc:
            # Upkeep failing is a reason to say so, not a reason to stop being an agent — and a
            # timer whose callback raises would stop rescheduling, so the guard is the clock's.
            log.error("%s: upkeep failed: %s", self.agent.id, exc)

    def stop(self) -> None:
        if self._timer:
            self._timer.stop()
