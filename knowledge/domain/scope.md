---
type: Domain Concept
title: Scope
description: >-
  A set of predicates joined wherever one action or one derivation reads or writes both, and
  separate where nothing does — a bulkhead in the vocabulary. Two wants in different
  scopes cannot contradict, because no action of one writes a fact the other reads, which
  is what would make it safe to plan them apart and concatenate their plans. Computed from what
  the shipped rules do, never read off namespaces. The tower is the first world that splits:
  the puzzle's words and the grid's, one imaginarium each.
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
`planning:holdsAt` were already saying (#681).

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

An action whose [footprint](/domain/footprint.md) cannot be read from its text joins everything. An action that
might touch any predicate cannot be proven not to, and a scope wrongly split would let two
plans contradict each other.

# What it measures: the tower splits, and everything else is one

Most shipped worlds are ONE scope: every effect they ship predicts a reading of the same shape,
so the market's plumbing and sensing's readings are joined by the actions alone. The
greenhouse was built to break that and did not — a heater that dries the soil couples two
properties through a VALUE, and both readings carry the same predicates.

`world/tower` splits in two, the first world to: hanoi's Move reads and writes `hanoi:on` and
what a peg is, the courier's drives and drops read and write `courier:at` and
`courier:carriedBy`, and no action touches both — what joins them is a RULE, which is not an
action and couples nothing here ([refinement](/domain/refinement.md)). It split only once a
type pattern was read as its CLASS: keyed by `rdf:type` alone, `?x a hanoi:Peg` and
`?v a courier:Van` read one predicate, and every action of both domains was one scope.

**One imaginarium per scope, and a scope's worlds admit the scope's actions alone.** A want is
searched in the scope its met-test reads, counting only what some action can change — a disk's
size is read by a refined want and changed by nothing, and counted, it pulled a courier goal
into the puzzle's scope. An action of another scope writes nothing that want reads, so its
steps fork worlds the met-test cannot tell apart; admitted everywhere, the courier's drives
spent the puzzle's budget and moved no disk.

# Related

- [relevance](/domain/relevance.md) — the closure a want's view is built from.
- [identification](/domain/identification.md) — the view, as the cone already uses it.

# In the store

`scope_actions` writes the partition to the store's scope graph at boot — a `planning:Scope`
per part, each predicate and each action `planning:inScope` its own — and `derive_wants`
clusters a desire's results by reading it, never by recomputing it. The Planner keeps an
imaginarium per scope and hands each search the actions `planning:inScope` of it. The cases in
`agent/planning/tests/scope_actions/` hold the function to a snapshot of what it writes.
