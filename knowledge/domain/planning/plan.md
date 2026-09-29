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
path, ordered by `execution:then`, each with what it `execution:predicts`, what its rules read
(`execution:precondition`) and when it may be taken (`execution:notBefore`, the instant of the
world it is taken in). `planning:spent` is what the path cost.

# An empty plan is an answer

`planning:outcome` says which of three:

- **`planning:Satisfied`** — a world meeting the want was reached; the steps are the way there,
  none where it was met already.
- **`planning:NoCandidate`** — no action this agent holds was admitted at all: nothing points at
  the want.
- **`planning:Exhausted`** — actions were admitted and none reached it within the budget. The next
  pass continues the same search rather than starting over.

# What happens to it

`publish_plan` hands every plan of a pass down into the belief base as an `execution:PlanGraph`,
which the [executor](/domain/execution/executor.md) takes up and commits as an
[intention](/domain/execution/intention.md) — unless an intention, or a plan handed down, already
walks that want, or the want has gone. The plan graph stays in the imaginarium while the search's worlds
do.
