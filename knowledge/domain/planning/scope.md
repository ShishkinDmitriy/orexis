---
type: Domain Concept
title: Scope
description: >-
  A set of atoms - a predicate on a key - joined wherever one filling of one action reads or
  writes both, and separate where nothing does: a bulkhead in the vocabulary. Two wants in
  different scopes cannot contradict, because no action of one writes a fact the other reads,
  which is what makes it safe to plan them apart and concatenate their plans. Computed from what
  the shipped rules do over what the world states, never read off namespaces. The tower splits
  by its words; the greenhouse by the property each lever moves.
---

# What it is

Take every [action](/domain/kernel/action.md), ask its precondition what the world alone binds of
each filling, and join the atoms each filling reads or writes - a predicate on a KEY, the key being
the subject's own value where the filling binds it, a disk, a venue, the agent, and otherwise the
public values the filling binds it by, a reading's feature and its property. What falls out is a
partition: within a scope, some filling couples the atoms; across scopes, nothing does. A hull's compartments are the picture — flooding
one does not flood the next, because nothing passes between them — and SCOPE is the word,
because what this names is how far anything an agent does can reach.

The consequence is about [wants](/domain/planning/desire.md), each placed in the scope its met-test reads. Two wants whose views lie in
different scopes **cannot contradict**: no action serving one writes a fact the other reads,
so pursuing one can never move the other. That is what would let an agent plan them apart, one
[cone](/domain/planning/cone.md) each, and simply concatenate the plans.

# Proven, never declared

Independence is computed from what the rules actually do. It is not read off namespaces, and the
two cases that look obvious are the reason:

- A greenhouse's water words and climate words look like two vocabularies until a heater dries
  the soil. One action across both makes one scope.
- Two vans in one courier vocabulary look like one until you notice nothing they do touches the
  same van.

The second names what a predicate alone could not do. A scope was a set of PREDICATES until
#593, and separated a vocabulary and never two instances of one: a pump and a heater both write a
reading's side, and over predicates they were one scope though nothing the pump does reaches the
air. The KEY is what tells them apart, and it is public: the pump moves the bed's moisture and the
heater its temperature, each precondition keys the reading it writes by that property, and the
atoms `(below, bed and moisture)` and `(below, bed and temperature)` share nothing. A heater that
dried the soil as well would write an atom keyed by the soil too, and the two levers would be one
scope again - which they must be, since the order of dosing and heating is real there
([a-scope-is-a-predicate-on-a-key](/decisions/a-scope-is-a-predicate-on-a-key.md)).

A subject the world alone binds nothing of is keyed by nothing, and its atom is every atom of
its predicate - the predicate partition again, the safe side. An action whose
[footprint](/domain/planning/footprint.md) cannot be read from its text joins everything. An action that
might touch any predicate cannot be proven not to, and a scope wrongly split would let two
plans contradict each other.

# What it measures: the tower splits by its words, the greenhouse by its keys

Over predicates most shipped worlds were ONE scope: every effect they ship predicts a reading of
the same shape, so the market's plumbing and sensing's readings were joined by the actions alone,
and the greenhouse, built to break that, did not. Over keys the greenhouse is two: the soil's
moisture with the pump, the air's temperature with the heater, and a cold dry bed is two wants in
two imaginaria of one world each, where it was one want searched over both levers in four
([measure-the-search](/runbooks/measure-the-search.md)).

`world/tower` splits in two, the first world to: hanoi's Move reads and writes `hanoi:on` and
what a peg is, the courier's drives and drops read and write `courier:at` and
`courier:carriedBy`, and no action touches both — what joins them is a RULE, which is not an
action and couples nothing here ([refinement](/domain/planning/refinement.md)). It split only once a
type pattern was read as its CLASS: keyed by `rdf:type` alone, `?x a hanoi:Peg` and
`?v a courier:Van` read one predicate, and every action of both domains was one scope.

**One imaginarium per scope, holding the scope's readings, and a scope's worlds admit the scope's
fillings alone.** A reading keyed by another scope's term crosses into no imaginarium but its own,
so a world is the scope's readings and a sensor added elsewhere adds nothing to it. A want is
searched in the scope its met-test reads, counting only what some action can change — a disk's
size is read by a refined want and changed by nothing, and counted, it pulled a courier goal
into the puzzle's scope. An action of another scope writes nothing that want reads, so its
steps fork worlds the met-test cannot tell apart; admitted everywhere, the courier's drives
spent the puzzle's budget and moved no disk.

# Related

- [footprint](/domain/planning/footprint.md) — what a text reads and writes, which the partition joins.
- [cone](/domain/planning/cone.md) — one per scope's imaginarium, kept from pass to pass.

# In the store

`scope_actions` writes the partition to the store's scope graph at boot — a `planning:Scope`
per part, each action `planning:inScope` every scope a filling of it falls in, and each predicate
and each TERM a filling binds — the property, the valve — `planning:inScope` its own where that is
one scope and nowhere where it is two, since a reader told nothing joins every group — and `derive_wants` clusters a desire's
witnesses by the scope of what each is about, never recomputing it. The Planner keeps an
imaginarium per scope, places a want by the predicates its met-test reads and, where those place
it nowhere, by the terms it names, and hands each search the actions `planning:inScope` of it and
the terms that are another scope's, so a scope admits the FILLINGS that are its own: the lamp's
heating is admitted in the light's search and not in the air's, though the action is in both. The cases in
`agent/planning/tests/scope_actions/` hold the function to a snapshot of what it writes.
