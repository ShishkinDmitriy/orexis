---
type: Domain Concept
title: Causal component
description: >-
  A set of predicates joined wherever one action or one derivation reads or writes both, and
  separate where nothing does. Two wants in different components cannot contradict, because no
  action of one writes a fact the other reads — which is what would make it safe to plan them
  apart and concatenate their plans. Computed from what the shipped rules do, never read off
  namespaces. Measured on every shipped world: one component, so nothing yet splits.
---

# What it is

Take every [action](/domain/action.md) and every derivation, and join the predicates each one
reads or writes. What falls out is a partition of the vocabulary: within a component, some
lever couples the words; across components, nothing does.

The consequence is about [wants](/domain/desire.md). A want's view is what it reads plus what
the actions [relevant](/domain/relevance.md) to it read and write. Two wants whose views lie in
different components **cannot contradict**: no action serving one writes a fact the other reads,
so pursuing one can never move the other. That is what would let an agent plan them apart, one
[cone](/domain/identification.md) each, and simply concatenate the plans.

# Proven, never declared

Independence is computed from what the rules actually do. It is not read off namespaces, and the
two cases that look obvious are the reason:

- A greenhouse's water words and climate words look like two vocabularies until a heater dries
  the soil. One lever across both makes one component.
- Two vans in one courier vocabulary look like one until you notice nothing they do touches the
  same van.

The second names the limit. A component here is a set of PREDICATES, so it separates a
vocabulary and never two instances of one. Two vans are two components only over VARIABLES, a
subject and a predicate together, which is what a mechanism that split a plan would need.

An action whose reads or writes cannot be read from its text joins everything. A lever that
might touch any predicate cannot be proven not to, and a component wrongly split would let two
plans contradict each other.

# What it measures today: nothing splits

Every shipped world is ONE component, around ninety predicates, whether the derivations are
counted or the actions taken alone. The actions alone already join the market's plumbing to
sensing's readings, because every effect this project ships predicts a reading of the same
shape. Every want every shipped agent holds falls inside that one component.

So the mechanism this concept exists for — one cone per component, plans concatenated — has
nothing to split, and is not built. The measurement is the point: it is what says so, and the
first world that breaks it is the first one worth planning as several cones. See
[#565](https://github.com/ShishkinDmitriy/orexis/issues/565).

# Related

- [relevance](/domain/relevance.md) — the closure a want's view is built from.
- [identification](/domain/identification.md) — the view, as the cone already uses it.
