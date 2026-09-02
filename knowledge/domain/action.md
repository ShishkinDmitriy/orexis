---
type: Domain Concept
title: Action
term: http://example.org/orexis#Action
description: >-
  One way of acting, whole — the STRIPS operator as a single node a package ships in its
  `actions.ttl` — and the KIND of act itself, which a row carries and an intention commits to:
  when it is available (`orexis:available`, a SELECT whose rows are the affordances it puts on the
  menu now), what it makes true
  (`sh:construct` and `orexis:retracts`, with timing and confirmation route), and who carries it
  out (`orexis:takenBy`). Loaded into the action graph at genesis so a planner, a sovereign or a
  model reads the whole tool list in one place. Adding a way of acting is one node and one
  `take()`.
---

# What it is

The one thing the three BDI-planning surfaces were always describing. An
[affordance](/domain/affordance.md) says the action is available through a
[lever](/domain/lever.md) now; an [effect](/domain/effect.md) says what it would make true; an
[actor](/domain/actor.md) carries it out. An **action** is the node those hang off — and it is
the KIND of act too, since [the-action-is-the-kind](/decisions/the-action-is-the-kind.md):
there is no separate word for what a row offers, an intention commits to and a trace weighs.

```turtle
market:Acquiring a orexis:Action ;
    orexis:available  """SELECT ?property ?via ?direction WHERE { … }""" ;
    sh:construct  """CONSTRUCT { … } WHERE { … }""" ;
    orexis:retracts   """CONSTRUCT { … } WHERE { … }""" ;
    orexis:landsAfter """SELECT ?seconds WHERE { … }""" ;
    orexis:takenBy    market:Bidding .
```

Six ship: `sensing:Observing`, `actuation:Dosing`, `market:Acquiring`, `market:Offering`,
`market:Serving` — an obligation's, whose availability binds `?for_agent` — and `market:Presenting`,
the buyer's hold on a won claim, which has no availability and no effect because no plan
chooses it: the claim arriving is the adoption, and it is a node so the hold can be a
commitment and an urgency. A premise may
read `$beliefs` (the agent's own graph — an open round) and `$sensed` (the readings of the
world being asked about, so a row an earlier step made available appears in that step's
world and not in this one).

# How it is found and read

`loader.action_files()` finds every package's `actions.ttl`; genesis loads them into the action
graph beside the T-Box. Three readers, one join:

- `menu_of` runs every action's `orexis:available` with `$me` and the desired `$properties` filled
  in, and each row it returns is an affordance carrying the action;
- `effects.rule_for(action)` reads the node's construct and retraction and runs them against
  the [imaginarium](/domain/imaginarium.md);
- `execution.taken_by(action)` reads the node's `orexis:takenBy` and asks `agent.providers`.

# Two kinds, and the vocabulary says which

This page is the menu's kind: chosen by a plan, with both texts stated and the gate refusing
either missing. The other kind is the [triggered action](/domain/triggered-action.md), which an
event adopts and which owns its own description. Naming the second kind is what let the
runtime stop guessing from absence — a missing effect used to mean "passed over, plan
partial", and now means a world the gate refuses.

# The precondition is the query, whole

An action carries no `sh:condition`. SHACL-AF has the slot, and the three shipped actions
carried one for a while — a node-level shape saying "this agent polls something" beside the
query saying which probe, which subject, which property. Nothing evaluated it: a shape validates
a focus node and cannot bind the columns a row needs, so it could only ever restate a subset of
the walk, and a second statement of a precondition nobody reads is one that can disagree with
the first. What a shape would add — a validation report saying *why* an action is unavailable —
is real and unbuilt; the day it is wanted, the slot is there.

# What an author writes

A node here, and a `take()` on the module its `orexis:takenBy` names. Nothing else — no registry,
no edit to the kernel, no second file. An action without `sh:construct` is legal to ship and
refused at the gate the moment it puts a row on some agent's menu, because a lever the search
cannot simulate is one it must not conclude about.

# Related

- [an-action-is-one-node](/decisions/an-action-is-one-node.md) — why the four surfaces became one.
- [a-plan-is-a-path-of-graph-diffs](/decisions/a-plan-is-a-path-of-graph-diffs.md) — the record
  that first read the menu row as an action schema.

# It is a term code may name, and the ladder is its order

An action is the exception rule 1 carves out: a T-Box term, so `bidding.py` may say
`ACQUIRING` in Python while never naming a venue — the [lever](/domain/lever.md) beside it is
always an instance. Nothing enumerates the set: a sixth way of acting is a node in a new
directory. The ladder — look, act with what is yours, buy what is not — is their *order*, not
a ranking: `actuation:Dosing` is offered exactly where the lever and the resource are both the
agent's own and `market:Acquiring` where the resource is someone else's, and what chooses
between two rungs is which reaches the better world.
