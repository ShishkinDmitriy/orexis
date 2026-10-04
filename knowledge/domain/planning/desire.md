---
type: Domain Concept
title: Desire
term: http://example.org/orexis/planning#Desire
description: >-
  What an agent stands for, in two kinds. A DESIRE is standing and universal - this subject
  inside its range, no claim left unserved - held for the agent's life and never searched. A WANT
  is what a desire comes to where the world makes it bite - this plant, dry at noon - minted per
  instance and period, searched, and withdrawn once met.
---

# The two kinds

A **desire** is a `planning:Desire` an agent `planning:holds`, carrying its met-test — a SHACL
shape through `planning:metWhen`, or the pattern of what it avoids through `planning:unmetWhen` —
and, where its domain has one, `planning:estimates`, a select saying how far a world still is in
the unit actions cost. It is about every instance at every instant, so it is never met once and
for all and never handed to a search. A world authors it, in a `planning:DesireGraph`.

A **want** is a `planning:Want`, `prov:wasDerivedFrom` its desire, bound to the instances in
trouble and holding during a period of its own — its graph's — with `planning:holdsAt` where it
must hold at a foreseen instant. It is one-shot: it carries where it has got to
(`planning:state`, Recognized to Done, each written by whoever decides it) and it goes once met.
Three worlds author a want directly — Hanoi's, the courier's and the tower's movers hold one and
no desire, and exit when it is reached. And [refinement](/domain/planning/refinement.md) mints one
the agent records for itself, to keep a step one level down.

# How a want comes to be

`derive_wants` judges every desire in every ground — the present, and what each prediction makes
of the period after it ([prediction](/domain/prediction/prediction.md)) — by the same `weigh` the
search uses: the met-test's violation rows are the instances in trouble, and each ground's start
is when. A want is minted per [scope](/domain/planning/scope.md) of those rows — each placed by what
it is about and, where that belongs to two scopes, by what its offending value is keyed by, the bed,
which the want then carries as `planning:keyedBy` — and one the rows no
longer imply is withdrawn by the same pass — unless an intention is walking it. Nothing ranks one
want before the search that could rank it: every want is searched, and what their plans cost is
the comparison.

# What it is judged by

Its met-test, and nothing else: the search sees no partial progress, and a want is reached where a
world passes the shape ([shape](/domain/planning/shape.md)). The core compares triples — a plant wants
its soil `sensing:inside` its range, a side the rules concluded — and interprets no number.
