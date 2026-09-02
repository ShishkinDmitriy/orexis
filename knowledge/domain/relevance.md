---
type: Domain Concept
title: Relevance
description: >-
  Which of an agent's levers could serve one want — read off the actions themselves, never
  declared, and closed backward through preconditions to a fixed point. A pass simulates only
  relevant rows; the rest are recorded as touching nothing the want reads. Anything a parser
  cannot name reads as anything and keeps every lever, so the filter can cost forks and never
  a plan.
---

# What it is

The set of [actions](/domain/action.md) whose effect writes a predicate the [want](/domain/desire.md)
reads, or whose effect writes what a relevant action's precondition reads, and so on to a
fixed point. Computed per pass in `packages/orexis-agent-deliberation/relevance.py`, from three
sets that are all derived:

- **what the want reads** — every `sh:path` on its shape flattened to predicates, and the
  predicates of any `sh:sparql` constraint or authored pattern, parsed;
- **what an action writes** — the predicates of its `sh:construct` template and its
  `orexis:retracts` template;
- **what an action reads** — the predicates of its `orexis:available`.

A derivation rule joins as an edge, its INSERT writing and its WHERE reading, with no row of
its own; a narrower property reaches a want reading the broader one, as the entailment would
fold it. See [relevance-is-read-off-the-actions-and-closed-backward](/decisions/relevance-is-read-off-the-actions-and-closed-backward.md).

# How to use it

**Nothing to declare.** A package states its actions' texts and its rules; relevance is what
they imply. A declared list of what each action touches would be a second statement of what the construct
settles, and the search carries the scar of a guard that disagreed with the effect it described.

**Read the trace.** A row the filter passed over is written as `irrelevant` beside the rows
that were weighed, so "this lever was there and touched nothing the want reads" is visible and
distinct from "this was weighed and lost". A menu of only such rows is the finding NOTHING —
equip me — which is honest where no lever points at the want.

**The rule it rests on: over-approximation is safe.** A `sh:sparql` body the parser refuses, an
effect with a variable predicate — every plant lever's retraction of `?obs ?p ?o` — a want
with no shape and no pattern, an obligation, a call: each reads as *anything* and keeps every
action. Predicates are a coarse key on purpose; two domains sharing one stay mutually relevant,
which costs forks and never correctness. An action stating no effect is outside the closure
entirely, because the search never simulates it anyway.

**Where it bites.** Nowhere in a world of one domain: the shipped menus are one to three rows
and every row serves the want. It bites where a world composes two domains, or where a
package adds a free action the want never reads — measured in
[measure-the-search](/runbooks/measure-the-search.md), where since the budget replaced depth
such a lever does not slow a solve but spends the budget and leaves the puzzle unsolved.
