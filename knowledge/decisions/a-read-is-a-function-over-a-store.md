---
type: Decision
title: A read is a function over a store, and a class earns its keep by owning one
description: >-
  The repository convention had two instances and both are gone - `Wants` and `Desires` are
  functions over a store now, and what is left of the second is a modality rather than a
  collection. What the convention was right about is kept as lines: a read takes a store and
  nothing else, a criterion is an argument and never a name, a read only reads, a plural read
  is ordered before it is cut. What it was wrong about is the shape, because the Spring Data
  spelling charges a name per criterion and a name per combination - five finders over one
  query text in `Wants`, three in `Desires`, several called by nothing but their own test. A
  class still earns its keep for owning a store whose nature is its own decision, or for
  reaching the choir; neither of those is a collection.
status: accepted
timestamp: 2026-09-21T22:00:00Z
---

# What the convention bought, and what it cost

[a-repository-is-named-for-what-it-holds](/decisions/a-repository-is-named-for-what-it-holds.md)
set out a DDD repository: a collection of domain objects, backed by a store and owning none,
named for the plural of its element, with Spring Data's `find_all` / `find_all_by_x` /
`find_first_by_x`. Two things were built to it. Both are gone.

**What it bought is real and is kept.** The graph names and the query texts stopped being
things a caller knew. Every plural read is bounded, ordered before it is cut, and says so when
a page comes back full. A read takes somewhere to search and no identity, because one agent,
one volume means the store IS the scope. None of that needed a class: it is where the text
lives, not what the text is attached to.

**What it cost is a name per criterion.** `Wants` was five finders over ONE query with a
`where` clause swapped and a graph family named or not; three of the five were called by
nothing but their own test. `Desires` was three over one text. That is what the spelling
charges: a new criterion is a new method, and a combination of two is a method per
combination, so a query with two optional narrowings becomes four names for one question.

The sovereign's ruling, on reading `find_steps` land as a function over a store: *a function
over a triple store is more convenient, especially where an update query brings no data into
Python and keeps everything in the triplestore.*

# What survives as a rule

- **A read is handed a store and nothing else.** An agent id is another aggregate root's
  identity; identity travels as a query criterion where one is needed, and the reads need none
  at all.
- **A criterion is an ARGUMENT, never a name.** `find_wants(store, desire=…, derived=True)`
  says at the call site what `find_first_by_desire` hid — including which family it scoped to,
  which no method name said anywhere.
- **The one distinction worth a name is the answer's SHAPE.** A page against one-or-None, and
  nothing else: that much of `find_all_by_x` against `find_first_by_x` was carrying its weight.
- **A read only reads.** The function that decides a thing owns writing it.

# What a class is still for

Two things, and neither is a collection.

**Owning a store whose nature is its decision** — a MODALITY
([a-store-is-a-modality](/decisions/a-store-is-a-modality.md)). `Desires` is in memory,
derived, never edited, and read-only on its surface; the rebuild is the only way it changes,
and no caller may write. That is a class with an invariant to hold, not a place to keep
queries.

**Reaching the choir** — `Considering` is handed the whole agent, because what a want reads as
is CONTRIBUTED and the contributors are modules. A read over stored rows needs a store; a read
over contributed answers needs the contributors, and the asymmetry is what tells the two apart.

# Seams left open

- **`Store` keeps its name and is infrastructure**, which the superseded record already said
  and nothing here changes.
- **The layer above it is absent rather than thin.** Domain code writes its own SPARQL against
  the store, which was the observation that prompted the convention in the first place. That is
  now the settled answer rather than a gap: the text lives beside the function that needs it,
  and what stops it sprawling is that a question with one asker is a function with one caller
  and gets deleted when the caller does.
