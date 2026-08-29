---
type: Service
title: Afforder
description: >-
  The service that answers what an agent could do — it runs each action template's precondition
  against the world it is asked about and returns rows nobody writes down. The world is a
  PARAMETER, which is what lets the planner ask for the affordances of a state that has not
  happened.
---

# What it runs

**Affording.** For every `ag:Action` the [menu](/domain/menu.md) holds, run its `ag:available`
query with `$me`, `$wants`, `$beliefs` and `$state` filled in, and collect the
[affordance](/domain/affordance.md) rows it binds. Sorted, returned, written nowhere.

# What it reads and writes

![afforder — what it reads and writes](../diagrams/service-afforder.svg)

**`$state` is a parameter, and that is the whole reason nothing is stored.** The
[planner](/domain/planner.md) binds it to a node of the [imaginarium](/domain/imaginarium.md), so
stock after a refill appears among that world's rows and not among this one's. A stored answer
has one state; a search needs one per node.

# What it is not

**Not the menu.** The menu is the repository — the templates, kept. This is what reads them, and
the two were one page until the split: a thing that holds and a thing that does are different
kinds, and calling both *the menu* hid which one a sentence meant.
