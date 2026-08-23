---
type: Decision
title: A package is a directory — discovered, never listed
description: Each package is one self-contained directory (ontology, shapes, derivation rules, code, beliefs, and its own namespace) found by looking rather than named in a registry; capabilities reach each other through T-Box terms, never through Python imports. Adding one is adding a directory. A package may provide SEVERAL capabilities — that distinction was added later.
status: accepted
timestamp: 2026-08-03T12:00:00Z
---

> **Current statement: [package](/domain/package.md).** This record is how the model got
> there and why; the domain concept is what it is now. Four records amend each other on
> this subject, so read the concept first unless you want the argument.

# Context

[capability-modules](/decisions/capability-modules.md) established what a capability *is*:
a vocabulary, its rules, its derivation, and the code that reads them — derived from hardware
rather than declared. That decision stands. What it got wrong was where those four things
live.

They were split across four top-level trees by **file type**: `ontology/sensing.ttl`,
`shapes/sensing.ttl`, `rules/sensing.ru`, `modules/sensing.py`. Nothing held them
together but a shared filename. Three consequences, all of them felt:

1. **A capability could not be read in one place.** Four directories to open, and no
   mechanism to notice when one of the four drifted from the others.
2. **Adding one edited three central files.** A new capability meant its four files *plus*
   `ontology.py` (a term constant and the `MODULE_FILES` tuple), `modules/__init__.py` (the
   `REGISTRY`), and `beliefs.py` (a dataclass, a term map, an accessor, a cast table). The
   extendable axis was the one place you had to touch everything.
3. **One flat list conflated four different kinds of thing.** `MODULE_FILES` named the kernel
   (`core`), capabilities (`sensing`, `market`, `actuation`), a *transport* (`mqtt` —
   explicitly not a capability by that same decision), and the plug-in *domain* (`water`,
   vocabulary with no code). The claim "a capability is four files with the same name" was
   already false: `market.ttl` served two modules, `mqtt.ttl` served a driver, `water.ttl`
   served none.

There was a fourth problem the layout was hiding. Modules reached for each other by class:
`bidding` imported `SensingModule`, `hosting` imported `ActuationModule`, and sensing
read the *bidding* capability's private beliefs inside a bare `except` to get a band. Any of
those imports made one capability impossible to remove without breaking another.

# Decision — one directory, four names, no list

A **package** is a directory, and the tree it sits in says what kind it is:

| | |
|---|---|
| ~~`packages/core/<name>/`~~ | **GONE.** The base vocabulary was a family of exactly one, forever, that every other package layers on and nothing can remove. That is not a package; it is the base, and it lives in `agent/` beside the code that reads it |
| `packages/capability/<name>/` | what an agent can **do**. The extendable axis |
| `packages/transport/<name>/` | how a device is **reached**. Deliberately not a capability |
| `packages/part/`, `plant/`, `bus/`, `tool/` | the things a world names, and the vocabularies they layer on |

A package may also declare a **namespace of its own**, in its `ontology.ttl`, and
`agent.loader.prefixes()` reads it from there so a query can name its terms. That was added after
this record: the prefix map used to be a kernel constant, which made a namespace the one thing a
package could not have without editing the kernel.

**AMENDED.** This paragraph used to say that two of the three sat inside `agent/` and one did
not, because a capability's Python is loaded by an agent runtime and vocabulary is shared with
onboarding. The reasoning was sound and the arrangement is gone: there is ONE tree now, and the
family is the parent directory. What has not changed is the fact underneath — onboarding reads a
package's `ontology.ttl`, `shapes.ttl` and `rules.ru` through the loader and never imports a
module from one — but that is now held by `lint-imports` and the `Containerfile` rather than
shown by where the directory sits. See
[one-tree-and-one-mechanic](/decisions/one-tree-and-one-mechanic.md).

Inside a package the same names mean the same things every time:

| | |
|---|---|
| `ontology.ttl` | the vocabulary — what its terms mean |
| `shapes.ttl` | the rules — what an agent must believe to hold it |
| `rules.ru` | the derivation — what wiring **gives** an agent it |
| `terms.py` | the terms it implements, and the families it asks others for |
| `beliefs.py` | its `Block`s — the private parameters it reads, and their dataclasses |
| `__init__.py` | the manifest: `PROVIDES = (…)` |

**Every one of them is optional, and an omission is a statement.** `packages/plant/water/` has no
code, because a domain contributes vocabulary. `packages/transport/mqtt/` has no `rules.ru`, because
a transport grants no capability — which is the whole point of it not being one.
`packages/capability/actuation/` has no `beliefs.py`, because it decides nothing: it reads the
device's own calibration from the world and obeys.

`orexis.loader` finds all of this by looking. There is no list of capabilities anywhere in the
codebase — not in the seeder, not in the validator, not in the runtime, not in the tests.

