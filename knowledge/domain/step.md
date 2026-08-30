---
type: Domain Concept
title: Step
description: >-
  Planning's word — one act at its place in a plan, with what the search predicted taking it
  would reach. A plan is a sequence of steps; only the head's act is ever committed, because
  the plan is re-derived every pass. A weighed step that was not chosen is a candidate in the
  trace, and a step never outlives the pass that found it.
---

# What it is

A **step** is an [act](/domain/act.md) at a position in a plan: its order, and what the
search predicted — the urgency the want would have in the world after it (`urgency_after`).
`Plan.steps` holds them (`packages/orexis-progression-patience/act.py`'s `Step`); the [imaginarium](/domain/imaginarium.md)
holds the world each one reached, for the life of one pass, and names that world by the path
of steps that reached it.

# Only the head is committed

The plan is re-derived every pass because the world moves, so a committed tail would be a
promise about a future nobody has seen. [Execution](/domain/executor.md) takes the first
step's act, hands it to the keeper as an [intention](/domain/intention.md), and the rest is
trace: every step weighed is an `ag:Candidate` in the deliberation graph, chosen or not, and
none of it is read back.

# What it is not

**Not an act.** The act is what the step proposes; it survives the plan when committed. The
step does not — it is a hypothesis about a world, and a hypothesis must survive nothing
([imaginarium](/domain/imaginarium.md)).
