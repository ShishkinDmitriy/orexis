---
type: Domain Concept
title: Holding
term: http://example.org/orexis/coordination#Holding
description: >-
  What an agent says of its own future, and the one thing of its plan that crosses - a thing it acts for, the
  values its walking plans give that thing on a constraint's key, and the period they hold over. Read off the
  intentions, and the key off the constraint's own text, so any constraint two things can both be in is a
  resource.
---

# The key

A constraint's select joins two subjects on some of their predicates - the courier's *no two vans at one
position* joins two vans on their column and their row - and those predicates are its **key**, what two
agents can both want. It is read by parsing the text (`agent/coordination/holdings.py`): every predicate
whose object is a variable some other subject's pattern also ends in. A constraint that joins nothing has no
key, and nothing is asked under it.

# The holdings

For each thing the agent acts for: the values it holds on the key now, and after each step of a walking
[intention](/domain/execution/intention.md) whose predicted change, `execution:adds`, gives it new ones. A
[step](/domain/execution/step.md) lands somewhere in its band, so the values before it hold until its latest
landing and the new from its earliest: two holdings in a row overlap by the band. The last holds on. An
intention ending after its step in flight gives that step alone.

As said, a holding is a node of `coordination:Holding`: the thing, `coordination:of`; the values, under the
key's own predicates; `coordination:from` and `coordination:until`, either absent where the holding began
before anything was said or holds on; and `coordination:taken` where a step already taken gives the values - a
step in flight, which the winner of a draw still yields to.

# What it is not

Not the plan: no step, no action, no want crosses, and a holding does not say why. Not a promise either - the
plan may change, and then the agent asks again with the holdings it now has.
