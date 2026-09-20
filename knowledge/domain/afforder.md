---
type: Service
title: Afforder
description: >-
  The service between two collections - it decides WHAT to ask and they know HOW to fetch. Which
  actions are worth asking about, whose wants to ask them against, and how to order what comes
  back are its; the vocabulary's templates are `Actions`', one action's rows in one world are
  `Affordances`', and what this agent holds is the desire modality's. It authors no query and
  touches no store, which a test in its package holds it to.
---

# What it decides

Three things, and none of them is a query.

**Which actions are worth asking about at all.** A precondition is a query per action per world,
and an action that touches nothing the want reads was already never simulated; asked through here it
is never asked either, so a menu that grows by unrelated domains costs a pass nothing. That is the
search's relevant set (#504), and it is a judgement about the search rather than something either
collection could know.

**Whose wants to ask them against.** It asks the desire modality once for what this agent holds
and what each of them is about, and hands that to every ask. Fetching it here was the defect this
service was carved out of: the file that consumed the answer held the query for another
collection's contents.

**Which world each ask is about.** What a package DECLARES is public and timeless; what a WORLD
affords is neither, so a search names a different world at every node — and names it, rather than
being given a collection built for it.

An agent holds ONE of these and it keeps nothing. It held a memo once, so that it would ask each
side only as often as that side could change — and a service with state is a thing every caller
has to keep, so there were three. Each collection remembers its own answer now, against something
that already knows when to forget it.

# The world is a parameter of the ask, not of the service

`offered(query, only=…)` takes a DOOR onto whichever world is meant. Why that has to be so
belongs to [affordance](/domain/affordance.md), which owns the argument; what it buys HERE is that
an agent holds one of everything — this service and each collection it uses — while the world
under them changes at every node of a search. The planner builds nothing but the door.

# Why it is a service and the two beside it are not

A repository holds data and a service holds logic, and the split was invisible while one file held
both. This one decides; `Actions` and `Affordances` fetch. The test that keeps it honest asks the
syntax tree rather than the text: this module authors no query string and never reaches for the
store's binder, `Actions` authors the one question only it can phrase, and `Affordances` authors
NONE — the select it runs is the action's own, declared by whichever package ships the action.
That last one is the sharpest statement of why an affordance is not an
[action](/domain/action.md).

See [a-repository-is-not-a-service](/decisions/a-repository-is-not-a-service.md) and
[an-afforder-is-a-service-between-two-collections](/decisions/an-afforder-is-a-service-between-two-collections.md).
