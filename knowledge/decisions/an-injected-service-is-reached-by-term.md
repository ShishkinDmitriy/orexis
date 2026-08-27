---
type: Decision
title: An injected service is reached by term, and the bean graph is one per agent
description: >-
  Stores are attributes on the agent and no package can bring one; there is no way for a package
  to offer another package anything but a capability. The design is Anvil-style aggregation with
  one substitution — the binding key is a URI rather than a type, because capability packages may
  not import each other and because the graph addresses everything by term. Declared eagerly,
  resolved lazily, one term one provider. NOT BUILT: nothing needs it yet, and the trigger is
  written down.
status: accepted
timestamp: 2026-08-27T18:00:00Z
---

# What is true now

An agent owns four stores — `beliefs`, `desires`, `intentions`, `revision` — and packages reach
them by attribute: `self.agent.beliefs` in 41 places, `.desires` in 11, `.keeper` in 5. It works,
and it has two limits.

**A package cannot bring a store.** The four are constructed in `Agent.__init__` and named there.
[#311](https://github.com/ShishkinDmitriy/orexis/issues/311)'s history ring — *"a store in its own
room of the volume, holding what the agent DID"* — has nowhere to be.

**A package cannot offer another package anything but a capability.** `agent.provider(family)`
resolves a derived family to a module. Anything that is not a named ability with interchangeable
implementations has no door: a series sink, a client, a registry.

The choir already covers the other half. `agent.ask(POINT)` is a multibinding — many contributors,
merged by the asker's own rule — and the merge rules differ per point: `max` for urgency,
highest-floor/lowest-ceiling for bounds, dict-update for annotate, `sum` for sweep. **Fan-out is
built; fan-in is missing.**

# What is decided

**A [service](/domain/service.md) is offered by term and resolved lazily.** A package's manifest
declares one; the agent hands it back on request; nothing imports the provider to find out it
exists.

**The key is a URI, not a Python type**, which every Kotlin and Java container would use. Two
reasons, one forced and one preferred. Forced: `lint-imports` holds an `independence` contract
over the capability packages, so market often *cannot import* sensing's type to key on it.
Preferred: a URI key is graph-addressable, and `agent.service(HISTORY)` is a fact a sovereign
could ask about where `agent.service(HistoryRing)` is not.

**One term, one provider**, which is `loader._members()`'s rule generalised — it already refuses a
term implemented twice, because the alternative is settled by whichever package the filesystem
yielded first.

**Declared eagerly, resolved lazily.** `@requires(…)` declares what a module needs so the gate can
check it; what is injected is a **handle**, resolved on first use. Constructing at injection time
brings back the ordering problem the runtime does not have today — every module is built with just
the agent and looks things up later in `start()` — and it would undo #216, because resolving would
import providers before knowing what was granted.

**A dependency is imported as a CONTRACT, never as an implementation.** This is the project's
existing rule, written for a different reason and exactly right here: `packages/codec/json/` imports
`packages.capability.sensing.codec` for `Codec`, and the mqtt driver imports sensing's `Driver`.
A `contract.py` may import stdlib and `assembly` and nothing else — which is what makes mutual
dependencies safe, because contracts do not import back and so nothing loops at import time.
Cycles at *resolution* time are fine: resolution is lazy.

That needs one change to the `independence` contract, which today forbids capability↔capability
outright: an `ignore_imports` carve-out for `packages.capability.*.contract`. Worth making
deliberately, because it is the line between packages knowing each other's interfaces and packages
knowing each other's code.

# The bean graph is per agent, and that is not a limitation

Anvil-style aggregation contributes by **scope**, and a scope is a compile-time marker the author
picks. Here there is no single graph to merge into: a fern composes Subscribing, Bidding,
Reckoning, Storing and Linking; a supplier composes Hosting, Actuation, PayAsBid and more. One
build, different graphs, because the world says so.

So the check is per agent — and it can run **without booting one**. `onboarding/validate.py`
already calls `loader.registry_for(me.capabilities)`, so `orexis-validate <world>` knows exactly
which packages each agent composes and can say *"fern requires `series:sink`, and nothing fern
composes provides it."*

That is as close to compile-time as this gets, and it answers a question a static graph cannot
express: not *is this graph satisfiable* but *are these grants satisfiable for this agent*.

# Why not an existing library

`dependency-injector`, `injector`, `svcs`, `dishka`, `wireup` were considered. All resolve
primarily by **type**, which the independence contract makes unusable between capabilities. All
want a **container declared somewhere**, which is the registry `capability-packages` exists to
avoid. All would need the container built eagerly, which imports every provider and undoes #216.
And the expensive half — multibindings with a per-point merge rule — none of them offers and the
choir already does.

What is left to write is small: `_members()` is the single-binding registry already, at about
twenty-five lines.

# NOT BUILT, and the trigger

**Nothing here exists.** There is no `@provides`, no `agent.service()`, no `@requires`, and no
service in the tree.

It is recorded rather than built because **there is no consumer**. Measured while writing this:
`self.keeper = Keeper(self)` is unconditional, nothing anywhere sets it to `None`, and the same
holds for the deliberator and the metrics — so every service the kernel offers is always present,
and the two `if keeper is None` guards (`agent/execution.py`, `market/bidding.py`) defend against a
state that cannot occur. Declaring requirements today would check something that cannot fail.

**Build it when a package needs to bring a store or a service.** #311 is the first — its history
ring wants a room in the volume and a door for `orexis-ask <world> <agent> history`. Whoever picks
it up should build the mechanism with it, so the ring is what proves the machinery rather than the
machinery arriving first and waiting.

# Seams left open

- **Stores stay attributes** until something brings one. Registering `agent.beliefs` as a service
  before that is ceremony over 41 working call sites.
- **`@requires` would check names, not shapes.** That a required term is provided says nothing
  about the object satisfying the contract the requirer imported.
- **Nothing decides service lifetime**, because there is exactly one: the agent process. If a
  service ever needs to outlive or subdivide that, this record is where the assumption was made.
