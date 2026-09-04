---
type: Domain Concept
title: Bridge
term: http://example.org/orexis#Bridge
description: >-
  What joins an abstract action to the vocabulary beneath it: a translation of the action's
  promised facts into the lower vocabulary, and the lower level's estimate for the want those
  facts make. Declared by the package that knows both vocabularies, applied to a step's
  promise going down and its verdict coming back, never to the world a search plans over.
---

# What it is

`orexis:Bridge`. A [level](/decisions/a-level-is-a-vocabulary-and-a-bridge.md) is a vocabulary,
and an [action](/domain/action.md) nobody takes at its own level — hanoi's Move — is a
promise the level beneath keeps. The bridge is what makes the promise sayable below:
`orexis:refines` the action; `sh:construct` translates its predicted facts, bound as `$via`
and `$about` from the [step](/domain/step.md) with the world at `$state`, into the lower
vocabulary's facts (a disk on a peg becomes the disk at the peg's cell); `orexis:estimates`
names the lower package's estimate for the want those facts make, a template over the same
tokens, bound once into a node of the promise's own.

# How a promise is kept

When the keeper reaches a step of a taker-less action, it asks for the action's bridge, runs
the translation, and writes the result as an `orexis:Desire` this agent holds — in its
promises graph, `progression:promisedBy` the step, projected into the desire modality — so the
ordinary road lifts it, plans it over the actions that ARE taken, and walks the plan. The
step itself waits on the same translated fact as its completion. When the fact arrives the
promise is withdrawn, whatever stood for it is resolved, and the step's own predicted facts
are written to the state: the bridge says the fact the world showed and the fact the step
promised are one thing described twice, and materialising it upward is the keeper's until a
saturation rule exists. Then the next abstract step becomes current and is planned in turn,
from wherever the world now stands.

# What it is not

**Not a method.** A [method](/domain/method.md) is declared, for a protocol; a bridge declares
nothing about HOW the promise is kept. The drives are found by the search below, from the
world as it is when the step is reached.

**Not applied to the world.** The outer search never sees the lower actions, because the
bridge is not a rule inside the search: relevance keeps each search inside its want's
vocabulary. Applied inside the search, seven moves would be thirty drives in one budget.

**Not a claim the world is allowed to make lightly.** A bridge asserts that a level beneath
exists, and onboarding and boot hold it to the actions the tree declares: every predicate its
construct writes must be one some action's effect writes, taken here or not, since a level
nobody executes is still a level somebody could plan (#532). A bridge into facts no action
writes is refused with its name and the fact. A taker-less action with NO bridge is a different
thing and admitted: knowledge-only, planned and never executed — hanoi's own world, whose point
is the search — and said loudly at execution when a step of it is reached.

The tower package (`packages/orexis-tool-tower/`) is the one that ships: one axiom (a disk is
a parcel), one bridge, one estimate, and a world naming both domains.
