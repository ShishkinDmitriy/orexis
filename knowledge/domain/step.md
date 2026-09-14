---
type: Domain Concept
title: Step
term: http://example.org/orexis/progression#Step
description: >-
  A planned instance of an action, not yet done: the lever, the quantity, the window, what the
  search predicted taking it would reach, what it waits for, what follows. A plan is steps, an
  intention commits to steps and stands at one, a claim promises one. Taking a step writes an
  act, the record; a step may be attempted more than once.
---

# What it is

`progression:Step`. One [action](/domain/action.md) filled in and planned — which template, the lever
it goes through, the want it serves and what that want is about, how much, for whom where it is
an obligation's, and its window — with what the search predicted it would reach. Nothing has
happened yet, and that is the whole reason for the word: a plan is not executed, so its
elements are not [acts](/domain/act.md). The sovereign's ruling, 2026-09-02.

Since #550 a step also carries its **precondition** — the facts its rules read in the world it
was planned from — beside the prediction, in the same canonical form and on the same ledger
row. The term was `progression:premises` until #580, when the concept and its term were given
one name; see [precondition](/domain/precondition.md).

# Where it appears

- a plan is a sequence of them, each with the urgency the want would have in the world it reaches
- an [intention](/domain/intention.md) commits to them — `progression:step` to each, `progression:by` to the
  one it stands at, `progression:then` between them in order
- a [claim](/domain/claim.md) promises one: the host's Serving step, so many litres, not after the
  window closes
- the step is what WAITS: its readiness (`progression:until`, `progression:untilNot`), its completion
  (`progression:answeredWhen`), and what the keeper does if a wait lapses (`progression:whenLapsed`)
- it carries what it PREDICTED (`progression:predicts`): the facts the search said taking it makes
  true and false, in the plan's own canonical form — a reading as the [band](/domain/band.md) its
  rule declared (#579) — which is what the world is held to once it is taken, and why no actor
  sizes a watch of its own
- its QUANTITY is filled when it is TAKEN, not when it is planned (#579): the search sizes
  nothing, and the actuator or the bidder computes how much from the reading in hand
- where it was expanded from a [method](/domain/method.md), the filling it is part of
  (`progression:partOf`)
- once answered, the number it predicted and the number the world showed
  (`progression:predictedValue`, `progression:observedValue`) — the residual [review](/domain/review.md)
  reads, met or unmet alike

# What it is not

**Not an act.** An act is the record that a step was taken. One step, possibly several acts,
since an actor may be unable to take it now and a later tick takes it.

**Not a place of its own beside the thing placed.** Every step is minted for the place it fills,
so its place in the plan is the links from the intention and to the next step, not a node.
