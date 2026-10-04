---
type: Domain Concept
title: Plan
term: http://example.org/orexis/planning#Plan
description: >-
  What a search found for one want, written down - a `planning:PlanGraph` in the imaginarium
  holding the steps on the winning world's ancestry in execution's words, what the path was scored
  to spend, and why the search ended. Never executed itself - the executor adopts it into an
  intention, and the world verifies each step as it is taken.
---

# What it is

`extract_plan` reads one world's ancestry — each possible world names the candidate that reached
it, and each candidate the world it was taken in — and writes it as a graph of its own: one
`planning:Plan` `planning:for` the want, one [step](/domain/execution/step.md) per candidate on the
path, ordered by `execution:then`, each naming the two graphs it predicts in (`execution:adds`,
`execution:retracts`, filled by the same update as the diff of its world against the one before),
when it may be taken (`execution:notBefore`, the start of the
world it is taken in) and the earliest and the latest its change lands (`execution:landsAt`,
`execution:notAfter`, the two ends of the world it reaches). `planning:spent` is what the path cost.

# An empty plan is an answer

`planning:outcome` says which of three:

- **`planning:Satisfied`** — a world meeting the want was reached; the steps are the way there,
  none where it was met already.
- **`planning:NoCandidate`** — no action this agent holds was admitted at all: nothing points at
  the want.
- **`planning:Exhausted`** — actions were admitted and none reached it within the budget. The next
  pass continues the same search rather than starting over.

# What happens to it

`publish_plan` publishes every plan of a pass into the belief base once, as an `orexis:PlanGraph`
under a name of its own, its steps' two graphs beside it under theirs, which planning owns and which
stay; the [executor](/domain/execution/executor.md)
hears it published and adopts it by reference as an [intention](/domain/execution/intention.md) — unless
an intention, or a plan published and not yet adopted, already
walks that want, or the want has gone. The plan graph stays in the imaginarium while the search's worlds
do.
