---
type: Decision
title: A layer is a distribution, and the arrow between layers is a tested dependency
description: >-
  The three-layer ruling — handlers, progression, deliberation — was enforced by nothing.
  The kernel measured 32 Python files and 8,093 lines sharing one import space, with two
  import contracts among three root trees and none inside the kernel itself, so a handler
  importing the search was legal. Decided that the kernel splits along its own layering into
  root distributions beside the assembly — the mind's stores beneath, then execution,
  progression and deliberation, review already a granted package above — each importing only
  the contract of the layer below, the arrows held by the same dependencies-to-imports gate
  every package already answers to. Refuses the monolith the mind's record accepted as a
  seam, and the one-distribution argument whose premise every-package-is-a-project removed.
status: accepted
timestamp: 2026-08-30T12:00:00Z
---

# Context

[layered-by-timescale-and-interruptibility](/decisions/layered-by-timescale-and-interruptibility.md)
rules that anything blocking belongs in progression, anything searching in deliberation, anything
that must never block in a handler. That ruling is prose. Measured today, read off
`pyproject.toml` rather than verified by breaking: `lint-imports` holds two contracts among the
three root trees and none between the kernel's own modules, so `agent/act.py` importing
`agent/planner.py` — a handler importing the search — would pass every gate this repository has.
The kernel is 32 Python files, 8,093 lines counting its ontology and rules, in one import space.

[the-mind-is-not-a-package](/decisions/the-mind-is-not-a-package.md) saw this and accepted it:
"`agent/` is large, and that was accepted rather than overlooked: cohesion was the point." This
record overturns that seam — the acceptance, not the ruling it was a seam of.

# What was decided

**The kernel splits along its own layering, and each layer becomes a root distribution beside
`assembly/`.** Four trees where `agent/` was one:

- **the stores beneath everything** — `agent/store.py`, `agent/beliefs.py`, `agent/graphs.py`,
  `agent/desire.py`, `agent/intentions.py`: the modalities every layer meets at, importing no
  layer. The layers mostly do not call each other; they meet at the belief base, which is why
  this tree is the floor rather than a peer (#451);
- **execution** — the acts and the actor road: dumb carrying-out, returning what happened,
  asking nothing;
- **progression** — the keeper, commitment, upkeep: timers, patience, verification, suspension;
- **deliberation** — the deliberator, the planner, the imaginarium, the afforder, the effects:
  the search (#452).

**Review, the fourth layer up, already IS a distribution** — `packages/orexis-capability-review/` —
and does not move. It stays granted where the four below are unconditional, and that asymmetry
is correct: latitude is a premise some agents lack, a mind is not.

**A layer imports only the contract of the layer below.** The pattern is the one the repository
already blessed for a family's plug-ins — codec imports sensing's `Codec`, never its
implementation. The arrow is a `pyproject.toml` dependency, and the gate that holds every
package's dependencies to its imports in both directions
([every-package-is-a-project](/decisions/every-package-is-a-project.md)) holds these: a layer
reaching past a contract fails, and a boundary no longer used fails too.

**They are root trees, not members of `packages/`.** The granted tree is for what a world can
grant, and a layer is unconditional — a grant nobody can lack is not a grant, which is the
mind's record applied consistently rather than argued with. This also keeps
[package](/domain/package.md)'s claim intact: the kernel is not a family. `assembly/` stays
beneath all of it, unchanged — a layer is one more thing it assembles
([the-assembly-is-not-the-mind](/decisions/the-assembly-is-not-the-mind.md)).

Working names are the domain's — [executor](/domain/executor.md), [keeper](/domain/keeper.md),
[deliberator](/domain/deliberator.md) — and the implementing change has final say, including the
stores' name (#451).

# The alternatives, and what each was refused for

**An import-linter layers contract inside the kernel, and no split.** Cheaper, and refused for
three reasons. A contract over module names is a registry, and this repository already learned
what registries do — the `pyproject.toml` comment refusing to list twenty-one packages says
"a registry goes stale the first time somebody adds a package and forgets this file." It cannot
flag a boundary that stopped being used, where the dependencies gate fails on an unused
declaration. And it ships nothing: one distribution cannot put only the executor and the stores
on a dumb device's image.

**Layers as granted capability packages.** Refused by the part of
[the-mind-is-not-a-package](/decisions/the-mind-is-not-a-package.md) that stands: stores built
unconditionally with readers arriving by grant is exactly the failure shape that retired
wanting, committing and deciding. A layer loads because the agent exists.

**The monolith, which was the standing choice.**
[repository-layout](/decisions/repository-layout.md) refused two distributions because the
packaging split "only described the intent" while the `COPY` line and `lint-imports` enforced
it. That premise is gone: since
[every-package-is-a-project](/decisions/every-package-is-a-project.md), a distribution boundary
is held to its imports in both directions, so it fails when violated instead of describing.
The same record's "why there is no `agent/kernel/`" survives untouched — it refused a false
symmetry between discovered trees and the trunk they import, and these layers are imported,
not discovered; none joins the globbed tree. The cost that section counted is paid knowingly:
every import of the kernel in the repository changes spelling once.

# What this does not enforce

**The graph axis.** Import direction sees who calls whom and nothing else. Who writes and who
reads a modality travels through the store, where shapes and provenance are the guards — the
mind's original failure, an unconditional store beside granted readers, would have sailed
through this split. Expecting the package boundary to catch graph-axis coupling is the mistake
this section exists to refuse.

# Seams left open

- **Which layers an agent ships stays an image concern.** No world declares a layer roster, and
  every agent gets all four; a dumb device shipping only the stores and the executor is a
  `Containerfile` variant nobody has asked for yet. The day a world wants to declare it, that
  is a grant question, and the record to reread is the mind's.
- **Where the `Agent` object and the choir live** — `agent/runtime.py`, `agent/module.py` — is
  #452's to settle: the assembling shell above the layers, or absorbed into `assembly/`.
- **An interchangeable deliberator is now a swap above a tested boundary.**
  [llm-heavy-deliberation](/decisions/llm-heavy-deliberation.md) argued for one and
  `ag:deliberatesBy` stayed unreserved; the layer split is what makes that arrival a member
  joining a family rather than surgery on the kernel.

The trigger for revisiting: a contract module that grows logic. The day a layer's contract
holds behaviour rather than types and signatures, the boundary has moved and this record is
due a rereading.
