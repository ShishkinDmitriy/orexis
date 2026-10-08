---
type: Domain Concept
title: Self
term: http://example.org/orexis#Self
description: >-
  The one agent a store is this agent's - authored by its world in the agent's self graph,
  `<agent> a orexis:Self`, and checked by the boot against the identifier the process was told,
  never minted from it. A text asks `?me a orexis:Self` and is handed nobody. A class held to one
  instance at every door an instance could come through, never a singleton IRI.
---

# What it is

`orexis:Self` is a class, and an agent's store holds one instance of it: the
[agent](/domain/kernel/agent.md) the process was told to be. The [sovereign](/domain/kernel/sovereign.md)
says which, as it says what the agent desires: in a document of the agent's own, its **self
graph**, written in the [world](/domain/kernel/world.md) under `beliefs/`:

```turtle
<> a orexis:SelfGraph .
:fern_grower a orexis:Self .
# put in by the boot: an orexis:SelfGraph, orexis:beliefsOf :fern_grower, orexis:arrivedBy orexis:Asserted
```

The agent keeps the name its world gave it. Being the self is something that agent IS in its own
store, and not a second name for it. The self graph is the one graph of an agent's own that is its
owner's by what it holds — the self it states; every other says whose beside its kind.

# How it is used

Every text that means the agent asks for it, and is handed nothing: a precondition
(`?me a orexis:Self ; actuation:hasActuator ?valve`), an effect, a command, a saying, a premise,
a [stance](/domain/kernel/stance.md). The `$me` token each of those texts was handed is gone, and
`tests/test_store.py` refuses one written back.

The self graph is also where the agent's word about itself lives: each stance is a triple about the
self there, and is read in no other graph.

The self graph is a BELIEF and not public. A reader answering a text over what is known — a
precondition in a possible world, a command over the present — reads it as it reads any belief,
and it crosses into an [imaginarium](/domain/planning/imaginarium.md) with the rest. A reader of the
public graphs alone that asks the self states the self graph's kind beside them
(`graphs_of(store, PUBLIC, SELF_GRAPH)`).

A [footprint](/domain/planning/footprint.md) reads the self's pattern as absent, and says why.

# One, and only one

A class does not hold itself to one instance, so every door an instance could come through is held:

- **a world's file** states a self only in a graph saying it is a self graph and nothing else,
  exactly once there, and an owner stated beside it is that self (`store.document`);
- **a peer's message heard, and the agent's own saying,** state no self and no self graph, nor
  whose any graph is (`store.refuse_the_sovereigns`);
- **the boot** finds exactly one self graph among the documents that say they are the agent's,
  or does not start: none is a world that never said who the agent is, two are two homes for it;
- **a lived-in volume** whose self is another agent does not boot: the right id was handed the
  wrong volume;
- **any count of selves but one**, counted in every graph, does not boot either. Two selves are
  never picked between, since a text asking over two answers for both and says nothing.

A volume lived in before its world authored a self graph holds none, and the boot puts the
authored one in then.

# Where there is none

A store holding a whole world — what the operator's tools and the simulator read (`world_of`), a
test standing several agents side by side — is no agent's: it passes over every graph of an
agent's own, the self graphs among them, so it holds no self however many its documents state. A
text asking for the self there answers nothing; such a store names the agent it means as a holder,
or, for a premise, asks of every `orexis:Agent` at once.

Why authored and checked rather than minted, why a class held to one instance and not a singleton
IRI, and why a belief and not a public graph:
[the-self-is-a-class-held-to-one-instance](/decisions/the-self-is-a-class-held-to-one-instance.md).
