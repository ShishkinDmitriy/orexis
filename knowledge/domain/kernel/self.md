---
type: Domain Concept
title: Self
term: http://example.org/orexis#Self
description: >-
  The one agent a store is this agent's - written by the boot alone, once, as `<agent> a
  orexis:Self` in a graph of the agent's own, for the agent the process was told to be. A text
  asks `?me a orexis:Self` and is handed nobody. A class held to one instance at every door an
  instance could come through, never a singleton IRI.
---

# What it is

`orexis:Self` is a class, and an agent's store holds one instance of it: the
[agent](/domain/kernel/agent.md) the process was told to be. The [runtime](/domain/kernel/runtime.md)
writes it at boot, once it has found that agent by the identifier it was handed and before it asks
any premise, into a graph of its own:

```trig
<…/graph/self/fern_grower> { :fern_grower a orexis:Self }
# catalogue: an orexis:SelfGraph, orexis:beliefsOf :fern_grower, orexis:arrivedBy orexis:Recorded
```

The agent keeps the name its world gave it. Being the self is something that agent IS in this
store — the agent's own word about itself, recorded — and not a second name for it.

# How it is used

Every text that means the agent asks for it, and is handed nothing: a precondition
(`?me a orexis:Self ; actuation:hasActuator ?valve`), an effect, a command, a saying, a premise,
sensing's limits. The `$me` token each of those texts was handed is gone, and `tests/test_store.py`
refuses one written back.

The self graph is a BELIEF and not public. A reader answering a text over what is known — a
precondition in a possible world, a command over the present — reads it as it reads any belief,
and it crosses into an [imaginarium](/domain/planning/imaginarium.md) with the rest. A reader of the
public graphs alone that asks the self states the self graph's kind beside them
(`graphs_of(store, PUBLIC, SELF_GRAPH)`).

A [footprint](/domain/planning/footprint.md) reads the self's pattern as absent, and says why.

# One, and only one

A class does not hold itself to one instance, so every door an instance could come through is held:

- **a document** — a world's file, a peer's message heard, the agent's own saying — stating that
  anything is `orexis:Self`, or that a graph of its is an `orexis:SelfGraph`, is refused whole
  (`store.refuse_the_self`);
- **a lived-in volume** whose self is another agent does not boot: the right id was handed the
  wrong volume;
- **any count but one** does not boot either. Two selves are never picked between, since a text
  asking over two answers for both and says nothing.

A volume lived in before the self existed holds none, and the boot writes it then.

# Where there is none

A store holding a whole world — what the operator's tools and the simulator read (`world_of`), a
test standing several agents side by side — is no agent's, and holds no self. A text asking for
the self there answers nothing; such a store names the agent it means as a holder, or, for a
premise, asks of every `orexis:Agent` at once.

Why a class held to one instance and not a singleton IRI, and why a belief and not a public graph:
[the-self-is-a-class-held-to-one-instance](/decisions/the-self-is-a-class-held-to-one-instance.md).
