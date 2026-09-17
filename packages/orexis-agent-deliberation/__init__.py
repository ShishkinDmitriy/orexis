"""The manifest: the deliberation layer — BDI's whether, by bounded search.

The top of the kernel's three layers (a-layer-is-a-package-and-need-loads-it, #452), the row
layered-by-timescale-and-interruptibility calls deliberation: slow, should be interruptible,
and the only layer that searches. Everything here was the kernel's under `agent/` and moved
whole:

- the **deliberator** — asked `decide(desire)`, answering with a plan, and the mind's own
  clock: on the agent's patience it marks every want for reconsideration (`deliberator.py`);
- the **planner**, the **imaginarium** it searches in, the **affordances** it ranges over,
  the **effects** that predict a step's world and the **signature** that tells two worlds
  apart (`planner.py`, `imaginarium.py`, `affordances.py`, `effects.py`, `signature.py`);
- the **trace** — what a pass considered and why, for a reader (`trace.py`);
- the **reviser** — the belief-revision seam: a mark per want, drained on a thread of the
  mind's own, so nothing that notices a change ever waits for a search (`reviser.py`);
- **pursuit** — plan, commit the head, hand it DOWN to progression to be carried out
  (`pursuit.py`), the deciding half of what was `agent/execution.py`.

It imports progression's contract — the keeper it commits to, the act it fills, the timer it
ticks on, the `carry_out` it hands to — the floor, and the reactive loop for exactly one thing:
handing a plan's head across to be committed and taken as one item there. A search never runs
on the loop; the layer between them is where a tick becomes a mark.

The name is `orexis-agent-deliberation`: the family `agent` groups the three layers in a
listing ("hard to locate packages in the list without it"), and a layer is ONE package, not a
family with members. This one deliberates by a bounded search over predicted worlds; asking a model
what next, which llm-heavy-deliberation argues for and `orexis:deliberatesBy` would pick, is a
decision for then — inside this package or beside it — rather than a sibling waiting for a slot.

Not a capability: nothing grants it and there is no `provides()` here.
"""

from pathlib import Path

from assembly import contributes, VOCABULARY


@contributes(VOCABULARY)
def vocabulary(package: Path) -> list[Path]:
    """the layer's own words (#529)."""
    return [package / "ontology.ttl"]
