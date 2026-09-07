---
type: Domain Concept
title: Precondition
term: http://example.org/orexis/progression#premises
description: >-
  What must be true of a world for a step's diff to apply — the instantiated facts the step's
  effect rule read when it produced the diff. A chain's precondition is the regression of its
  steps'. Checked by asking the present, never by re-running the rule. Named by the record
  the-future-is-a-cone; carried on the step as its premises (#550).
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

# What carries it

A [step](/domain/step.md) carries its premises beside its prediction — a reading among them
stated by its [cell](/domain/cell.md), so the premise is "moisture dry" and not "moisture
0.23" (#573): the positive patterns
of its effect's WHERE and of its availability query, instantiated by the store's own engine
for the step's binding in the world it was planned from, and stated as the same canonical
facts the prediction is made of. The planner fills them once along the winning path, while
the imaginarium still holds each step's parent world; the keeper writes them to the ledger
and hands them back with the path a plan walked; a [remembered plan](/domain/remembered-plan.md)
keeps them per step. An absence a rule requires is not among them — it is the regression's
to state.

# The chain

A [remembered plan](/domain/remembered-plan.md) is keyed by the regression of its steps'
premises (#551): step n's less what steps 1 to n−1 add, asked of the present as one query, a
keyed reading by class and key and never by its value. What is not yet in it is an absence a
rule requires — a `FILTER NOT EXISTS` in an availability select — which the first-step menu
check covers for the first step alone. Lifting to variables is the seam after this.
