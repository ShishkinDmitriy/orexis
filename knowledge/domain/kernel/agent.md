---
type: Role
title: Agent
term: http://example.org/orexis#Agent
description: >-
  A self-interested principal: one process, one store in a volume of its own, told its own
  `orexis:localId` and given one world. It acts for a subject, holds the desires and wants its
  documents give it, and plans and acts for them alone. What it can do is the actions its world's
  domains ship; nothing is granted.
---

# What it is

An `orexis:Agent` in a world's documents, with the one identifier a process is handed at boot:

```turtle
:fern_grower a orexis:Agent ; orexis:localId "fern_grower" ; orexis:actsFor :fern .
```

`orexis:actsFor` names the subject whose interest it advances — a plant, a tank, a tower. The
[runtime](/domain/kernel/runtime.md) finds the agent by that id among the `orexis:Agent`s of the
society graph — or of the world graph, in a world with no society — and nowhere else: a plant and
the agent acting for it may share a local id, and only one of them is an agent.

# What is its own

Its store, held in a volume nothing else mounts, and in it the graphs the catalogue says are its
(`orexis:beliefsOf`): the one saying it is the [self](/domain/kernel/self.md), the documents of its
world that say they are its, the state it senses and revises, the wants derived for it, the
intentions it walks. A world of several agents states each
one's desires apart for that reason — the derivation mints a want under every desire a store holds.

Everything else it discovers: which sensors report to it, which venues it bids in, which actions
admit steps in its world. What it believes about another agent stays first-order — what that
agent SAID, as a document, never what it believes ([speech](/domain/speech/speech.md)).

# What it is not

Not a kind with abilities of its own. An agent does what the actions its world imports admit, and
two agents of one world differ by their documents and their subjects, not by a grant. The
[sovereign](/domain/kernel/sovereign.md) who wrote the world is not an agent at all.
