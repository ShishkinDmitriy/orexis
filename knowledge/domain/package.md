---
type: Domain Concept
title: Package — the one unit the loader knows, and the one tree it lives in
description: >-
  What a package IS today, in one place: `packages/orexis-<family>-<name>/`, five optional files,
  the family read off the NAME, the namespace read off the ontology, and `PROVIDES` as the only
  registration. Five decision records got here in five steps and each amends the one before;
  this says where they landed, so nobody has to replay them to learn the current model.
---

# What a package is

A **package is a directory** — `packages/orexis-<family>-<name>/` — holding whichever of five
files it wants. **The directory name is the distribution name**, and the module is that name with
underscores: one string in three spellings, fixed by punctuation. It is found by looking, never by being listed. Adding one is adding a directory; removing
one is deleting it.

```
packages/orexis-<family>-<name>/
    pyproject.toml THE PROJECT — what this package needs, and the one name it installs under
    __init__.py    THE MANIFEST — what this package contributes, and what it provides
    ontology.ttl   the vocabulary — what its terms mean
    shapes.ttl     the rules — what must be true of something that has it
    rules.ru       the derivation — what premise GRANTS it
    desires.ru     what holding it makes an agent want
    actions.ttl    the ways of acting it brings
    review.rq      the second thought — how an agent re-picks one of its beliefs
```

**The manifest is the only file the loader knows by name**, and it says what the rest are:

```python
@contributes(VOCABULARY)
def vocabulary(package: Path) -> list[Path]:
    return [package / "ontology.ttl"]

def provides() -> tuple:                    # LAZY — the heavy import lives here
    from .module import SubscribingModule
    return (SubscribingModule,)
```

So the filenames above are convention, not requirement: a package may split its shapes across
three files or call its vocabulary anything, and it says so. What it may NOT do is make
`__init__.py` expensive — every one of them is imported at assembly, for every agent, which is
why `provides()` is a function rather than a constant (the-assembly-is-not-the-mind).

**Two of those are not optional.** A package is a **project** — its own distribution,
`orexis-<family>-<name>`, with its own dependencies — and a project needs a `pyproject.toml`; the
manifest is how the loader learns what the rest of the files are. Everything below them is
chosen. Why a package is a project at all, and the four dependency defects one shared list was
hiding, is [every-package-is-a-project](/decisions/every-package-is-a-project.md)'s.

**Every other one is optional, and an omission is a statement.** `packages/orexis-part-esp32/` is an ontology
and nothing else, because a board has no behaviour a runtime could load.
`packages/orexis-capability-market/` has all of them. Neither is more of a package than the other, and
that is the point: **a plant, a part and a capability are the same kind of thing to the loader.**

A package whose Python is its manifest and nothing else is **knowledge-only** — legitimate, and
the majority: thirteen of the twenty-one shipped today load no module at run time. The tell is
`PROVIDES`, not the presence of a file. It used to be the absence of `__init__.py`, and that
stopped being true when every package gained a manifest.

# The family is the second segment of the name, and it is declared nowhere else

`agent.loader` walks ONE level under `packages/` and reads the family off the **name**. It used to
be a directory, and that was a second place for the same fact: a package's distribution said
`orexis-capability-market` while its path said `capability/market`, and nothing held the two
together. A package can no longer be filed under one family and published under another, because
there is only one statement to make. See
[a-package-is-its-name](/decisions/a-package-is-its-name.md).

`packages/` itself is a **plain directory** — somewhere to keep projects, not somewhere to import
from. Each package owns a top-level module of its own, so there is no shared root to join and
none to shut anybody out of. Nothing enumerates the families; `KINDS` in `assembly/loader.py` fixes only the **order they merge in**, for
determinism in logs and diffs. A family invented tomorrow is found without editing anything — it
merely sorts after the named ones.

| family | borne by | what having one means |
|---|---|---|
| `capability` | an **agent** | `ag:hasCapability` on the agent |
| `transport`, `codec`, `scaling` | a **binding** | a predicate on the **sensor** |
| `part`, `plant`, `bus`, `tool` | nothing — knowledge only | a model others are instances of |

