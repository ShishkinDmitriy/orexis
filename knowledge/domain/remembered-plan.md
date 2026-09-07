---
type: Domain Concept
title: Remembered plan
term: http://example.org/orexis/deliberation#RememberedPlan
description: >-
  A plan that reached its end, lifted into the agent's own graph and hung on the want it
  served, its steps carrying their predictions and premises. Keyed by its regressed
  precondition — what its rules read that the plan did not produce, computed from the steps
  and never stored: a pursuit of that want where those facts hold and the first step is on the
  menu adopts it with no search; where a fact is absent the trace names it; one that fails a
  step is forgotten. A method on the want, filled — not yet lifted to variables.
---

# What it is

`deliberation:RememberedPlan`. On the axis [action](/domain/action.md), [step](/domain/step.md)
and [act](/domain/act.md) sit on, a [method](/domain/method.md) is a template of several steps
and a plan is a method filled; a remembered plan is a filling kept. When a plan the search found
is walked to its end — the deliberator hears the plan finished and the keeper says what was
walked — its steps, with their predictions, their [premises](/domain/precondition.md), lever
and subject, are written into the agent's remembered graph with `deliberation:forWant` the
want and `deliberation:measuredCost` what the search scored it at. Nothing about WHEN it
applies is written: that is computed from the steps each time it is asked.

# How it is used

Before searching for a want, the deliberator asks each plan remembered for it whether it
applies here: the plan's **regressed precondition** — step n's premises less what steps 1 to
n−1 add, the facts the plan read of the world and did not itself produce — held to the present
as one query, a keyed reading asked by class and key and never by its value; and the first
step on the menu now, which is the availability's own answer and carries what a fact set
cannot, a direction among them. One that applies is adopted as the plan, its outcome
`remembered` in the trace, and walked as any plan is: each step verified by the world, the tail
dropped on a surprise (#510). That verification is what makes reuse safe without re-simulating
the plan beforehand — the world checks it, one step at a time. A plan adopted from memory that
fails a step is forgotten, the promotion rule's converse. A remembered plan finishing again is
not remembered twice. One lifted before its steps carried premises is forgotten when asked,
since nothing can say when it applies.

Where a fact the plan read is absent, the plan does not apply here and the pass searches; the
[planner](/domain/planner.md) asks the same precondition of the root world first and, on a miss,
writes the verdict `a remembered plan's precondition does not hold here` with
`deliberation:missing` naming the fact, before any of the plan's steps cost a fork. Where the
precondition holds but a search runs anyway — entered by a road without the adoption in
front of it — the plan is on the menu as ONE candidate: its steps re-simulated in order, each
taken only where the menu of the world the previous step reached offers that very row, and the
world reached settled like any step's; ties among achievers fall to the route already walked.

# What it is not

**Not a habit as the habit record means it.** A [habit](/decisions/a-habit-is-a-compiled-deliberation.md)
is compiled by review into a lookup that answers before the search and is retired by review; a
remembered plan is lifted by the deliberator from what worked and forgotten by the same on
failure. The two may meet when review takes over the forgetting.

**Not a possible world.** What is kept here is the steps to re-try, never the worlds the
search built. The worlds are the [imaginarium](/domain/imaginarium.md)'s to keep, as diffs,
across passes (#553) — a different thing, kept for a different reason: a remembered plan
survives a restart in the agent's own graph, a kept world lives only while its premises stand.

**Not general yet.** Filled, it applies wherever the facts its steps read hold — the same
lever, the same subject, the same standing facts, whatever else the world says. Lifting to
variables (the same instance across steps becoming one variable) is the seam after this. The
tower is where it will pay: the same seven moves every time the stack stands on peg A.
