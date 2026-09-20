---
type: Domain Concept
title: Scope
description: >-
  A set of predicates joined wherever one action or one derivation reads or writes both, and
  separate where nothing does — a bulkhead in the vocabulary. Two wants in different
  scopes cannot contradict, because no action of one writes a fact the other reads, which
  is what would make it safe to plan them apart and concatenate their plans. Computed from what
  the shipped rules do, never read off namespaces. Measured on every shipped world: one
  scope, so nothing yet splits.
---

# What it is

Take every [action](/domain/action.md) and every derivation, and join the predicates each one
reads or writes. What falls out is a partition of the vocabulary: within a scope, some action
couples the words; across scopes, nothing does. A hull's compartments are the picture — flooding
one does not flood the next, because nothing passes between them — and SCOPE is the word,
because what this names is how far anything an agent does can reach.

**Not "component", which is what this repo calls a package**, and whose graph theory is not the
reader's. The word was taken twice and both uses yielded, by the sovereign's ruling that a core
concept outranks a niche one: a commitment's token now says what it `permits`, in its own words
rather than JWT's, and what a want sits on was the BINDING axis — a property named for the
name this page took over. The axis has since gone the way the name did: what a want sits on is
its graph's period, and `orexis:bindsWhen` said in a fourth place what the type, the period and
`orexis:holdsAt` were already saying (#681).

The consequence is about [wants](/domain/desire.md). A want's view is what it reads plus what
the actions [relevant](/domain/relevance.md) to it read and write. Two wants whose views lie in
different scopes **cannot contradict**: no action serving one writes a fact the other reads,
so pursuing one can never move the other. That is what would let an agent plan them apart, one
[cone](/domain/cone.md) each, and simply concatenate the plans.

# Proven, never declared

Independence is computed from what the rules actually do. It is not read off namespaces, and the
two cases that look obvious are the reason:

- A greenhouse's water words and climate words look like two vocabularies until a heater dries
  the soil. One action across both makes one scope.
- Two vans in one courier vocabulary look like one until you notice nothing they do touches the
  same van.

The second names the limit. A scope here is a set of PREDICATES, so it separates a
vocabulary and never two instances of one. Two vans are two scopes only over VARIABLES, a
subject and a predicate together, which is what a mechanism that split a plan would need.

An action whose reads or writes cannot be read from its text joins everything. An action that
might touch any predicate cannot be proven not to, and a scope wrongly split would let two
plans contradict each other.

# What it measures today: nothing splits

Every shipped world is ONE scope, around ninety predicates, whether the derivations are
counted or the actions taken alone. The actions alone already join the market's plumbing to
sensing's readings, because every effect this project ships predicts a reading of the same
shape. Every want every shipped agent holds falls inside that one scope.

So the mechanism this concept exists for — one cone per scope, plans concatenated — has
nothing to split, and is not built. The measurement is the point: it is what says so, and the
first world that breaks it is the first one worth planning as several cones. See
[#565](https://github.com/ShishkinDmitriy/orexis/issues/565).

**The world built to break it did not, and that is the finding.** `world/greenhouse` holds one
want about two properties, a pump that moves one and a heater that moves the other, and a world
fact — `heating:driesTheSoil` — that makes the heater reach into the pump's property. The plan
reorders when it is set, so the coupling is real and the search reads it. The scope count does
not move: one, either way, because both readings carry the same predicates and differ only in a
VALUE. That world is what will measure a scope over variables the day one is computed.

# Related

- [relevance](/domain/relevance.md) — the closure a want's view is built from.
- [identification](/domain/identification.md) — the view, as the cone already uses it.

# In the store

`scope_actions` writes the partition to the agent's scope graph at boot — a
`deliberation:Scope` per part, each predicate and each action `deliberation:inScope` its own —
and `derive_wants` clusters a desire's results by reading it, never by recomputing it
([judge-desires-then-derive-wants](/decisions/judge-desires-then-derive-wants.md)). The
partition is `relevance.scopes`' as it always was; what changed is that it is data, replaced
whole when the actions are, and a store holding no scope graph is refused rather than
clustered as one scope. The cases in `packages/orexis-agent-deliberation/tests/scope_actions/`
hold the function to a snapshot of what it writes.