# Consequences that were the point

**A package is not a capability, and this record originally said it was.** The title above said *a
capability is a directory*, and `capabilities/market/` already provided two — bidding and hosting —
when it was written. A directory is how a package is FOUND and how one is DELETED; what isolates a
capability is `PROVIDES` and its term. See
[a-package-owns-its-namespace](a-package-owns-its-namespace.md), which corrected the rule and folded
a third capability into that same package to show the seam holds without it.

**Adding a capability is adding a directory.** No registry line, no term constant, no belief
accessor, no edit to any existing file. This is checkable, and it was checked: dropping a
throwaway `packages/capability/forecast/` into the tree made an agent load its vocabulary, run its
derivation, and boot with `forecasting` in its module list — with nothing else
in the repo touched. Deleting the directory removed it just as completely.

**Removing one is deleting a directory,** which is the harder half and the one that fails
when packages import each other. So they do not:

- **`agent.provider(family)`** — a module asks its agent for whoever provides a *capability
  family*, resolved through the T-Box. `bidding` asks for `sensing:SensingCapability` and gets
  polling or listening without knowing there are two ways to perceive. `hosting` asks for
  `actuation:Actuation` and issues paper claims if the answer is None.
- **`annotate` / `urgency`** — where a capability needs a *judgment* it does not hold, it
  asks every sibling and takes what it gets. This replaced the worst coupling in the old
  layout: sensing reading bidding's band through a swallowed exception.

The term is the interface. A package names another's family with `term("SensingCapability")`
— building the IRI from the kernel prefix, exactly as the constitution already permits, since
a T-Box term is public and a Python class is not.

# What moved, and why it belongs where it landed

**Judging moved out of sensing.** A band is a fact about a *stake*, not about a sensor:
the same reading is trouble for a fern and comfort for a succulent. So `band()` and
`urgency()` left sensing, and sensing — which owns the number and the freshness rule and
nothing else — asks. An agent with no stake in a subject gets no answer and watches at its slow
cadence, which is the honest reading of "nothing here is urgent to me". A perceiving agent that
holds no band is now a coherent thing to be, rather than a `try/except`.

They landed on `BiddingBeliefs`, moved again to a desire package, and have since come into the
kernel with the rest of the mind — `agent/deducer.py`. That second move is the one this section
is about, and it is
where they should have gone the first time: putting them on a bidder made *having an opinion
about your own state* conditional on being a market participant, and limited it to the one
property a bid is priced in. The seam this section is about is unchanged and is why the second
move cost nothing — sensing still asks whoever will answer, and never learned either address.
See
[desire-is-deduced-from-the-ranges-the-world-states](/decisions/desire-is-deduced-from-the-ranges-the-world-states.md).

**Belief blocks moved to their capabilities.** `orexis.beliefs` keeps the *reader* — the block
query, the no-defaults error, the freshness rule — because that is identical for every
capability. What each one believes is a `Block` declared next to the module that reads it, and
the cast for each field is taken from the dataclass annotation, so a block states its types
once instead of twice.

**`verify_command` moved to the kernel** (`orexis.signing`). It is the *device's* half of
actuation: a simulator or a firmware stub must be able to check a co-signed command without
loading the module that issued it.

**The market mechanism stayed in the kernel.** `market.py`, `auction.py` and `clearing.py` are
pure and domain-neutral, and clearing is a separate authority on its way to being a separate
service (see [standalone-clearing](/decisions/standalone-clearing.md)). What lives in
`packages/capability/market/` is the *choreography* — announce, collect, match, issue — which is the
part that reads the vocabulary and holds a capability.

# Cost, stated plainly

The package trees sit at the repo root and are put on `sys.path` by `orexis.loader` on import.
That is a real mechanism with a real cost: capability code is not part of the installed
`orexis` distribution, so a capability cannot yet be shipped independently of the repo. The
trade was deliberate — the ontology stays a first-class, top-level artifact rather than being
buried under a Python `src/` tree, and the four files of a capability stay side by side. The
path is appended rather than prepended, so an installed distribution always wins and a new
tree can never shadow a real dependency.

# What is still open

- **A capability cannot be installed from elsewhere.** The natural next step is an entry-point
  group, so a third party could publish one — the manifest (`PROVIDES`) is already the shape
  an entry point would need.
- **Nothing checks that a package's four files agree.** A `rules.ru` deriving a capability no
  `__init__.py` provides is caught at agent startup (as a warning, correctly — a world may
  legitimately expect more than a build has), but a `shapes.ttl` demanding a belief no `Block`
  reads is caught by nothing.
- **`domain/` holds one plug-in and no code.** Whether a domain should ever provide behaviour
  is unanswered; today it does not, and the loader does not require it to.
