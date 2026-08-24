---
type: Domain Concept
title: Action
term: http://example.org/orexis#Action
description: >-
  One way of acting, whole — the STRIPS operator as a single node a package ships in its
  `actions.ttl`: what kind of act it is (`ag:means`), when it is available (`ag:available`, a
  SELECT whose rows are the affordances it puts on the menu now), what it makes true
  (`sh:construct` and `ag:retracts`, with timing and confirmation route), and who carries it
  out (`ag:takenBy`). Loaded into the action graph at genesis so a planner, a sovereign or a
  model reads the whole tool list in one place. Adding a way of acting is one node and one
  `take()`.
---

# What it is

The one thing the four BDI-planning surfaces were always describing. A [means](/domain/means.md)
says what kind of act; an [affordance](/domain/affordance.md) says it is available through a
[lever](/domain/lever.md) now; an [effect](/domain/effect.md) says what it would make true; an
[actor](/domain/actor.md) carries it out. An **action** is the node those hang off.

```turtle
market:Acquiring a ag:Action ;
    ag:means      ag:Acquire ;
    ag:available  """SELECT ?property ?via ?direction WHERE { … }""" ;
    sh:construct  """CONSTRUCT { … } WHERE { … }""" ;
    ag:retracts   """CONSTRUCT { … } WHERE { … }""" ;
    ag:landsAfter """SELECT ?seconds WHERE { … }""" ;
    ag:confirmedBy ag:ByObservation ;
    ag:takenBy    market:Bidding .
```

Four ship: `sensing:Observing`, `actuation:Dosing`, `market:Acquiring` and `market:Serving` —
the last a duty's, whose availability binds `?for_agent`.

# How it is found and read

`loader.action_files()` finds every package's `actions.ttl`; genesis loads them into the action
graph beside the T-Box. Three readers, one join:

- `menu_of` runs every action's `ag:available` with `$me` and the desired `$properties` filled
  in, and each row it returns is an affordance carrying the action's means;
- `effects.rule_for(means)` finds the action by `ag:means` and runs its construct and retraction
  against the [imaginarium](/domain/imaginarium.md);
- `execution.taken_by(means)` finds the same action and asks `agent.providers` for its taker.

# The precondition is the query, whole

An action carries no `sh:condition`. SHACL-AF has the slot, and the three shipped actions
carried one for a while — a node-level shape saying "this agent polls something" beside the
query saying which probe, which subject, which property. Nothing evaluated it: a shape validates
a focus node and cannot bind the columns a row needs, so it could only ever restate a subset of
the walk, and a second statement of a precondition nobody reads is one that can disagree with
the first. What a shape would add — a validation report saying *why* an action is unavailable —
is real and unbuilt; the day it is wanted, the slot is there.

# What an author writes

A node here, and a `take()` on the module its `ag:takenBy` names. Nothing else — no registry,
no edit to the kernel, no second file. An action without `sh:construct` is legal to ship and
refused at the gate the moment it puts a row on some agent's menu, because a lever the search
cannot simulate is one it must not conclude about.

# Related

- [an-action-is-one-node](/decisions/an-action-is-one-node.md) — why the four surfaces became one.
- [a-plan-is-a-path-of-graph-diffs](/decisions/a-plan-is-a-path-of-graph-diffs.md) — the record
  that first read the menu row as an action schema.
