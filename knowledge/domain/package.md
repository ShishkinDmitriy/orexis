---
type: Domain Concept
title: Package — the one unit the loader knows, and the one tree it lives in
description: What a package IS today, in one place: `packages/<family>/<name>/`, five optional
  files, the family read off the path, the namespace read off the ontology, and `PROVIDES` as
  the only registration. Four decision records got here in four steps and each amends the one
  before; this says where they landed, so nobody has to replay them to learn the current model.
---

# What a package is

A **package is a directory** — `packages/<family>/<name>/` — holding whichever of five files it
wants. It is found by looking, never by being listed. Adding one is adding a directory; removing
one is deleting it.

```
packages/<family>/<name>/
    ontology.ttl   the vocabulary — what its terms mean
    shapes.ttl     the rules — what must be true of something that has it
    rules.ru       the derivation — what premise GRANTS it
    review.rq      the second thought — how an agent re-picks one of its beliefs
    __init__.py    the manifest — PROVIDES = (…), the classes it contributes
```

**Every one is optional, and an omission is a statement.** `packages/part/esp32/` is an ontology
and nothing else, because a board has no behaviour a runtime could load.
`packages/capability/market/` has all of them. Neither is more of a package than the other, and
that is the point: **a plant, a part and a capability are the same kind of thing to the loader.**

A package with no `__init__.py` is **knowledge-only** — legitimate, and the majority. Twelve of
the twenty-three packages shipped today carry no Python at all.

# The family is the directory above, and it is declared nowhere

`agent.loader` walks two levels down from `packages/` and reads the family off the path. Nothing
enumerates the families; `KINDS` in `agent/loader.py` fixes only the **order they merge in**, for
determinism in logs and diffs. A family invented tomorrow is found without editing anything — it
merely sorts after the named ones.

| family | borne by | what having one means |
|---|---|---|
| `core` | — | the base vocabulary, merged first |
| `capability` | an **agent** | `ag:hasCapability` on the agent |
| `transport`, `codec`, `scaling` | a **binding** | a predicate on the **sensor** |
| `part`, `plant`, `bus`, `tool` | nothing — knowledge only | a model others are instances of |

The split that matters is **bearer**, not importance: a codec family is a capability by the
definition in rule 2, it is simply not something an *agent* has. See
[bytes-become-a-quantity-in-stages](/decisions/bytes-become-a-quantity-in-stages.md).

# A package owns its namespace

A package declares its own `owl:Ontology` IRI and prefix in its `ontology.ttl`, mirrored in
`terms.py`. **`agent.loader` reads every project namespace off the ontology that declares it**, so
`market:` reaches a SPARQL query without `store.PREFIXES` learning the package exists. There is no
registry, which is the property the whole tree exists to have: a package is nameable without
editing the kernel.

A package implements the terms **it** declares. That is what lets imports follow grants — a
runtime imports only the packages its own capabilities name.

# What isolates a capability is `PROVIDES`, not the directory

**A directory is a package. A package is not a capability, and may hold several.**
`packages/capability/market/` provides three — bidding, hosting, and the matching *family* — and
it is one package.

A **family** is the slot; its **members** are the interchangeable implementations.
`sensing:SensingCapability` is a family; `sensing:Subscribing` and `sensing:Listening` are two ways
of having it. `hosting.py` asks `agent.provider(BID_MATCHING)` and never learns which member
answered, which is why uniform price landed without touching a line of it.

**Packages never import each other's Python.** Reach another package by asking
`agent.provider(family)` for a term, or contribute through the choir hooks — `annotate`,
`urgency`, `notices`, `series`, `quiet`.

# What grants one is its own premise

There is no pattern to fit a new capability into. **The premise lives in the capability's own
`rules.ru`**, and it is whatever fact makes *that* capability meaningful:

| granted by | capability | the premise |
|---|---|---|
| **wiring** | `sensing`, `actuation`, `market` | equipment, or a position in a market |
| **latitude** | `review:Reckoning` | an `review:commits` mandate whose ends differ — settings you may move |
| **a stake** | `desire:Deducing` | `ag:actsFor` a subject that states what it needs |
| **a stake AND a lever** | `intention:Keeping`, `deliberation:Reflex` | wanting without means is a wish; means without wants decide nothing |
| **universally** | `reporting` | granted by a rule and insisted on by a shape — mandatory, not optional |

When you add one, ask what makes *yours* meaningful rather than which of these it resembles.

**Capabilities are worked out at genesis, never hand-declared** — `world.ttl` must not contain
`ag:hasCapability`. Sensing's are `derived` (the hardware forces the answer); the others are
`deduced` (someone judged, and could have judged otherwise). Both land in the world graph, and
since the provenance split they are distinguishable rather than merely distinct.

# `agent/` is the kernel that loads them, not their home

Capability Python used to live under `agent/`, so the tree itself showed which of it a runtime
loads. **It does not show that now** — `packages/capability/market/` and `packages/part/dht11/`
look identical. The contracts carry the boundary alone:

- `lint-imports` holds `packages` away from `onboarding`, and onboarding away from nothing;
- the `Containerfile` decides what reaches an image by naming two trees and not a third, with
  `tests/test_layout.py` failing if a `COPY onboarding/` appears.

Both were always the real enforcement. The layout was a reminder, and the reminder is gone.

# How it got here

Four records, each amending the one before. Read them for *why*; read this for *what*.

1. [capability-modules](/decisions/capability-modules.md) — a capability is an ontology module
   plus shapes plus rules plus code, derived from hardware rather than declared. Still true.
2. [capability-packages](/decisions/capability-packages.md) — it becomes one directory,
   discovered rather than listed.
3. [a-package-owns-its-namespace](/decisions/a-package-owns-its-namespace.md) — prefixes are read
   off the ontologies, and a directory turns out to be a package rather than a capability.
4. [one-tree-and-one-mechanic](/decisions/one-tree-and-one-mechanic.md) — the two package systems
   become one tree, with the family read off the path.

Also: [repository-layout](/decisions/repository-layout.md) for why the trees are flat and why
there is one distribution; [a-package-may-test-itself](/decisions/a-package-may-test-itself.md)
for why tests sit beside the code as plain `test_*.py`;
[telemetry-is-a-mandatory-capability](/decisions/telemetry-is-a-mandatory-capability.md) for why a
capability every agent holds is still a capability.
