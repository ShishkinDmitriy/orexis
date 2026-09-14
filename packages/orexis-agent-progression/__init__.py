"""The manifest: the progression layer — executing what is already committed, on the loop.

The middle of the kernel's three layers (a-layer-is-a-package-and-need-loads-it, #452), and
the row layered-by-timescale-and-interruptibility calls intention progression: seconds to
minutes, suspends rather than blocks, searches nothing. What it holds is exactly what that
record listed as already true of the code, gathered from `agent/` into one package:

- the **keeper** — the ledger of intentions, the patience that absorbs a repeated impulse,
  and the watch that verifies whether the world answered (`keeper.py`);
- the **act** and the **commitment** — what is committed to, and what a valve fulfils
  (`act.py`, `commitment.py`), the lowest place their importers put them;
- the **scheduler** and the **timer** — one thread that keeps time and runs nothing, and the
  cadence-or-deadline every caller in the society holds; a timer landing ENQUEUES its function
  onto the reactive loop rather than running it on a thread of its own (`scheduler.py`,
  `timer.py`);
- **execution** — the doing half of the old `agent/execution.py`: hand a committed act to
  whoever the T-Box says takes it, on the loop (`execution.py`);
- **upkeep** — the housekeeping clock, sweeping and compacting (`upkeep.py`).

Waiting is done by STANDING, never by sleeping. An actor that cannot act now answers False
and the intention stands for the next trigger; an act with a window carries its own deadline;
a watch is judged when a reading arrives. Nothing here holds the loop while it waits,
which is the constraint the reactive layer exists to make checkable.

The name is `orexis-agent-progression`: the family `agent` groups the three layers in a
listing ("hard to locate packages in the list without it"), and a layer is ONE package, not a
family with members. What this one does is keep a commitment standing within a stated patience and
supersede it past it — the amortised deliberation of an-intention-is-an-amortised-deliberation;
the open-minded commitment the keeper's own docstring sketches would be a change to this
package, a decision for then, not a sibling waiting for a slot.

Not a capability: nothing grants it and there is no `provides()` here. It imports the
reactive layer and the floor, and `tests/test_layering.py` holds it to that.
"""

from pathlib import Path

from assembly import contributes, VOCABULARY


@contributes(VOCABULARY)
def vocabulary(package: Path) -> list[Path]:
    """the layer's own words (#529)."""
    return [package / "ontology.ttl"]
