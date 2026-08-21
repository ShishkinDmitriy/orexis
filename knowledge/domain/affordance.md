---
type: Domain Concept
title: Affordance
description: >-
  One row of what an agent could do — a means, the property it is about, the lever it goes
  through, which way that moves it, and whether it is the agent's to CHOOSE or to honour on
  demand. Always DERIVED and never stored, because a stored row can outlive the plumbing it
  was concluded from; contributed by whichever package owns the lever, as its own
  `affordances.rq`, so a new way of acting is a new directory rather than an edit to a
  registry. The menu is the union of those rows, and it is also the precondition language —
  a row whose premises cannot hold does not exist, so chaining needs no separate `requires`.
  The row that is ABSENT is a finding too: a want with no lever is legitimate and legible.
---

# What it is

An **affordance** is one row of the answer to *what could I do?* — asked of the graph, never
written into it:

| | |
|---|---|
| `means` | the kind of act: `ag:Observe`, `ag:Actuate`, `ag:Acquire`, `ag:Offer` |
| `observed_property` | what it is about — the property the agent holds a desire in |
| `via` | the lever it goes through: this probe, this valve, this venue |
| `direction` | which way it moves the property, or **empty** for a look |
| `mode` | `Chosen` — mine to range over — or `Owed`, a duty exercised on demand |
| `for_agent` | on an owed row, whom it is owed to. Absent on a chosen one |

The **menu** is every such row for one agent, and `menu_of` is the whole of it. For the
simulation's fern: *look at moisture through the probe; look at temperature through the
thermometer; raise moisture through the market.* For the loner world's gardener: *raise it
through your own pump* — the Actuate rung, offered exactly where the lever chain and the
resource chain both end at the agent.

**A row's emptiness is data.** Looking moves nothing, so Observe's `direction` column is blank,
and a model reading the menu learns from that blank which moves change the world and which only
change what it knows.

# It is derived, and that is not a performance choice

A row is a **conclusion whose premises are stored** — regions, wiring, denominations, all facts
that exist for their own reasons. Storing the conclusion would let it outlive them: unplumb the
valve and an authored row still says you can dose. So the menu is computed on every ask, and the
[menu graph](/decisions/the-mind-is-six-graphs.md) holds rules about means but never rows about
levers.

The same argument in reverse is why a rule about a means *is* stored — `effects.ttl` is a schema,
and a schema cannot outlive anything.

# The menu is the precondition language

This is the part worth internalising, because it is why planning needs no `requires` clause of
its own.

**A row whose premises cannot hold does not exist.** Sensing's walk is `polls → monitors →
observes`; the market's closes venue → source → good → valuation. Every hop must hold or there
is no row. So "is this act available?" and "does this row exist?" are the same question — and
**chaining is the same query re-run in the simulated world**: an effect that makes a missing row
appear is the step before it.

`packages/capability/deliberation/search.py` therefore consults no declaration of what a lever
repairs. Simulation is the authority either way: trying a lever that turns out not to help costs
one validation; trusting a declaration that turns out to be wrong costs a plant.

# Each package ships its own rows

There is no menu file. Each package that owns a lever ships an `affordances.rq` beside its
ontology, and `menu_of` collects whatever the loader finds — sensing contributes Observe,
actuation Actuate, the market Acquire and Offer.

It began as one `menu.rq` in the deliberation package, which made the menu's KINDS a registry in
one directory: adding a way of acting meant editing another package's file. The sovereign caught
the overclaim — *how is it dynamic if the list is hardcoded?* — and the fix was this repo's
mechanic applied again. **A new way of acting is a new directory**: an ontology for the tool's
schema, an `affordances.rq` for its availability, a module for its implementation — or no module
at all, where execution reduces to an actor that already exists.

`$me` is the one thing a shipped query cannot know, and it is substituted by whoever collects the
menu. Everything else is an unqualified pattern, because regions and wiring are public.

# Two modes: what I choose, and what I honour

A **chosen** row is an option a deliberator ranges over. An **owed** row is a duty: a lever the
agent must exercise on a valid presentation and must never *propose*. A host holding a claim
owes the dose; nothing about that is a decision, and a deliberator that ranged over it would be
choosing whether to keep its word.

`for_agent` is what lets a duty find its means — an obligation names who it is owed to, and the
row that answers is the one honoured for exactly that agent. Absent mode means chosen, so a
branch written before the distinction keeps its meaning.

# The row that is not there

A want with no row is a real answer and a legible one. Fern holds a desire in air temperature
and can see it, but nothing it owns or can buy moves it: three Observe rows, no lever. That is a
**want with no means** — legitimate, not a misconfiguration — and the search reports it as
`no candidate` rather than as failure. It is the difference between *equip me* and *my doses are
too coarse*, which is a distinction a planner that reported them alike would destroy.

# Related

- [deliberation](/domain/deliberation.md) ranges over the chosen rows, scores them by simulation,
  and holds what a lever DOES — a row says only that one is available.
- [desire](/domain/desire.md) is the other half of a decision: a row answers *what could I do*, a
  gap answers *about what*.
- [package](/domain/package.md) is how a contribution is found: a directory, and nothing lists it.
- [the-mind-is-six-graphs](/decisions/the-mind-is-six-graphs.md) places rows in the menu modality
  and explains why they are derived where a rule is asserted.
