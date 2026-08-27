---
type: Domain Concept
title: Service — something a package offers, that nothing grants
description: >-
  A thing one package makes available for others to use, keyed by the CONTRACT TYPE wherever
  one can be imported. Distinguished from a capability by how it comes to exist: a capability
  is derived from a premise the world states, so an agent may or may not hold one; a service
  simply exists for any agent whose build includes the package that offers it. Offered with
  `@provides` in a manifest, needed with `@requires` on a class, and handed over as an
  attribute resolved on first touch.
---

# What it is

A **service** is something one package offers for other packages to use — a store, a sink, a
client, a registry — reached by its term through the agent that owns it.

The distinction that matters is **how it comes to exist**. A [capability](/domain/capability.md)
is derived: the world states a premise, genesis works out who qualifies, and an agent may hold it
or not. A service is not derived and not granted. It exists for any agent whose build includes
the package offering it, and there is no fact in any world that decides otherwise.

That is why it needs its own word. Calling a series sink a capability would put it through
machinery built for a question it does not raise — *which agents qualify?* — and the honest
answer for a sink is *all of them, or none, depending on what was installed*.

# What it is not

- **Not a capability.** No premise grants it, no `rules.ru` derives it, and no world can refuse
  one agent a service another agent has.
- **Not a [module](/domain/choir.md) answering a question.** The choir collects from everyone who
  has an opinion; a service is one thing, looked up. Fan-in where the choir is fan-out.
- **Not a store, though a store may be offered as one.** The agent owns its stores today —
  beliefs, desires, intentions — and reaches them by attribute. Offering one as a service is what
  would let a package bring a store of its own, which nothing yet does.

# Where it sits

Three ways a package reaches another package's work, and a service is the third:

| what you want | how |
|---|---|
| everyone's opinion | `agent.ask(POINT)` — the choir |
| whoever implements an ability | `agent.provider(family)` — one member of a derived family |
| **a particular thing another package offers** | **a service, by term** |

# How to use one

Offer one from a package's manifest. The function runs when an agent first asks, never when the
manifest is read, so the import is paid only by an agent that wants it:

```python
@provides(HistoryRing)             # the CONTRACT — cheap to import, defines nothing heavy
def history(agent):
    from .ring import Ring         # the implementation, only for an agent that asks
    return Ring(agent)
```

Need one by declaring it. It arrives as an attribute named for the key — `Beliefs` becomes
`self.beliefs` — so the declaration and the use cannot drift apart:

```python
from agent.beliefs import Beliefs
from agent.metrics import Metrics

@requires(Beliefs, Metrics)
class Recorder(Module):
    def start(self):
        self.metrics.event("started", "")
```

**The key is a type wherever one can be imported.** You import the thing you want and ask for
it; the type checker follows you, and there is no parallel naming system to keep in step.
`packages -> agent` is an allowed import, so every service the kernel offers is keyed by its
class, and a package's own is keyed by the contract in its `contract` module — the one
cross-package import the layering has always allowed.

A **term** is the fallback, for a service whose contract is not an importable class. Terms
belong to [extension points](/domain/choir.md), where a point IS a declared thing in the graph;
a service is a Python object, and its type already says what it is.

**One term, one provider.** A term offered by two packages is refused at load rather than
resolved, because the alternative is settled by whichever package the filesystem yielded first.

**Asking for one nothing offers raises, naming it.** That is the opposite of
`agent.provider(family)`, which answers `None` on purpose — an agent that composed neither
member of a family simply cannot do that thing. A module that declared `@requires` has said it
cannot work without one, so silence would be wrong twice: at the point of use, far from the
declaration, and indistinguishable from a service that returned nothing.

# What the kernel offers

Seven, and every agent has all of them, each under its own class: `Beliefs`, `Desires`,
`Intentions`, `Keeper`, `Deliberator`, `Owing`, `Metrics`. They were twelve undeclared attributes
on the agent before this, which a package author had to know by having read other packages.
The attributes remain as the kernel's own wiring; a package declares what it needs.

Nothing beyond the kernel offers one yet. [#311](https://github.com/ShishkinDmitriy/orexis/issues/311),
the history ring, is the first that would.
