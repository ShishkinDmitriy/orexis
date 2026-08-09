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
is the ability to review something an agent *chose*; keeping your own house is not a choice.

**The ratio that revealed the problem is the ratio that triggers the remedy.** `metrics.py`
already computes both numbers on its own clock, and neither alone shows anything: the triples are
flat (correct) and the bytes rise (alarming only if you know the triples are flat). Their quotient
is the whole signal, and it is the trigger. See knowledge/decisions/a-belief-is-a-pick-within-a-range.md and issue #45.

The threshold lives in the ontology rather than here, for the same reason the cadence bounds do:
it is what this society tolerates, not how this file happens to be written.
"""

from __future__ import annotations

import logging
import time

from .metrics import tree_bytes
from .store import bindings

log = logging.getLogger("upkeep")

# Read from the T-Box, never compiled in. Hangs off ag:SelfReview because that is the term the
# whole review mechanism is named by — the same shape as ag:PerceptionCapability holding the
# sleep bounds for every transport that will ever perceive.
_RATIO_Q = """
SELECT ?ratio WHERE {
  GRAPH ?g { ag:SelfReview ag:maxBytesPerTriple ?ratio }
} LIMIT 1"""


class BeliefBaseUpkeep:
    """Compact when the store is mostly write amplification. Runs on the reviewer's clock."""

    name = "belief-base"

    def __init__(self, agent):
        self.agent = agent
        rows = bindings(agent.store.query(_RATIO_Q))
        if not rows:
            raise RuntimeError(
                "the ontology states no ag:maxBytesPerTriple — this build's vocabulary is older "
                "than its code")
        self.max_bytes_per_triple = int(rows[0]["ratio"])
        self.compactions = 0

    def ratio(self) -> float | None:
        """Bytes on disk per triple held, or None for a store that has no disk.

        None rather than zero: an in-memory store — every test, and every tool that builds a
        world to read it and throw it away — has nothing to compact and no ratio to report, and
        reporting a number for it would put a meaningless line on every dashboard.
        """
        path = getattr(self.agent.store, "path", None)
        if not path:
            return None
        held = len(self.agent.store)
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
            self.agent.store.optimize()
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
