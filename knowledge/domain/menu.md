---
type: Repository
title: Menu
description: >-
  The modality that holds what could be done — one `ag:Action` node per way of acting, each
  carrying its precondition, its effect and its taker. It keeps TEMPLATES and never rows: a row
  exists exactly while its premise holds, so storing one would keep a conclusion its own plumbing
  can outlive.
---

# What it holds

One node per way of acting, and everything a search needs to reason about it:

| part | property |
|---|---|
| precondition | `ag:available` — a SELECT binding the lever, the want and the direction |
| effect | `sh:construct`, `ag:retracts`, `ag:landsAfter`, `ag:confirmedBy` |
| taker | `ag:takenBy` — the capability family that carries it out |

Each package ships its own in `actions.ttl`, so adding a way of acting is a node in a new
directory rather than an edit here.

# Templates, never rows

The rows are the [afforder](/domain/afforder.md)'s, derived per ask and stored nowhere. What
this holds is what those rows are derived FROM — which is why the modality can be a repository
at all while its conclusions cannot be.

# Where it lives today

`ag:MenuGraph` is a real class and `ag:ActionGraph` is a subclass of it, so the modality's only
instance is the action graph — which sits in the [belief base](/domain/belief-base.md) rather
than a store of its own. One of the two graphs whose modality is not their store's, and the
target [a-store-is-a-modality](/decisions/a-store-is-a-modality.md) states is the other way
round.
