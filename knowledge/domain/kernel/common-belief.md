---
type: Domain Concept
title: Common belief
description: >-
  A belief every agent of a world holds, because the world put it in each of their stores alike -
  a graph whose catalogue row names no owner. Asked for as `graphs_of(store, BELIEF, common=True)`;
  the opposite is a belief of the agent's own, whose row names it.
---

# What it is

Every belief is somebody's: an agent believes it. What sets a common belief apart is that it is
not ONE agent's. The [world](/domain/kernel/world.md) authors it in a document that names no agent,
every agent of the world reads that document at boot, and so every one of them holds the same
graph, and each can count on the others holding it too. The vocabulary, the world graph, the
society and what the boot derives of them are common beliefs; a reading an agent observed, a state
it derived and a word a peer said to it are its own.

The catalogue says which by `orexis:beliefsOf`. A graph of an agent's own names its owner there;
a common belief names none:

```turtle
<graph/world>        a orexis:WorldGraph .                                     # common
<graph/fern/desires> a planning:DesireGraph ; orexis:beliefsOf :fern_grower .  # the grower's own
```

That is provenance and not a kind: being common is how a graph arrived, which a graph class may
not say. So the [belief base](/domain/belief/belief-base.md) holds both under one kind,
`orexis:BeliefGraph`, and a reader asks for the common ones by passing `common=True` to
`store.graphs_of`, which keeps the rows that name no owner.

# How it is used

A reader that means what the world states, and not what this agent has come to believe since,
asks for the common beliefs: a scope's [footprint](/domain/planning/footprint.md) is read over them,
so a fact only one agent's store holds cannot place a want; revision reads a graph beside them and
never beside another testimony; onboarding grants what they imply. A volume lived in reads the
common beliefs again at every boot and keeps the agent's own, which is how a ratified change to a
world reaches a running agent.

The same mark applies to what the agent reads to act. A domain's actions, a world's constraints
and a desire the world states without naming an agent are common to every agent of the world, and
`common=True` asks for those of any kind.

A common belief is never where an agent states itself: a figure about an agent in one is the
world's word about it, not the agent's ([stance](/domain/kernel/stance.md),
[self](/domain/kernel/self.md)).
