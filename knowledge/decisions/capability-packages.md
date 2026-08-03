---
type: Decision
title: A capability is a directory — discovered, never listed
description: Each capability is one self-contained package (ontology, shapes, derivation rules, code, beliefs) found by looking rather than named in a registry; capabilities reach each other through T-Box terms, never through Python imports. Adding one is adding a directory.
status: accepted
stage: v1
tags: [ontology, modules, capabilities, architecture, extensibility, packaging]
timestamp: 2026-08-03T12:00:00Z
---

# Context

[capability-modules](/decisions/capability-modules.md) established what a capability *is*:
a vocabulary, its rules, its derivation, and the code that reads them — derived from hardware
rather than declared. That decision stands. What it got wrong was where those four things
live.

They were split across four top-level trees by **file type**: `ontology/perception.ttl`,
`shapes/perception.ttl`, `rules/perception.ru`, `modules/perception.py`. Nothing held them
together but a shared filename. Three consequences, all of them felt:

1. **A capability could not be read in one place.** Four directories to open, and no
   mechanism to notice when one of the four drifted from the others.
2. **Adding one edited three central files.** A new capability meant its four files *plus*
   `ontology.py` (a term constant and the `MODULE_FILES` tuple), `modules/__init__.py` (the
   `REGISTRY`), and `beliefs.py` (a dataclass, a term map, an accessor, a cast table). The
   extendable axis was the one place you had to touch everything.
3. **One flat list conflated four different kinds of thing.** `MODULE_FILES` named the kernel
   (`core`), capabilities (`perception`, `market`, `actuation`), a *transport* (`mqtt` —
   explicitly not a capability by that same decision), and the plug-in *domain* (`water`,
   vocabulary with no code). The claim "a capability is four files with the same name" was
   already false: `market.ttl` served two modules, `mqtt.ttl` served a driver, `water.ttl`
   served none.

There was a fourth problem the layout was hiding. Modules reached for each other by class:
`bidding` imported `PerceptionModule`, `hosting` imported `ActuationModule`, and perception
read the *bidding* capability's private beliefs inside a bare `except` to get a band. Any of
those imports made one capability impossible to remove without breaking another.

# Decision — one directory, four names, no list

A **package** is a directory, and the tree it sits in says what kind it is:

| | |
|---|---|
| `kernel/` | the T-Box everything layers on. Not a capability; there is exactly one |
| `capabilities/<name>/` | what an agent can **do**. The extendable axis |
| `transports/<name>/` | how a device is **reached**. Deliberately not a capability |
| `domain/<name>/` | what the society is **about**. Vocabulary, usually no code |

Inside a package the same names mean the same things every time:

| | |
|---|---|
| `ontology.ttl` | the vocabulary — what its terms mean |
| `shapes.ttl` | the rules — what an agent must believe to hold it |
| `rules.ru` | the derivation — what wiring **gives** an agent it |
| `terms.py` | the terms it implements, and the families it asks others for |
| `beliefs.py` | its `Block`s — the private parameters it reads, and their dataclasses |
| `__init__.py` | the manifest: `PROVIDES = (…)` |

**Every one of them is optional, and an omission is a statement.** `domain/water/` has no
code, because a domain contributes vocabulary. `transports/mqtt/` has no `rules.ru`, because
a transport grants no capability — which is the whole point of it not being one.
`capabilities/actuation/` has no `beliefs.py`, because it decides nothing: it reads the
device's own calibration from the world and obeys.

`agora.loader` finds all of this by looking. There is no list of capabilities anywhere in the
codebase — not in the seeder, not in the validator, not in the runtime, not in the tests.

# Consequences that were the point

**Adding a capability is adding a directory.** No registry line, no term constant, no belief
accessor, no edit to any existing file. This is checkable, and it was checked: dropping a
throwaway `capabilities/forecast/` into the tree made `agora-seed` load its vocabulary, run
its derivation, and an agent boot with `forecasting` in its module list — with nothing else
in the repo touched. Deleting the directory removed it just as completely.

**Removing one is deleting a directory,** which is the harder half and the one that fails
when packages import each other. So they do not:

- **`agent.provider(family)`** — a module asks its agent for whoever provides a *capability
  family*, resolved through the T-Box. `bidding` asks for `ag:PerceptionCapability` and gets
  polling or listening without knowing there are two ways to perceive. `hosting` asks for
  `ag:Actuation` and issues paper vouchers if the answer is None.
- **`annotate` / `urgency`** — where a capability needs a *judgment* it does not hold, it
  asks every sibling and takes what it gets. This replaced the worst coupling in the old
  layout: perception reading bidding's band through a swallowed exception.

The term is the interface. A package names another's family with `term("PerceptionCapability")`
— building the IRI from the kernel prefix, exactly as the constitution already permits, since
a T-Box term is public and a Python class is not.

# What moved, and why it belongs where it landed

**Judging moved out of perception.** A band is a fact about a *stake*, not about a sensor:
the same reading is trouble for a fern and comfort for a succulent. So `band()` and
`urgency()` are methods on `BiddingBeliefs`, and perception — which owns the number and the
freshness rule and nothing else — asks. An agent with no stake in a subject gets no answer
and watches at its slow cadence, which is the honest reading of "nothing here is urgent to
me". A perceiving agent that holds no band is now a coherent thing to be, rather than a
`try/except`.

**Belief blocks moved to their capabilities.** `agora.beliefs` keeps the *reader* — the block
query, the no-defaults error, the freshness rule — because that is identical for every
capability. What each one believes is a `Block` declared next to the module that reads it, and
the cast for each field is taken from the dataclass annotation, so a block states its types
once instead of twice.

**`verify_command` moved to the kernel** (`agora.signing`). It is the *device's* half of
actuation: a simulator or a firmware stub must be able to check a co-signed command without
loading the module that issued it.

**The market mechanism stayed in the kernel.** `market.py`, `auction.py` and `clearing.py` are
pure and domain-neutral, and clearing is a separate authority on its way to being a separate
service (see [standalone-clearing](/decisions/standalone-clearing.md)). What lives in
`capabilities/market/` is the *choreography* — announce, collect, match, issue — which is the
part that reads the vocabulary and holds a capability.

# Cost, stated plainly

The package trees sit at the repo root and are put on `sys.path` by `agora.loader` on import.
That is a real mechanism with a real cost: capability code is not part of the installed
`agora` distribution, so a capability cannot yet be shipped independently of the repo. The
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