There was a `core` family and it held one member, forever: the base vocabulary every other
package layers on and nothing can remove. That is not a package, it is the base, and it lives in
`agent/` beside the code that reads it. Every family left is one an agent can hold **zero**
members of, which is what "a package is optional" always meant and now says.

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

# A package is not a capability

**A directory is a package**, and one package may provide several abilities — the market's
provides three. What an ability IS, what separates its members, and the premise that hands it to
an agent are all [capability](/domain/capability.md)'s.

What belongs here is the consequence for the tree: nothing about a directory says which abilities
it carries, so `PROVIDES` in `__init__.py` is the only registration, and a directory with none is
knowledge and nothing else.

# `agent/` is the container: it loads packages and assembles the layers, and it is not one

The container is the one thing **not discovered**, because it is what discovers — a record the
loader prepends rather than a directory it finds. It carries the same four filenames a package
carries (`ontology.ttl`, `shapes.ttl`, `rules.ru`, and Python), so every reader reaches it
without knowing it is special; what it is not is a FAMILY, since `packages/kernel/` is not a
directory anyone can add a sibling to.

**The kernel itself is three packages in the one tree** — the three rows of
[layered-by-timescale-and-interruptibility](/decisions/layered-by-timescale-and-interruptibility.md),
each ONE package named for its row — not a family with members, which is why the name has
two segments where a granted package has three:
`packages/orexis-reactive/` (the queue and the one executing thread),
`packages/orexis-progression/` (the ledger, the patience, the scheduler and the store
engine) and `packages/orexis-deliberation/` (the belief base, the desires and the
search). Each imports only the layers beneath it; what a lower layer has to say to an upper
one it says as an EVENT through the choir, and `agent/` — the `Agent` object, the choir, the
`Module` contract, genesis, validation — is what assembles the three into a process. See
[a-layer-is-a-package-and-need-loads-it](/decisions/a-layer-is-a-package-and-need-loads-it.md).

Capability Python used to live under `agent/`, so the tree itself showed which of it a runtime
loads. **It does not show that now** — `packages/orexis-capability-market/` and `packages/orexis-part-dht11/`
look identical. The contracts carry the boundary alone:

- `lint-imports` holds `packages` away from `onboarding`, onboarding away from nothing, and —
  since the mind came home — **`agent` away from every GRANTED package**: the container loads
  them and never reaches into one. That contract could not be stated while three capability
  packages held the mind, and the violations were not theoretical. What it does import is the
  three LAYERS, carried by its own declared dependencies until #455, and
  `tests/test_layering.py` finds them by family rather than by name and holds each to importing
  only the layers beneath it;
- but it binds **Python and nothing else**, and the kernel does still reach into a package's
  *vocabulary*, across its code, its shapes, its ontology's prefix block and the desire
  derivation. That is debt rather than a permitted exception — **the kernel names no package's
  word**, in RDF as in Python, and the remaining occurrences are tolerated while they are worked
  off. `tests/test_kernel_namespaces.py` is the second contract and the count of record: every
  spelled-out IRI allowlisted with what removes it, a new one failing the suite, and an entry
  that has stopped occurring failing it too, so the number can only fall to zero (#334 — twenty-one
  keys when the ratchet landed, eighteen since #339 retired the reflex, fourteen since #331 moved
  the freshness want into the package whose equipment its premise is). See
  [the-kernel-names-no-package-word](/decisions/the-kernel-names-no-package-word.md) for why the
  rule has no exceptions and which of the survivors are dangerous rather than merely untidy;
- the `Containerfile` decides what reaches an image by naming two trees and not a third, with
  `tests/test_layout.py` failing if a `COPY onboarding/` appears.

The import contract and the `Containerfile` were always the real enforcement. The layout was a
reminder, and the reminder is gone. The ratchet is newer than either, and it is there because
what the kernel imports was watched from the day the mind came home while what it SAYS was not.

**And "optional" is now a test rather than a sentence.**
`test_the_kernel_stands_alone_with_no_packages_at_all` builds with `packages/` absent and gets
the kernel alone — a working one. Narrower than it sounds and deliberately: every shipped world
names `water:`, `mqtt:` and `part:` terms and would not validate. The claim is that the thing
which loads packages does not need one. See
[the-mind-is-not-a-package](/decisions/the-mind-is-not-a-package.md).

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
