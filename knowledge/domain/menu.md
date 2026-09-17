---
type: Repository
title: Menu
description: >-
  The modality that holds what could be done — one `orexis:Action` node per way of acting, each
  carrying its precondition, its effect and its taker. It keeps TEMPLATES and never rows: a row
  exists exactly while its premise holds, so storing one would keep a conclusion its own plumbing
  can outlive.
---

# What it holds

One node per way of acting, and everything a search needs to reason about it:

| part | property |
|---|---|
| precondition | `orexis:available` — a SELECT binding the lever, the want and the direction |
| effect | `sh:construct`, `orexis:retracts`, `orexis:landsAfter` |
| taker | the module that contributes the action — `@contributes(<action>)`, read off the code |

Each package ships its own in `actions.ttl`, so adding a way of acting is a node in a new
directory rather than an edit here.

# Its class is `Actions`, and its name is going

The collection this page describes had no class until the afforder was split into the service it
is and the two collections it uses; it is `Actions` now, reading public knowledge because a
template is the same in every world.

**The word "menu" is on its way out** (#686), and this page's own definition is why: it defines
the menu as the TEMPLATES, while eight other pages use the word for the ROWS — so a reader meets
one word for two concepts, which is how [action](/domain/action.md) and
[affordance](/domain/affordance.md) come to feel like one thing. Where it meant the rows it will
say affordances; where it meant these, actions.

# Templates, never rows

The rows are [affordances](/domain/affordance.md), derived per ask and stored nowhere. What
this holds is what those rows are derived FROM — which is why the modality can be a repository
at all while its conclusions cannot be.

# Where it lives today

`orexis:MenuGraph` is a real class and `orexis:ActionGraph` is a subclass of it, so the modality's only
instance is the action graph — which sits in the [belief base](/domain/belief-base.md) rather
than a store of its own. One of the two graphs whose modality is not their store's, and the
target [a-store-is-a-modality](/decisions/a-store-is-a-modality.md) states is the other way
round.
