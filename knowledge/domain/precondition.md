---
type: Domain Concept
title: Precondition
description: >-
  What must be true of a world for a step's diff to apply — the instantiated facts the step's
  effect rule read when it produced the diff. A chain's precondition is the regression of its
  steps'. Checked by asking the present, never by re-running the rule. Named by the record
  the-future-is-a-cone and not yet carried on a step (#550).
---

# What it is

A step's diff was produced by an effect rule whose WHERE read some facts of the world it ran
in. Those facts, instantiated with the bindings the rule found, are the step's precondition:
the world in which the diff is what the rule says. An [action](/domain/action.md) states its
applicability as a query, and that query is the template; the precondition is one binding of it,
taken at the moment the step was planned.

A chain of steps has a precondition too, and it is not the union. Step two's premises include
what step one produced, and those are not asked of the present because the chain supplies them.
The chain's precondition is the **regression**: each step's facts minus what the steps before it
add, plus the absences those steps create that a later step needs. That regressed set is what
makes a [remembered plan](/domain/remembered-plan.md) apply wherever it holds, whatever else the
present says, and it is the first half of a [method](/domain/method.md).

# How it is used

- **Obtained once, along the winning path.** The rule's WHERE with its bindings, asked at each
  step's parent world before the pass drops its worlds. Never per fork.
- **Checked as an ASK over the present.** A shape may give the same verdict with a report
  saying which fact is missing, which is what the sovereign reads when a method is not taken.
- **Lifted at promotion.** The terms the action's availability query bound become variables;
  the rest stays constant.

# Not built yet

Nothing carries a precondition today. The effect reader returns the constructed triples and
discards the bindings, and a remembered plan is keyed by a hash of the whole world. The issues
are [#550](https://github.com/ShishkinDmitriy/orexis/issues/550) for the step and
[#551](https://github.com/ShishkinDmitriy/orexis/issues/551) for the chain.
