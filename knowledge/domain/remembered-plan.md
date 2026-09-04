---
type: Domain Concept
title: Remembered plan
term: http://example.org/orexis/deliberation#RememberedPlan
description: >-
  A plan that reached its end, lifted into the agent's own graph and hung on the want it
  served with the signature of the world it was decided in. A pursuit of that want in a world
  of the same signature adopts it with no search; in a world of another signature it is
  walked as one candidate on the menu, weighed against the primitives and seeding the bound;
  one that fails a step is forgotten. A method on the want, filled — not yet lifted to variables.
---

# What it is

`deliberation:RememberedPlan`. On the axis [action](/domain/action.md), [step](/domain/step.md)
and [act](/domain/act.md) sit on, a [method](/domain/method.md) is a template of several steps
and a plan is a method filled; a remembered plan is a filling kept. When a plan the search found
is walked to its end — the deliberator hears the plan finished and the keeper says what was
walked — its steps, with their predictions and lever and subject, are written into the agent's
remembered graph with `deliberation:forWant` the want, `deliberation:inWorld` the signature of
the world it was decided in, and `deliberation:measuredCost` what the search scored it at.

# How it is used

Before searching for a want, the deliberator hashes the world it stands in — the topology and
the readings, the same canonical facts the search's signature is made of, and nothing the agent
writes about itself, since the ledger and the trace change with every pass — and asks for a
remembered plan of that want in that world. One found is adopted as the plan, its outcome
`remembered` in the trace, and walked as any plan is: each step verified by the world, the
tail dropped on a surprise (#510). That verification is what makes reuse safe without checking
the stored plan against the world beforehand — the world checks it, one step at a time. A plan
adopted from memory that fails a step is forgotten, the promotion rule's converse. A remembered
plan finishing again is not remembered twice.

Where the world's signature is not one the want was remembered in, the pass searches — and the
[planner](/domain/planner.md) puts every plan remembered for the want on the menu first, as ONE
candidate: its steps re-simulated in order, each taken only where the menu of the world the
previous step reached offers that very row, and the world reached settled like any step's. An
achiever's cost is the bound before any primitive is looked at, ties among achievers fall to the
route already walked, and the trace names it as taken and as chosen by its own node. A step off
the menu is the verdict `a remembered step is not on the menu here`. A route that fails when
walked is forgotten by its steps, whichever road adopted it.

# What it is not

**Not a habit as the habit record means it.** A [habit](/decisions/a-habit-is-a-compiled-deliberation.md)
is compiled by review into a lookup that answers before the search and is retired by review; a
remembered plan is lifted by the deliberator from what worked and forgotten by the same on
failure. The two may meet when review takes over the forgetting.

**Not a possible world.** What is kept is the steps to re-try, never the worlds the search
built; the imaginarium stays required to be lost, and #527 — resuming a search from a kept
frontier — is a different, parked thing.

**Not general yet.** Filled, it applies where its steps are on the menu in order — the same
lever, the same subject — which is the same world or one differing in what no step reads.
Lifting to variables (the same instance across steps becoming one variable) and the applicability
regressed through the effects are the seams after this, in that order. The tower is where they
will pay: the same seven moves every time the stack stands on peg A.
