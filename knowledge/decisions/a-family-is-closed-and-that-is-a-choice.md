---
type: Decision
title: A family is closed — an alternative implementation of an ability is the declaring package's to add
description: >-
  A package may implement only terms it declares, which is what lets imports follow grants. The
  consequence, noticed while placing a model-backed review: nobody outside a package can ship an
  alternative member of its family. `review:Consulting` must live in `packages/capability/review/`
  because the term is review's. Decided that the rule stands and the consequence is stated rather
  than discovered by hitting a RuntimeError, with the two ways to relax it written down and the
  trigger for doing so.
status: accepted
timestamp: 2026-08-27T22:00:00Z
---

# The rule, and what it buys

`registry()` refuses a class whose `CAPABILITY` is not in its own package's namespace:

> a package implements the terms it declares, which is what lets imports follow grants (#216)

That is not a tidiness rule. It is what makes `registry_for(capabilities)` able to resolve a
granted capability to its implementer **by string alone**, so a fern imports sensing, market,
review and reporting and never actuation's — and a missing optional extra costs only the agents
granted the capability that needs it.

# The consequence, noticed while placing Consulting

The sovereign asked where a consulting package would declare its dependencies. It would not:
**there is no consulting package and there cannot be one.** `review:Consulting` is declared by
`packages/capability/review/ontology.ttl`, so only that package may implement it — exactly as
`market:PayAsBid` and `market:UniformPrice` live in `packages/capability/market/`.

Generalised: **a family is closed.** Whoever declares the family owns every member of it. Nobody
outside can ship a different matching algorithm, a model-backed review, or a second codec for a
format sensing named — because the term belongs to the package that declared it.

That is a real limit on packages developed in another repository, and it is not a packaging
problem: entry-point discovery would find such a package and the loader would then refuse what
it provides.

# What is decided

**The rule stands, and the consequence is written down here rather than met as a RuntimeError.**
An external package brings NEW abilities — its own family, its own terms, its own members — and
not alternative implementations of ours. That is a smaller promise than a plugin ecosystem
usually makes, and it is the honest one for a build where imports follow grants.

**A dependency that only one member needs is an extra**, declared on the distribution and named
for the capability, and imported inside `provides()` where only a granted agent pays for it.
`_provider_in` already carries the degrade path and already names the case:

> a package whose optional extra is not installed — `orexis[consulting]` and its model client —
> leaves its capability unprovided for the agents that were granted it, and costs nothing at all
> to the agents that were not

Nothing implements Consulting yet, so no extra is declared: naming a model client before anyone
has chosen one would be a dependency on a decision nobody has made.

# The two ways to relax it, and neither is taken

- **Allow implementing another package's term where a dependency on it is declared.** What a
  plugin ecosystem normally does. It costs the string-alone resolution: the owner of a term
  would no longer be the package that implements it, so `registry_for` would have to search
  every package, importing them to find out — and #216 goes with it.
- **Let a family declare itself OPEN**, with a term on the family meaning others may add
  members. Keeps the default closed, so nothing already shipped changes, and confines the cost
  to families that opted in. This is the better of the two if the question is ever forced.

# The trigger

**Someone wanting to ship an alternative member from another repository.** Not someone wanting a
new ability — that already works. Until then the closed rule costs nothing real, because every
family here is declared and implemented by the same hands.
