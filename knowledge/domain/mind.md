---
type: Component
title: Mind
description: >-
  What an agent holds, organised by modality: the collection of its stores — beliefs,
  desires, and the rest of the table as a-store-is-a-modality lands it. The word is the
  sovereign's, from the sitting that produced the-mind-is-six-graphs: the mind was six
  graphs in one store, and is becoming the same six as stores. It exists as a concept
  because no older word could name the whole once the whole stopped being one container:
  the belief base is one store IN the mind, a store is one modality OF it, and the agent
  is the principal that HAS it — and the sovereign's ask addresses it by modality, which
  is a question you can only put to a thing with a name.
---

# What it is

`agent/mind.py`. The holder of an agent's stores, one per modality: `agent.mind.desires`
today, with the menu, intention and history stores joining as
[a-store-is-a-modality](/decisions/a-store-is-a-modality.md) is carried out — that record
owns the table of stores, their persistence and their write rules, and this page does not
restate it. A module asks `agent.mind.<modality>` and never learns how a store is built or
where it persists.

The word predates the code. The sovereign named it in the sitting recorded as
[the-mind-is-six-graphs](/decisions/the-mind-is-six-graphs.md) — *an agent's mind is named
graphs in one vocabulary, differing in what they assert* — and the store-per-modality ruling
kept the concept while moving its carrier: the same mind, its modalities now containers
rather than classifications. What [there-is-no-bdi-ontology](/decisions/there-is-no-bdi-ontology.md)
established holds here too: the mind needs no ontology of its own, and this page names a part
of the implementation, not a new theory.

# Why no existing word could serve

The rule is that a new concept must say why its neighbours cannot cover it, so, each in turn:

- **[belief base](/domain/belief-base.md)** was the name for the whole store, and that was
  already an overreach when everything lived in one container —
  [#65](https://github.com/ShishkinDmitriy/agora/issues/65) recorded it from the graph side:
  calling one graph "the beliefs graph" inside a store that is all beliefs asserts nothing.
  Once modalities are stores, "belief base" naming the whole repeats the same overreach one
  level up. It keeps its honest meaning instead: the store of the belief modality — and, until
  the migration completes, the home of record the other stores are built from.
- **A store** is one modality — that is the record's whole sentence. The mind is their sum,
  and the sum needed a name precisely because the parts stopped sharing one.
- **The [agent](/domain/agent.md)** is the principal: an identity, a connection, modules,
  conduct. Conflating the holder with what it holds is what the sovereign's third ruling
  separates — `agora-ask` names a modality, so what it addresses is the mind, not the agent's
  whole apparatus and not any single store.
- **The [imaginarium](/domain/imaginarium.md)** is one row of the mind's table — the
  hypothesised modality, the store required to be lost — and was the pattern's first
  instance, not its name.

# What it is not

Not a namespace of convenience: the class exists because the concept was already load-bearing
in the records and the ask surface, and the code caught up. And not a registry — nothing
enumerates the mind's stores to read them all at once, for the same reason nothing counts the
public graphs: a reader asks for the modality it means.
