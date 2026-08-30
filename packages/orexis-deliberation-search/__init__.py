"""The manifest: the deliberation layer — BDI's whether, by bounded search.

The top of the kernel's three layers (a-layer-is-a-package-and-need-loads-it, #452), the row
layered-by-timescale-and-interruptibility calls deliberation: slow, should be interruptible,
and the only layer that searches. Everything here was the kernel's under `agent/` and moved
whole:

- the **deliberator** — asked `decide(desire)`, answering with a plan, and the mind's own
  clock: on the agent's patience it marks every want for reconsideration (`deliberator.py`);
- the **planner**, the **imaginarium** it searches in, the **afforder** that finds the rows,
  the **effects** that predict a step's world and the **signature** that tells two worlds
  apart (`planner.py`, `imaginarium.py`, `afforder.py`, `effects.py`, `signature.py`);
- the **trace** — what a pass considered and why, for a reader (`trace.py`);
- the **reviser** — the belief-revision seam: a mark per want, drained on a thread of the
  mind's own, so nothing that notices a change ever waits for a search (`reviser.py`);
- **pursuit** — plan, commit the head, hand it DOWN to progression to be carried out
  (`pursuit.py`), the deciding half of what was `agent/execution.py`.

It imports progression's contract — the keeper it commits to, the act it fills, the timer it
ticks on, the `carry_out` it hands to — the floor, and the reactive loop for exactly one thing:
handing a plan's head across to be committed and taken as one item there. A search never runs
on the loop; the layer between them is where a tick becomes a mark.

The family is `deliberation`; the member is `search`, because this way of having it is a
bounded search over predicted worlds. Asking a model what next is the sibling member
llm-heavy-deliberation argues for, and `ag:deliberatesBy` is the pick that would choose it.

Not a capability: nothing grants it and there is no `provides()` here.
"""
