---
type: Decision
title: An injected service is reached by term, and the bean graph is one per agent
description: >-
  Stores are attributes on the agent and no package can bring one; there is no way for a package
  to offer another package anything but a capability. The design is Anvil-style aggregation with
  one substitution — the binding key is a URI rather than a type, because capability packages may
  not import each other and because the graph addresses everything by term. Declared eagerly,
  resolved lazily, one term one provider. BUILT — the sovereign's ruling that a seam this
  foundational should not wait for its first customer, because packages are shaped by its
  absence.
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

**The key is the CONTRACT TYPE wherever one can be imported, and a term where none can.**

This record first said a term, full stop, on the reasoning that `lint-imports` forbids capability
packages importing each other — so market could not import sensing's type to key on. **That is
true of an implementation and false of a contract**, and importing a contract is the one
cross-package import this project has always allowed: `packages/codec/json/` imports sensing's
`Codec`. The sovereign made the correction — terms were proposed for extension POINTS, where a
point is a declared thing in the graph, and were never an argument against types elsewhere.

So a type is the default and the better key: you import the thing you want and ask for it, the
type checker follows, and there is no parallel naming system to keep in step. `packages -> agent`
is allowed outright, so all seven of the kernel's services are keyed by their classes with no
carve-out at all. A term remains available for a service whose contract is not an importable
class.

Seven `ag:*Store` terms were declared for this and removed the same day, which is the shortest
life any term in this project has had.

**And the key is read off the provider's return annotation**, so it is written once rather than
named beside a function that already says it. Not off the returned OBJECT — finding out what a
provider returns means calling it, and a provider runs only when an agent asks. An annotation
says the same thing without building anything, and a type checker holds the provider to it.

**One term, one provider**, which is `loader._members()`'s rule generalised — it already refuses a
term implemented twice, because the alternative is settled by whichever package the filesystem
yielded first.

**Declared eagerly, resolved lazily.** `@requires(…)` declares what a module needs so the gate can
check it; what is injected is a **handle**, resolved on first use.

**A module declares what it needs by ANNOTATING A FIELD**, the same convention `dataclasses`
uses: a value beside it makes it an ordinary attribute, no value makes it a service, and
`X | None` makes it one the module can work without.

This was `@requires` and `@uses` for a day. The decorators went for a reason that is about
who reads the code rather than about taste: **a decorator that makes attributes appear is
invisible to every tool a Python developer brings** — no autocomplete, no go-to-definition, and
a type checker calling `self.beliefs` an error — where an annotation is seen by all of them.
This matters most for the reader this design is FOR, an external package author with no repo
context. And `| None` says optional in the language's own vocabulary, so a second decorator
stopped being needed at all.

The split still is what a gate can say: a missing requirement is a broken build and is refused
before anything runs; a missing optional is a fact about which packages were installed, and is
refused by nobody. Both are DECLARED, which is the point — an undeclared reach is invisible,
and that was the condition this design was written against.

**An injected field may not shadow an inherited name, and that is enforced loudly.** The first
attempt wrote `desires: Desires`, which collided with `Module.desires()` — a choir extension
point. The injection was silently skipped, the module went on calling a bound method as if it
were a store, and the failure surfaced three layers away as an arithmetic assertion in a review
test. It raises now, naming both sides. Constructing at injection time
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

**The check turned out to be build-wide, not per agent**, which is simpler than this record
first claimed and worth correcting. A service is offered by a PACKAGE, and every package is in
every build; what differs between agents is which MODULES are constructed, and a module class's
requirements are static. So the question is *does anything offer this*, and asking it needs no
world at all — `test_every_hard_requirement_is_offered_by_something` runs against the tree.

What remains genuinely per-agent is capability composition, which was already checked. The
per-agent framing came from assuming a service could be granted; it cannot, which is exactly what
makes it a service rather than a capability.

# Why not an existing library

`dependency-injector`, `injector`, `svcs`, `dishka`, `wireup` were considered. All resolve
primarily by **type**, which the independence contract makes unusable between capabilities. All
want a **container declared somewhere**, which is the registry `capability-packages` exists to
avoid. All would need the container built eagerly, which imports every provider and undoes #216.
And the expensive half — multibindings with a per-point merge rule — none of them offers and the
choir already does.

What is left to write is small: `_members()` is the single-binding registry already, at about
twenty-five lines.

# Why it was built without a customer

This record first said: do not build it, there is no consumer, wait for #311. The sovereign
overruled that, and the audit done before building says why they were right.

**Reaching outside a package was four mechanisms and a folk memory.** Measured across
`packages/`: `agent.provider(family)` in 28 places, `ask`/`tell` in 13, direct kernel imports —
and **twelve undeclared attributes on the agent**, led by `self.agent.beliefs` at 41 uses,
`.desires` at 11, `.keeper` at 5, `.metrics` at 2. Nothing declared them, nothing listed them,
and nothing said which a package might touch. A package author learned them by reading other
packages.

So the consumer was never the missing store. It was every package already reaching for things it
could not declare — and a seam this foundational shapes what packages can be, which is an
argument for building it before the first customer rather than after.

What the earlier measurement got right stands: the kernel's services are always present, and the
two `if keeper is None` guards defend a state that cannot occur. That is why the kernel's seven
are REGISTERED rather than made optional — declaring one cannot fail, and the value is that the
declaration exists at all.

# Seams left open

- **The 41 `self.agent.beliefs` call sites are not migrated.** `review` is the worked example —
  `@requires(DESIRE_STORE, METRICS)` — and the rest follow when they are next touched. The
  attributes remain the kernel's own wiring; what changed is that a package can now DECLARE
  instead of reaching, and the runbook tells it to.
- **Nothing yet refuses `self.agent.<service>` in a package.** The guard is writable — the
  attribute names are the seven terms — and it should wait until the call sites are migrated,
  or it is a gate that fails on arrival.
- **`@requires` would check names, not shapes.** That a required term is provided says nothing
  about the object satisfying the contract the requirer imported.
- **Nothing decides service lifetime**, because there is exactly one: the agent process. If a
  service ever needs to outlive or subdivide that, this record is where the assumption was made.
- **A provider that yields is closed at shutdown**, newest first — added after reading what
  `svcs` offers and finding the gap was ours: a module has `stop()`, a service had nothing, and
  #311's ring would have had nowhere to flush. What is NOT decided is failure policy beyond
  logging: a service that will not close does not stop the others, and nothing retries.
